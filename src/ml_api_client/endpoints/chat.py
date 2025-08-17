import asyncio
import json
import random
import warnings
from typing import Any, AsyncGenerator, Dict, Iterable, Optional

from openai import AsyncOpenAI
from openai import APIConnectionError, RateLimitError
from openai._exceptions import APIStatusError  # status_code available
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk

from ..models import TextGenerationRequest


class ChatEndpoint:
    def __init__(self, client):
        self.client = client
        self.max_stream_retries = 3
        self.retry_delay_base = 1.0
        self._sdk: Optional[AsyncOpenAI] = None

    # --------------------------
    # SDK bootstrap
    # --------------------------
    def _ensure_sdk(self) -> AsyncOpenAI:
        if self._sdk:
            return self._sdk

        timeout_s = getattr(self.client.timeout, "total", None)
        default_headers: Dict[str, str] = {}

        api_key_for_sdk = self.client.auth_token or (self.client.api_key or "none")
        if self.client.api_key:
            default_headers["X-ML-API-Key"] = self.client.api_key

        self._sdk = AsyncOpenAI(
            base_url=self.client.base_url,
            api_key=api_key_for_sdk,
            max_retries=self.client.max_retries,
            timeout=timeout_s if timeout_s is not None else 60,
            default_headers=default_headers or None,
        )
        return self._sdk

    # --------------------------
    # Non-streaming
    # --------------------------
    async def complete(
        self,
        model: str,
        messages: Iterable[ChatCompletionMessageParam],
        stream: Optional[bool] = None,
        **kwargs: Any,
    ) -> ChatCompletion:
        """
        Non-streaming chat completion. Returns OpenAI-like ChatCompletion.
        """
        if stream:
            warnings.warn(
                "stream=True on non-streaming call. For streaming use stream/stream_text.",
                stacklevel=2,
            )

        payload = {"model": model, "messages": messages, "stream": stream, **kwargs}

        sdk = self._ensure_sdk()
        try:
            # OpenAI SDK accepts typed kwargs (model, messages, ...).
            # Ensure your TextGenerationRequest fields match OpenAI params.
            return await sdk.chat.completions.create(**payload)  # type: ignore[arg-type]
        except APIStatusError as e:
            await self._maybe_refresh_and_raise(e)
        except (APIConnectionError, RateLimitError) as e:
            raise ConnectionError(str(e))

        # Satisfy type checker. _maybe_refresh_and_raise always raises.
        raise RuntimeError("Unreachable")

    # --------------------------
    # Streaming helpers
    # --------------------------
    async def _stream_with_retries(
        self, model: str, messages: Iterable[ChatCompletionMessageParam], **kwargs: Any
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        """
        Centralized streaming with retry and token refresh.
        Yields ChatCompletionChunk from OpenAI SDK.
        """
        attempts = 0
        sdk = self._ensure_sdk()

        while attempts <= self.max_stream_retries:
            try:
                # Newer SDKs return an async iterator when stream=True.
                stream = await sdk.chat.completions.create(
                    model=model, messages=messages, stream=True, **kwargs
                )  # type: ignore[arg-type]
                async for chunk in stream:
                    yield chunk
                return

            except APIStatusError as e:
                # 401: try refresh if creds available, then retry.
                if (
                    e.status_code == 401
                    and self.client.username
                    and self.client.password
                ):
                    attempts += 1
                    if attempts > self.max_stream_retries:
                        raise PermissionError(
                            "Unauthorized and refresh retries exhausted."
                        )
                    try:
                        self.client.logger.info("Token expired, refreshing...")
                        await self.client.auth.login(
                            username=self.client.username,
                            password=self.client.password,
                            expires_in=1,
                        )
                        # Rebuild SDK with fresh token
                        self._sdk = None
                        sdk = self._ensure_sdk()
                        continue
                    except Exception as auth_error:
                        self.client.logger.error(f"Refresh failed: {auth_error}")
                        raise PermissionError("Token refresh failed.") from auth_error
                else:
                    raise

            except (APIConnectionError, RateLimitError, asyncio.TimeoutError) as e:
                attempts += 1
                if attempts > self.max_stream_retries:
                    raise ConnectionError(
                        f"Maximum number of attempts ({self.max_stream_retries}) exceeded: {str(e)}"
                    )
                delay = self.retry_delay_base * (2 ** (attempts - 1))
                jitter = delay * 0.1 * random.random()
                total_delay = delay + jitter
                self.client.logger.warning(
                    f"Connection error, retrying in {total_delay:.2f}s "
                    f"(attempt {attempts}/{self.max_stream_retries}): {str(e)}"
                )
                await asyncio.sleep(total_delay)

    async def _maybe_refresh_and_raise(self, e: APIStatusError) -> None:
        if e.status_code == 401 and self.client.username and self.client.password:
            try:
                self.client.logger.info("Token expired, refreshing...")
                await self.client.auth.login(
                    username=self.client.username,
                    password=self.client.password,
                    expires_in=1,
                )
                # Successful refresh, let caller retry explicitly if needed.
                raise PermissionError("Token was expired. Please retry the request.")
            except Exception as auth_error:
                self.client.logger.error(f"Refresh failed: {auth_error}")
                raise PermissionError("Token refresh failed.") from auth_error
        # Map common statuses to your previous errors
        if e.status_code == 403:
            raise PermissionError(f"Access forbidden: {e}")
        if e.status_code == 404:
            raise ValueError(f"Resource not found: {e}")
        raise

    # --------------------------
    # Streaming: OpenAI chunks
    # --------------------------
    async def stream(
        self, model: str, messages: Iterable[ChatCompletionMessageParam], **kwargs: Any
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        """
        Streaming chat completions. Yields dicts like ChatCompletionChunk.
        """

        async for chunk in self._stream_with_retries(model, messages, **kwargs):
            yield chunk

    # --------------------------
    # Streaming: text only
    # --------------------------
    async def stream_text(
        self, model: str, messages: Iterable[ChatCompletionMessageParam], **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        """
        Yields choices[0].delta.content as text tokens arrive.
        """
        async for event in self._stream_with_retries(model, messages, **kwargs):
            try:
                if (
                    isinstance(event, ChatCompletionChunk)
                    and event.object == "chat.completion.chunk"
                ):
                    choices = event.choices or []
                    if choices:
                        delta = choices[0].delta or {}
                        content = delta.content
                        if content is not None:
                            yield content
            except Exception:
                continue

    # --------------------------
    # Streaming: raw SSE lines
    # --------------------------
    async def stream_sse(
        self, model: str, messages: Iterable[ChatCompletionMessageParam], **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        """
        Emits raw SSE-like lines built from SDK chunks.
        Matches "data: {json}\\n\\n" then final "data: [DONE]\\n\\n".
        """
        async for chunk in self._stream_with_retries(model, messages, **kwargs):
            line = f"data: {json.dumps(chunk.model_dump(), separators=(',', ':'))}\n\n"
            yield line
        # Signal logical end
        yield "data: [DONE]\n\n"
