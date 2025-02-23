import aiohttp

from .endpoints import (
    AuthEndpoint,
    ChatEndpoint,
    EmbeddingsEndpoint,
    ModelsEndpoint,
    RAGEndpoint,
    VectorDBEndpoint,
)


class APIClient:
    def __init__(
        self, base_url: str = "https://api.mathislambert.fr/v1", api_key: str = None
    ):
        self.base_url = base_url
        self.api_key = api_key
        self.auth_token = None
        self.session = aiohttp.ClientSession()

        self.auth = AuthEndpoint(self)
        self.chat = ChatEndpoint(self)
        self.models = ModelsEndpoint(self)
        self.vector_db = VectorDBEndpoint(self)
        self.embeddings = EmbeddingsEndpoint(self)
        self.rag = RAGEndpoint(self)

    async def close(self):
        await self.session.close()

    async def _request(self, method: str, url: str, **kwargs):
        headers = kwargs.pop("headers", {})
        if self.api_key:
            headers["X-ML-API-Key"] = self.api_key
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        async with self.session.request(
            method, url, headers=headers, **kwargs
        ) as response:
            response.raise_for_status()
            return await response.json()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
