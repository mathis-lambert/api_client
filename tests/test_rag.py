import pytest

from ml_api_client.models import RagEncodeRequest, RagRetrieveRequest


@pytest.mark.asyncio
async def test_encode(api_client, env_variables):
    request = RagEncodeRequest(chunks=["Hello, world!"])
    response = await api_client.rag.encode("test", request)
    assert "success" in response


@pytest.mark.asyncio
async def test_retrieve(api_client, env_variables):
    request = RagRetrieveRequest(query="Hello, world!")
    response = await api_client.rag.retrieve("test", request)
    assert "results" in response
