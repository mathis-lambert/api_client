import asyncio
import warnings
from typing import Any, AsyncGenerator, Dict

import aiohttp

from ..models import ChatCompletionsRequest


class ChatEndpoint:
    def __init__(self, client):
        self.client = client
        self.max_stream_retries = 3
        self.retry_delay_base = 1.0  # Base delay in seconds

    async def get_completions(self, request: ChatCompletionsRequest) -> Dict[str, Any]:
        """
        Get chat completions using the non-streaming endpoint.
        """
        url = f"{self.client.base_url}/chat/completions"

        if request.stream:
            warnings.warn(
                "streaming is set to True, but you are using the non-streaming endpoint.",
                stacklevel=2,
            )

        request.stream = False
        return await self.client._request("POST", url, json=request.model_dump())

    async def get_streaming_completions(
        self, request: ChatCompletionsRequest
    ) -> AsyncGenerator[bytes, None]:
        """
        Get chat completions using streaming, with automatic reconnection on failure.
        Yields each raw chunk of the response as bytes without any parsing.
        """
        if not request.stream:
            warnings.warn(
                "streaming is set to False, but you are using the streaming endpoint.",
                stacklevel=2,
            )

        request.stream = True
        url = f"{self.client.base_url}/chat/completions"

        # Nombre total d'essais
        attempts = 0
        last_job_id = None  # Pour reprendre là où la connexion s'était arrêtée

        while True:
            try:
                headers = {}
                if self.client.api_key:
                    headers["X-ML-API-Key"] = self.client.api_key
                if self.client.auth_token:
                    headers["Authorization"] = f"Bearer {self.client.auth_token}"

                # Ajout de l'en-tête de reprise si nécessaire
                if last_job_id:
                    headers["X-Resume-From"] = last_job_id

                request_data = request.model_dump()

                # Initialisation automatique de la session si nécessaire
                if self.client.session is None or self.client.session.closed:
                    self.client.session = aiohttp.ClientSession(
                        timeout=self.client.timeout
                    )

                async with self.client.session.post(
                    url, headers=headers, json=request_data, timeout=self.client.timeout
                ) as response:
                    response.raise_for_status()

                    # Connexion établie : on réinitialise le compteur d'essais
                    attempts = 0

                    async for line in response.content.iter_any():
                        if line:  # Skip empty lines but don't decode or parse
                            yield line  # Pass through raw bytes directly

                # Si le flux se termine normalement, on sort de la boucle
                break

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                attempts += 1
                if attempts > self.max_stream_retries:
                    raise ConnectionError(
                        f"Maximum stream retry attempts ({self.max_stream_retries}) exceeded: {str(e)}"
                    )

                # Backoff exponentiel avec jitter
                delay = self.retry_delay_base * (2 ** (attempts - 1))
                jitter = delay * 0.1 * (asyncio.get_event_loop().time() % 1.0)
                total_delay = delay + jitter

                self.client.logger.warning(
                    f"Stream connection error, retrying in {total_delay:.2f}s (attempt {attempts}/{self.max_stream_retries}): {str(e)}"
                )

                # En cas d'erreur d'authentification, tenter de rafraîchir le token
                if isinstance(e, aiohttp.ClientResponseError) and e.status == 401:
                    if self.client.username and self.client.password:
                        try:
                            self.client.logger.info(
                                "Stream token expired, refreshing authentication..."
                            )
                            await self.client.auth.login(
                                username=self.client.username,
                                password=self.client.password,
                                expires_in=1,
                            )
                        except Exception as auth_error:
                            self.client.logger.error(
                                f"Failed to refresh authentication: {auth_error}"
                            )

                await asyncio.sleep(total_delay)

    async def stream(
        self, request: ChatCompletionsRequest
    ) -> AsyncGenerator[str, None]:
        """
        Streams raw chunks decoded as UTF-8 strings without any parsing.
        Simply relays the data for client-side processing.
        """
        request.stream = True

        async for raw_chunk in self.get_streaming_completions(request):
            yield raw_chunk.decode("utf-8")  # Just decode bytes to string, no parsing
