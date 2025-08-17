from typing import Optional

from ..models import DeleteApiKeyResponse, GetApiKeyResponse


class AuthEndpoint:
    def __init__(self, client):
        self.client = client

    async def login(
        self, username: str = None, password: str = None, expires_in: int = 30
    ):
        """
        Allows a user to log in and obtain an authentication token.
        If username and password are not provided, the method will use the credentials
        stored in the APIClient instance, you can set it up with APIClient(username="...", password="...")
        or just pass them to this method

        :param username:
        :param password:
        :param expires_in:
        :return:
        """
        url = f"{self.client.base_url}/auth/token"

        if not username or not password:
            username = self.client.username
            password = self.client.password

        # OAuth2 password flow uses form-encoded body
        data = {"username": username, "password": password, "expires_in": expires_in}
        response = await self.client._request("POST", url, data=data)
        # Stocker le jeton d'authentification dans l'instance de APIClient
        self.client.auth_token = response["access_token"]
        return response

    async def generate_api_key(
        self,
        username: str = None,
        password: str = None,
        expires_in: Optional[int] = None,
        raise_on_error: bool = True,
    ) -> GetApiKeyResponse:
        # Vérifier si l'utilisateur est authentifié
        if not self.client.auth_token:
            if raise_on_error:
                raise PermissionError("User must be logged in to generate an API key.")
            else:
                if not username or not password:
                    username = self.client.username
                    password = self.client.password

                await self.login(username, password)

        self.client.logger.info(f"Auth Token : {self.client.auth_token}")
        self.client.logger.info(f"Generating API key for user {username}")

        url = f"{self.client.base_url}/auth/api-key"
        data = {"expires_in": expires_in}
        return await self.client._request("POST", url, json=data)

    async def list_api_keys(self):
        url = f"{self.client.base_url}/auth/api-keys"
        return await self.client._request("GET", url)

    async def delete_api_key(self, api_key_id: str) -> DeleteApiKeyResponse | dict:
        url = f"{self.client.base_url}/auth/api-key/{api_key_id}"
        return await self.client._request("DELETE", url)

    async def register(self, username: str, email: str, password: str):
        # Registration endpoint not present in new OpenAPI; keeping method for compatibility
        url = f"{self.client.base_url}/auth/register"
        data = {"username": username, "email": email, "password": password}
        return await self.client._request("POST", url, json=data)

    async def verify_token(self):
        url = f"{self.client.base_url}/auth/verify"
        return await self.client._request("GET", url)
