import pytest

from ml_api_client.models import EmbeddingsRequest


@pytest.mark.asyncio
async def test_get_embeddings(api_client, env_variables):
    request = EmbeddingsRequest(input=["Hello, world!"], model="mistral-embed")
    response = await api_client.embeddings.get_embeddings(request)
    assert "data" in response
