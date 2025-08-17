class ModelsEndpoint:
    def __init__(self, client):
        self.client = client

    async def list_models(self):
        url = f"{self.client.base_url}/models/"
        return await self.client._request("GET", url)

    async def retrieve_model(self, provider: str, model_id: str):
        url = f"{self.client.base_url}/models/{provider}/{model_id}"
        return await self.client._request("GET", url)
