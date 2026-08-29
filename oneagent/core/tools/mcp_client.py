from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional


class MCPClient:
    """Minimal Model Context Protocol (MCP) client.

    Supports connecting to MCP servers via stdio or SSE transport.
    """

    def __init__(self, name: str, command: str, args: Optional[List[str]] = None, env: Optional[Dict[str, str]] = None):
        self.name = name
        self.command = command
        self.args = args or []
        self.env = {**os.environ, **(env or {})}
        self._process: Optional[subprocess.Popen] = None
        self._request_id = 0

    async def start(self):
        self._process = subprocess.Popen(
            [self.command] + self.args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self.env,
            text=True,
        )
        # Initialize handshake
        init_req = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "oneagent-mcp-client", "version": "0.1.0"},
            },
        }
        await self._send(init_req)
        resp = await self._recv()
        return resp

    async def list_tools(self) -> List[Dict[str, Any]]:
        req = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/list",
        }
        await self._send(req)
        resp = await self._recv()
        return resp.get("result", {}).get("tools", [])

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        req = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
        await self._send(req)
        resp = await self._recv()
        return resp.get("result", {}).get("content", [])

    async def stop(self):
        if self._process:
            self._process.terminate()
            self._process.wait(timeout=5)
            self._process = None

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    async def _send(self, message: Dict[str, Any]):
        if not self._process:
            raise RuntimeError("MCP client not started")
        line = json.dumps(message) + "\n"
        self._process.stdin.write(line)
        self._process.stdin.flush()

    async def _recv(self) -> Dict[str, Any]:
        if not self._process:
            raise RuntimeError("MCP client not started")
        line = self._process.stdout.readline()
        if not line:
            return {}
        return json.loads(line)


class MCPRegistry:
    """Registry of MCP servers."""

    def __init__(self):
        self._servers: Dict[str, MCPClient] = {}

    def register(self, name: str, client: MCPClient):
        self._servers[name] = client

    def get(self, name: str) -> MCPClient:
        return self._servers[name]

    def list(self) -> List[str]:
        return list(self._servers)


GLOBAL_MCP_REGISTRY = MCPRegistry()
