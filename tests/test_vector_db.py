import pytest


@pytest.mark.asyncio
async def test_list_collections(api_client, env_variables):
    response = await api_client.vector_db.list_collections()
    assert "collections" in response


# Ajoutez d'autres tests pour les méthodes de la base de vecteurs...
