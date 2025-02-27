from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class ChatCompletionsRequest(BaseModel):
    model: str = "mistral-small-latest"
    input: str = "Hello, how are you?"
    prompt: str = "You are a helpful assistant."
    history: List[Dict[str, Any]] = []
    temperature: float = 0.7
    max_tokens: int = 512
    top_p: float = 1.0
    stream: bool = False


class ChatCompletionResponse(BaseModel):
    response: str
    job_id: str


class ApiKeyEntry(BaseModel):
    api_key: str
    user_id: str
    created_at: datetime
    expires_at: Optional[datetime] = None


class BaseModelCard(BaseModel):
    id: str
    capabilities: "ModelCapabilities"
    object: Optional[str] = Field(default="model")
    created: Optional[int] = None
    owned_by: Optional[str] = Field(default="mistralai")
    name: Optional[str] = Field(default="~?~unset~?~sentinel~?~")
    description: Optional[str] = Field(default="~?~unset~?~sentinel~?~")
    max_context_length: Optional[int] = Field(default=32768)
    aliases: Optional[List[str]] = Field(default_factory=list)
    deprecation: Optional[datetime] = Field(default="~?~unset~?~sentinel~?~")
    default_model_temperature: Optional[float] = Field(default="~?~unset~?~sentinel~?~")
    type: Optional[str] = Field(default="base")


class FTModelCard(BaseModel):
    id: str
    capabilities: "ModelCapabilities"
    job: str
    root: str
    object: Optional[str] = Field(default="model")
    created: Optional[int] = None
    owned_by: Optional[str] = Field(default="mistralai")
    name: Optional[str] = Field(default="~?~unset~?~sentinel~?~")
    description: Optional[str] = Field(default="~?~unset~?~sentinel~?~")
    max_context_length: Optional[int] = Field(default=32768)
    aliases: Optional[List[str]] = Field(default_factory=list)
    deprecation: Optional[datetime] = Field(default="~?~unset~?~sentinel~?~")
    default_model_temperature: Optional[float] = Field(default="~?~unset~?~sentinel~?~")
    type: Optional[str] = Field(default="fine-tuned")
    archived: Optional[bool] = Field(default=False)


class ModelCapabilities(BaseModel):
    completion_chat: Optional[bool] = Field(default=True)
    completion_fim: Optional[bool] = Field(default=False)
    function_calling: Optional[bool] = Field(default=True)
    fine_tuning: Optional[bool] = Field(default=False)
    vision: Optional[bool] = Field(default=False)


class Body_login_v1_auth_token_post(BaseModel):
    username: str
    password: str
    expires_in: int = 30


class GetApiKeyRequestBody(BaseModel):
    expires_in: Optional[int] = None


class GetApiKeyResponse(BaseModel):
    api_key: str
    expires_at: Optional[str] = None


class GetModelResponse(BaseModel):
    model: Union[BaseModelCard, FTModelCard]


class GetTokenResponse(BaseModel):
    access_token: str
    token_type: str


class HTTPValidationError(BaseModel):
    detail: List[Dict[str, Any]]


class RegisterRequestBody(BaseModel):
    username: str
    email: str
    password: str


class RegisterResponse(BaseModel):
    msg: str
    user: Dict[str, Any]


class VerifyResponse(BaseModel):
    msg: str
    user: Dict[str, Any]


class EmbeddingsRequest(BaseModel):
    chunks: List[str]
    model: str
    encoding_format: str = "float"


class EmbeddingsResponse(BaseModel):
    embeddings: List["Embedding"]
    job_id: str


class Embedding(BaseModel):
    index: int
    embedding: List[float]
    payload: Dict[str, Any]
    object: str


class RagEncodeRequest(BaseModel):
    chunks: List[str]
    model: str = "mistral-embed"
    encoding_format: str = "float"


class RagEncodeResponse(BaseModel):
    collection_name: str
    success: bool


class RagRetrieveRequest(BaseModel):
    query: str
    model: str = "mistral-embed"
    limit: int = 5


class RagRetrieveResponse(BaseModel):
    collection_name: str
    results: List["RetrieveResult"]
    success: bool


class RetrieveResult(BaseModel):
    score: float
    payload: Dict[str, Any]
