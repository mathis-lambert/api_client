import pytest


@pytest.mark.asyncio
async def test_login(api_client, env_variables):
    response = await api_client.auth.login(
        username=env_variables["USERNAME"], password=env_variables["PASSWORD"]
    )
    assert "access_token" in response


@pytest.mark.asyncio
async def test_generate_api_key(api_client, env_variables):
    response = await api_client.auth.generate_api_key(
        username=env_variables["USERNAME"],
        password=env_variables["PASSWORD"],
        raise_on_error=False,
    )
    assert "api_key" in response


# Ajoutez d'autres tests pour les méthodes d'authentification...
