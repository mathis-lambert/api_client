from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Type

from pydantic import BaseModel

__all__ = ["ChatToolRegistry"]


# --------------------------
# Tool registry
# --------------------------
@dataclass
class _ToolEntry:
    name: str
    func: Callable[..., Any]
    params_model: Optional[Type[BaseModel]] = None
    description: Optional[str] = None


class ChatToolRegistry:
    """
    client.chat.tools.register(name, func, params_model=..., description=...)
    client.chat.tools.to_openai_tools()
    """

    def __init__(self) -> None:
        self._tools: Dict[str, _ToolEntry] = {}

    def register(
        self,
        name: str,
        func: Callable[..., Any],
        params_model: Optional[Type[BaseModel]] = None,
        description: Optional[str] = None,
    ) -> None:
        if not isinstance(name, str) or not name:
            raise ValueError("tool name must be a non-empty string")
        self._tools[name] = _ToolEntry(
            name=name, func=func, params_model=params_model, description=description
        )

    def get(self, name: str) -> _ToolEntry:
        if name not in self._tools:
            raise KeyError(f"tool '{name}' not registered")
        return self._tools[name]

    def has(self, name: str) -> bool:
        return name in self._tools

    def list(self) -> List[str]:
        return list(self._tools.keys())

    def _model_json_schema(self, model: Type[BaseModel]) -> Dict[str, Any]:
        # pydantic v2: model.model_json_schema()
        # pydantic v1: model.schema()
        if hasattr(model, "model_json_schema"):
            return model.model_json_schema()  # type: ignore[attr-defined]
        return model.schema()

    def to_openai_tools(self) -> List[Dict[str, Any]]:
        """
        OpenAI Chat Completions `tools` format.
        """
        tools_payload: List[Dict[str, Any]] = []
        for entry in self._tools.values():
            params_schema: Dict[str, Any] = {
                "type": "object",
                "properties": {},
                "required": [],
            }
            if entry.params_model:
                schema = self._model_json_schema(entry.params_model)
                # Accept either full JSON Schema or pydantic’s wrapper. Keep minimal.
                if "type" in schema:
                    params_schema = schema
                elif "properties" in schema or "required" in schema:
                    params_schema.update(
                        {
                            k: v
                            for k, v in schema.items()
                            if k in ("type", "properties", "required")
                        }
                    )
            tools_payload.append(
                {
                    "type": "function",
                    "function": {
                        "name": entry.name,
                        "description": entry.description
                        or f"Callable tool '{entry.name}'.",
                        "parameters": params_schema,
                    },
                }
            )
        return tools_payload
