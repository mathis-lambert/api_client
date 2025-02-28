import asyncio
import logging
from typing import Any, Dict, Optional

import aiohttp
from aiohttp import ClientTimeout

from .endpoints import (
    AuthEndpoint,
    ChatEndpoint,
    EmbeddingsEndpoint,
    ModelsEndpoint,
    RAGEndpoint,
    VectorDBEndpoint,
)

# Configure logging once with all settings
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class APIClient:
    def __init__(
        self,
        base_url: str = "https://api.mathislambert.fr/v1",
        api_key: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 60,
        max_retries: int = 3,
        retry_delay: float = 0.5,
    ):
        self.base_url = base_url
        self.api_key = api_key
        self.username = username
        self.password = password
        self.auth_token = None
        self.timeout = ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.retry_count = 0

        # La session est initialisée dans __aenter__ pour la gestion du contexte asynchrone
        self.session = None

        # Initialisation des endpoints
        self.auth = AuthEndpoint(self)
        self.chat = ChatEndpoint(self)
        self.models = ModelsEndpoint(self)
        self.vector_db = VectorDBEndpoint(self)
        self.embeddings = EmbeddingsEndpoint(self)
        self.rag = RAGEndpoint(self)

        self.logger = logger

    async def close(self) -> None:
        """Close the client session if it exists."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None

    async def _request(
        self, method: str, url: str, retry: bool = True, **kwargs
    ) -> Dict[str, Any]:
        """Make an HTTP request with automatic authentication retry if needed."""
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout)

        headers = kwargs.pop("headers", {})

        if self.api_key and not self.auth_token:
            headers["X-ML-API-Key"] = self.api_key
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        logger.info(f"Headers: {headers}")
        try:
            async with self.session.request(
                method, url, headers=headers, **kwargs
            ) as response:
                logger.debug(f"Request URL: {url}")
                response.raise_for_status()
                result = await response.json()
                # Réinitialisation du compteur après un appel réussi
                self.retry_count = 0
                return result

        except aiohttp.ClientResponseError as e:
            logger.error(f"HTTP error: {e.status} - {e.message}")
            if e.status == 401 and retry:
                if self.retry_count < self.max_retries:
                    self.retry_count += 1
                    self.auth_token = None
                    self.api_key = None

                    logger.info(
                        f"Token expired, re-authenticating (attempt {self.retry_count}/{self.max_retries})..."
                    )
                    await asyncio.sleep(self.retry_delay * self.retry_count)
                    if self.username and self.password:
                        await self.auth.login(
                            username=self.username, password=self.password, expires_in=1
                        )
                        return await self._request(method, url, retry=True, **kwargs)
                    else:
                        raise PermissionError(
                            "Invalid API key or authentication token."
                        )
                else:
                    raise ConnectionError(
                        f"Maximum retry attempts ({self.max_retries}) exceeded for authentication."
                    )
            elif e.status == 403:
                raise PermissionError(f"Access forbidden: {e.message}")
            elif e.status == 404:
                raise ValueError(f"Resource not found: {e.message}", 404)
            else:
                raise APIError(
                    f"HTTP error: {e.status} - {e.message}", status_code=e.status
                )
        except aiohttp.ClientConnectionError as e:
            raise ConnectionError(f"Connection error: {str(e)}")
        except asyncio.TimeoutError:
            raise TimeoutError(f"Request timed out: {url}")

    async def __aenter__(self):
        """Initialize the session when entering async context."""
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Ensure resources are properly cleaned up."""
        await self.close()


class APIError(Exception):
    """Custom exception for API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        self.status_code = status_code
        super().__init__(message)
