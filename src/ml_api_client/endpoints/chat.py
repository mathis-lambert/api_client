from ..models import ChatCompletionsRequest


class ChatEndpoint:
    def __init__(self, client):
        self.client = client

    async def get_completions(self, request: ChatCompletionsRequest):
        url = f"{self.client.base_url}/chat/completions"
        return await self.client._request("POST", url, json=request.model_dump())
