"""
Built-in Tools - Basic tools for the agent
"""

import json
import math
import re
from typing import Any, List

from .registry import tool_registry


@tool_registry.register(
    name="calculator",
    description="Perform a mathematical calculation",
    parameters={
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Mathematical expression to evaluate (e.g., '2 + 2', 'sqrt(16)', 'sin(pi/2)')"
            }
        },
        "required": ["expression"]
    }
)
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression."""
    try:
        # Safe math evaluation - only allow math functions
        allowed_names = {
            k: v for k, v in math.__dict__.items()
            if not k.startswith('_')
        }
        allowed_names['abs'] = abs
        allowed_names['round'] = round
        allowed_names['min'] = min
        allowed_names['max'] = max
        allowed_names['sum'] = sum
        allowed_names['len'] = len

        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return str(result)
    except Exception as e:
        return f"Error: {e}"


@tool_registry.register(
    name="read_file",
    description="Read the contents of a file",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file to read"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of lines to read",
                "default": 100
            }
        },
        "required": ["path"]
    }
)
def read_file(path: str, limit: int = 100) -> str:
    """Read file contents."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            lines = []
            for i, line in enumerate(f):
                if i >= limit:
                    lines.append(f"... (truncated at {limit} lines)")
                    break
                lines.append(line.rstrip('\n'))
        return '\n'.join(lines)
    except Exception as e:
        return f"Error reading file: {e}"


@tool_registry.register(
    name="write_file",
    description="Write content to a file",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file to write"
            },
            "content": {
                "type": "string",
                "description": "Content to write to the file"
            }
        },
        "required": ["path", "content"]
    }
)
def write_file(path: str, content: str) -> str:
    """Write content to a file."""
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"Error writing file: {e}"


@tool_registry.register(
    name="search",
    description="Search for a pattern in text",
    parameters={
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Text to search in"
            },
            "pattern": {
                "type": "string",
                "description": "Regex pattern to search for"
            },
            "case_sensitive": {
                "type": "boolean",
                "description": "Whether to search case-sensitive",
                "default": False
            }
        },
        "required": ["text", "pattern"]
    }
)
def search(text: str, pattern: str, case_sensitive: bool = False) -> str:
    """Search for a pattern in text using regex."""
    try:
        flags = 0 if case_sensitive else re.IGNORECASE
        matches = re.findall(pattern, text, flags)
        if matches:
            return f"Found {len(matches)} matches: {matches[:10]}"
        return "No matches found"
    except Exception as e:
        return f"Error in search: {e}"


@tool_registry.register(
    name="grep",
    description="Search for lines containing a pattern in a file",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file to search in"
            },
            "pattern": {
                "type": "string",
                "description": "Pattern to search for"
            },
            "case_sensitive": {
                "type": "boolean",
                "description": "Whether to search case-sensitive",
                "default": False
            }
        },
        "required": ["path", "pattern"]
    }
)
def grep(path: str, pattern: str, case_sensitive: bool = False) -> str:
    """Grep-like search in a file."""
    try:
        flags = 0 if case_sensitive else re.IGNORECASE
        regex = re.compile(pattern, flags)
        matches = []
        with open(path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f, 1):
                if regex.search(line):
                    matches.append(f"{i}: {line.rstrip()}")
        if matches:
            return '\n'.join(matches[:50])
        return "No matches found"
    except Exception as e:
        return f"Error grepping file: {e}"


@tool_registry.register(
    name="json_parse",
    description="Parse and validate JSON string",
    parameters={
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "JSON string to parse"
            }
        },
        "required": ["text"]
    }
)
def json_parse(text: str) -> str:
    """Parse JSON string and return formatted result."""
    try:
        data = json.loads(text)
        return json.dumps(data, indent=2, default=str)
    except Exception as e:
        return f"Error parsing JSON: {e}"


@tool_registry.register(
    name="json_query",
    description="Query data from a JSON object using JMESPath-like syntax",
    parameters={
        "type": "object",
        "properties": {
            "data": {
                "type": "object",
                "description": "JSON data to query"
            },
            "key_path": {
                "type": "string",
                "description": "Dot-separated key path (e.g., 'user.profile.name')"
            }
        },
        "required": ["data", "key_path"]
    }
)
def json_query(data: dict, key_path: str) -> str:
    """Query nested data from a JSON object."""
    try:
        keys = key_path.split('.')
        current = data
        for key in keys:
            if isinstance(current, dict):
                current = current[key]
            else:
                return f"Error: '{key}' is not a dictionary at current level"
        return json.dumps(current, indent=2, default=str)
    except KeyError as e:
        return f"Error: Key not found - {e}"
    except Exception as e:
        return f"Error querying JSON: {e}"


@tool_registry.register(
    name="echo",
    description="Echo back the input (for testing)",
    parameters={
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Message to echo back"
            }
        },
        "required": ["message"]
    }
)
def echo(message: str) -> str:
    """Echo back the input message."""
    return message


def register_builtin_tools(registry: "ToolRegistry") -> None:
    """Register all built-in tools with a registry."""
    # This is a no-op since tools are registered via decorator
    # but provides a hook for explicit registration if needed
    pass