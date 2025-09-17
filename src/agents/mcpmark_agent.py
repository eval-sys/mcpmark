"""
MCPMark Agent Implementation
============================

Unified agent using LiteLLM for all model interactions with minimal MCP support.
"""

import asyncio
import json
import time
import uuid
import copy
 
from typing import Any, Dict, List, Optional, Callable

import httpx
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

class MCPMarkAgent:
    """
    Unified agent for LLM and MCP server management using LiteLLM.
    
    - Anthropic models: Native MCP support via extra_body
    - Other models: Manual MCP server management with function calling
    """
    
    # Constants
    MAX_TURNS = 100
    DEFAULT_TIMEOUT = 600
    SYSTEM_PROMPT = (
        "You are a helpful agent that uses tools iteratively to complete the user's task, "
        "and when finished, provides the final answer or simply states \"Task completed\" without further tool calls."
    )
    
    # Service categories
    STDIO_SERVICES = ["notion", "filesystem", "playwright", "playwright_webarena", "postgres"]
    HTTP_SERVICES = ["github"]
    
    # Claude thinking budget mapping
    CLAUDE_THINKING_BUDGETS = {
        "low": 1024,
        "medium": 2048,
        "high": 4096
    }
    
    # ==================== Initialization and Configuration ====================

    def __init__(
        self,
        litellm_input_model_name: str,
        api_key: str,
        base_url: str,
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
            base_url: Base url
            mcp_service: MCP service type
            timeout: Execution timeout in seconds
            service_config: Service-specific configuration
            service_config_provider: Optional provider for dynamic config
            reasoning_effort: Reasoning effort level ("default", "minimal", "low", "medium", "high")
        """
        self.litellm_input_model_name = litellm_input_model_name
        self.api_key = api_key
        self.base_url = base_url
        self.mcp_service = mcp_service
        self.timeout = timeout
        self.service_config = service_config or {}
        self._service_config_provider = service_config_provider
        self.reasoning_effort = reasoning_effort
        
        # Detect if this is a Claude model
        self.is_claude = self._is_anthropic_model(litellm_input_model_name)
        
        # Determine execution path: Claude with thinking or LiteLLM
        self.use_claude_thinking = self.is_claude and reasoning_effort != "default"
        
        # Initialize usage tracker
        self.usage_tracker = TokenUsageTracker()
        
        # Track the actual model name from responses
        self.litellm_run_model_name = None

        # Track partial progress for error/timeout handling
        self._partial_messages = []
        self._partial_token_usage = {}
        self._partial_turn_count = 0
        
        logger.debug(
            f"Initialized MCPMarkAgent for '{mcp_service}' with model '{litellm_input_model_name}' "
            f"(Claude: {self.is_claude}, Thinking: {self.use_claude_thinking}, Reasoning: {reasoning_effort})"
        )
    

    def __repr__(self):
        return (
            f"MCPMarkAgent(service='{self.mcp_service}', model='{self.litellm_input_model_name}', "
        )

    def _is_anthropic_model(self, model_name: str) -> bool:
        """Check if the model is an Anthropic model."""
        return "claude" in model_name.lower()
    

    def _get_claude_thinking_budget(self) -> Optional[int]:
        """Get thinking budget for Claude based on reasoning effort."""
        if not self.use_claude_thinking:
            return None
        return self.CLAUDE_THINKING_BUDGETS.get(self.reasoning_effort, 2048)
    

    def _refresh_service_config(self):
        """Refresh service config from provider if available."""
        if self._service_config_provider:
            try:
                latest_cfg = self._service_config_provider() or {}
                self.service_config.update(latest_cfg)
            except Exception as e:
                logger.warning(f"| Failed to refresh service config: {e}")

    def _reset_progress(self):
        """Reset stored partial progress for a new execution run."""
        self._partial_messages = []
        self._partial_token_usage = {}
        self._partial_turn_count = 0

    def _update_progress(self, messages: List[Dict], token_usage: Dict, turn_count: int):
        """Record partial progress so we can return it on timeout/errors."""
        try:
            # Deep copy to avoid mutation by callers
            self._partial_messages = copy.deepcopy(messages)
            self._partial_token_usage = dict(token_usage or {})
            self._partial_turn_count = int(turn_count or 0)
        except Exception:
            # Best-effort; don't let progress recording crash execution
            pass
    


    # ==================== Public Interface Methods ====================

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
            # Reset partial progress for this run
            self._reset_progress()
            # Refresh service configuration
            self._refresh_service_config()
            
            # Execute with timeout control
            async def _execute_with_strategy():
                if self.use_claude_thinking:
                    # Claude with thinking -> native Anthropic API with tools
                    return await self._execute_claude_native_with_tools(
                        instruction, tool_call_log_file
                    )
                else:
                    # All other cases -> LiteLLM with tools
                    return await self._execute_litellm_with_tools(
                        instruction, tool_call_log_file
                    )
            
            # Apply timeout to the entire execution
            result = await asyncio.wait_for(
                _execute_with_strategy(),
                timeout=self.timeout
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
            if isinstance(e, asyncio.TimeoutError):
                error_msg = f"Execution timed out after {self.timeout} seconds"
                logger.error(error_msg)
            else:
                error_msg = f"Agent execution failed: {e}"
                logger.error(error_msg, exc_info=True)
            
            self.usage_tracker.update(
                success=False,
                token_usage=self._partial_token_usage or {},
                turn_count=self._partial_turn_count or 0,
                execution_time=execution_time
            )

            if self._partial_messages:
                if not self.is_claude:
                    final_msg = self._convert_to_sdk_format(self._partial_messages)
                else:
                    final_msg = self._partial_messages
            else:
                final_msg = []
                
            return {
                "success": False,
                "output": final_msg,
                "token_usage": self._partial_token_usage or {},
                "turn_count": self._partial_turn_count or 0,
                "execution_time": execution_time,
                "error": error_msg,
                "litellm_run_model_name": self.litellm_run_model_name,
            }
            

    def execute_sync(
        self,
        instruction: str,
        tool_call_log_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Synchronous wrapper for execute method.
        """
        return asyncio.run(self.execute(instruction, tool_call_log_file))
    

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        return self.usage_tracker.get_stats()
    

    def reset_usage_stats(self):
        """Reset usage statistics."""
        self.usage_tracker.reset()
    


    # ==================== Claude Native API Execution Path ====================

    async def _execute_claude_native_with_tools(
        self,
        instruction: str,
        tool_call_log_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute Claude with thinking using native Anthropic API.
        Creates MCP server, gets tools, and executes with thinking.
        """
        logger.debug("Using Claude native API with thinking")
        
        thinking_budget = self._get_claude_thinking_budget()
        
        # Create and start MCP server
        mcp_server = await self._create_mcp_server()
        
        async with mcp_server:
            # Get available tools
            tools = await mcp_server.list_tools()
            
            # Convert MCP tools to Anthropic format
            anthropic_tools = self._convert_to_anthropic_format(tools)
            
            # Execute with function calling loop
            return await self._execute_anthropic_native_tool_loop(
                instruction, anthropic_tools, mcp_server, 
                thinking_budget, tool_call_log_file
            )
    

    async def _call_claude_native_api(
        self,
        messages: List[Dict],
        thinking_budget: int,
        tools: Optional[List[Dict]] = None,
        mcp_servers: Optional[List[Dict]] = None,
        system: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Call Claude's native API directly using httpx.
        
        Args:
            messages: Conversation messages
            thinking_budget: Token budget for thinking
            tools: Tool definitions for function calling
            mcp_servers: MCP server configurations
            system: System prompt
            
        Returns:
            API response as dictionary
        """
        # Get API base and headers
        import os
        api_base = os.getenv("ANTHROPIC_API_BASE", "https://api.anthropic.com") 
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
            "anthropic-beta": "context-1m-2025-08-07" # by default
        } 
        
        # Build payload
        max_tokens = max(thinking_budget + 4096, 4096)
        payload = {
            "model": self.litellm_input_model_name.replace("anthropic/", ""),
            "max_tokens": max_tokens,
            "messages": messages,
        }
        
        # Add thinking configuration
        if thinking_budget:
            payload["thinking"] = {
                "type": "enabled",
                "budget_tokens": thinking_budget
            }
        
        # Add tools if provided
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = {"type": "auto"}
        
        # Add MCP servers if provided
        if mcp_servers:
            headers["anthropic-beta"] = "mcp-client-2025-04-04"
            payload["mcp_servers"] = mcp_servers
        
        # Add system prompt if provided
        if system:
            payload["system"] = system
        
        # Make the API call
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{api_base}/v1/messages",
                    headers=headers,
                    json=payload,
                    timeout=self.timeout
                )
                response.raise_for_status()
                return response.json(), None
            except httpx.HTTPStatusError as e:
                return None, e.response.text
            except Exception as e:
                return None, e
    

    async def _execute_anthropic_native_tool_loop(
        self,
        instruction: str,
        tools: List[Dict],
        mcp_server: Any,
        thinking_budget: int,
        tool_call_log_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute Claude thinking loop with function calling.
        Handles thinking blocks, tool calls, and message formatting.
        """
        messages = [{"role": "user", "content": instruction}]
        total_tokens = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "reasoning_tokens": 0}
        turn_count = 0
        max_turns = self.MAX_TURNS
        hit_turn_limit = False
        ended_normally = False
        
        system_text = self.SYSTEM_PROMPT
        # Record initial state
        self._update_progress(messages, total_tokens, turn_count)
        
        for _ in range(max_turns):
            turn_count += 1
            
            # Call Claude native API
            response, error_msg = await self._call_claude_native_api(
                messages=messages,
                thinking_budget=thinking_budget,
                tools=tools,
                system=system_text
            )
            if turn_count == 1:
                self.litellm_run_model_name = response['model'].split("/")[-1]
            
            if error_msg:
                break
            
            # Update token usage
            if "usage" in response:
                usage = response["usage"]
                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)
                # Calculate output tokens as total - input for consistency
                total_tokens_count = output_tokens + input_tokens
                
                total_tokens["input_tokens"] += input_tokens
                total_tokens["output_tokens"] += output_tokens
                total_tokens["total_tokens"] += total_tokens_count
                
                ## TODO: add reasoning tokens for claude
            
            # Extract blocks from response
            blocks = response.get("content", [])
            tool_uses = [b for b in blocks if b.get("type") == "tool_use"]
            thinking_blocks = [b for b in blocks if b.get("type") == "thinking"]
            text_blocks = [b for b in blocks if b.get("type") == "text"]
            
            # Log text output
            for tb in text_blocks:
                if tb.get("text") and tool_call_log_file:
                    with open(tool_call_log_file, 'a', encoding='utf-8') as f:
                        f.write(f"{tb['text']}\n")
                if tb.get("text"):
                    for line in tb["text"].splitlines():
                        logger.info(f"| {line}")
            
            # Build assistant message with all blocks
            assistant_content = []
            
            # Add thinking blocks
            for tb in thinking_blocks:
                assistant_content.append({
                    "type": "thinking",
                    "thinking": tb.get("thinking", ""),
                    "signature": tb.get("signature", ""),
                })
            
            # Add text blocks
            for tb in text_blocks:
                if tb.get("text"):
                    assistant_content.append({"type": "text", "text": tb["text"]})
            
            # Add tool_use blocks
            for tu in tool_uses:
                assistant_content.append({
                    "type": "tool_use",
                    "id": tu.get("id"),
                    "name": tu.get("name"),
                    "input": tu.get("input", {}),
                })
            
            messages.append({"role": "assistant", "content": assistant_content})
            
            # Update partial progress after assistant response
            self._update_progress(messages, total_tokens, turn_count)

            # If no tool calls, we're done
            if not tool_uses:
                ended_normally = True
                break
            
            # Execute tools and add results
            tool_results = []
            for tu in tool_uses:
                name = tu.get("name")
                inputs = tu.get("input", {})
                
                # Log tool call
                args_str = json.dumps(inputs, separators=(",", ": "))
                display_args = args_str[:140] + "..." if len(args_str) > 140 else args_str
                logger.info(f"| \033[1m{name}\033[0m \033[2;37m{display_args}\033[0m")
                
                if tool_call_log_file:
                    with open(tool_call_log_file, 'a', encoding='utf-8') as f:
                        f.write(f"| {name} {args_str}\n")
                
                # Execute tool
                try:
                    result = await asyncio.wait_for(
                        mcp_server.call_tool(name, inputs),
                        timeout=60
                    )
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tu["id"],
                        "content": [{"type": "text", "text": json.dumps(result)}],
                    })
                except Exception as e:
                    logger.error(f"Tool call failed: {e}")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tu["id"],
                        "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                    })
            
            messages.append({"role": "user", "content": tool_results})
            # Update partial progress after tool results
            self._update_progress(messages, total_tokens, turn_count)
        
        # Detect if we exited due to hitting the turn limit
        if not ended_normally:
            if turn_count >= max_turns:
                hit_turn_limit = True
                logger.warning(f"| Max turns ({max_turns}) exceeded; returning failure with partial output.")
                if tool_call_log_file:
                    try:
                        with open(tool_call_log_file, 'a', encoding='utf-8') as f:
                            f.write(f"| Max turns ({max_turns}) exceeded\n")
                    except Exception:
                        pass
            elif error_msg:
                logger.warning(f"| {error_msg}\n")
                if tool_call_log_file:
                    try:
                        with open(tool_call_log_file, 'a', encoding='utf-8') as f:
                            f.write(f"| {error_msg}\n")
                    except Exception:
                        pass
        
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
        
        # Convert messages to SDK format
        # sdk_format_messages = self._convert_to_sdk_format(messages)
        
        if hit_turn_limit:
            return {
                "success": False,
                "output": messages,
                "token_usage": total_tokens,
                "turn_count": turn_count,
                "error": f"Max turns ({max_turns}) exceeded",
                "litellm_run_model_name": self.litellm_run_model_name,
            }
        
        if error_msg:
            return {
                "success": False,
                "output": messages,
                "token_usage": total_tokens,
                "turn_count": turn_count,
                "error": error_msg,
                "litellm_run_model_name": self.litellm_run_model_name,
            }
        
        return {
            "success": True,
            "output": messages,
            "token_usage": total_tokens,
            "turn_count": turn_count,
            "error": None,
            "litellm_run_model_name": self.litellm_run_model_name,
        }


    # ==================== LiteLLM Execution Path ====================

    async def _execute_litellm_with_tools(
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
                functions = self._convert_to_openai_format(tools)
                
                # Execute with function calling loop
                return await self._execute_litellm_tool_loop(
                    instruction, functions, mcp_server, tool_call_log_file
                )
                
        except Exception as e:
            logger.error(f"Manual MCP execution failed: {e}")
            raise
        

    async def _execute_litellm_tool_loop(
        self,
        instruction: str,
        functions: List[Dict],
        mcp_server: Any,
        tool_call_log_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute function calling loop with LiteLLM."""
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": instruction}
        ]
        total_tokens = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "reasoning_tokens": 0}
        turn_count = 0
        max_turns = self.MAX_TURNS  # Limit turns to prevent infinite loops
        consecutive_failures = 0
        max_consecutive_failures = 3
        hit_turn_limit = False
        ended_normally = False
        
        # Convert functions to tools format for newer models
        tools = [{"type": "function", "function": func} for func in functions] if functions else None

        # Record initial state
        self._update_progress(messages, total_tokens, turn_count)
        
        try:
            while turn_count < max_turns:
                
                # Build completion kwargs
                completion_kwargs = {
                    "model": self.litellm_input_model_name,
                    "messages": messages,
                    "api_key": self.api_key,
                }
                
                # Always use tools format if available - LiteLLM will handle conversion
                if tools:
                    completion_kwargs["tools"] = tools
                    completion_kwargs["tool_choice"] = "auto"
                
                # Add reasoning_effort and base_url if specified
                if self.reasoning_effort != "default":
                    completion_kwargs["reasoning_effort"] = self.reasoning_effort
                if self.base_url:
                    completion_kwargs["base_url"] = self.base_url
                
                try:
                    # Call LiteLLM with timeout for individual call
                    response = await asyncio.wait_for(
                        litellm.acompletion(**completion_kwargs),
                        timeout = self.timeout / 2  # Use half of total timeout
                    )
                    consecutive_failures = 0  # Reset failure counter on success
                except asyncio.TimeoutError:
                    logger.warning(f"| ✗ LLM call timed out on turn {turn_count + 1}")
                    consecutive_failures += 1
                    if consecutive_failures >= max_consecutive_failures:
                        raise Exception(f"Too many consecutive failures ({consecutive_failures})")
                    await asyncio.sleep(8 ** consecutive_failures)  # Exponential backoff
                    continue
                except Exception as e:
                    logger.error(f"| ✗ LLM call failed on turn {turn_count + 1}: {e}")
                    consecutive_failures += 1
                    if consecutive_failures >= max_consecutive_failures:
                        raise
                    if "ContextWindowExceededError" in str(e):
                        raise
                    elif "RateLimitError" in str(e):
                        await asyncio.sleep(12 ** consecutive_failures)
                    else:
                        await asyncio.sleep(2 ** consecutive_failures)
                    continue
                
                # Extract actual model name from response (first turn only)
                if turn_count == 0 and hasattr(response, 'model') and response.model:
                    self.litellm_run_model_name = response.model.split("/")[-1]
                
                # Update token usage including reasoning tokens
                if hasattr(response, 'usage') and response.usage:
                    input_tokens = response.usage.prompt_tokens or 0
                    total_tokens_count = response.usage.total_tokens or 0
                    # Calculate output tokens as total - input for consistency
                    output_tokens = total_tokens_count - input_tokens if total_tokens_count > 0 else (response.usage.completion_tokens or 0)
                    
                    total_tokens["input_tokens"] += input_tokens
                    total_tokens["output_tokens"] += output_tokens
                    total_tokens["total_tokens"] += total_tokens_count
                    
                    # Extract reasoning tokens if available
                    if hasattr(response.usage, 'completion_tokens_details'):
                        details = response.usage.completion_tokens_details
                        if hasattr(details, 'reasoning_tokens'):
                            total_tokens["reasoning_tokens"] += details.reasoning_tokens or 0
                
                # Get response message
                choices = response.choices
                if len(choices):
                    message = choices[0].message
                    message_dict = message.model_dump() if hasattr(message, 'model_dump') else dict(message)
                    
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
                    messages.append(message_dict)
                    turn_count += 1
                    # Update progress after assistant with tool calls
                    self._update_progress(messages, total_tokens, turn_count)
                    # Process tool calls
                    for tool_call in message.tool_calls:
                        func_name = tool_call.function.name
                        func_args = json.loads(tool_call.function.arguments)
                        
                        try:
                            result = await asyncio.wait_for(
                                mcp_server.call_tool(func_name, func_args),
                                timeout=60
                            )
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": json.dumps(result)
                            })
                        except asyncio.TimeoutError:
                            error_msg = f"Tool call '{func_name}' timed out after 60 seconds"
                            logger.error(error_msg)
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": f"Error: {error_msg}"
                            })
                        except Exception as e:
                            logger.error(f"Tool call failed: {e}")
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": f"Error: {str(e)}"
                            })   
                            
                        # Format arguments for display (truncate if too long)
                        args_str = json.dumps(func_args, separators=(",", ": "))
                        display_arguments = args_str[:140] + "..." if len(args_str) > 140 else args_str
                        
                        # Log with ANSI color codes (bold tool name, dim gray arguments)
                        logger.info(f"| \033[1m{func_name}\033[0m \033[2;37m{display_arguments}\033[0m")
                        
                        if tool_call_log_file:
                            with open(tool_call_log_file, 'a', encoding='utf-8') as f:
                                f.write(f"| {func_name} {args_str}\n")
                    # Update progress after tool results appended
                    self._update_progress(messages, total_tokens, turn_count)
                    continue
                else:
                    # Log end reason
                    if not choices:
                        logger.info("|\n|\n| Task ended with no messages generated by the model.")
                    elif choices[0].finish_reason == "stop":
                        logger.info("|\n|\n| Task ended with the finish reason from messages being 'stop'.")
                    
                    # No tool/function call, add message and we're done
                    messages.append(message_dict)
                    turn_count += 1
                    # Update progress before exiting
                    self._update_progress(messages, total_tokens, turn_count)
                    ended_normally = True
                    break
                
        except Exception as loop_error:
            # On any error, return partial conversation, token usage, and turn count
            logger.error(f"Manual MCP loop failed: {loop_error}", exc_info=True)
            sdk_format_messages = self._convert_to_sdk_format(messages)
            return {
                "success": False,
                "output": sdk_format_messages,
                "token_usage": total_tokens,
                "turn_count": turn_count,
                "error": str(loop_error),
                "litellm_run_model_name": self.litellm_run_model_name,
            }
        
        # Detect if we exited due to hitting the turn limit
        if (not ended_normally) and (turn_count >= max_turns):
            hit_turn_limit = True
            logger.warning(f"| Max turns ({max_turns}) exceeded); returning failure with partial output.")
            if tool_call_log_file:
                try:
                    with open(tool_call_log_file, 'a', encoding='utf-8') as f:
                        f.write(f"| Max turns ({max_turns}) exceeded\n")
                except Exception:
                    pass

        # Display final token usage
        if total_tokens["total_tokens"] > 0:
            log_msg = (
                f"| Token usage: Total: {total_tokens['total_tokens']:,} | "
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
            "success": not hit_turn_limit,
            "output": sdk_format_messages,
            "token_usage": total_tokens,
            "turn_count": turn_count,
            "error": (f"Max turns ({max_turns}) exceeded" if hit_turn_limit else None),
            "litellm_run_model_name": self.litellm_run_model_name
        }
    


    # ==================== Format Conversion Methods ====================

    def _convert_to_sdk_format(self, messages: List[Dict]) -> List[Dict]:
        """Convert OpenAI messages format to old SDK format for backward compatibility."""
        sdk_format = []
        function_call_map = {}  # Track function names to call IDs for legacy format

        for msg in messages:
            role = msg.get("role")

            if role == "user":
                # User messages stay mostly the same
                user_content = msg.get("content", "")
                
                # Handle tool_result messages (content as list)
                if isinstance(user_content, list):
                    # Check if this is a tool_result message
                    tool_results = [item for item in user_content if isinstance(item, dict) and item.get("type") == "tool_result"]
                    if tool_results:
                        # Convert tool_results to function_call_output format
                        for tr in tool_results:
                            content_items = tr.get("content", [])
                            text_content = ""
                            for ci in content_items:
                                if isinstance(ci, dict) and ci.get("type") == "text":
                                    text_content = ci.get("text", "")
                                    break
                            sdk_format.append({
                                "call_id": tr.get("tool_use_id", ""),
                                "output": json.dumps({
                                    "type": "text",
                                    "text": text_content,
                                    "annotations": None,
                                    "meta": None
                                }),
                                "type": "function_call_output"
                            })
                    else:
                        # Regular user content as list - extract text
                        text_parts = []
                        for item in user_content:
                            if isinstance(item, dict) and item.get("type") == "text":
                                text_parts.append(item.get("text", ""))
                        sdk_format.append({
                            "content": "\n".join(text_parts) if text_parts else "",
                            "role": "user"
                        })
                else:
                    # String content
                    sdk_format.append({
                        "content": user_content,
                        "role": "user"
                    })

            elif role == "assistant":
                # === CHANGED ORDER START ===
                tool_calls = msg.get("tool_calls", [])
                function_call = msg.get("function_call")
                content = msg.get("content")

                # Handle both string content and list content (for Claude thinking)
                if isinstance(content, list):
                    # Extract text from content blocks (e.g., Claude responses with thinking)
                    text_parts = []
                    claude_tool_uses = []
                    for block in content:
                        if isinstance(block, dict):
                            if block.get("type") == "text":
                                text_parts.append(block.get("text", ""))
                            elif block.get("type") == "thinking":
                                # Include thinking in output (marked as such)
                                thinking_text = block.get("thinking", "")
                                if thinking_text:
                                    text_parts.append(f"<think>\n{thinking_text}\n</think>")
                            elif block.get("type") == "tool_use":
                                # Store tool_use blocks for later processing
                                claude_tool_uses.append(block)
                    content = "\n".join(text_parts) if text_parts else ""
                    
                    # Add Claude tool_uses to regular tool_calls
                    if claude_tool_uses and not tool_calls:
                        tool_calls = []
                        for tu in claude_tool_uses:
                            tool_calls.append({
                                "id": tu.get("id"),
                                "function": {
                                    "name": tu.get("name"),
                                    "arguments": json.dumps(tu.get("input", {}))
                                }
                            })
                
                # 1) First add assistant's text content (if present)
                if content:
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

                # 2) Then add (new format) tool_calls
                if tool_calls:
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

                # 3) Finally handle (legacy format) function_call
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

                # 4) If neither content nor any calls exist, maintain fallback behavior
                if not content and not tool_calls and not function_call:
                    sdk_format.append({
                        "id": "__fake_id__",
                        "content": [
                            {
                                "annotations": [],
                                "text": "",
                                "type": "output_text"
                            }
                        ],
                        "role": "assistant",
                        "status": "completed",
                        "type": "message"
                    })
                # === CHANGED ORDER END ===

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

    

    def _convert_to_anthropic_format(self, tools: List[Dict]) -> List[Dict]:
        """Convert MCP tool definitions to Anthropic format."""
        anthropic_tools = []
        
        for tool in tools:
            anthropic_tool = {
                "name": tool.get("name"),
                "description": tool.get("description", ""),
                "input_schema": tool.get("inputSchema", {
                    "type": "object",
                    "properties": {},
                    "required": []
                })
            }
            anthropic_tools.append(anthropic_tool)
        
        return anthropic_tools
    
    def _is_gemini_model(self) -> bool:
        """Check if the model is a Gemini model."""
        model_lower = self.litellm_input_model_name.lower()
        return "gemini" in model_lower or "bison" in model_lower
    
    def _simplify_schema_for_gemini(self, schema: Dict) -> Dict:
        """
        Simplify nested schemas for Gemini compatibility.
        Gemini has issues with deeply nested array type definitions.
        
        Note: This is a compatibility layer for Gemini API via LiteLLM.
        Can be removed once LiteLLM handles this internally.
        """
        if not isinstance(schema, dict):
            return schema
        
        simplified = {}
        
        for key, value in schema.items():
            if key == "type" and isinstance(value, list):
                # Gemini doesn't like type as array, use first type
                simplified[key] = value[0] if value else "string"
            elif key == "items" and isinstance(value, dict):
                # Recursively simplify items
                simplified[key] = self._simplify_schema_for_gemini(value)
            elif key == "properties" and isinstance(value, dict):
                # Recursively simplify each property
                simplified[key] = {
                    prop_key: self._simplify_schema_for_gemini(prop_val)
                    for prop_key, prop_val in value.items()
                }
            elif isinstance(value, dict):
                # Recursively simplify nested objects
                simplified[key] = self._simplify_schema_for_gemini(value)
            elif isinstance(value, list) and key not in ["required", "enum"]:
                # For non-special arrays, check if they contain schemas
                simplified[key] = [
                    self._simplify_schema_for_gemini(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                simplified[key] = value
        
        return simplified
    

    def _convert_to_openai_format(self, tools: List[Dict]) -> List[Dict]:
        """
        Convert MCP tool definitions to OpenAI function format.
        
        For Gemini models, applies schema simplification to handle
        compatibility issues with deeply nested array type definitions.
        """
        functions = []
        is_gemini = self._is_gemini_model()
        
        if is_gemini:
            logger.debug(f"Detected Gemini model: {self.litellm_input_model_name}")
            logger.debug(f"Processing {len(tools)} tools for Gemini compatibility")
        
        for i, tool in enumerate(tools):
            # Get the input schema
            input_schema = tool.get("inputSchema", {
                "type": "object",
                "properties": {},
                "required": []
            })
            
            # Simplify schema for Gemini if needed
            if is_gemini:
                original_schema = input_schema.copy()  # Keep for debugging
                input_schema = self._simplify_schema_for_gemini(input_schema)
                
                # Log significant changes for debugging
                if input_schema != original_schema:
                    logger.debug(f"Simplified schema for tool #{i} '{tool.get('name')}'")
            
            function = {
                "name": tool.get("name"),
                "description": tool.get("description", ""),
                "parameters": input_schema
            }
            functions.append(function)
        
        if is_gemini:
            logger.info(f"| Converted {len(functions)} tools for Gemini model with schema simplification")
        
        return functions

    


    # ==================== MCP Server Management ====================

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
    
