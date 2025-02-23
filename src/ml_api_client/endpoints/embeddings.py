from ..models import EmbeddingsRequest


class EmbeddingsEndpoint:
    def __init__(self, client):
        self.client = client

    async def get_embeddings(self, request: EmbeddingsRequest):
        url = f"{self.client.base_url}/embeddings"
        return await self.client._request("POST", url, json=request.model_dump())
