class VectorDBEndpoint:
    def __init__(self, client):
        self.client = client

    async def list_collections(self):
        url = f"{self.client.base_url}/vector-db/collections"
        return await self.client._request("GET", url)

    async def get_collection(self, collection_name: str):
        url = f"{self.client.base_url}/vector-db/collections/{collection_name}"
        return await self.client._request("GET", url)
