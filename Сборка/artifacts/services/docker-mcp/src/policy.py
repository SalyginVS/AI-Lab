from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class PolicyError(Exception):
    """Raised when an operation is denied by policy."""


@dataclass
class PolicyDecision:
    allowed: bool
    reason: str


class DockerPolicy:
    def __init__(self, path: str | Path = "docker-policy.yaml") -> None:
        self.path = Path(path)
        self.data = self._load()

    def _load(self) -> dict[str, Any]:
        return yaml.safe_load(self.path.read_text(encoding="utf-8"))

    def category_enabled(self, category: str) -> bool:
        return bool(self.data["categories"].get(category, {}).get("enabled", False))

    def check_category(self, category: str) -> PolicyDecision:
        if not self.category_enabled(category):
            return PolicyDecision(False, f"Category '{category}' is disabled by policy")
        return PolicyDecision(True, f"Category '{category}' is allowed")

    def check_blocked_operation(self, operation: str) -> PolicyDecision:
        blocked = set(self.data.get("blocked_operations", []))
        if operation in blocked:
            return PolicyDecision(False, f"Operation '{operation}' is blocked by policy")
        return PolicyDecision(True, f"Operation '{operation}' is not blocked")

    def check_exec_command(self, command: str) -> PolicyDecision:
        exec_cfg = self.data["categories"]["exec"]
        if not exec_cfg.get("enabled", False):
            return PolicyDecision(False, "Category 'exec' is disabled by policy")

        cmd = command.strip()
        allowlist = exec_cfg.get("command_allowlist", [])
        denylist = exec_cfg.get("command_denylist", [])

        for denied in denylist:
            if denied in cmd:
                return PolicyDecision(False, f"Command denied by denylist match: '{denied}'")

        allowed = any(cmd == allowed_cmd or cmd.startswith(allowed_cmd + " ") for allowed_cmd in allowlist)
        if not allowed:
            return PolicyDecision(False, f"Command not present in allowlist: '{cmd}'")

        return PolicyDecision(True, f"Command allowed: '{cmd}'")

    def require_category(self, category: str) -> None:
        decision = self.check_category(category)
        if not decision.allowed:
            raise PolicyError(decision.reason)

    def require_operation_allowed(self, operation: str) -> None:
        decision = self.check_blocked_operation(operation)
        if not decision.allowed:
            raise PolicyError(decision.reason)

    def require_exec_command(self, command: str) -> None:
        decision = self.check_exec_command(command)
        if not decision.allowed:
            raise PolicyError(decision.reason)


if __name__ == "__main__":
    policy = DockerPolicy("docker-policy.yaml")

    tests = [
        ("category:read", policy.check_category("read")),
        ("category:lifecycle", policy.check_category("lifecycle")),
        ("blocked:run", policy.check_blocked_operation("run")),
        ("exec:hostname", policy.check_exec_command("hostname")),
        ("exec:rm -rf /", policy.check_exec_command("rm -rf /")),
    ]

    for name, result in tests:
        print(f"{name} -> allowed={result.allowed}; reason={result.reason}")
