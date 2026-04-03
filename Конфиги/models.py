"""
Pydantic-модели запросов и ответов LLM Gateway.

Chat: ChatMessage, ReasoningConfig, ChatCompletionRequest.
Embeddings: EmbeddingsRequest, EmbeddingItem, EmbeddingsUsage,
            EmbeddingsResponse, NormalizedEmbeddingsInput,
            OllamaEmbedRequest, ValidatedOllamaEmbedResult.
"""

from dataclasses import dataclass
from typing import Optional, Literal, Union

from pydantic import BaseModel, Field, ConfigDict

from . import (
    MAX_TEMPERATURE, MAX_PENALTY, MIN_PENALTY,
    MAX_REPEAT_PENALTY, MAX_NUM_CTX,
)


# ---------------------------------------------------------------------------
# Chat models (P2, P3)
# ---------------------------------------------------------------------------


class ChatMessage(BaseModel):
    """
    Сообщение чата. extra="ignore" — неизвестные поля молча отбрасываются.
    content: str | list (multimodal vision) | None (tool_calls msg).
    """
    model_config = ConfigDict(extra="ignore")

    role: str
    content: Union[str, list, None] = None
    name: Optional[str] = None
    tool_calls: Optional[list] = None
    tool_call_id: Optional[str] = None


class ReasoningConfig(BaseModel):
    effort: Literal["none", "low", "medium", "high"] = "none"


class ChatCompletionRequest(BaseModel):
    """extra="ignore" — неизвестные параметры от клиента молча игнорируются."""
    model_config = ConfigDict(extra="ignore")

    model: str
    messages: list[ChatMessage]
    stream: bool = False

    temperature: Optional[float] = Field(
        default=None, ge=0.0, le=MAX_TEMPERATURE)
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    frequency_penalty: Optional[float] = Field(
        default=None, ge=MIN_PENALTY, le=MAX_PENALTY)
    presence_penalty: Optional[float] = Field(
        default=None, ge=MIN_PENALTY, le=MAX_PENALTY)
    seed: Optional[int] = Field(default=None, ge=0)

    # P3: stop, tools, tool_choice
    stop: Union[str, list, None] = Field(default=None)
    tools: Optional[list] = Field(default=None)
    tool_choice: Union[str, dict, None] = Field(default=None)

    # Reasoning (Этап 2)
    reasoning: Optional[ReasoningConfig] = None
    reasoning_effort: Optional[str] = None

    # Depth-over-Speed (Этап 2)
    num_ctx: Optional[int] = Field(default=None, ge=1, le=MAX_NUM_CTX)
    num_gpu: Optional[int] = Field(default=None, ge=0)
    num_batch: Optional[int] = Field(default=None, ge=1)

    # Ollama-native (Этап 3)
    repeat_penalty: Optional[float] = Field(
        default=None, ge=0.0, le=MAX_REPEAT_PENALTY)
    repeat_last_n: Optional[int] = Field(default=None, ge=-1)


# ---------------------------------------------------------------------------
# Embeddings models (Этап 9A)
# ---------------------------------------------------------------------------


class EmbeddingsRequest(BaseModel):
    """OpenAI-compatible embeddings request."""
    model_config = ConfigDict(extra="ignore")

    model: str
    input: Union[str, list[str]]
    encoding_format: Optional[str] = None
    dimensions: Optional[int] = Field(default=None, ge=1)
    user: Optional[str] = None


class EmbeddingItem(BaseModel):
    object: str = "embedding"
    embedding: list[float]
    index: int


class EmbeddingsUsage(BaseModel):
    prompt_tokens: int
    total_tokens: int


class EmbeddingsResponse(BaseModel):
    object: str = "list"
    data: list[EmbeddingItem]
    model: str
    usage: EmbeddingsUsage


@dataclass
class NormalizedEmbeddingsInput:
    model: str
    inputs: list[str]
    dimensions: Optional[int]
    user: Optional[str]


@dataclass
class OllamaEmbedRequest:
    model: str
    input: list[str]
    dimensions: Optional[int] = None


@dataclass
class ValidatedOllamaEmbedResult:
    model: str
    embeddings: list[list[float]]
    prompt_eval_count: int
