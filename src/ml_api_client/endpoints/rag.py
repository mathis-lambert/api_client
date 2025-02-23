from ..models import RagEncodeRequest, RagRetrieveRequest


class RAGEndpoint:
    def __init__(self, client):
        self.client = client

    async def encode(self, collection_name: str, request: RagEncodeRequest):
        url = f"{self.client.base_url}/rag/encode/{collection_name}"
        return await self.client._request("POST", url, json=request.model_dump())

    async def retrieve(self, collection_name: str, request: RagRetrieveRequest):
        url = f"{self.client.base_url}/rag/retrieve/{collection_name}"
        return await self.client._request("POST", url, json=request.model_dump())
