from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------
# Authentication
# ---------------


class Body_login_v1_auth_token_post(BaseModel):
    username: str
    password: str
    expires_in: int = 30


class GetTokenResponse(BaseModel):
    access_token: str
    token_type: str


class ApiKeyEntry(BaseModel):
    api_key: str
    user_id: str
    created_at: datetime
    expires_at: Optional[datetime] = None


class GetApiKeyRequestBody(BaseModel):
    expires_in: Optional[int] = None


class GetApiKeyResponse(BaseModel):
    api_key: str
    api_key_id: str
    expires_at: Optional[str]


class DeleteApiKeyResponse(BaseModel):
    msg: str
    success: bool


class VerifyResponse(BaseModel):
    msg: str
    user: Dict[str, Any]


class HTTPValidationError(BaseModel):
    detail: List[Dict[str, Any]]


# ---------------
# Chat Completions
# ---------------


class ToolCallFunction(BaseModel):
    name: str
    arguments: str


class ToolCall(BaseModel):
    id: str
    type: str
    function: ToolCallFunction


class ChatMessage(BaseModel):
    role: str
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    refusal: Optional[str] = None
    annotations: List[Dict[str, Any]] = Field(default_factory=list)
    reasoning_content: Optional[str] = None


class Message(BaseModel):
    role: str
    content: str


class TokenDetails(BaseModel):
    cached_tokens: int = 0
    audio_tokens: int = 0


class CompletionTokenDetails(BaseModel):
    reasoning_tokens: int = 0
    audio_tokens: int = 0
    accepted_prediction_tokens: int = 0
    rejected_prediction_tokens: int = 0


class ChatUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    prompt_tokens_details: TokenDetails = Field(
        default_factory=lambda: TokenDetails(cached_tokens=0, audio_tokens=0)
    )
    completion_tokens_details: CompletionTokenDetails = Field(
        default_factory=lambda: CompletionTokenDetails(
            reasoning_tokens=0,
            audio_tokens=0,
            accepted_prediction_tokens=0,
            rejected_prediction_tokens=0,
        )
    )


class ChatCompletionChoice(BaseModel):
    index: int
    message: ChatMessage
    logprobs: Optional[Dict[str, Any]] = None
    finish_reason: Optional[str] = None


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: ChatUsage
    service_tier: str = "default"
    system_fingerprint: Optional[str] = None


class ChatCompletionsRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    model: str
    messages: Optional[List[Message]] = None
    prompt: Optional[str] = None
    input: Optional[str] = None
    history: Optional[List[Message]] = None
    stream: bool = False
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Any] = None


# ---------------
# Embeddings
# ---------------


class EmbeddingData(BaseModel):
    object: str = "embedding"
    embedding: List[float]
    index: int


class EmbeddingsUsage(BaseModel):
    prompt_tokens: int = 0
    total_tokens: int = 0


class EmbeddingsResponse(BaseModel):
    id: str
    object: str = "list"
    model: str
    data: List[EmbeddingData]
    usage: EmbeddingsUsage


class EmbeddingsRequest(BaseModel):
    input: List[str]
    model: str


# ---------------
# Models
# ---------------


class Model(BaseModel):
    id: str
    object: str = "model"
    owned_by: Optional[str] = None


class ListModelsResponse(BaseModel):
    object: str = "list"
    data: List[Model]


# ---------------
# Vector Stores
# ---------------


class VectorStore(BaseModel):
    id: str
    object: str = "vector_store"
    name: str
    created_at: int
    usage_bytes: int = 0


class CreateVectorStoreRequest(BaseModel):
    name: str


class CreateVectorStoreResponse(BaseModel):
    id: str
    object: str = "vector_store"
    name: str
    created_at: int
    usage_bytes: int = 0


class ListVectorStoresResponse(BaseModel):
    data: List[VectorStore]


class VectorStoreSearchRequest(BaseModel):
    query: str
    model: str
    limit: int = 5
