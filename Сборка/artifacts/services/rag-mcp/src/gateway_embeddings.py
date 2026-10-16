"""Custom ChromaDB embedding function using gateway /v1/embeddings."""

import json
import os

import httpx
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings

GATEWAY_URL = "http://127.0.0.1:8000/v1/embeddings"
EMBEDDING_MODEL = "qwen3-embedding"


def _load_gateway_token() -> str:
    """Load one gateway token from LLM_GATEWAY_TOKENS env JSON."""
    raw = os.environ.get("LLM_GATEWAY_TOKENS", "").strip()
    if not raw:
        raise RuntimeError("LLM_GATEWAY_TOKENS env var is not set for rag-mcp")

    try:
        token_map = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"LLM_GATEWAY_TOKENS is invalid JSON: {exc}") from exc

    if not isinstance(token_map, dict) or not token_map:
        raise RuntimeError("LLM_GATEWAY_TOKENS must be a non-empty JSON object")

    # Use the first available token for server-to-server embeddings calls.
    return next(iter(token_map.keys()))


class GatewayEmbeddingFunction(EmbeddingFunction):
    """Embedding function that calls gateway /v1/embeddings endpoint."""

    def __init__(
        self,
        gateway_url: str = GATEWAY_URL,
        model: str = EMBEDDING_MODEL,
        timeout: float = 120.0,
    ):
        self._gateway_url = gateway_url
        self._model = model
        self._timeout = timeout
        self._token = _load_gateway_token()

    def __call__(self, input: Documents) -> Embeddings:
        """Embed a list of documents via gateway."""
        payload = {
            "model": self._model,
            "input": input,
            "encoding_format": "float",
        }

        headers = {
            "Authorization": f"Bearer {self._token}",
        }

        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(self._gateway_url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        sorted_data = sorted(data["data"], key=lambda x: x["index"])
        return [item["embedding"] for item in sorted_data]
