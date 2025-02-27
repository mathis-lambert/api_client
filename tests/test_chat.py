import pytest
from aiohttp import ClientResponseError

from ml_api_client.models import ChatCompletionsRequest


@pytest.mark.asyncio
async def test_get_completions(api_client, env_variables):
    request = ChatCompletionsRequest(
        input="This is a test! Answer 'yes' or 'no' only.", stream=False
    )
    response = await api_client.chat.get_completions(request)
    assert "response" in response


@pytest.mark.asyncio
async def test_get_streaming_completions(api_client, env_variables):
    request = ChatCompletionsRequest(
        input="This is a streaming test! Answer 'yes' or 'no' only.", stream=True
    )
    responses = []
    async for response in api_client.chat.get_streaming_completions(request):
        responses.append(response)

    assert len(responses) > 0

    for response in responses:
        assert response.strip() != ""


@pytest.mark.asyncio
async def test_invalid_model(api_client, env_variables):
    request = ChatCompletionsRequest(input="This is a test!", model="invalid_model")
    with pytest.raises(ClientResponseError) as exc_info:
        await api_client.chat.get_completions(request)

    assert exc_info.value.status == 404
    assert "Not Found" in exc_info.value.message
