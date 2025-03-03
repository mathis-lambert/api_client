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
        """Ferme la session cliente si elle existe."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None

    async def _prepare_headers(self) -> Dict[str, str]:
        """Prépare les en-têtes pour la requête, avec authentification si disponible."""
        headers = {}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        elif self.api_key:
            headers["X-ML-API-Key"] = self.api_key
        return headers

    async def _request(
        self, method: str, url: str, retry: bool = True, **kwargs
    ) -> Dict[str, Any]:
        """Effectue une requête HTTP avec retry automatique en cas d'échec d'authentification."""
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout)

        headers = await self._prepare_headers()
        headers.update(kwargs.pop("headers", {}))

        try:
            async with self.session.request(
                method, url, headers=headers, **kwargs
            ) as response:
                response.raise_for_status()
                result = await response.json()
                # Réinitialisation du compteur après une requête réussie
                self.retry_count = 0
                return result

        except aiohttp.ClientResponseError as e:
            if e.status == 401 and retry and self.retry_count < self.max_retries:
                self.retry_count += 1
                self.auth_token = None
                self.logger.info(
                    f"Token expiré, nouvelle tentative d'authentification ({self.retry_count}/{self.max_retries})..."
                )
                await asyncio.sleep(self.retry_delay * self.retry_count)
                if self.username and self.password:
                    await self.auth.login(
                        username=self.username, password=self.password, expires_in=1
                    )
                    return await self._request(method, url, retry=True, **kwargs)
                else:
                    raise PermissionError(
                        "Clé API ou token d'authentification invalide."
                    )
            elif e.status == 403:
                raise PermissionError(f"Accès interdit : {e.message}")
            elif e.status == 404:
                raise ValueError(f"Ressource introuvable : {e.message}")
            else:
                raise APIError(
                    f"Erreur HTTP : {e.status} - {e.message}", status_code=e.status
                )
        except aiohttp.ClientConnectionError as e:
            raise ConnectionError(f"Erreur de connexion : {str(e)}")
        except asyncio.TimeoutError:
            raise TimeoutError(f"Délai dépassé pour la requête : {url}")

    async def __aenter__(self):
        """Initialise la session lors de l'entrée dans le contexte asynchrone."""
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Assure le nettoyage des ressources."""
        await self.close()


class APIError(Exception):
    """Exception personnalisée pour les erreurs d'API."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        self.status_code = status_code
        super().__init__(message)
