from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional
from openai.types.chat import ChatCompletionMessageParam

from pydantic import BaseModel, ConfigDict


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


class TextGenerationRequest(BaseModel):
    model: str
    messages: Iterable[ChatCompletionMessageParam]
    stream: Optional[bool] = None

    model_config = ConfigDict(extra="allow")


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
