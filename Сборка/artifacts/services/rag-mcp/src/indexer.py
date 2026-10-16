"""Batch index documents into ChromaDB using gateway-backed embeddings."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import chromadb

from chunker import chunk_file, supported_files
from gateway_embeddings import GatewayEmbeddingFunction

COLLECTION_NAME = "lab_docs"
STATUS_FILE = "index_status.json"


def build_index(docs_dir: Path, chroma_dir: Path) -> dict:
    start_ts = time.time()

    client = chromadb.PersistentClient(path=str(chroma_dir))
    embedding_fn = GatewayEmbeddingFunction()
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
    )

    all_files = sorted(supported_files(docs_dir))
    total_chunks = 0
    total_files = 0

    for file_path in all_files:
        records = chunk_file(file_path)
        if not records:
            continue

        ids = [f"{file_path.relative_to(docs_dir)}::chunk::{r['metadata']['chunk_index']}" for r in records]
        documents = [r["text"] for r in records]
        metadatas = [r["metadata"] for r in records]

        collection.add(ids=ids, documents=documents, metadatas=metadatas)
        total_chunks += len(records)
        total_files += 1
        print(f"Indexed {file_path} -> {len(records)} chunks")

    duration = round(time.time() - start_ts, 2)
    status = {
        "collection": COLLECTION_NAME,
        "docs_dir": str(docs_dir),
        "chroma_dir": str(chroma_dir),
        "files_indexed": total_files,
        "chunks_indexed": total_chunks,
        "embedding_model": "qwen3-embedding",
        "duration_sec": duration,
        "indexed_at_epoch": int(time.time()),
    }

    status_path = Path(__file__).with_name(STATUS_FILE)
    status_path.write_text(json.dumps(status, indent=2, ensure_ascii=False), encoding="utf-8")

    print("-" * 72)
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Files indexed: {total_files}")
    print(f"Chunks indexed: {total_chunks}")
    print(f"Collection count: {collection.count()}")
    print(f"Status file: {status_path}")
    print(f"Time: {duration}s")

    return status


def main() -> None:
    parser = argparse.ArgumentParser(description="Index documents into ChromaDB")
    parser.add_argument("--docs-dir", default="/home/vladimir/rag-mcp-server/docs")
    parser.add_argument("--chroma-dir", default="/home/vladimir/rag-data/chroma")
    args = parser.parse_args()

    build_index(Path(args.docs_dir), Path(args.chroma_dir))


if __name__ == "__main__":
    main()
