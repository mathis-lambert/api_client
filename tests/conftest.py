import os

import pytest
import pytest_asyncio
from dotenv import load_dotenv

from ml_api_client import APIClient

# Charger les variables d'environnement à partir du fichier .env
load_dotenv()


@pytest.fixture
def env_variables():
    return {
        "API_KEY": os.getenv("API_KEY"),
        "USERNAME": os.getenv("USERNAME"),
        "PASSWORD": os.getenv("PASSWORD"),
    }


@pytest_asyncio.fixture
async def api_client(env_variables):
    client = APIClient(api_key=env_variables["API_KEY"])
    yield client
    await client.close()
