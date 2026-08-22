"""
Tool Registry - Decorator-based tool registration with schema validation
"""

from typing import Dict, Any, Callable, List, Optional
from dataclasses import dataclass
from functools import wraps
import inspect

from ..logging import get_logger

logger = get_logger("tools.registry")


@dataclass
class ToolSchema:
    """Schema definition for a tool."""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema for parameters
    is_async: bool = False


class ToolNotFoundError(Exception):
    """Raised when a tool is not found in the registry."""
    pass


class ToolRegistry:
    """
    Registry for agent tools with decorator-based registration.

    Usage:
        registry = ToolRegistry()

        @registry.register(
            name="search_web",
            description="Search the web for information",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "limit": {"type": "integer", "default": 5}
                },
                "required": ["query"]
            }
        )
        async def search_web(query: str, limit: int = 5) -> List[str]:
            # Tool implementation
            pass
    """

    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._schemas: Dict[str, ToolSchema] = {}

    def register(
        self,
        name: str,
        description: str = "",
        parameters: Optional[Dict] = None,
    ) -> Callable:
        """Decorator to register a tool."""
        def decorator(func: Callable) -> Callable:
            # Store tool
            self._tools[name] = func

            # Build schema from function signature if not provided
            params = parameters
            if params is None:
                params = self._build_schema_from_signature(func)

            self._schemas[name] = ToolSchema(
                name=name,
                description=description or func.__doc__ or "",
                parameters=params,
                is_async=inspect.iscoroutinefunction(func),
            )

            logger.debug(f"Registered tool: {name}")

            return func

        return decorator

    def _build_schema_from_signature(self, func: Callable) -> Dict:
        """Build JSON Schema from function signature."""
        sig = inspect.signature(func)
        params = sig.parameters

        properties = {}
        required = []

        for param_name, param in params.items():
            param_type = "string"
            default = inspect.Parameter.empty

            # Get default value
            if param.default is not inspect.Parameter.empty:
                default = param.default

            # Infer type from annotation or default
            if param.annotation in (int,):
                param_type = "integer"
            elif param.annotation == float:
                param_type = "number"
            elif param.annotation == bool:
                param_type = "boolean"
            elif param.annotation == list or param.annotation == List:
                param_type = "array"
            elif param.annotation == dict or param.annotation == Dict:
                param_type = "object"

            prop: Dict[str, Any] = {"type": param_type}
            if default is not inspect.Parameter.empty:
                prop["default"] = default
            else:
                required.append(param_name)

            properties[param_name] = prop

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }

    async def execute(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """Execute a tool by name."""
        if tool_name not in self._tools:
            available = list(self._tools.keys())
            raise ToolNotFoundError(
                f"Tool '{tool_name}' not found. Available: {available}"
            )

        func = self._tools[tool_name]

        try:
            if inspect.iscoroutinefunction(func):
                return await func(**args)
            else:
                return func(**args)
        except Exception as e:
            logger.error(f"Tool '{tool_name}' failed: {e}")
            raise

    def get_tool_names(self) -> List[str]:
        """Get list of registered tool names."""
        return list(self._tools.keys())

    def get_schemas(self) -> List[Dict]:
        """Get all tool schemas for LLM."""
        return [
            {
                "name": schema.name,
                "description": schema.description,
                "parameters": schema.parameters,
            }
            for schema in self._schemas.values()
        ]

    def get_schema(self, name: str) -> Optional[ToolSchema]:
        """Get schema for a specific tool."""
        return self._schemas.get(name)

    def has_tool(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._tools


# Global registry instance
_global_registry = ToolRegistry()

# Decorator shortcut - use @register(...) instead of @tool_registry.register(...)
def register(name: str, description: str = "", parameters: Optional[Dict] = None):
    """Decorator to register a tool with the global registry."""
    return _global_registry.register(name, description, parameters)

def get_registry() -> ToolRegistry:
    """Get the global tool registry."""
    return _global_registry

async def execute_tool(tool_name: str, args: Dict[str, Any]) -> Any:
    """Execute a tool from the global registry."""
    return await _global_registry.execute(tool_name, args)


# Alias for convenience
tool_registry = _global_registry