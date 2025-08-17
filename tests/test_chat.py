import pytest

from ml_api_client.models import ChatCompletionsRequest


@pytest.mark.asyncio
async def test_get_completions(api_client, env_variables):
    request = ChatCompletionsRequest(
        input="This is a test! Answer 'yes' or 'no' only.", stream=False
    )
    response = await api_client.chat.get_completions(request)
    assert "choices" in response


@pytest.mark.asyncio
async def test_get_streaming_completions(api_client, env_variables):
    request = ChatCompletionsRequest(
        input="This is a streaming test! Answer 'yes' or 'no' only.", stream=True
    )
    responses = []
    await api_client.auth.login()
    async for event in api_client.chat.get_streaming_completions(request):
        responses.append(event)

    assert len(responses) > 0

    for event in responses:
        assert isinstance(event, dict)


@pytest.mark.asyncio
async def test_stream_text(api_client, env_variables):
    request = ChatCompletionsRequest(
        input="This is a streaming test! Answer 'yes' or 'no' only.", stream=True
    )
    responses = []
    async for completion in api_client.chat.stream_text(request):
        responses.append(completion)

    assert len(responses) > 0

    for chunk in responses:
        assert isinstance(chunk, str)


@pytest.mark.asyncio
async def test_invalid_model(api_client, env_variables):
    request = ChatCompletionsRequest(input="This is a test!", model="invalid_model")
    with pytest.raises(ValueError) as exc_info:
        await api_client.chat.get_completions(request)
    assert "introuvable" in str(exc_info.value).lower()
