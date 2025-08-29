"""
Minimal MCP Stdio Server Implementation
========================================

Provides stdio-based MCP server communication for services like
Notion, Filesystem, Playwright, and Postgres.
"""

import asyncio
import json
import os
import uuid
from typing import Any, Dict, List, Optional
from src.logger import get_logger

logger = get_logger(__name__)


class MCPStdioServer:
    """Minimal MCP server implementation using stdio communication."""
    
    def __init__(
        self,
        command: str,
        args: List[str],
        env: Optional[Dict[str, str]] = None,
        timeout: int = 120
    ):
        """
        Initialize MCP stdio server.
        
        Args:
            command: Command to execute (e.g., 'npx', 'pipx')
            args: Command arguments
            env: Environment variables
            timeout: Timeout for operations in seconds
        """
        self.command = command
        self.args = args
        self.env = env or {}
        self.timeout = timeout
        self.process = None
        self._tools_cache = None
        self._request_id = 0
        
    async def start(self):
        """Start the MCP server process."""
        try:
            # Merge environment variables
            full_env = {**os.environ, **self.env}
            
            # Start the subprocess
            self.process = await asyncio.create_subprocess_exec(
                self.command,
                *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=full_env
            )
            
            logger.debug(f"Started MCP server: {self.command} {' '.join(self.args)}")
            
            # Wait for server to be ready (give it some time to initialize)
            await asyncio.sleep(2)
            
            # Initialize connection
            await self._initialize_connection()
            
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            raise
    
    async def stop(self):
        """Stop the MCP server process."""
        if self.process:
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=5)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()
            finally:
                self.process = None
                logger.debug("MCP server stopped")
    
    async def _initialize_connection(self):
        """Initialize JSON-RPC connection with the server."""
        # Send initialize request
        request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "0.1.0",
                "capabilities": {
                    "tools": {}
                },
                "clientInfo": {
                    "name": "MCPMark",
                    "version": "1.0.0"
                }
            },
            "id": self._get_next_id()
        }
        
        response = await self._send_request(request)
        if "error" in response:
            raise Exception(f"Failed to initialize MCP server: {response['error']}")
        
        # Send initialized notification
        notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        await self._send_notification(notification)
        
        logger.debug("MCP server initialized successfully")
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        List available tools from the MCP server.
        
        Returns:
            List of tool definitions
        """
        if self._tools_cache is not None:
            return self._tools_cache
            
        request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": self._get_next_id()
        }
        
        response = await self._send_request(request)
        
        if "error" in response:
            raise Exception(f"Failed to list tools: {response['error']}")
        
        self._tools_cache = response.get("result", {}).get("tools", [])
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
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": arguments
            },
            "id": self._get_next_id()
        }
        
        response = await self._send_request(request)
        
        if "error" in response:
            raise Exception(f"Tool call failed: {response['error']}")
        
        return response.get("result", {})
    
    async def _send_request(self, request: Dict) -> Dict:
        """Send a JSON-RPC request and wait for response."""
        if not self.process or not self.process.stdin:
            raise Exception("MCP server not running")
        
        # Send request
        request_str = json.dumps(request) + "\n"
        self.process.stdin.write(request_str.encode())
        await self.process.stdin.drain()
        
        # Read response
        response_line = await asyncio.wait_for(
            self.process.stdout.readline(),
            timeout=self.timeout
        )
        
        if not response_line:
            raise Exception("No response from MCP server")
        
        try:
            response = json.loads(response_line.decode())
            return response
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse response: {response_line}")
            raise e
    
    async def _send_notification(self, notification: Dict):
        """Send a JSON-RPC notification (no response expected)."""
        if not self.process or not self.process.stdin:
            raise Exception("MCP server not running")
        
        notification_str = json.dumps(notification) + "\n"
        self.process.stdin.write(notification_str.encode())
        await self.process.stdin.drain()
    
    def _get_next_id(self) -> str:
        """Generate next request ID."""
        self._request_id += 1
        return str(self._request_id)
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()