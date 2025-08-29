"""
Minimal MCP HTTP Server Implementation  
=======================================

Provides HTTP-based MCP server communication for services like GitHub.
"""

import aiohttp
import json
import uuid
from typing import Any, Dict, List, Optional
from src.logger import get_logger

logger = get_logger(__name__)


class MCPHttpServer:
    """Minimal MCP server implementation using HTTP/SSE communication."""
    
    def __init__(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30
    ):
        """
        Initialize MCP HTTP server.
        
        Args:
            url: MCP server URL
            headers: HTTP headers (e.g., Authorization)
            timeout: Timeout for operations in seconds
        """
        self.url = url.rstrip('/')
        self.headers = headers or {}
        self.timeout = timeout
        self.session = None
        self._tools_cache = None
        self._session_id = None
        
    async def start(self):
        """Start the HTTP session and initialize connection."""
        try:
            # Create aiohttp session
            timeout_config = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(
                headers=self.headers,
                timeout=timeout_config
            )
            
            # Initialize MCP session
            await self._initialize_session()
            
            logger.debug(f"Connected to MCP HTTP server: {self.url}")
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP HTTP server: {e}")
            if self.session:
                await self.session.close()
            raise
    
    async def stop(self):
        """Stop the HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
            logger.debug("MCP HTTP server connection closed")
    
    async def _initialize_session(self):
        """Initialize MCP session with the server."""
        # Create session
        create_url = f"{self.url}/sessions"
        
        payload = {
            "id": str(uuid.uuid4()),
            "capabilities": {
                "tools": {}
            }
        }
        
        async with self.session.post(create_url, json=payload) as response:
            if response.status != 200:
                text = await response.text()
                raise Exception(f"Failed to create MCP session: {response.status} - {text}")
            
            data = await response.json()
            self._session_id = data.get("sessionId", payload["id"])
            
        logger.debug(f"MCP session created: {self._session_id}")
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        List available tools from the MCP server.
        
        Returns:
            List of tool definitions
        """
        if self._tools_cache is not None:
            return self._tools_cache
        
        if not self.session:
            raise Exception("MCP HTTP server not connected")
        
        # For HTTP-based MCP, tools are typically listed via a specific endpoint
        list_url = f"{self.url}/tools"
        
        async with self.session.get(list_url) as response:
            if response.status != 200:
                text = await response.text()
                raise Exception(f"Failed to list tools: {response.status} - {text}")
            
            data = await response.json()
            self._tools_cache = data.get("tools", [])
            
        return self._tools_cache
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call a tool on the MCP server.
        
        Args:
            name: Tool name
            arguments: Tool arguments
            
        Returns:
            Tool execution result
        """
        if not self.session:
            raise Exception("MCP HTTP server not connected")
        
        # For HTTP-based MCP, tool calls are made via POST
        call_url = f"{self.url}/tools/call"
        
        payload = {
            "sessionId": self._session_id,
            "name": name,
            "arguments": arguments
        }
        
        async with self.session.post(call_url, json=payload) as response:
            if response.status != 200:
                text = await response.text()
                raise Exception(f"Tool call failed: {response.status} - {text}")
            
            data = await response.json()
            return data.get("result", {})
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()