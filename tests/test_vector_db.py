import pytest


@pytest.mark.asyncio
async def test_list_collections(api_client, env_variables):
    response = await api_client.vector_db.list_vector_stores()
    assert "data" in response
