import pytest

from ml_api_client.models import EmbeddingsRequest


@pytest.mark.asyncio
async def test_get_embeddings(api_client, env_variables):
    request = EmbeddingsRequest(chunks=["Hello, world!"], model="mistral-embed")
    response = await api_client.embeddings.get_embeddings(request)
    assert "embeddings" in response


# Ajoutez d'autres tests pour les méthodes d'embeddings...
