"""
MCPMark Agent Implementation
============================

Unified agent using LiteLLM for all model interactions with minimal MCP support.
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Callable
from pydantic import AnyUrl

import httpx
import litellm
import nest_asyncio

from src.logger import get_logger
from .base_agent import BaseMCPAgent
from .mcp import MCPStdioServer, MCPHttpServer

# Apply nested asyncio support
nest_asyncio.apply()

# Configure LiteLLM
litellm.suppress_debug_info = True

logger = get_logger(__name__)


# To fix the "Object of type AnyUrl is not JSON serializable" error in the find_file_contents function.
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, AnyUrl):
            return str(obj)
        return super().default(obj)


class MCPMarkAgent(BaseMCPAgent):
    """
    Unified agent for LLM and MCP server management using LiteLLM.

    - Anthropic models: Native MCP support via extra_body
    - Other models: Manual MCP server management with function calling
    """

    MAX_TURNS = 100
    SYSTEM_PROMPT = (
        "You are a helpful agent that uses tools iteratively to complete the user's task, "
        'and when finished, provides the final answer or simply states "Task completed" without further tool calls.'
    )
    COMPACTION_PROMPT = (
        "You are performing a CONTEXT CHECKPOINT COMPACTION.\n"
        "Summarize the conversation so far for another model to continue.\n\n"
        "Include:\n"
        "- Current progress and key decisions made\n"
        "- Important context, constraints, or user preferences\n"
        "- What remains to be done (clear next steps)\n"
        "- Any critical data, examples, or references needed to continue\n\n"
        "Be concise and structured. Do NOT call tools."
    )
    DEFAULT_TIMEOUT = BaseMCPAgent.DEFAULT_TIMEOUT

    def __init__(
        self,
        litellm_input_model_name: str,
        api_key: str,
        base_url: str,
        mcp_service: str,
        timeout: int = DEFAULT_TIMEOUT,
        service_config: Optional[Dict[str, Any]] = None,
        service_config_provider: Optional[Callable[[], Dict[str, Any]]] = None,
        reasoning_effort: Optional[str] = "default",
        compaction_token: int = BaseMCPAgent.COMPACTION_DISABLED_TOKEN,
    ):
        super().__init__(
            litellm_input_model_name=litellm_input_model_name,
            api_key=api_key,
            base_url=base_url,
            mcp_service=mcp_service,
            timeout=timeout,
            service_config=service_config,
            service_config_provider=service_config_provider,
            reasoning_effort=reasoning_effort,
            compaction_token=compaction_token,
        )
        logger.debug(
            "Initialized MCPMarkAgent for '%s' with model '%s' (Claude: %s, Thinking: %s, Reasoning: %s)",
            mcp_service,
            litellm_input_model_name,
            self.is_claude,
            self.use_claude_thinking,
            reasoning_effort,
        )

    # ==================== Public Interface Methods ====================

    async def execute(
        self, instruction: str, tool_call_log_file: Optional[str] = None
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
                _execute_with_strategy(), timeout=self.timeout
            )

            execution_time = time.time() - start_time

            # Update usage statistics
            self.usage_tracker.update(
                success=result["success"],
                token_usage=result.get("token_usage", {}),
                turn_count=result.get("turn_count", 0),
                execution_time=execution_time,
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
                execution_time=execution_time,
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
        self, instruction: str, tool_call_log_file: Optional[str] = None
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
        self, instruction: str, tool_call_log_file: Optional[str] = None
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
                instruction,
                anthropic_tools,
                mcp_server,
                thinking_budget,
                tool_call_log_file,
            )

    async def _call_claude_native_api(
        self,
        messages: List[Dict],
        thinking_budget: int,
        tools: Optional[List[Dict]] = None,
        mcp_servers: Optional[List[Dict]] = None,
        system: Optional[str] = None,
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
            "anthropic-beta": "context-1m-2025-08-07",  # by default
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
            payload["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}

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
                    timeout=self.timeout,
                )
                response.raise_for_status()
                return response.json(), None
            except httpx.HTTPStatusError as e:
                return None, e.response.text
            except Exception as e:
                return None, e

    async def _count_claude_input_tokens(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict]] = None,
        system: Optional[str] = None,
    ) -> int:
        import os

        api_base = os.getenv("ANTHROPIC_API_BASE", "https://api.anthropic.com")
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload: Dict[str, Any] = {
            "model": self.litellm_input_model_name.replace("anthropic/", ""),
            "messages": messages,
        }
        if tools:
            payload["tools"] = tools
        if system:
            payload["system"] = system

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{api_base}/v1/messages/count_tokens",
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json() or {}
            return int(data.get("input_tokens", 0) or 0)

    def _extract_litellm_text(self, response: Any) -> str:
        try:
            choices = getattr(response, "choices", None) or []
            if not choices:
                return ""
            msg = getattr(choices[0], "message", None)
            if msg is not None:
                return str(getattr(msg, "content", "") or "")
            return str(getattr(choices[0], "text", "") or "")
        except Exception:  # pragma: no cover - best effort
            return ""

    def _extract_anthropic_text(self, response_json: Dict[str, Any]) -> str:
        pieces: List[str] = []
        for block in response_json.get("content", []) or []:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text")
                if text:
                    pieces.append(str(text))
        return "\n".join(pieces).strip()

    def _merge_usage(self, total_tokens: Dict[str, int], usage: Dict[str, Any]) -> None:
        try:
            input_tokens = int(usage.get("input_tokens", 0) or 0)
            output_tokens = int(usage.get("output_tokens", 0) or 0)
            total_tokens_count = int(
                usage.get("total_tokens", 0) or (input_tokens + output_tokens)
            )
            total_tokens["input_tokens"] += input_tokens
            total_tokens["output_tokens"] += output_tokens
            total_tokens["total_tokens"] += total_tokens_count
        except Exception:  # pragma: no cover - best effort
            return

    async def _maybe_compact_litellm_messages(
        self,
        messages: List[Dict[str, Any]],
        total_tokens: Dict[str, int],
        tool_call_log_file: Optional[str],
        current_prompt_tokens: int,
    ) -> List[Dict[str, Any]]:
        if not self._compaction_enabled():
            return messages
        if current_prompt_tokens < self.compaction_token:
            return messages

        logger.info(
            f"| [compaction] Triggered at prompt tokens: {current_prompt_tokens:,}"
        )
        if tool_call_log_file:
            try:
                with open(tool_call_log_file, "a", encoding="utf-8") as f:
                    f.write(
                        f"| [compaction] Triggered at prompt tokens: {current_prompt_tokens:,}\n"
                    )
            except Exception:
                pass

        compact_messages = [
            {"role": "system", "content": self.COMPACTION_PROMPT},
            {"role": "user", "content": json.dumps(messages, ensure_ascii=False)},
        ]
        completion_kwargs = {
            "model": self.litellm_input_model_name,
            "messages": compact_messages,
            "api_key": self.api_key,
        }
        if self.base_url:
            completion_kwargs["base_url"] = self.base_url
        response = await litellm.acompletion(**completion_kwargs)

        usage = getattr(response, "usage", None)
        if usage:
            input_tokens = (
                getattr(usage, "prompt_tokens", None)
                or getattr(usage, "input_tokens", None)
                or 0
            )
            output_tokens = (
                getattr(usage, "completion_tokens", None)
                or getattr(usage, "output_tokens", None)
                or 0
            )
            total_tokens_count = getattr(usage, "total_tokens", None)
            if total_tokens_count is None:
                total_tokens_count = input_tokens + output_tokens
            total_tokens["input_tokens"] += int(input_tokens or 0)
            total_tokens["output_tokens"] += int(output_tokens or 0)
            total_tokens["total_tokens"] += int(total_tokens_count or 0)

        summary = self._extract_litellm_text(response).strip() or "(no summary)"
        system_msg = (
            messages[0]
            if messages
            else {"role": "system", "content": self.SYSTEM_PROMPT}
        )
        first_user = (
            messages[1] if len(messages) > 1 else {"role": "user", "content": ""}
        )
        return [
            system_msg,
            first_user,
            {
                "role": "user",
                "content": f"Context summary (auto-compacted due to token limit):\n{summary}",
            },
        ]

    async def _maybe_compact_anthropic_messages(
        self,
        messages: List[Dict[str, Any]],
        total_tokens: Dict[str, int],
        thinking_budget: int,
        tool_call_log_file: Optional[str],
        current_input_tokens: int,
    ) -> List[Dict[str, Any]]:
        if not self._compaction_enabled():
            return messages
        if current_input_tokens < self.compaction_token:
            return messages

        logger.info(
            f"| [compaction] Triggered at input tokens: {current_input_tokens:,}"
        )
        if tool_call_log_file:
            try:
                with open(tool_call_log_file, "a", encoding="utf-8") as f:
                    f.write(
                        f"| [compaction] Triggered at input tokens: {current_input_tokens:,}\n"
                    )
            except Exception:
                pass

        compact_messages = [
            {"role": "user", "content": self.COMPACTION_PROMPT},
            {"role": "user", "content": json.dumps(messages, ensure_ascii=False)},
        ]
        response, error_msg = await self._call_claude_native_api(
            messages=compact_messages,
            thinking_budget=thinking_budget,
            tools=None,
            system=None,
        )
        if error_msg or not response:
            logger.warning(f"| [compaction] Failed: {error_msg}")
            return messages

        usage = response.get("usage", {}) or {}
        input_tokens = usage.get("input_tokens", 0) or 0
        output_tokens = usage.get("output_tokens", 0) or 0
        total_tokens["input_tokens"] += int(input_tokens)
        total_tokens["output_tokens"] += int(output_tokens)
        total_tokens["total_tokens"] += int(input_tokens + output_tokens)

        summary = self._extract_anthropic_text(response) or "(no summary)"
        first_user = messages[0] if messages else {"role": "user", "content": ""}
        return [
            first_user,
            {
                "role": "user",
                "content": f"Context summary (auto-compacted due to token limit):\n{summary}",
            },
        ]

    async def _execute_anthropic_native_tool_loop(
        self,
        instruction: str,
        tools: List[Dict],
        mcp_server: Any,
        thinking_budget: int,
        tool_call_log_file: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute Claude thinking loop with function calling.
        Handles thinking blocks, tool calls, and message formatting.
        """
        messages = [{"role": "user", "content": instruction}]
        total_tokens = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "reasoning_tokens": 0,
        }
        turn_count = 0
        max_turns = self.MAX_TURNS
        hit_turn_limit = False
        ended_normally = False

        system_text = self.SYSTEM_PROMPT
        # Record initial state
        self._update_progress(messages, total_tokens, turn_count)

        for _ in range(max_turns):
            turn_count += 1

            current_input_tokens = 0
            if self._compaction_enabled():
                try:
                    current_input_tokens = await self._count_claude_input_tokens(
                        messages=messages,
                        tools=tools,
                        system=system_text,
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Claude token counting failed: %s", exc)

            messages = await self._maybe_compact_anthropic_messages(
                messages=messages,
                total_tokens=total_tokens,
                thinking_budget=thinking_budget,
                tool_call_log_file=tool_call_log_file,
                current_input_tokens=current_input_tokens,
            )
            self._update_progress(messages, total_tokens, turn_count)

            # Call Claude native API
            response, error_msg = await self._call_claude_native_api(
                messages=messages,
                thinking_budget=thinking_budget,
                tools=tools,
                system=system_text,
            )
            if turn_count == 1:
                self.litellm_run_model_name = response["model"].split("/")[-1]

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
                    with open(tool_call_log_file, "a", encoding="utf-8") as f:
                        f.write(f"{tb['text']}\n")
                if tb.get("text"):
                    for line in tb["text"].splitlines():
                        logger.info(f"| {line}")

            # Build assistant message with all blocks
            assistant_content = []

            # Add thinking blocks
            for tb in thinking_blocks:
                assistant_content.append(
                    {
                        "type": "thinking",
                        "thinking": tb.get("thinking", ""),
                        "signature": tb.get("signature", ""),
                    }
                )

            # Add text blocks
            for tb in text_blocks:
                if tb.get("text"):
                    assistant_content.append({"type": "text", "text": tb["text"]})

            # Add tool_use blocks
            for tu in tool_uses:
                assistant_content.append(
                    {
                        "type": "tool_use",
                        "id": tu.get("id"),
                        "name": tu.get("name"),
                        "input": tu.get("input", {}),
                    }
                )

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
                display_args = (
                    args_str[:140] + "..." if len(args_str) > 140 else args_str
                )
                logger.info(f"| \033[1m{name}\033[0m \033[2;37m{display_args}\033[0m")

                if tool_call_log_file:
                    with open(tool_call_log_file, "a", encoding="utf-8") as f:
                        f.write(f"| {name} {args_str}\n")

                # Execute tool
                try:
                    result = await asyncio.wait_for(
                        mcp_server.call_tool(name, inputs), timeout=60
                    )
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tu["id"],
                            "content": [
                                {
                                    "type": "text",
                                    "text": json.dumps(result, cls=CustomJSONEncoder),
                                }
                            ],
                        }
                    )
                except Exception as e:
                    logger.error(f"Tool call failed: {e}")
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tu["id"],
                            "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                        }
                    )

            messages.append({"role": "user", "content": tool_results})
            # Update partial progress after tool results
            self._update_progress(messages, total_tokens, turn_count)

        # Detect if we exited due to hitting the turn limit
        if not ended_normally:
            if turn_count >= max_turns:
                hit_turn_limit = True
                logger.warning(
                    f"| Max turns ({max_turns}) exceeded; returning failure with partial output."
                )
                if tool_call_log_file:
                    try:
                        with open(tool_call_log_file, "a", encoding="utf-8") as f:
                            f.write(f"| Max turns ({max_turns}) exceeded\n")
                    except Exception:
                        pass
            elif error_msg:
                logger.warning(f"| {error_msg}\n")
                if tool_call_log_file:
                    try:
                        with open(tool_call_log_file, "a", encoding="utf-8") as f:
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
        sdk_format_messages = self._convert_to_sdk_format(messages)

        if hit_turn_limit:
            return {
                "success": False,
                "output": sdk_format_messages,
                "token_usage": total_tokens,
                "turn_count": turn_count,
                "error": f"Max turns ({max_turns}) exceeded",
                "litellm_run_model_name": self.litellm_run_model_name,
            }

        if error_msg:
            return {
                "success": False,
                "output": sdk_format_messages,
                "token_usage": total_tokens,
                "turn_count": turn_count,
                "error": error_msg,
                "litellm_run_model_name": self.litellm_run_model_name,
            }

        return {
            "success": True,
            "output": sdk_format_messages,
            "token_usage": total_tokens,
            "turn_count": turn_count,
            "error": None,
            "litellm_run_model_name": self.litellm_run_model_name,
        }

    # ==================== LiteLLM Execution Path ====================

    async def _execute_litellm_with_tools(
        self, instruction: str, tool_call_log_file: Optional[str] = None
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
        tool_call_log_file: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute function calling loop with LiteLLM."""
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": instruction},
        ]
        total_tokens = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "reasoning_tokens": 0,
        }
        turn_count = 0
        max_turns = self.MAX_TURNS  # Limit turns to prevent infinite loops
        consecutive_failures = 0
        max_consecutive_failures = 3
        hit_turn_limit = False
        ended_normally = False

        # Convert functions to tools format for newer models
        tools = (
            [{"type": "function", "function": func} for func in functions]
            if functions
            else None
        )

        if tool_call_log_file and tools:
            max_name_length = (
                max(len(tool.get("function", {}).get("name", "")) for tool in tools)
                if tools
                else 15
            )
            with open(tool_call_log_file, "a", encoding="utf-8") as f:
                f.write("===== Available Tools =====\n")
                for tool in tools:
                    function_info = tool.get("function", {})
                    tool_name = function_info.get("name", "N/A")
                    description = function_info.get("description", "N/A")
                    f.write(
                        f"- ToolName: {tool_name:<{max_name_length}} Description: {description}\n"
                    )
                f.write("\n===== Execution Logs =====\n")

        # Record initial state
        self._update_progress(messages, total_tokens, turn_count)

        try:
            while turn_count < max_turns:
                current_prompt_tokens = 0
                if self._compaction_enabled():
                    current_prompt_tokens = self._count_prompt_tokens_litellm(messages)

                messages = await self._maybe_compact_litellm_messages(
                    messages=messages,
                    total_tokens=total_tokens,
                    tool_call_log_file=tool_call_log_file,
                    current_prompt_tokens=current_prompt_tokens,
                )
                self._update_progress(messages, total_tokens, turn_count)

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
                        timeout=self.timeout / 2,  # Use half of total timeout
                    )
                    consecutive_failures = 0  # Reset failure counter on success
                except asyncio.TimeoutError:
                    logger.warning(f"| ✗ LLM call timed out on turn {turn_count + 1}")
                    consecutive_failures += 1
                    if consecutive_failures >= max_consecutive_failures:
                        raise Exception(
                            f"Too many consecutive failures ({consecutive_failures})"
                        )
                    await asyncio.sleep(8**consecutive_failures)  # Exponential backoff
                    continue
                except Exception as e:
                    logger.error(f"| ✗ LLM call failed on turn {turn_count + 1}: {e}")
                    consecutive_failures += 1
                    if consecutive_failures >= max_consecutive_failures:
                        raise
                    if "ContextWindowExceededError" in str(e):
                        # Best-effort fallback: compact and retry once.
                        messages = await self._maybe_compact_litellm_messages(
                            messages=messages,
                            total_tokens=total_tokens,
                            tool_call_log_file=tool_call_log_file,
                            current_prompt_tokens=self.compaction_token,
                        )
                        self._update_progress(messages, total_tokens, turn_count)
                        continue
                    elif "RateLimitError" in str(e):
                        await asyncio.sleep(12**consecutive_failures)
                    else:
                        await asyncio.sleep(2**consecutive_failures)
                    continue

                # Extract actual model name from response (first turn only)
                if turn_count == 0 and hasattr(response, "model") and response.model:
                    self.litellm_run_model_name = response.model.split("/")[-1]

                # Update token usage including reasoning tokens
                if hasattr(response, "usage") and response.usage:
                    input_tokens = response.usage.prompt_tokens or 0
                    total_tokens_count = response.usage.total_tokens or 0
                    # Calculate output tokens as total - input for consistency
                    output_tokens = (
                        total_tokens_count - input_tokens
                        if total_tokens_count > 0
                        else (response.usage.completion_tokens or 0)
                    )

                    total_tokens["input_tokens"] += input_tokens
                    total_tokens["output_tokens"] += output_tokens
                    total_tokens["total_tokens"] += total_tokens_count

                    # Extract reasoning tokens if available
                    if hasattr(response.usage, "completion_tokens_details"):
                        details = response.usage.completion_tokens_details
                        if hasattr(details, "reasoning_tokens"):
                            total_tokens["reasoning_tokens"] += (
                                details.reasoning_tokens or 0
                            )

                # Get response message
                choices = response.choices
                if len(choices):
                    message = choices[0].message
                    # deeply dump the message to ensure we capture all fields
                    message_dict = (
                        message.model_dump()
                        if hasattr(message, "model_dump")
                        else dict(message)
                    )

                    # Explicitly preserve function_call if present (even if tool_calls exists),
                    # as it may contain provider-specific metadata (e.g. Gemini thought_signature)
                    if hasattr(message, "function_call") and message.function_call:
                        # Ensure it's in the dict if model_dump missed it or it was excluded
                        if (
                            "function_call" not in message_dict
                            or not message_dict["function_call"]
                        ):
                            fc = message.function_call
                            message_dict["function_call"] = (
                                fc.model_dump() if hasattr(fc, "model_dump") else fc
                            )

                # Log assistant's text content if present
                if hasattr(message, "content") and message.content:
                    # Display the content with line prefix
                    for line in message.content.splitlines():
                        logger.info(f"| {line}")

                    # Also log to file if specified
                    if tool_call_log_file:
                        with open(tool_call_log_file, "a", encoding="utf-8") as f:
                            f.write(f"{message.content}\n")

                # Check for tool calls (newer format)
                if hasattr(message, "tool_calls") and message.tool_calls:
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
                                mcp_server.call_tool(func_name, func_args), timeout=60
                            )
                            messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": tool_call.id,
                                    "content": json.dumps(
                                        result, cls=CustomJSONEncoder
                                    ),
                                }
                            )
                        except asyncio.TimeoutError:
                            error_msg = (
                                f"Tool call '{func_name}' timed out after 60 seconds"
                            )
                            logger.error(error_msg)
                            messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": tool_call.id,
                                    "content": f"Error: {error_msg}",
                                }
                            )
                        except Exception as e:
                            logger.error(f"Tool call failed: {e}")
                            messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": tool_call.id,
                                    "content": f"Error: {str(e)}",
                                }
                            )

                        # Format arguments for display (truncate if too long)
                        args_str = json.dumps(func_args, separators=(",", ": "))
                        display_arguments = (
                            args_str[:140] + "..." if len(args_str) > 140 else args_str
                        )

                        # Log with ANSI color codes (bold tool name, dim gray arguments)
                        logger.info(
                            f"| \033[1m{func_name}\033[0m \033[2;37m{display_arguments}\033[0m"
                        )

                        if tool_call_log_file:
                            with open(tool_call_log_file, "a", encoding="utf-8") as f:
                                f.write(f"| {func_name} {args_str}\n")
                    # Update progress after tool results appended
                    self._update_progress(messages, total_tokens, turn_count)
                    continue
                else:
                    # Log end reason
                    if not choices:
                        logger.info(
                            "|\n|\n| Task ended with no messages generated by the model."
                        )
                    elif choices[0].finish_reason == "stop":
                        logger.info(
                            "|\n|\n| Task ended with the finish reason from messages being 'stop'."
                        )

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
            logger.warning(
                f"| Max turns ({max_turns}) exceeded); returning failure with partial output."
            )
            if tool_call_log_file:
                try:
                    with open(tool_call_log_file, "a", encoding="utf-8") as f:
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
            "litellm_run_model_name": self.litellm_run_model_name,
        }

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
                args=["-y", "@notionhq/notion-mcp-server@1.9.1"],
                env={
                    "OPENAPI_MCP_HEADERS": (
                        '{"Authorization": "Bearer ' + notion_key + '", '
                        '"Notion-Version": "2022-06-28"}'
                    )
                },
            )

        elif self.mcp_service == "filesystem":
            test_directory = self.service_config.get("test_directory")
            if not test_directory:
                raise ValueError("Test directory required for filesystem service")

            return MCPStdioServer(
                command="npx",
                args=[
                    "-y",
                    "@modelcontextprotocol/server-filesystem",
                    str(test_directory),
                ],
            )

        elif self.mcp_service in ["playwright", "playwright_webarena"]:
            browser = self.service_config.get("browser", "chromium")
            headless = self.service_config.get("headless", True)
            viewport_width = self.service_config.get("viewport_width", 1280)
            viewport_height = self.service_config.get("viewport_height", 720)

            args = ["-y", "@playwright/mcp@latest"]
            if headless:
                args.append("--headless")
            args.extend(
                [
                    "--isolated",
                    "--no-sandbox",
                    "--browser",
                    browser,
                    "--viewport-size",
                    f"{viewport_width},{viewport_height}",
                ]
            )

            return MCPStdioServer(command="npx", args=args)

        elif self.mcp_service == "postgres":
            host = self.service_config.get("host", "localhost")
            port = self.service_config.get("port", 5432)
            username = self.service_config.get("username")
            password = self.service_config.get("password")
            database = self.service_config.get(
                "current_database"
            ) or self.service_config.get("database")

            if not all([username, password, database]):
                raise ValueError("PostgreSQL requires username, password, and database")

            database_url = (
                f"postgresql://{username}:{password}@{host}:{port}/{database}"
            )

            return MCPStdioServer(
                command="pipx",
                args=["run", "postgres-mcp", "--access-mode=unrestricted"],
                env={"DATABASE_URI": database_url},
            )

        elif self.mcp_service == "insforge":
            api_key = self.service_config.get("api_key")
            backend_url = self.service_config.get("backend_url")
            if not all([api_key, backend_url]):
                raise ValueError("Insforge requires api_key and backend_url")
            return MCPStdioServer(
                command="npx",
                args=["-y", "@insforge/mcp@dev"],
                env={
                    "INSFORGE_API_KEY": api_key,
                    "INSFORGE_BACKEND_URL": backend_url,
                },
            )

        elif self.mcp_service == "github":
            github_token = self.service_config.get("github_token")
            if not github_token:
                raise ValueError("GitHub token required")

            return MCPStdioServer(
                command="docker",
                args=[
                    "run", "-i", "--rm",
                    "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
                    "ghcr.io/github/github-mcp-server:v0.15.0",
                ],
                env={"GITHUB_PERSONAL_ACCESS_TOKEN": github_token},
            )

        else:
            raise ValueError(f"Unsupported stdio service: {self.mcp_service}")

    def _create_http_server(self) -> MCPHttpServer:
        """Create HTTP-based MCP server."""
        if self.mcp_service == "supabase":
            # Use built-in MCP server from Supabase CLI
            api_url = self.service_config.get("api_url", "http://localhost:54321")
            api_key = self.service_config.get("api_key", "")

            if not api_key:
                raise ValueError(
                    "Supabase requires api_key (use secret key from 'supabase status')"
                )

            # Supabase CLI exposes MCP at /mcp endpoint
            mcp_url = f"{api_url}/mcp"

            return MCPHttpServer(
                url=mcp_url,
                headers={
                    "apikey": api_key,
                    "Authorization": f"Bearer {api_key}",
                },
            )

        else:
            raise ValueError(f"Unsupported HTTP service: {self.mcp_service}")
