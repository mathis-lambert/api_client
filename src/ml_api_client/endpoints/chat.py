import asyncio
import json
import random
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
        Récupère les complétions de chat via l endpoint non-streaming.
        """
        url = f"{self.client.base_url}/chat/completions"

        if request.stream:
            warnings.warn(
                "streaming est à True, mais vous utilisez l endpoint non-streaming.",
                stacklevel=2,
            )

        request.stream = False
        return await self.client._request("POST", url, json=request.model_dump())

    async def _prepare_headers(self) -> Dict[str, str]:
        """Prépare les en-têtes HTTP pour la requête SSE."""
        headers = {
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
        if self.client.api_key:
            headers["X-ML-API-Key"] = self.client.api_key
        if self.client.auth_token:
            headers["Authorization"] = f"Bearer {self.client.auth_token}"
        return headers

    async def _parse_sse_event(
        self, event_type: str, data_lines: list[str]
    ) -> Dict[str, Any]:
        """Parse un événement SSE à partir de son type et de ses lignes de données."""
        data = "\n".join(data_lines)
        try:
            parsed_data = json.loads(data)
            if event_type == "done":
                return parsed_data
            elif event_type == "error":
                raise RuntimeError(parsed_data.get("error", "Erreur SSE inconnue"))
            return parsed_data
        except json.JSONDecodeError:
            self.client.logger.warning(f"Échec du parsing des données SSE : {data}")
            return {}

    async def _process_sse_stream(
        self, response: aiohttp.ClientResponse
    ) -> AsyncGenerator[dict, None]:
        """Traite le flux SSE ligne par ligne et génère les événements parsés."""
        event_type = "message"  # Type par défaut
        data_lines = []

        async for line in response.content:
            line = line.decode("utf-8").strip()

            if line:
                if line.startswith("event:"):
                    event_type = line[6:].strip()
                elif line.startswith("data:"):
                    data_lines.append(line[5:].strip())
            else:
                # Une ligne vide marque la fin d’un événement
                if data_lines:
                    event = await self._parse_sse_event(event_type, data_lines)
                    yield event
                    if event_type == "done":
                        return
                    event_type = "message"
                    data_lines = []

    async def get_streaming_completions(
        self, request: ChatCompletionsRequest
    ) -> AsyncGenerator[dict, None]:
        """
        Récupère les complétions de chat en streaming au format SSE.
        Génère des dictionnaires parsés à partir des événements SSE.

        Retourne:
            AsyncGenerator produisant des dictionnaires avec la structure suivante :
            - Pour les chunks normaux : {"chunk": str, "finish_reason": str|None, "job_id": str}
            - Pour la complétion finale : {"result": str, "finish_reason": str, "job_id": str}
        """
        request.stream = True
        url = f"{self.client.base_url}/chat/completions"

        # Initialise la session si nécessaire
        if self.client.session is None or self.client.session.closed:
            self.client.session = aiohttp.ClientSession(timeout=self.client.timeout)

        attempts = 0
        while attempts <= self.max_stream_retries:
            try:
                headers = await self._prepare_headers()
                async with self.client.session.post(
                    url,
                    headers=headers,
                    json=request.model_dump(),
                    timeout=self.client.timeout,
                ) as response:
                    response.raise_for_status()
                    async for event in self._process_sse_stream(response):
                        yield event
                return

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                attempts += 1
                if attempts > self.max_stream_retries:
                    raise ConnectionError(
                        f"Nombre maximal de tentatives ({self.max_stream_retries}) dépassé : {str(e)}"
                    )

                # Gestion des erreurs d’authentification
                if isinstance(e, aiohttp.ClientResponseError) and e.status == 401:
                    if self.client.username and self.client.password:
                        try:
                            self.client.logger.info(
                                "Token expiré, rafraîchissement en cours..."
                            )
                            await self.client.auth.login(
                                username=self.client.username,
                                password=self.client.password,
                                expires_in=1,
                            )
                            continue
                        except Exception as auth_error:
                            self.client.logger.error(
                                f"Échec du rafraîchissement : {auth_error}"
                            )

                # Calcul du délai avec jitter
                delay = self.retry_delay_base * (2 ** (attempts - 1))
                jitter = delay * 0.1 * random.random()
                total_delay = delay + jitter

                self.client.logger.warning(
                    f"Erreur de connexion, nouvelle tentative dans {total_delay:.2f}s "
                    f"(tentative {attempts}/{self.max_stream_retries}) : {str(e)}"
                )
                await asyncio.sleep(total_delay)

    async def stream_text(
        self, request: ChatCompletionsRequest
    ) -> AsyncGenerator[str, None]:
        """
        Diffuse le contenu textuel des complétions de chat au fur et à mesure de leur arrivée.
        """
        request.stream = True
        async for chunk in self.get_streaming_completions(request):
            if "chunk" in chunk:
                yield chunk["chunk"]
            elif "result" in chunk:
                yield chunk["result"]
