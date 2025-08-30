"""
Minimal MCP Stdio Server Implementation
========================================

Provides stdio-based MCP server communication for services like
Notion, Filesystem, Playwright, and Postgres.
"""

import asyncio
import os
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class MCPStdioServer:
    """Lightweight wrapper around the official MCP Python SDK."""

    def __init__(self, command: str, args: List[str], env: Optional[Dict[str, str]] = None, timeout: int = 120):
        self.params = StdioServerParameters(command=command, args=args, env={**os.environ, **(env or {})})
        self.timeout = timeout
        self._stack: Optional[AsyncExitStack] = None
        self._streams = None
        self.session: Optional[ClientSession] = None

    async def __aenter__(self):
        self._stack = AsyncExitStack()
        read, write = await self._stack.enter_async_context(stdio_client(self.params))
        self.session = await self._stack.enter_async_context(ClientSession(read, write))
        await asyncio.wait_for(self.session.initialize(), timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._stack:
            await self._stack.aclose()
        self._stack = None
        self.session = None

    async def list_tools(self) -> List[Dict[str, Any]]:
        resp = await asyncio.wait_for(self.session.list_tools(), timeout=self.timeout)
        return [t.model_dump() for t in resp.tools]

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        result = await asyncio.wait_for(self.session.call_tool(name, arguments), timeout=self.timeout)
        return result.model_dump()  # 同上，转成 dict
