"""RAG MCP server over streamable-http using ChromaDB + gateway embeddings."""

from __future__ import annotations

import json
from pathlib import Path

import chromadb
from mcp.server.fastmcp import FastMCP

from gateway_embeddings import GatewayEmbeddingFunction

CHROMA_DIR = "/home/vladimir/rag-data/chroma"
COLLECTION_NAME = "lab_docs"
STATUS_FILE = Path("/home/vladimir/rag-mcp-server/index_status.json")
DOCS_ROOT = Path("/home/vladimir/rag-mcp-server/docs").resolve()

mcp = FastMCP(
    "Lab RAG Server",
    host="0.0.0.0",
    port=8100,
    streamable_http_path="/mcp",
)

chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
embedding_fn = GatewayEmbeddingFunction()
collection = chroma_client.get_or_create_collection(
    name=COLLECTION_NAME,
    embedding_function=embedding_fn,
)


def _resolve_doc_path(name_or_path: str) -> Path:
    raw = Path(name_or_path.strip())
    candidate = raw if raw.is_absolute() else (DOCS_ROOT / raw)
    resolved = candidate.resolve()

    try:
        resolved.relative_to(DOCS_ROOT)
    except ValueError:
        raise ValueError("Access denied: path must stay inside docs corpus.")

    if not resolved.exists():
        raise FileNotFoundError(f"Document not found: {name_or_path}")

    if not resolved.is_file():
        raise ValueError(f"Path is not a file: {name_or_path}")

    return resolved


def _extract_markdown_section(text: str, heading_query: str) -> str:
    query = heading_query.strip().lower()
    if not query:
        raise ValueError("Heading query must not be empty.")

    lines = text.splitlines()
    start_idx = None
    start_level = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue

        level = len(stripped) - len(stripped.lstrip("#"))
        title = stripped[level:].strip().lower()

        if query == title or query in title:
            start_idx = i
            start_level = level
            break

    if start_idx is None:
        raise ValueError(f"Heading not found: {heading_query}")

    end_idx = len(lines)
    for i in range(start_idx + 1, len(lines)):
        stripped = lines[i].strip()
        if not stripped.startswith("#"):
            continue

        level = len(stripped) - len(stripped.lstrip("#"))
        if level <= start_level:
            end_idx = i
            break

    section = "\n".join(lines[start_idx:end_idx]).strip()
    if not section:
        raise ValueError(f"Section is empty: {heading_query}")

    return section


def _format_results(results: dict, top_k: int) -> str:
    docs = (results.get("documents") or [[]])[0]
    metas = (results.get("metadatas") or [[]])[0]
    distances = (results.get("distances") or [[]])[0]

    if not docs:
        return "No results found."

    lines = []
    for i, doc in enumerate(docs[:top_k], start=1):
        meta = metas[i - 1] if i - 1 < len(metas) else {}
        distance = distances[i - 1] if i - 1 < len(distances) else None
        lines.append(
            "\n".join(
                [
                    f"Result {i}",
                    f"source: {meta.get('source', 'unknown')}",
                    f"chunk_index: {meta.get('chunk_index', 'unknown')}",
                    f"file_type: {meta.get('file_type', 'unknown')}",
                    f"distance: {distance}",
                    "text:",
                    doc,
                ]
            )
        )

    return "\n\n" + ("\n" + ("-" * 72) + "\n\n").join(lines)


@mcp.tool()
def search_docs(query: str, top_k: int = 5) -> str:
    """Search indexed lab documentation by semantic similarity."""
    if not query.strip():
        return "Query must not be empty."

    results = collection.query(query_texts=[query], n_results=top_k)
    return _format_results(results, top_k=top_k)


@mcp.tool()
def get_doc_section(name_or_path: str, heading: str) -> str:
    """Read an exact Markdown section from a document inside the docs corpus."""
    if not name_or_path.strip():
        return "Document path must not be empty."
    if not heading.strip():
        return "Heading must not be empty."

    try:
        doc_path = _resolve_doc_path(name_or_path)
        text = doc_path.read_text(encoding="utf-8")
        section = _extract_markdown_section(text, heading)
    except Exception as exc:
        return f"Error: {exc}"

    return "\n".join(
        [
            f"source: {doc_path}",
            f"heading: {heading}",
            "section:",
            section,
        ]
    )


@mcp.tool()
def grep_doc(name_or_path: str, pattern: str) -> str:
    """Return exact matching lines from a document inside the docs corpus."""
    if not name_or_path.strip():
        return "Document path must not be empty."
    if not pattern.strip():
        return "Pattern must not be empty."

    try:
        doc_path = _resolve_doc_path(name_or_path)
        lines = doc_path.read_text(encoding="utf-8").splitlines()
        matches = [line for line in lines if pattern.lower() in line.lower()]
    except Exception as exc:
        return f"Error: {exc}"

    if not matches:
        return f"No matches found for pattern: {pattern}"

    return "\n".join(
        [f"source: {doc_path}", f"pattern: {pattern}", "matches:"] + matches
    )


@mcp.tool()
def list_collections() -> str:
    """List available ChromaDB collections."""
    items = chroma_client.list_collections()
    normalized = []

    for item in items:
        name = getattr(item, "name", None) or str(item)
        try:
            coll = chroma_client.get_collection(name=name, embedding_function=embedding_fn)
            count = coll.count()
        except Exception as exc:
            count = f"error: {exc}"
        normalized.append({"name": name, "count": count})

    return json.dumps(normalized, indent=2, ensure_ascii=False)


@mcp.tool()
def index_status() -> str:
    """Show latest indexing status."""
    if not STATUS_FILE.exists():
        return "index_status.json not found."

    return STATUS_FILE.read_text(encoding="utf-8")


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
