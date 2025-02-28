import pytest

from ml_api_client.models import ChatCompletionsRequest


@pytest.mark.asyncio
async def test_get_completions(api_client, env_variables):
    request = ChatCompletionsRequest(
        input="This is a test! Answer 'yes' or 'no' only.", stream=False
    )
    response = await api_client.chat.get_completions(request)
    api_client.logger.info(response)

    assert "response" in response


@pytest.mark.asyncio
async def test_get_streaming_completions(api_client, env_variables):
    request = ChatCompletionsRequest(
        input="This is a streaming test! Answer 'yes' or 'no' only.", stream=True
    )
    responses = []
    await api_client.auth.login()
    async for completion in api_client.chat.get_streaming_completions(request):
        api_client.logger.info(completion)
        responses.append(completion)

    assert len(responses) > 0

    for response in responses:
        assert response.strip() != ""


@pytest.mark.asyncio
async def test_stream(api_client, env_variables):
    request = ChatCompletionsRequest(
        input="This is a streaming test! Answer 'yes' or 'no' only.", stream=True
    )
    responses = []
    async for completion in api_client.chat.stream(request):
        api_client.logger.info(completion)
        responses.append(completion)

    assert len(responses) > 0

    for response in responses:
        assert response.strip() != ""


@pytest.mark.asyncio
async def test_invalid_model(api_client, env_variables):
    request = ChatCompletionsRequest(input="This is a test!", model="invalid_model")
    with pytest.raises(ValueError) as exc_info:
        await api_client.chat.get_completions(request)

    assert "resource not found" in str(exc_info.value).lower()
