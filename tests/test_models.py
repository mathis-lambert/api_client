import pytest


@pytest.mark.asyncio
async def test_list_models(api_client, env_variables):
    response = await api_client.models.list_models()
    assert "models" in response


# Ajoutez d'autres tests pour les méthodes de modèles...
