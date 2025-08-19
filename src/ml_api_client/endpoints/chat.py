import asyncio
import inspect
import json
import random
import warnings
from typing import (
    Any,
    AsyncGenerator,
    Dict,
    Iterable,
    Optional,
    Union,
    List,
    Tuple,
    Awaitable,
)

from openai import AsyncOpenAI
from openai import APIConnectionError, RateLimitError
from openai._exceptions import APIStatusError  # status_code available
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk


class ChatEndpoint:
    def __init__(self, client):
        self.client = client
        self.max_stream_retries = 3
        self.retry_delay_base = 1.0
        self._sdk: Optional[AsyncOpenAI] = None
        self.tools = client.tools

        # tool loop safety
        self.max_tool_iterations = 5

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
    # Helpers: tool execution
    # --------------------------
    async def _maybe_call_tool(
        self, name: str, arguments: Union[str, Dict[str, Any]]
    ) -> Any:
        if isinstance(arguments, str) and arguments.strip():
            try:
                args = json.loads(arguments)
            except Exception:
                # try forgiving parse (e.g., partial JSON)
                args = {}
        elif isinstance(arguments, dict):
            args = arguments
        else:
            args = {}

        if not name:
            return {"error": "Tool call missing function name"}
        entry = self.tools.get(name)

        # If a params_model exists, validate and coerce.
        if entry.params_model:
            try:
                params = entry.params_model(**args)
                args = params.dict() if hasattr(params, "dict") else params.model_dump()
            except Exception as e:
                return {"error": f"Invalid arguments for tool '{name}': {str(e)}"}

        fn = entry.func

        # Support async and sync functions. Prefer kwargs call.
        try:
            if inspect.iscoroutinefunction(fn):
                return await fn(**args)
            # run sync in thread to avoid blocking
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: fn(**args))
        except TypeError:
            # fallback: pass a single dict
            try:
                if inspect.iscoroutinefunction(fn):
                    return await fn(args)
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, lambda: fn(args))
            except Exception as e:
                return {"error": f"Tool '{name}' failed: {str(e)}"}
        except Exception as e:
            return {"error": f"Tool '{name}' failed: {str(e)}"}

    def _tools_param(
        self, explicit_tools: Optional[List[Dict[str, Any]]]
    ) -> Optional[List[Dict[str, Any]]]:
        if explicit_tools is not None:
            return explicit_tools
        registry_tools = self.tools.to_openai_tools()
        return registry_tools if registry_tools else None

    # --------------------------
    # Non-streaming with auto tool execution
    # --------------------------
    async def complete(
        self,
        model: str,
        messages: Iterable[ChatCompletionMessageParam],
        stream: Optional[bool] = None,
        auto_tool_execution: bool = False,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = "auto",
        **kwargs: Any,
    ) -> ChatCompletion:
        """
        Non-streaming chat completion.
        If auto_tool_execution=True, loops over tool calls until final answer.
        """
        if stream:
            warnings.warn(
                "stream=True on non-streaming call. Use stream/stream_text.",
                stacklevel=2,
            )

        sdk = self._ensure_sdk()
        msgs: List[ChatCompletionMessageParam] = list(messages)

        if not auto_tool_execution:
            payload = {
                "model": model,
                "messages": msgs,
                "tools": tools,
                "tool_choice": tool_choice,
                "stream": False,
                **kwargs,
            }
            try:
                return await sdk.chat.completions.create(**payload)  # type: ignore[arg-type]
            except APIStatusError as e:
                await self._maybe_refresh_and_raise(e)
            except (APIConnectionError, RateLimitError) as e:
                raise ConnectionError(str(e))
            raise RuntimeError("Unreachable")

        # Tool loop
        tools_payload = self._tools_param(tools)
        loop_count = 0
        while loop_count < self.max_tool_iterations:
            loop_count += 1
            try:
                resp: ChatCompletion = await sdk.chat.completions.create(
                    model=model,
                    messages=msgs,
                    tools=tools_payload,
                    tool_choice=tool_choice,
                    stream=False,
                    **kwargs,
                )  # type: ignore[arg-type]
            except APIStatusError as e:
                await self._maybe_refresh_and_raise(e)
            except (APIConnectionError, RateLimitError) as e:
                raise ConnectionError(str(e))

            choice = resp.choices[0]
            msg = choice.message
            tool_calls = getattr(msg, "tool_calls", None)

            if tool_calls:
                # Execute tool calls (can be parallel).
                execs: List[Awaitable[Any]] = []
                for call in tool_calls:
                    name = call.function.name
                    args = call.function.arguments or "{}"
                    execs.append(self._maybe_call_tool(name, args))
                results = await asyncio.gather(*execs)

                # Append assistant call message and each tool result.
                msgs.append(
                    {
                        "role": "assistant",
                        "content": msg.content or "",
                        "tool_calls": [tc.model_dump() for tc in tool_calls],
                    }
                )  # type: ignore
                for call, out in zip(tool_calls, results):
                    content = (
                        out
                        if isinstance(out, str)
                        else json.dumps(out, ensure_ascii=False)
                    )
                    msgs.append(
                        {"role": "tool", "tool_call_id": call.id, "content": content}
                    )  # type: ignore
                # Continue loop for another model turn.
                continue

            # No tool calls. Final.
            return resp

        raise RuntimeError("Max tool iterations exceeded")

    # --------------------------
    # Streaming core with retries
    # --------------------------
    async def _stream_with_retries(
        self, model: str, messages: Iterable[ChatCompletionMessageParam], **kwargs: Any
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        attempts = 0
        sdk = self._ensure_sdk()

        while attempts <= self.max_stream_retries:
            try:
                stream = await sdk.chat.completions.create(
                    model=model, messages=messages, stream=True, **kwargs
                )  # type: ignore[arg-type]
                async for chunk in stream:
                    yield chunk
                return
            except APIStatusError as e:
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
                        f"Maximum attempts ({self.max_stream_retries}) exceeded: {str(e)}"
                    )
                delay = self.retry_delay_base * (2 ** (attempts - 1))
                jitter = delay * 0.1 * random.random()
                total_delay = delay + jitter
                self.client.logger.warning(
                    f"Connection error, retrying in {total_delay:.2f}s (attempt {attempts}/{self.max_stream_retries}): {str(e)}"
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
                raise PermissionError("Token was expired. Please retry the request.")
            except Exception as auth_error:
                self.client.logger.error(f"Refresh failed: {auth_error}")
                raise PermissionError("Token refresh failed.") from auth_error
        if e.status_code == 403:
            raise PermissionError(f"Access forbidden: {e}")
        if e.status_code == 404:
            raise ValueError(f"Resource not found: {e}")
        raise

    # --------------------------
    # Streaming with auto tool execution
    # --------------------------
    async def stream(
        self,
        model: str,
        messages: Iterable[ChatCompletionMessageParam],
        auto_tool_execution: bool = False,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = "auto",
        **kwargs: Any,
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        if not auto_tool_execution:
            async for chunk in self._stream_with_retries(model, messages, **kwargs):
                yield chunk
            return

        msgs: List[ChatCompletionMessageParam] = list(messages)
        tools_payload = self._tools_param(tools)

        for _ in range(self.max_tool_iterations):
            # one assistant turn
            tool_call_buffers: Dict[str, Dict[str, Any]] = {}  # key = f"idx-{index}"
            saw_tool_call = False

            async for chunk in self._stream_with_retries(
                model,
                msgs,
                tools=tools_payload,
                tool_choice=tool_choice,
                **kwargs,
            ):
                ch = chunk.choices[0]
                delta = ch.delta

                # accumulate tool calls; suppress them from user output
                if delta and getattr(delta, "tool_calls", None):
                    saw_tool_call = True
                    for tc in delta.tool_calls:
                        # stable key based on streamed index, never by id
                        tc_index = getattr(tc, "index", None)
                        key = f"idx-{tc_index if tc_index is not None else 0}"
                        buf = tool_call_buffers.setdefault(
                            key, {"id": None, "name": None, "arguments": ""}
                        )

                        # fill id when it appears
                        if getattr(tc, "id", None):
                            buf["id"] = tc.id

                        # function fragments arrive over time
                        fn = getattr(tc, "function", None)
                        if fn is not None:
                            if getattr(fn, "name", None):
                                buf["name"] = fn.name
                            if getattr(fn, "arguments", None):
                                # arguments are streamed text; just concatenate
                                buf["arguments"] += fn.arguments or ""
                    continue  # do not yield tool-call chunks

                # pass through normal content chunks until we see a tool call
                if not saw_tool_call:
                    yield chunk

            # stream ended for this turn
            if saw_tool_call:
                # build assistant message with tool_calls using buffered data
                tool_calls_payload = []
                for key, tc in tool_call_buffers.items():
                    name = tc["name"]
                    if not name:
                        # still no name after the turn finished -> protocol error
                        raise RuntimeError(f"Missing function name for tool call {key}")
                    call_id = tc["id"] or key  # fall back to idx-based id if necessary
                    tool_calls_payload.append(
                        {
                            "id": call_id,
                            "type": "function",
                            "function": {
                                "name": name,
                                "arguments": tc["arguments"],
                            },
                        }
                    )

                # append the assistant message that issued the calls
                msgs.append(
                    {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": tool_calls_payload,
                    }
                )  # type: ignore

                # execute tools in parallel
                execs: List[Awaitable[Any]] = []
                id_name_args: List[Tuple[str, str, str]] = []
                for key, tc in tool_call_buffers.items():
                    call_id = tc["id"] or key
                    id_name_args.append((call_id, tc["name"], tc["arguments"]))
                    execs.append(self._maybe_call_tool(tc["name"], tc["arguments"]))
                results = await asyncio.gather(*execs)

                # append tool results
                for (tool_call_id, _name, _args), out in zip(id_name_args, results):
                    content = (
                        out
                        if isinstance(out, str)
                        else json.dumps(out, ensure_ascii=False)
                    )
                    msgs.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "content": content,
                        }
                    )  # type: ignore

                # next assistant turn will stream final answer
                continue

            # no tool calls -> final
            return

        raise RuntimeError("Max tool iterations exceeded during streaming")

    # --------------------------
    # Streaming: text-only helper
    # --------------------------
    async def stream_text(
        self,
        model: str,
        messages: Iterable[ChatCompletionMessageParam],
        auto_tool_execution: bool = False,
        return_reasoning: bool = False,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        async for event in self.stream(
            model, messages, auto_tool_execution=auto_tool_execution, **kwargs
        ):
            try:
                if isinstance(event, ChatCompletionChunk):
                    choices = event.choices or []
                    if choices:
                        delta = choices[0].delta or {}

                        if return_reasoning:
                            reasoning = delta.reasoning
                            if reasoning is not None:
                                yield reasoning

                        content = delta.content
                        if content is not None:
                            yield content

            except Exception:
                continue

    # --------------------------
    # Streaming: raw SSE lines
    # --------------------------
    async def stream_sse(
        self,
        model: str,
        messages: Iterable[ChatCompletionMessageParam],
        auto_tool_execution: bool = False,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        async for chunk in self.stream(
            model, messages, auto_tool_execution=auto_tool_execution, **kwargs
        ):
            line = f"data: {json.dumps(chunk.model_dump(), separators=(',', ':'))}\n\n"
            yield line
        yield "data: [DONE]\n\n"
