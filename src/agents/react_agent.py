"""ReAct agent implementation for the MCPMark pipeline."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Callable

import litellm

from src.logger import get_logger
from .base_agent import BaseMCPAgent

logger = get_logger(__name__)


class ReActAgent(BaseMCPAgent):
    """ReAct-style agent that reuses MCPMark infrastructure."""

    DEFAULT_SYSTEM_PROMPT = (
        "You are a careful ReAct (reasoning and acting) agent. "
        "At each step you must decide whether to call a tool or provide a final response. "
        "Only use the tools that are listed for you. When you finish, respond with either the final answer "
        "or the phrase \"Task completed.\" if no further detail is required. "
        "Every reply must be valid JSON without code fences."
    )

    def __init__(
        self,
        litellm_input_model_name: str,
        api_key: str,
        base_url: str,
        mcp_service: str,
        timeout: int = BaseMCPAgent.DEFAULT_TIMEOUT,
        service_config: Optional[Dict[str, Any]] = None,
        service_config_provider: Optional[Callable[[], Dict[str, Any]]] = None,
        reasoning_effort: Optional[str] = "default",
        max_iterations: int = 100,
        system_prompt: Optional[str] = None,
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
        )
        self.max_iterations = max_iterations
        self.react_system_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT

    async def execute(
        self,
        instruction: str,
        tool_call_log_file: Optional[str] = None,
    ) -> Dict[str, Any]:
        start_time = time.time()

        try:
            self._reset_progress()
            self._refresh_service_config()

            async def _run_react():
                return await self._execute_react_loop(instruction, tool_call_log_file)

            result = await asyncio.wait_for(_run_react(), timeout=self.timeout)
            execution_time = time.time() - start_time
            self.usage_tracker.update(
                success=result.get("success", False),
                token_usage=result.get("token_usage", {}),
                turn_count=result.get("turn_count", 0),
                execution_time=execution_time,
            )
            result["execution_time"] = execution_time
            return result
        except Exception as exc:  # noqa: BLE001
            execution_time = time.time() - start_time

            if isinstance(exc, asyncio.TimeoutError):
                error_msg = f"Execution timed out after {self.timeout} seconds"
                logger.error(error_msg)
            else:
                error_msg = f"ReAct agent execution failed: {exc}"
                logger.error(error_msg, exc_info=True)

            self.usage_tracker.update(
                success=False,
                token_usage=self._partial_token_usage or {},
                turn_count=self._partial_turn_count or 0,
                execution_time=execution_time,
            )

            if self._partial_messages:
                final_msg = self._convert_to_sdk_format(self._partial_messages)
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

    async def _execute_react_loop(
        self,
        instruction: str,
        tool_call_log_file: Optional[str],
    ) -> Dict[str, Any]:
        system_message = {"role": "system", "content": self.react_system_prompt}
        total_tokens = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "reasoning_tokens": 0,
        }
        turn_count = 0
        success = False
        final_error: Optional[str] = None

        mcp_server = await self._create_mcp_server()
        async with mcp_server:
            tools = await mcp_server.list_tools()
            tool_map = {tool.get("name"): tool for tool in tools}
            tools_description = self._render_tools_description(tools)

            task_message = {
                "role": "user",
                "content": self._build_task_prompt(
                    instruction=instruction,
                    tools_description=tools_description,
                ),
            }
            messages: List[Dict[str, Any]] = [system_message, task_message]
            self._update_progress(messages, total_tokens, turn_count)

            for step in range(1, self.max_iterations + 1):
                completion_kwargs = {
                    "model": self.litellm_input_model_name,
                    "messages": messages,
                    "api_key": self.api_key,
                }
                if self.base_url:
                    completion_kwargs["base_url"] = self.base_url
                if self.reasoning_effort != "default":
                    completion_kwargs["reasoning_effort"] = self.reasoning_effort

                try:
                    response = await asyncio.wait_for(
                        litellm.acompletion(**completion_kwargs),
                        timeout=self.timeout / 2,
                    )
                except asyncio.TimeoutError:
                    final_error = f"LLM call timed out on step {step}"
                    logger.error(final_error)
                    break
                except Exception as exc:  # noqa: BLE001
                    final_error = f"LLM call failed on step {step}: {exc}"
                    logger.error(final_error)
                    break

                if turn_count == 0 and getattr(response, "model", None):
                    self.litellm_run_model_name = response.model.split("/")[-1]

                usage = getattr(response, "usage", None)
                if usage:
                    prompt_tokens = (
                        getattr(usage, "prompt_tokens", None)
                        or getattr(usage, "input_tokens", None)
                        or 0
                    )
                    completion_tokens = (
                        getattr(usage, "completion_tokens", None)
                        or getattr(usage, "output_tokens", None)
                        or 0
                    )
                    total_tokens_count = getattr(usage, "total_tokens", None)
                    if total_tokens_count is None:
                        total_tokens_count = prompt_tokens + completion_tokens

                    total_tokens["input_tokens"] += prompt_tokens
                    total_tokens["output_tokens"] += completion_tokens
                    total_tokens["total_tokens"] += total_tokens_count

                    # Extract reasoning tokens if available
                    if hasattr(response.usage, 'completion_tokens_details'):
                        details = response.usage.completion_tokens_details
                        if hasattr(details, 'reasoning_tokens'):
                            total_tokens["reasoning_tokens"] += details.reasoning_tokens or 0

                choice = response.choices[0]
                message_obj = getattr(choice, "message", None)
                if message_obj is None and isinstance(choice, dict):
                    message_obj = choice.get("message")

                if message_obj is None:
                    content_raw = getattr(choice, "text", "")
                else:
                    content_raw = message_obj.get("content", "")

                assistant_text = self._normalize_content(content_raw)
                assistant_message = {"role": "assistant", "content": assistant_text}
                messages.append(assistant_message)
                turn_count += 1
                self._update_progress(messages, total_tokens, turn_count)

                parsed = self._parse_react_response(assistant_text)
                if not parsed or "thought" not in parsed:
                    warning = (
                        "The previous response was not valid JSON following the required schema. "
                        "Please respond again using the JSON formats provided."
                    )
                    messages.append({"role": "user", "content": warning})
                    self._update_progress(messages, total_tokens, turn_count)
                    final_error = "Model produced an invalid response format."
                    continue

                thought = parsed.get("thought", "")
                action = parsed.get("action")
                answer = parsed.get("answer")
                result = parsed.get("result")

                logger.info(f"|\n| \033[1;3mThought\033[0m: {str(thought)}")
                if tool_call_log_file:
                    try:
                        with open(tool_call_log_file, "a", encoding="utf-8") as log_file:
                            log_file.write(f"| {str(thought)}\n")
                    except Exception:  # noqa: BLE001
                        pass
                if action is not None:
                    func_name = action.get("tool")
                    arguments = action.get("arguments", {}) or {}
                    args_str = json.dumps(arguments, separators=(",", ": "))
                    display_arguments = args_str[:140] + "..." if len(args_str) > 140 else args_str
                    logger.info(f"| \033[1;3mAction\033[0m: \033[1m{func_name}\033[0m \033[2;37m{display_arguments}\033[0m")


                if answer is not None:
                    success = True
                    break

                if action is not None and isinstance(action, dict):
                    tool_name = action.get("tool")
                    arguments = action.get("arguments", {}) or {}

                    if tool_name not in tool_map:
                        observation = (
                            f"Invalid tool '{tool_name}'. Available tools: "
                            f"{', '.join(tool_map)}"
                        )
                    else:
                        try:
                            tool_response = await asyncio.wait_for(
                                mcp_server.call_tool(tool_name, arguments),
                                timeout=60,
                            )
                            observation = self._tool_result_to_text(tool_response)
                        except asyncio.TimeoutError:
                            observation = f"Tool '{tool_name}' timed out"
                        except Exception as tool_exc:  # noqa: BLE001
                            observation = f"Tool '{tool_name}' failed: {tool_exc}"

                        if tool_call_log_file:
                            try:
                                with open(tool_call_log_file, "a", encoding="utf-8") as log_file:
                                    log_file.write(f"| {tool_name} {json.dumps(arguments, ensure_ascii=False)}\n")
                            except Exception:  # noqa: BLE001
                                pass

                    observation_message = {
                        "role": "user",
                        "content": (
                            f"Observation:\n{observation}\n"
                            "Please continue reasoning and reply using the required JSON format."
                        ),
                    }
                    messages.append(observation_message)
                    self._update_progress(messages, total_tokens, turn_count)
                    continue

                if result is not None:
                    observation_message = {
                        "role": "user",
                        "content": (
                            f"Observation:\n{result}\n"
                            "Please continue reasoning and reply using the required JSON format."
                        ),
                    }
                    messages.append(observation_message)
                    self._update_progress(messages, total_tokens, turn_count)
                    continue

                # Unexpected structure: ask model to restate properly
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "The previous reply did not include an action, result, or answer. "
                            "Please respond again using the JSON formats provided."
                        ),
                    }
                )
                self._update_progress(messages, total_tokens, turn_count)

            if not success and final_error is None:
                final_error = (
                    f"Max iterations ({self.max_iterations}) reached without a final answer."
                )

        if total_tokens["total_tokens"] > 0:
            log_msg = (
                f"|\n|\n| Token usage: Total: {total_tokens['total_tokens']:,} | "
                f"Input: {total_tokens['input_tokens']:,} | "
                f"Output: {total_tokens['output_tokens']:,}"
            )
            if total_tokens.get("reasoning_tokens", 0) > 0:
                log_msg += f" | Reasoning: {total_tokens['reasoning_tokens']:,}"
            logger.info(log_msg)
            logger.info(f"| Turns: {turn_count}")

        sdk_messages = self._convert_to_sdk_format(messages)

        return {
            "success": success,
            "output": sdk_messages,
            "token_usage": total_tokens,
            "turn_count": turn_count,
            "error": None if success else final_error,
            "litellm_run_model_name": self.litellm_run_model_name,
        }

    def _build_task_prompt(
        self,
        instruction: str,
        tools_description: str,
    ) -> str:
        return (
            f"Task:\n{instruction}\n\n"
            f"Available MCP tools:\n{tools_description}\n\n"
            "Respond using the JSON formats below.\n\n"
            "If you need to use a tool:\n"
            "{\n"
            '  "thought": "Reasoning for the next action",\n'
            '  "action": {\n'
            '    "tool": "tool-name",\n'
            '    "arguments": {\n'
            '      "parameter": value\n'
            "    }\n"
            "  }\n"
            "}\n\n"
            "If you can provide the final answer:\n"
            "{\n"
            '  "thought": "Reasoning that justifies the answer",\n'
            '  "answer": "Either the final solution or \'Task completed.\' when no more detail is required"\n'
            "}\n\n"
            "Remember: omitting the action object ends the task, so only do this when finished."
        )

    def _render_tools_description(self, tools: List[Dict[str, Any]]) -> str:
        descriptions = []
        for tool in tools:
            name = tool.get("name", "unknown")
            description = tool.get("description", "No description provided.")
            input_schema = tool.get("inputSchema", {}) or {}
            properties = input_schema.get("properties", {}) or {}
            required = set(input_schema.get("required", []) or [])

            arg_lines = []
            for prop_name, prop_details in properties.items():
                details = json.dumps(prop_details, ensure_ascii=False, indent=2)
                suffix = " (required)" if prop_name in required else ""
                arg_lines.append(f"- {prop_name}{suffix}: {details}")

            if arg_lines:
                arguments_text = "\n".join(arg_lines)
            else:
                arguments_text = "(no arguments)"

            descriptions.append(
                f"Tool: {name}\nDescription: {description}\nArguments:\n{arguments_text}"
            )

        return "\n\n".join(descriptions) if descriptions else "(no tools available)"

    def _normalize_content(self, content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        parts.append(block.get("text", ""))
                    elif "text" in block:
                        parts.append(str(block.get("text")))
                else:
                    parts.append(str(block))
            return "\n".join(part for part in parts if part)
        return json.dumps(content, ensure_ascii=False)

    def _parse_react_response(self, payload: str) -> Dict[str, Any]:
        candidate = payload.strip().strip("`").strip()
        if candidate.lower().startswith("json"):
            candidate = candidate[4:].lstrip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            return {}

    def _tool_result_to_text(self, result: Any) -> str:
        if result is None:
            return ""
        if isinstance(result, str):
            return result
        try:
            return json.dumps(result, ensure_ascii=False)
        except TypeError:
            return str(result)
