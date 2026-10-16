"""Simple chunking helpers for RAG indexing."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable


MAX_CHARS = 2000
OVERLAP = 200


def _split_with_overlap(text: str, max_chars: int = MAX_CHARS, overlap: int = OVERLAP) -> list[str]:
    """Split long text into overlapping windows."""
    chunks: list[str] = []
    start = 0
    text = text.strip()

    while start < len(text):
        end = min(start + max_chars, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(0, end - overlap)

    return chunks


def split_text(text: str, max_chars: int = MAX_CHARS, overlap: int = OVERLAP) -> list[str]:
    """Chunk text using simple markdown-aware separators."""
    text = text.strip()
    if not text:
        return []

    if len(text) <= max_chars:
        return [text]

    separators = ["\n## ", "\n### ", "\n\n", "\n"]
    parts = [text]

    for sep in separators:
        new_parts: list[str] = []
        for part in parts:
            if len(part) <= max_chars:
                new_parts.append(part)
                continue
            split_parts = part.split(sep)
            if len(split_parts) == 1:
                new_parts.append(part)
                continue

            rebuilt: list[str] = []
            for i, item in enumerate(split_parts):
                if i == 0:
                    rebuilt.append(item)
                else:
                    rebuilt.append(sep.lstrip("\n") + item)

            new_parts.extend(rebuilt)
        parts = new_parts

    chunks: list[str] = []
    buffer = ""

    for part in parts:
        part = part.strip()
        if not part:
            continue

        candidate = f"{buffer}\n\n{part}".strip() if buffer else part
        if len(candidate) <= max_chars:
            buffer = candidate
        else:
            if buffer:
                chunks.append(buffer)
            if len(part) <= max_chars:
                buffer = part
            else:
                chunks.extend(_split_with_overlap(part, max_chars=max_chars, overlap=overlap))
                buffer = ""

    if buffer:
        chunks.append(buffer)

    return chunks


def chunk_file(path: Path) -> list[dict]:
    """Read a file and return chunk records with metadata."""
    text = path.read_text(encoding="utf-8", errors="ignore")
    chunks = split_text(text)

    return [
        {
            "text": chunk,
            "metadata": {
                "source": str(path),
                "chunk_index": idx,
                "file_type": path.suffix.lstrip(".") or "unknown",
            },
        }
        for idx, chunk in enumerate(chunks)
    ]


def supported_files(docs_dir: Path) -> Iterable[Path]:
    """Yield supported files under docs_dir."""
    patterns = ("*.md", "*.py", "*.yaml", "*.yml", "*.sh")
    for pattern in patterns:
        yield from docs_dir.rglob(pattern)
