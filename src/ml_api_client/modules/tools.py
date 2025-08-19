from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Type, Union

from pydantic import BaseModel, Field

__all__ = ["ToolRegistry", "ToolProperty", "ToolParams"]


# --------------------------
# Tool registry
# --------------------------
class ToolProperty(BaseModel):
    type: str
    description: Optional[str] = None
    enum: Optional[List[str]] = None
    default: Optional[Any] = None


class ToolParams(BaseModel):
    type: str = Field(default="object")
    properties: Dict[str, Union[ToolProperty, Dict[str, Any]]] = Field(
        default_factory=dict
    )
    required: List[str] = Field(default_factory=list)
    additionalProperties: bool = False  # explicit and strict by default


@dataclass
class _ToolEntry:
    name: str
    func: Callable[..., Any]
    description: Optional[str] = None
    strict: Optional[bool] = True
    # Normalized JSON Schema for OpenAI "parameters"
    params_schema: Optional[Dict[str, Any]] = None
    # Optional Pydantic model for runtime validation/coercion
    params_model: Optional[Type[BaseModel]] = None


class ToolRegistry:
    """
    Usage:
        tools.register("get_weather", get_weather, params=WeatherParams, description="...")
        tools.to_openai_tools()  -> for chat.completions tools=[]
    """

    def __init__(self) -> None:
        self._tools: Dict[str, _ToolEntry] = {}

    # --------------------------
    # Registration
    # --------------------------
    def register(
        self,
        name: str,
        func: Callable[..., Any],
        params: Optional[Union[ToolParams, Dict[str, Any], Type[BaseModel]]] = None,
        description: Optional[str] = None,
        strict: Optional[bool] = True,
    ) -> None:
        if not isinstance(name, str) or not name:
            raise ValueError("tool name must be a non-empty string")

        schema: Optional[Dict[str, Any]] = None
        params_model: Optional[Type[BaseModel]] = None

        if params is None:
            schema = self._empty_schema()
        elif isinstance(params, ToolParams):
            schema = self._params_json_schema(params)
        elif isinstance(params, dict):
            schema = self._coerce_schema_dict(params)
        elif isinstance(params, type) and issubclass(params, BaseModel):
            params_model = params
            schema = self._extract_object_schema(params.model_json_schema())
        else:
            raise TypeError(
                "params must be ToolParams, dict schema, BaseModel subclass, or None"
            )

        self._tools[name] = _ToolEntry(
            name=name,
            func=func,
            description=description,
            strict=strict,
            params_schema=schema,
            params_model=params_model,
        )

    # --------------------------
    # Introspection
    # --------------------------
    def get(self, name: str) -> _ToolEntry:
        if name not in self._tools:
            raise KeyError(f"tool '{name}' not registered")
        return self._tools[name]

    def has(self, name: str) -> bool:
        return name in self._tools

    def list(self) -> List[str]:
        return list(self._tools.keys())

    # --------------------------
    # Schema helpers
    # --------------------------
    def _empty_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        }

    def _params_json_schema(self, params: ToolParams) -> Dict[str, Any]:
        # Convert ToolProperty models to plain dicts
        props: Dict[str, Any] = {}
        for k, v in params.properties.items():
            if isinstance(v, ToolProperty):
                props[k] = v.model_dump(exclude_none=True)
            else:
                props[k] = v
        return {
            "type": params.type or "object",
            "properties": props,
            "required": list(params.required or []),
            "additionalProperties": bool(params.additionalProperties),
        }

    def _coerce_schema_dict(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        props = raw.get("properties") or {}
        norm_props: Dict[str, Any] = {}
        if isinstance(props, dict):
            for k, v in props.items():
                if isinstance(v, ToolProperty):
                    norm_props[k] = v.model_dump(exclude_none=True)
                else:
                    norm_props[k] = v
        return {
            "type": raw.get("type", "object"),
            "properties": norm_props,
            "required": list(raw.get("required", [])),
            "additionalProperties": bool(raw.get("additionalProperties", False)),
        }

    def _extract_object_schema(self, js: Dict[str, Any]) -> Dict[str, Any]:
        # Pydantic v2 top-level object schema
        return {
            "type": js.get("type", "object"),
            "properties": js.get("properties", {}) or {},
            "required": list(js.get("required", [])),
            "additionalProperties": bool(js.get("additionalProperties", False)),
        }

    # --------------------------
    # Export for OpenAI Chat Completions
    # --------------------------
    def to_openai_tools(self) -> List[Dict[str, Any]]:
        """
        Returns Chat Completions `tools` payload:
        [
          {
            "type": "function",
            "function": {
              "name": "...",
              "description": "...",
              "parameters": {...},
              "strict": true
            }
          }
        ]
        """
        tools_payload: List[Dict[str, Any]] = []
        for entry in self._tools.values():
            func_obj: Dict[str, Any] = {
                "name": entry.name,
                "description": entry.description or f"Callable tool '{entry.name}'.",
                "parameters": entry.params_schema or self._empty_schema(),
            }
            # Include strict only if provided
            if entry.strict is not None:
                func_obj["strict"] = bool(entry.strict)

            tools_payload.append({"type": "function", "function": func_obj})
        return tools_payload
