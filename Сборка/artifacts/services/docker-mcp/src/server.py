from __future__ import annotations

import asyncio
from typing import Any

import docker
import uvicorn
from docker.errors import NotFound
from mcp.server.fastmcp import FastMCP

from policy import DockerPolicy


mcp = FastMCP("docker-mcp")
policy = DockerPolicy("docker-policy.yaml")
client = docker.from_env(version="auto", timeout=10)


async def docker_call(fn, *args, **kwargs):
    return await asyncio.to_thread(fn, *args, **kwargs)


def require_read(operation: str) -> None:
    policy.require_category("read")
    policy.require_operation_allowed(operation)


def require_lifecycle(operation: str) -> None:
    policy.require_category("lifecycle")
    policy.require_operation_allowed(operation)


def require_exec(command: str) -> None:
    policy.require_category("exec")
    policy.require_exec_command(command)


def get_container_sync(container_name: str):
    return client.containers.get(container_name)


async def get_container(container_name: str):
    try:
        return await docker_call(get_container_sync, container_name)
    except NotFound:
        raise ValueError(f"Container not found: {container_name}")


@mcp.tool()
async def system_info() -> dict[str, Any]:
    """Return basic Docker daemon and disk usage information."""
    require_read("system_info")

    version_info = await docker_call(client.version)
    disk_usage = await docker_call(client.df)

    containers = disk_usage.get("Containers") or []
    images = disk_usage.get("Images") or []
    volumes = disk_usage.get("Volumes") or []

    return {
        "engine_version": version_info.get("Version"),
        "api_version": version_info.get("ApiVersion"),
        "os": version_info.get("Os"),
        "arch": version_info.get("Arch"),
        "containers_count": len(containers),
        "images_count": len(images),
        "volumes_count": len(volumes),
    }


@mcp.tool()
async def list_containers(all: bool = True) -> list[dict[str, Any]]:
    """List Docker containers."""
    require_read("list_containers")

    containers = await docker_call(client.containers.list, all=all)
    result = []

    for c in containers:
        result.append(
            {
                "id": c.short_id,
                "name": c.name,
                "image": c.image.tags,
                "status": c.status,
            }
        )

    return result


@mcp.tool()
async def list_images() -> list[dict[str, Any]]:
    """List Docker images."""
    require_read("list_images")

    images = await docker_call(client.images.list)
    result = []

    for img in images:
        result.append(
            {
                "id": img.short_id,
                "tags": img.tags,
            }
        )

    return result


@mcp.tool()
async def container_inspect(container_name: str) -> dict[str, Any]:
    """Inspect a Docker container by name or ID."""
    require_read("container_inspect")

    container = await get_container(container_name)
    attrs = container.attrs

    return {
        "id": attrs.get("Id"),
        "name": attrs.get("Name"),
        "image": (attrs.get("Config") or {}).get("Image"),
        "state": attrs.get("State"),
        "host_config": attrs.get("HostConfig"),
        "network_settings": attrs.get("NetworkSettings"),
    }


@mcp.tool()
async def container_logs(container_name: str, tail: int = 100) -> dict[str, Any]:
    """Return the last N lines of container logs."""
    require_read("container_logs")

    max_tail = int(policy.data["limits"]["logs_tail_max"])
    if tail < 1:
        raise ValueError("tail must be >= 1")
    if tail > max_tail:
        raise ValueError(f"tail exceeds policy limit: {tail} > {max_tail}")

    container = await get_container(container_name)
    logs = await docker_call(container.logs, tail=tail)

    return {
        "container": container_name,
        "tail": tail,
        "logs": logs.decode("utf-8", errors="replace"),
    }


@mcp.tool()
async def container_stats(container_name: str) -> dict[str, Any]:
    """Return a one-shot stats snapshot for a container."""
    require_read("container_stats")

    container = await get_container(container_name)
    stats = await docker_call(container.stats, stream=False)

    return {
        "container": container_name,
        "cpu_stats": stats.get("cpu_stats"),
        "memory_stats": stats.get("memory_stats"),
        "pids_stats": stats.get("pids_stats"),
        "networks": stats.get("networks"),
    }


@mcp.tool()
async def stop_container(container_name: str, timeout: int = 10) -> dict[str, Any]:
    """Stop an existing container."""
    require_lifecycle("stop_container")

    container = await get_container(container_name)
    await docker_call(container.stop, timeout=timeout)
    await docker_call(container.reload)

    return {
        "container": container_name,
        "status": container.status,
        "action": "stopped",
    }


@mcp.tool()
async def start_container(container_name: str) -> dict[str, Any]:
    """Start an existing container."""
    require_lifecycle("start_container")

    container = await get_container(container_name)
    await docker_call(container.start)
    await docker_call(container.reload)

    return {
        "container": container_name,
        "status": container.status,
        "action": "started",
    }


@mcp.tool()
async def restart_container(container_name: str, timeout: int = 10) -> dict[str, Any]:
    """Restart an existing container."""
    require_lifecycle("restart_container")

    container = await get_container(container_name)
    await docker_call(container.restart, timeout=timeout)
    await docker_call(container.reload)

    return {
        "container": container_name,
        "status": container.status,
        "action": "restarted",
    }


@mcp.tool()
async def exec_command(container_name: str, command: str) -> dict[str, Any]:
    """Execute an allowed command inside a running container."""
    require_exec(command)

    container = await get_container(container_name)
    result = await docker_call(container.exec_run, command)

    output = result.output.decode("utf-8", errors="replace") if result.output else ""

    return {
        "container": container_name,
        "command": command,
        "exit_code": result.exit_code,
        "output": output,
    }


app = mcp.streamable_http_app()


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8200)
