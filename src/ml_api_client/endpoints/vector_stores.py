from ..models import (
    CreateVectorStoreRequest,
    CreateVectorStoreResponse,
    ListVectorStoresResponse,
    VectorStore,
    VectorStoreSearchRequest,
)


class VectorStoresEndpoint:
    def __init__(self, client):
        self.client = client

    # New API
    async def list_vector_stores(self) -> ListVectorStoresResponse | dict:
        url = f"{self.client.base_url}/vector_stores"
        return await self.client._request("GET", url)

    async def create_vector_store(
        self, request: CreateVectorStoreRequest
    ) -> CreateVectorStoreResponse | dict:
        url = f"{self.client.base_url}/vector_stores"
        return await self.client._request("POST", url, json=request.model_dump())

    async def get_vector_store(self, vector_store_id: str) -> VectorStore | dict:
        url = f"{self.client.base_url}/vector_stores/{vector_store_id}"
        return await self.client._request("GET", url)

    async def search_vector_store(
        self, vector_store_id: str, request: VectorStoreSearchRequest
    ) -> dict:
        url = f"{self.client.base_url}/vector_stores/{vector_store_id}/search"
        return await self.client._request("POST", url, json=request.model_dump())

    # Backward-compat aliases
    async def list_collections(self):
        return await self.list_vector_stores()

    async def get_collection(self, collection_name: str):
        return await self.get_vector_store(collection_name)
