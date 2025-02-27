import warnings

from ..models import ChatCompletionsRequest


class ChatEndpoint:
    def __init__(self, client):
        self.client = client

    async def get_completions(self, request: ChatCompletionsRequest):
        url = f"{self.client.base_url}/chat/completions"

        if request.stream:
            warnings.warn(
                "streaming is set to True, but you are using the non-streaming endpoint.",
                stacklevel=2,
            )

        request.stream = False
        return await self.client._request("POST", url, json=request.model_dump())

    async def get_streaming_completions(self, request: ChatCompletionsRequest):
        url = f"{self.client.base_url}/chat/completions"

        if not request.stream:
            warnings.warn(
                "streaming is set to False, but you are using the streaming endpoint.",
                stacklevel=2,
            )

        request.stream = True

        headers = {}
        if self.client.api_key:
            headers["X-ML-API-Key"] = self.client.api_key
        if self.client.auth_token:
            headers["Authorization"] = f"Bearer {self.client.auth_token}"

        async with self.client.session.post(
            url, headers=headers, json=request.model_dump()
        ) as response:
            response.raise_for_status()
            async for line in response.content.iter_any():
                if line:
                    yield line.decode("utf-8")
