"""
MCPMark Agent Implementation
============================

Unified agent using LiteLLM for all model interactions with minimal MCP support.
"""

import asyncio
import json
import time
import uuid
from typing import Any, Dict, List, Optional, Callable

import litellm
import nest_asyncio

from src.logger import get_logger
from .mcp import MCPStdioServer, MCPHttpServer
from .utils import TokenUsageTracker

# Apply nested asyncio support
nest_asyncio.apply()

# Configure LiteLLM
litellm.suppress_debug_info = True

logger = get_logger(__name__)

# import os
# os.environ["ANTHROPIC_API_BASE"] = "https://aihubmix.com"


class MCPMarkAgent:
    """
    Unified agent for LLM and MCP server management using LiteLLM.
    
    - Anthropic models: Native MCP support via extra_body
    - Other models: Manual MCP server management with function calling
    """
    
    # Constants
    MAX_TURNS = 2
    DEFAULT_TIMEOUT = 600
    
    # Service categories
    STDIO_SERVICES = ["notion", "filesystem", "playwright", "playwright_webarena", "postgres"]
    HTTP_SERVICES = ["github"]
    
    def __init__(
        self,
        model_name: str,
        api_key: str,
        mcp_service: str,
        timeout: int = DEFAULT_TIMEOUT,
        service_config: Optional[Dict[str, Any]] = None,
        service_config_provider: Optional[Callable[[], Dict]] = None,
        reasoning_effort: Optional[str] = "default",
    ):
        """
        Initialize the MCPMark agent.
        
        Args:
            model_name: Name of the LLM model
            api_key: API key for the model provider
            mcp_service: MCP service type
            timeout: Execution timeout in seconds
            service_config: Service-specific configuration
            service_config_provider: Optional provider for dynamic config
            reasoning_effort: Reasoning effort level ("default", "minimal", "low", "medium", "high")
        """
        self.model_name = model_name
        self.api_key = api_key
        self.mcp_service = mcp_service
        self.timeout = timeout
        self.service_config = service_config or {}
        self._service_config_provider = service_config_provider
        self.reasoning_effort = reasoning_effort
        
        # Detect if this is an Anthropic model with HTTP MCP service
        self.is_anthropic = self._is_anthropic_model(model_name)
        self.use_anthropic_native = self.is_anthropic and mcp_service in self.HTTP_SERVICES
        
        # Initialize usage tracker
        self.usage_tracker = TokenUsageTracker()
        
        # Track the actual model name from responses
        self.litellm_run_model_name = None
        
        logger.debug(
            f"Initialized MCPMarkAgent for '{mcp_service}' with model '{model_name}' "
            f"(Anthropic Native MCP: {self.use_anthropic_native}, Reasoning: {reasoning_effort})"
        )
    
    def _is_anthropic_model(self, model_name: str) -> bool:
        """Check if the model is an Anthropic model."""
        return "claud" in model_name
    
    def _refresh_service_config(self):
        """Refresh service config from provider if available."""
        if self._service_config_provider:
            try:
                latest_cfg = self._service_config_provider() or {}
                self.service_config.update(latest_cfg)
            except Exception as e:
                logger.warning(f"Failed to refresh service config: {e}")
    
    async def execute(
        self, 
        instruction: str, 
        tool_call_log_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute instruction with the agent.
        
        Args:
            instruction: The instruction/prompt to execute
            tool_call_log_file: Optional path to log tool calls
            
        Returns:
            Dictionary containing execution results
        """
        start_time = time.time()
        
        try:
            # Refresh service configuration
            self._refresh_service_config()
            
            if self.use_anthropic_native:
                # Use native MCP support only for Anthropic + HTTP MCP services (e.g., GitHub)
                result = await self._execute_anthropic_native(
                    instruction, tool_call_log_file
                )
            else:
                # Use manual MCP management for all other cases
                # This includes: non-Anthropic models, or Anthropic with STDIO services
                result = await self._execute_with_manual_mcp(
                    instruction, tool_call_log_file
                )
            
            execution_time = time.time() - start_time
            
            # Update usage statistics
            self.usage_tracker.update(
                success=result["success"],
                token_usage=result.get("token_usage", {}),
                turn_count=result.get("turn_count", 0),
                execution_time=execution_time
            )
            
            result["execution_time"] = execution_time
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Agent execution failed: {e}"
            logger.error(error_msg, exc_info=True)
            
            self.usage_tracker.update(
                success=False,
                token_usage={},
                turn_count=0,
                execution_time=execution_time
            )
            
            return {
                "success": False,
                "output": [],
                "token_usage": {},
                "turn_count": 0,
                "execution_time": execution_time,
                "error": str(e)
            }
    
    async def _execute_anthropic_native(
        self, 
        instruction: str,
        tool_call_log_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute using Anthropic's native MCP support for HTTP-based services.
        Only used for Claude models with GitHub MCP service.
        """
        logger.debug("Using Anthropic native MCP execution for HTTP service")
        
        # Get MCP configuration for Anthropic
        mcp_config = self._get_anthropic_mcp_config()
        
        # Prepare messages
        messages = [{"role": "user", "content": instruction}]
        
        # Prepare extra headers and body for Anthropic
        extra_headers = {
            "anthropic-version": "2023-06-01",
            "anthropic-beta": "mcp-client-2025-04-04",
        }
        
        extra_body = {
            "mcp_servers": [mcp_config],
        }
        
        return await self._get_anthropic_response(
            messages, extra_headers, extra_body, tool_call_log_file
        )
    
    async def _get_anthropic_response(
        self,
        messages: List[Dict],
        extra_headers: Dict,
        extra_body: Dict,
        tool_call_log_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get non-streaming response from Anthropic."""
        try:
            # Build completion kwargs
            completion_kwargs = {
                "model": self.model_name,
                "messages": messages,
                "api_key": self.api_key,
                "extra_headers": extra_headers,
                "extra_body": extra_body,
            }
            
            # Add reasoning_effort if specified
            if self.reasoning_effort != "default":
                completion_kwargs["reasoning_effort"] = self.reasoning_effort
            
            response = await litellm.acompletion(**completion_kwargs)
            
            # Extract actual model name from response
            if hasattr(response, 'model') and response.model:
                self.litellm_run_model_name = response.model
            
            # Extract response content
            content = response.choices[0].message.content if response.choices else ""
            
            # Extract token usage including reasoning tokens
            token_usage = {}
            if hasattr(response, 'usage') and response.usage:
                token_usage = {
                    "input_tokens": response.usage.prompt_tokens or 0,
                    "output_tokens": response.usage.completion_tokens or 0,
                    "total_tokens": response.usage.total_tokens or 0
                }
                
                # Extract reasoning tokens if available
                if hasattr(response.usage, 'completion_tokens_details'):
                    details = response.usage.completion_tokens_details
                    if hasattr(details, 'reasoning_tokens'):
                        token_usage["reasoning_tokens"] = details.reasoning_tokens or 0
            
            # Log to file if specified
            if tool_call_log_file and content:
                with open(tool_call_log_file, 'a', encoding='utf-8') as f:
                    f.write(content + "\n")
            
            # Display token usage
            if token_usage:
                log_msg = (
                    f"\n| Token usage: Total: {token_usage['total_tokens']:,} | "
                    f"Input: {token_usage['input_tokens']:,} | "
                    f"Output: {token_usage['output_tokens']:,}"
                )
                if "reasoning_tokens" in token_usage:
                    log_msg += f" | Reasoning: {token_usage['reasoning_tokens']:,}"
                logger.info(log_msg)
            
            # Convert to SDK format for backward compatibility
            messages_with_response = messages + [{"role": "assistant", "content": content}]
            sdk_format_messages = self._convert_to_sdk_format(messages_with_response)
            
            return {
                "success": True,
                "output": sdk_format_messages,
                "token_usage": token_usage,
                "turn_count": 1,
                "error": None,
                "litellm_run_model_name": self.litellm_run_model_name
            }
            
        except Exception as e:
            logger.error(f"Anthropic execution failed: {e}")
            raise
    
    async def _execute_with_manual_mcp(
        self,
        instruction: str,
        tool_call_log_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute with manual MCP server management.
        Used for all non-Anthropic models and Anthropic models with STDIO services.
        """
        logger.debug("Using manual MCP execution with function calling loop")
        
        # Create and start MCP server
        mcp_server = await self._create_mcp_server()
        
        try:
            async with mcp_server:
                # Get available tools
                tools = await mcp_server.list_tools()
                
                # Convert MCP tools to OpenAI function format
                functions = self._convert_mcp_tools_to_functions(tools)
                
                # Execute with function calling loop
                return await self._execute_function_calling_loop(
                    instruction, functions, mcp_server, tool_call_log_file
                )
                
        except Exception as e:
            logger.error(f"Manual MCP execution failed: {e}")
            raise
    
    def _convert_to_sdk_format(self, messages: List[Dict]) -> List[Dict]:
        """Convert OpenAI messages format to old SDK format for backward compatibility."""
        sdk_format = []
        function_call_map = {}  # Track function names to call IDs for legacy format
        
        for msg in messages:
            role = msg.get("role")
            
            if role == "user":
                # User messages stay mostly the same
                sdk_format.append({
                    "content": msg.get("content", ""),
                    "role": "user"
                })
                
            elif role == "assistant":
                # Check for tool calls
                tool_calls = msg.get("tool_calls", [])
                if tool_calls:
                    # Add tool calls as separate entries
                    for tool_call in tool_calls:
                        call_id = tool_call.get("id", f"call_{uuid.uuid4().hex}")
                        func_name = tool_call.get("function", {}).get("name", "")
                        sdk_format.append({
                            "arguments": tool_call.get("function", {}).get("arguments", "{}"),
                            "call_id": call_id,
                            "name": func_name,
                            "type": "function_call",
                            "id": "__fake_id__"
                        })
                
                # Check for legacy function calls
                function_call = msg.get("function_call")
                if function_call:
                    func_name = function_call.get("name", "")
                    call_id = f"call_{uuid.uuid4().hex}"
                    function_call_map[func_name] = call_id  # Store for matching responses
                    sdk_format.append({
                        "arguments": function_call.get("arguments", "{}"),
                        "call_id": call_id,
                        "name": func_name,
                        "type": "function_call",
                        "id": "__fake_id__"
                    })
                
                # Only add assistant message if there's content or it's the final message
                content = msg.get("content")
                if content or (not tool_calls and not function_call):
                    sdk_format.append({
                        "id": "__fake_id__",
                        "content": [
                            {
                                "annotations": [],
                                "text": content if content else "",
                                "type": "output_text"
                            }
                        ],
                        "role": "assistant",
                        "status": "completed",
                        "type": "message"
                    })
                
            elif role == "tool":
                # Tool responses
                sdk_format.append({
                    "call_id": msg.get("tool_call_id", ""),
                    "output": json.dumps({
                        "type": "text",
                        "text": msg.get("content", ""),
                        "annotations": None,
                        "meta": None
                    }),
                    "type": "function_call_output"
                })
                
            elif role == "function":
                # Legacy function responses - try to match with stored call ID
                func_name = msg.get("name", "")
                call_id = function_call_map.get(func_name, f"call_{uuid.uuid4().hex}")
                sdk_format.append({
                    "call_id": call_id,
                    "output": json.dumps({
                        "type": "text",
                        "text": msg.get("content", ""),
                        "annotations": None,
                        "meta": None
                    }),
                    "type": "function_call_output"
                })
        
        return sdk_format
    
    async def _execute_function_calling_loop(
        self,
        instruction: str,
        functions: List[Dict],
        mcp_server: Any,
        tool_call_log_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute function calling loop with LiteLLM."""
        messages = [{"role": "user", "content": instruction}]
        total_tokens = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "reasoning_tokens": 0}
        turn_count = 0
        max_turns = self.MAX_TURNS  # Limit turns to prevent infinite loops
        
        # Convert functions to tools format for newer models
        tools = [{"type": "function", "function": func} for func in functions] if functions else None
        
        while turn_count < max_turns:
            turn_count += 1
            
            # Build completion kwargs
            completion_kwargs = {
                "model": self.model_name,
                "messages": messages,
                "tools": tools,
                "tool_choice": "auto" if tools else None,
                "api_key": self.api_key,
            }
            
            # Add reasoning_effort if specified
            if self.reasoning_effort != "default":
                completion_kwargs["reasoning_effort"] = self.reasoning_effort
            
            # Call LiteLLM with tools
            response = await litellm.acompletion(**completion_kwargs)
            
            # Extract actual model name from response (first turn only)
            if turn_count == 1 and hasattr(response, 'model') and response.model:
                self.litellm_run_model_name = response.model
            
            # Update token usage including reasoning tokens
            if hasattr(response, 'usage') and response.usage:
                total_tokens["input_tokens"] += response.usage.prompt_tokens or 0
                total_tokens["output_tokens"] += response.usage.completion_tokens or 0
                total_tokens["total_tokens"] += response.usage.total_tokens or 0
                
                # Extract reasoning tokens if available
                if hasattr(response.usage, 'completion_tokens_details'):
                    details = response.usage.completion_tokens_details
                    if hasattr(details, 'reasoning_tokens'):
                        total_tokens["reasoning_tokens"] += details.reasoning_tokens or 0
            
            # Get response message
            message = response.choices[0].message
            # Convert to dict (prefer model_dump over deprecated dict())
            if hasattr(message, 'model_dump'):
                message_dict = message.model_dump()
            else:
                # Fallback for simple dict-like objects or legacy versions
                message_dict = dict(message)
            messages.append(message_dict)
            
            # Log assistant's text content if present
            if hasattr(message, 'content') and message.content:
                # Display the content with line prefix
                for line in message.content.splitlines():
                    logger.info(f"| {line}")
                
                # Also log to file if specified
                if tool_call_log_file:
                    with open(tool_call_log_file, 'a', encoding='utf-8') as f:
                        f.write(f"{message.content}\n")
            
            # Check for tool calls (newer format)
            if hasattr(message, 'tool_calls') and message.tool_calls:
                # Process tool calls
                for tool_call in message.tool_calls:
                    func_name = tool_call.function.name
                    func_args = json.loads(tool_call.function.arguments)
                    
                    # Format arguments for display (truncate if too long)
                    args_str = json.dumps(func_args, separators=(",", ": "))
                    display_arguments = args_str[:140] + "..." if len(args_str) > 140 else args_str
                    
                    # Log with ANSI color codes (bold tool name, dim gray arguments)
                    logger.info(f"| \033[1m{func_name}\033[0m \033[2;37m{display_arguments}\033[0m")
                    
                    if tool_call_log_file:
                        with open(tool_call_log_file, 'a', encoding='utf-8') as f:
                            f.write(f"| {func_name} {args_str}\n")
                    
                    try:
                        # Call the MCP tool
                        result = await mcp_server.call_tool(func_name, func_args)
                        
                        # Add tool result to messages (using tool role)
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(result)
                        })
                        
                    except Exception as e:
                        logger.error(f"Tool call failed: {e}")
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": f"Error: {str(e)}"
                        })
            else:
                # No tool/function call, we're done
                break
        
        # Display final token usage
        if total_tokens["total_tokens"] > 0:
            log_msg = (
                f"|\n| Token usage: Total: {total_tokens['total_tokens']:,} | "
                f"Input: {total_tokens['input_tokens']:,} | "
                f"Output: {total_tokens['output_tokens']:,}"
            )
            if total_tokens.get("reasoning_tokens", 0) > 0:
                log_msg += f" | Reasoning: {total_tokens['reasoning_tokens']:,}"
            logger.info(log_msg)
            logger.info(f"| Turns: {turn_count}")
        
        # Convert messages to SDK format for backward compatibility
        sdk_format_messages = self._convert_to_sdk_format(messages)
        
        return {
            "success": True,
            "output": sdk_format_messages,
            "token_usage": total_tokens,
            "turn_count": turn_count,
            "error": None,
            "litellm_run_model_name": self.litellm_run_model_name
        }
    
    def _convert_mcp_tools_to_functions(self, tools: List[Dict]) -> List[Dict]:
        """Convert MCP tool definitions to OpenAI function format."""
        functions = []
        
        for tool in tools:
            function = {
                "name": tool.get("name"),
                "description": tool.get("description", ""),
                "parameters": tool.get("inputSchema", {
                    "type": "object",
                    "properties": {},
                    "required": []
                })
            }
            functions.append(function)
        
        return functions
    
    def _get_anthropic_mcp_config(self) -> Dict[str, Any]:
        """Get MCP configuration for Anthropic native support."""
        if self.mcp_service == "github":
            return {
                "type": "url",
                "url": "https://api.githubcopilot.com/mcp/",
                "name": "github",
                "authorization_token": self.service_config.get("github_token", "")
            }
        else:
            # For stdio-based services, Anthropic expects a different format
            # This would need to be implemented based on Anthropic's requirements
            raise NotImplementedError(
                f"Anthropic native MCP for {self.mcp_service} not yet implemented"
            )
    
    async def _create_mcp_server(self) -> Any:
        """Create and return an MCP server instance."""
        if self.mcp_service in self.STDIO_SERVICES:
            return self._create_stdio_server()
        elif self.mcp_service in self.HTTP_SERVICES:
            return self._create_http_server()
        else:
            raise ValueError(f"Unsupported MCP service: {self.mcp_service}")
    
    def _create_stdio_server(self) -> MCPStdioServer:
        """Create stdio-based MCP server."""
        if self.mcp_service == "notion":
            notion_key = self.service_config.get("notion_key")
            if not notion_key:
                raise ValueError("Notion API key required")
            
            return MCPStdioServer(
                command="npx",
                args=["-y", "@notionhq/notion-mcp-server"],
                env={
                    "OPENAPI_MCP_HEADERS": (
                        '{"Authorization": "Bearer ' + notion_key + '", '
                        '"Notion-Version": "2022-06-28"}'
                    )
                }
            )
        
        elif self.mcp_service == "filesystem":
            test_directory = self.service_config.get("test_directory")
            if not test_directory:
                raise ValueError("Test directory required for filesystem service")
            
            return MCPStdioServer(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-filesystem", str(test_directory)]
            )
        
        elif self.mcp_service in ["playwright", "playwright_webarena"]:
            browser = self.service_config.get("browser", "chromium")
            headless = self.service_config.get("headless", True)
            viewport_width = self.service_config.get("viewport_width", 1280)
            viewport_height = self.service_config.get("viewport_height", 720)
            
            args = ["-y", "@playwright/mcp@latest"]
            if headless:
                args.append("--headless")
            args.extend([
                "--isolated",
                "--no-sandbox",
                "--browser", browser,
                "--viewport-size", f"{viewport_width},{viewport_height}"
            ])
            
            return MCPStdioServer(command="npx", args=args)
        
        elif self.mcp_service == "postgres":
            host = self.service_config.get("host", "localhost")
            port = self.service_config.get("port", 5432)
            username = self.service_config.get("username")
            password = self.service_config.get("password")
            database = self.service_config.get("current_database") or self.service_config.get("database")
            
            if not all([username, password, database]):
                raise ValueError("PostgreSQL requires username, password, and database")
            
            database_url = f"postgresql://{username}:{password}@{host}:{port}/{database}"
            
            return MCPStdioServer(
                command="pipx",
                args=["run", "postgres-mcp", "--access-mode=unrestricted"],
                env={"DATABASE_URI": database_url}
            )
        
        else:
            raise ValueError(f"Unsupported stdio service: {self.mcp_service}")
    
    def _create_http_server(self) -> MCPHttpServer:
        """Create HTTP-based MCP server."""
        if self.mcp_service == "github":
            github_token = self.service_config.get("github_token")
            if not github_token:
                raise ValueError("GitHub token required")
            
            return MCPHttpServer(
                url="https://api.githubcopilot.com/mcp/",
                headers={
                    "Authorization": f"Bearer {github_token}",
                    "User-Agent": "MCPMark/1.0"
                }
            )
        else:
            raise ValueError(f"Unsupported HTTP service: {self.mcp_service}")
    
    def execute_sync(
        self,
        instruction: str,
        tool_call_log_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Synchronous wrapper for execute method.
        """
        try:
            return asyncio.run(self.execute(instruction, tool_call_log_file))
        except asyncio.TimeoutError:
            self.usage_tracker.update(False, {}, 0, self.timeout)
            return {
                "success": False,
                "output": [],
                "token_usage": {},
                "turn_count": 0,
                "execution_time": self.timeout,
                "error": f"Execution timed out after {self.timeout} seconds"
            }
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        return self.usage_tracker.get_stats()
    
    def reset_usage_stats(self):
        """Reset usage statistics."""
        self.usage_tracker.reset()
    
    def __repr__(self):
        return (
            f"MCPMarkAgent(service='{self.mcp_service}', model='{self.model_name}', "
            f"anthropic={self.is_anthropic})"
        )