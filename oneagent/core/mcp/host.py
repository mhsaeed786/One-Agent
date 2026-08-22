"""
MCP Host - Model Context Protocol server host and client
"""

import os
import json
import subprocess
import asyncio
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from pathlib import Path

from ..logging import get_logger

logger = get_logger("mcp.host")


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server."""
    name: str
    command: str  # e.g., "python", "npx"
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    description: str = ""


@dataclass
class MCPTool:
    """A tool provided by an MCP server."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    server_name: str


class MCPHost:
    """
    Manages MCP (Model Context Protocol) servers.

    Can mount any MCP server (filesystem, web, browser, custom) and
    exposes its tools to the OneAgent agent loop.
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.getenv(
            "ONEAGENT_MCP_CONFIG", "./mcp_servers.json"
        )
        self._servers: Dict[str, MCPServerConfig] = {}
        self._tools: Dict[str, MCPTool] = {}
        self._processes: Dict[str, subprocess.Popen] = {}

        self._load_config()

    def _load_config(self):
        """Load MCP server configurations."""
        config_file = Path(self.config_path)
        if not config_file.exists():
            logger.debug("No MCP config file found")
            return

        try:
            with open(config_file, "r") as f:
                data = json.load(f)

            for server_data in data.get("servers", []):
                config = MCPServerConfig(
                    name=server_data["name"],
                    command=server_data["command"],
                    args=server_data.get("args", []),
                    env=server_data.get("env", {}),
                    enabled=server_data.get("enabled", True),
                    description=server_data.get("description", ""),
                )
                self._servers[config.name] = config

            logger.info(f"Loaded {len(self._servers)} MCP server configs")
        except Exception as e:
            logger.warning(f"Failed to load MCP config: {e}")

    def register_server(self, config: MCPServerConfig):
        """Register an MCP server."""
        self._servers[config.name] = config

    def remove_server(self, name: str) -> bool:
        """Remove an MCP server."""
        if name in self._servers:
            self.stop_server(name)
            del self._servers[name]
            # Remove tools from this server
            self._tools = {
                n: t for n, t in self._tools.items()
                if t.server_name != name
            }
            return True
        return False

    def start_server(self, name: str) -> bool:
        """Start an MCP server process."""
        config = self._servers.get(name)
        if not config:
            logger.error(f"MCP server {name} not found")
            return False

        if name in self._processes:
            logger.warning(f"MCP server {name} already running")
            return True

        try:
            env = {**os.environ, **config.env}
            process = subprocess.Popen(
                [config.command] + config.args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            self._processes[name] = process
            logger.info(f"Started MCP server: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to start MCP server {name}: {e}")
            return False

    def stop_server(self, name: str) -> bool:
        """Stop an MCP server process."""
        process = self._processes.get(name)
        if process:
            process.terminate()
            del self._processes[name]
            logger.info(f"Stopped MCP server: {name}")
            return True
        return False

    def register_tool(self, tool: MCPTool):
        """Register a tool from an MCP server."""
        self._tools[tool.name] = tool

    def get_tools(self) -> List[MCPTool]:
        """Get all available MCP tools."""
        return list(self._tools.values())

    def get_tool_schemas(self) -> List[Dict]:
        """Get tool schemas for LLM consumption."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.input_schema,
            }
            for tool in self._tools.values()
        ]

    def list_servers(self) -> List[MCPServerConfig]:
        """List all registered MCP servers."""
        return list(self._servers.values())

    def save_config(self):
        """Save current configuration to file."""
        data = {
            "servers": [
                {
                    "name": s.name,
                    "command": s.command,
                    "args": s.args,
                    "env": s.env,
                    "enabled": s.enabled,
                    "description": s.description,
                }
                for s in self._servers.values()
            ]
        }
        with open(self.config_path, "w") as f:
            json.dump(data, f, indent=2)

    def shutdown(self):
        """Stop all MCP servers."""
        for name in list(self._processes.keys()):
            self.stop_server(name)
