import pytest

from ml_api_client.models import ChatCompletionsRequest


@pytest.mark.asyncio
async def test_get_completions(api_client, env_variables):
    request = ChatCompletionsRequest(
        input="This is a test ! Answer 'yes' or 'no' only."
    )
    response = await api_client.chat.get_completions(request)
    assert "response" in response


# Ajoutez d'autres tests pour les méthodes de chat...
