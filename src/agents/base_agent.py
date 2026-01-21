"""Shared base agent functionality for MCPMark agents."""

from __future__ import annotations

import asyncio
import copy
import json
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable

from src.logger import get_logger
from .mcp import MCPStdioServer, MCPHttpServer
from .utils import TokenUsageTracker

logger = get_logger(__name__)


class BaseMCPAgent(ABC):
    """Base class with shared functionality for MCPMark agents."""

    STDIO_SERVICES = [
        "notion",
        "filesystem",
        "playwright",
        "playwright_webarena",
        "postgres",
        "insforge",
        "github",
    ]
    HTTP_SERVICES = ["supabase"]
    DEFAULT_TIMEOUT = 600
    COMPACTION_DISABLED_TOKEN = 999_999_999

    CLAUDE_THINKING_BUDGETS = {
        "low": 1024,
        "medium": 2048,
        "high": 4096,
    }

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
        compaction_token: int = COMPACTION_DISABLED_TOKEN,
    ):
        self.litellm_input_model_name = litellm_input_model_name
        self.api_key = api_key
        self.base_url = base_url
        self.mcp_service = mcp_service
        self.timeout = timeout
        self.service_config = service_config or {}
        self._service_config_provider = service_config_provider
        self.reasoning_effort = reasoning_effort or "default"
        self.compaction_token = int(compaction_token)

        self.is_claude = self._is_anthropic_model(litellm_input_model_name)
        self.use_claude_thinking = self.is_claude and self.reasoning_effort != "default"

        self.usage_tracker = TokenUsageTracker()
        self.litellm_run_model_name = None

        self._partial_messages: List[Dict[str, Any]] = []
        self._partial_token_usage: Dict[str, int] = {}
        self._partial_turn_count: int = 0

        logger.debug(
            "Initialized %s for service '%s' with model '%s'",
            self.__class__.__name__,
            self.mcp_service,
            self.litellm_input_model_name,
        )

        # Warn if Gemini 3 model uses unsupported reasoning_effort value
        if self._is_gemini_3_model() and self.reasoning_effort not in [
            "default",
            "low",
            "high",
        ]:
            logger.warning(
                "Gemini 3 models only support reasoning_effort 'low' or 'high', "
                "got '%s'. LiteLLM may map this to the nearest supported value.",
                self.reasoning_effort,
            )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"{self.__class__.__name__}(service='{self.mcp_service}', "
            f"model='{self.litellm_input_model_name}')"
        )

    @abstractmethod
    async def execute(
        self,
        instruction: str,
        tool_call_log_file: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute the agent logic and return execution metadata."""

    def execute_sync(
        self,
        instruction: str,
        tool_call_log_file: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Synchronous wrapper for async execution."""
        return asyncio.run(self.execute(instruction, tool_call_log_file))

    def get_usage_stats(self) -> Dict[str, Any]:
        """Return aggregated usage statistics."""
        return self.usage_tracker.get_stats()

    def reset_usage_stats(self):
        """Clear usage statistics."""
        self.usage_tracker.reset()

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _is_anthropic_model(self, model_name: str) -> bool:
        return "claude" in model_name.lower()

    def _get_claude_thinking_budget(self) -> Optional[int]:
        if not self.use_claude_thinking:
            return None
        return self.CLAUDE_THINKING_BUDGETS.get(self.reasoning_effort, 2048)

    def _refresh_service_config(self):
        if not self._service_config_provider:
            return
        try:
            latest_cfg = self._service_config_provider() or {}
            self.service_config.update(latest_cfg)
        except Exception as exc:  # pragma: no cover - best effort refresh
            logger.warning("Failed to refresh service config: %s", exc)

    def _reset_progress(self):
        self._partial_messages = []
        self._partial_token_usage = {}
        self._partial_turn_count = 0

    def _update_progress(
        self,
        messages: List[Dict[str, Any]],
        token_usage: Dict[str, Any],
        turn_count: int,
    ):
        try:
            self._partial_messages = copy.deepcopy(messages)
            self._partial_token_usage = dict(token_usage or {})
            self._partial_turn_count = int(turn_count or 0)
        except Exception:  # pragma: no cover - defensive copy
            pass

    # ------------------------------------------------------------------
    # MCP server management
    # ------------------------------------------------------------------

    async def _create_mcp_server(self) -> Any:
        if self.mcp_service in self.STDIO_SERVICES:
            return self._create_stdio_server()
        if self.mcp_service in self.HTTP_SERVICES:
            return self._create_http_server()
        raise ValueError(f"Unsupported MCP service: {self.mcp_service}")

    def _create_stdio_server(self) -> MCPStdioServer:
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
                },
            )

        if self.mcp_service == "filesystem":
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

        if self.mcp_service in ("playwright", "playwright_webarena"):
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

        if self.mcp_service == "postgres":
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

        if self.mcp_service == "insforge":
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

        raise ValueError(f"Unsupported stdio service: {self.mcp_service}")

    def _create_http_server(self) -> MCPHttpServer:
        if self.mcp_service == "github":
            github_token = self.service_config.get("github_token")
            if not github_token:
                raise ValueError("GitHub token required")
            return MCPHttpServer(
                url="https://api.githubcopilot.com/mcp/",
                headers={
                    "Authorization": f"Bearer {github_token}",
                    "User-Agent": "MCPMark/1.0",
                },
            )
        raise ValueError(f"Unsupported HTTP service: {self.mcp_service}")

    # ------------------------------------------------------------------
    # Message/Tool formatting helpers
    # ------------------------------------------------------------------

    def _compaction_enabled(self) -> bool:
        return 0 < self.compaction_token < self.COMPACTION_DISABLED_TOKEN

    def _count_prompt_tokens_litellm(self, messages: List[Dict[str, Any]]) -> int:
        try:
            from litellm import token_counter

            return int(
                token_counter(model=self.litellm_input_model_name, messages=messages)
                or 0
            )
        except Exception:  # pragma: no cover - best effort
            return 0

    def _convert_to_sdk_format(
        self, messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        sdk_format: List[Dict[str, Any]] = []
        function_call_map: Dict[str, str] = {}

        for msg in messages:
            role = msg.get("role")

            if role == "user":
                user_content = msg.get("content", "")
                if isinstance(user_content, list):
                    tool_results = [
                        item
                        for item in user_content
                        if isinstance(item, dict) and item.get("type") == "tool_result"
                    ]
                    if tool_results:
                        for tr in tool_results:
                            content_items = tr.get("content", [])
                            text_content = ""
                            for ci in content_items:
                                if isinstance(ci, dict) and ci.get("type") == "text":
                                    text_content = ci.get("text", "")
                                    break
                            sdk_format.append(
                                {
                                    "call_id": tr.get("tool_use_id", ""),
                                    "output": json.dumps(
                                        {
                                            "type": "text",
                                            "text": text_content,
                                            "annotations": None,
                                            "meta": None,
                                        }
                                    ),
                                    "type": "function_call_output",
                                }
                            )
                    else:
                        text_parts = []
                        for item in user_content:
                            if isinstance(item, dict) and item.get("type") == "text":
                                text_parts.append(item.get("text", ""))
                        sdk_format.append(
                            {"content": "\n".join(text_parts), "role": "user"}
                        )
                else:
                    sdk_format.append({"content": user_content, "role": "user"})

            elif role == "assistant":
                tool_calls = msg.get("tool_calls", [])
                function_call = msg.get("function_call")
                content = msg.get("content")

                if isinstance(content, list):
                    text_parts = []
                    claude_tool_uses = []
                    for block in content:
                        if isinstance(block, dict):
                            if block.get("type") == "text":
                                text_parts.append(block.get("text", ""))
                            elif block.get("type") == "thinking":
                                thinking_text = block.get("thinking", "")
                                if thinking_text:
                                    text_parts.append(
                                        f"<think>\n{thinking_text}\n</think>"
                                    )
                            elif block.get("type") == "tool_use":
                                claude_tool_uses.append(block)
                    content = "\n".join(text_parts)
                    if claude_tool_uses and not tool_calls:
                        tool_calls = []
                        for tu in claude_tool_uses:
                            tool_calls.append(
                                {
                                    "id": tu.get("id"),
                                    "function": {
                                        "name": tu.get("name"),
                                        "arguments": json.dumps(tu.get("input", {})),
                                    },
                                }
                            )

                if content:
                    sdk_format.append(
                        {
                            "id": "__fake_id__",
                            "content": [
                                {
                                    "annotations": [],
                                    "text": content,
                                    "type": "output_text",
                                }
                            ],
                            "role": "assistant",
                            "status": "completed",
                            "type": "message",
                        }
                    )

                if tool_calls:
                    for tool_call in tool_calls:
                        call_id = tool_call.get("id", f"call_{uuid.uuid4().hex}")
                        func_name = tool_call.get("function", {}).get("name", "")
                        sdk_format.append(
                            {
                                "arguments": tool_call.get("function", {}).get(
                                    "arguments", "{}"
                                ),
                                "call_id": call_id,
                                "name": func_name,
                                "type": "function_call",
                                "id": "__fake_id__",
                            }
                        )

                if function_call:
                    func_name = function_call.get("name", "")
                    call_id = f"call_{uuid.uuid4().hex}"
                    function_call_map[func_name] = call_id
                    sdk_format.append(
                        {
                            "arguments": function_call.get("arguments", "{}"),
                            "call_id": call_id,
                            "name": func_name,
                            "type": "function_call",
                            "id": "__fake_id__",
                        }
                    )

            elif role == "tool":
                sdk_format.append(
                    {
                        "call_id": msg.get("tool_call_id", ""),
                        "output": json.dumps(
                            {
                                "type": "text",
                                "text": msg.get("content", ""),
                                "annotations": None,
                                "meta": None,
                            }
                        ),
                        "type": "function_call_output",
                    }
                )

            elif role == "function":
                func_name = msg.get("name", "")
                call_id = function_call_map.get(func_name, f"call_{uuid.uuid4().hex}")
                sdk_format.append(
                    {
                        "call_id": call_id,
                        "output": json.dumps(
                            {
                                "type": "text",
                                "text": msg.get("content", ""),
                                "annotations": None,
                                "meta": None,
                            }
                        ),
                        "type": "function_call_output",
                    }
                )

        return sdk_format

    def _convert_to_anthropic_format(
        self, tools: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        anthropic_tools = []
        for tool in tools:
            anthropic_tool = {
                "name": tool.get("name"),
                "description": tool.get("description", ""),
                "input_schema": tool.get(
                    "inputSchema",
                    {"type": "object", "properties": {}, "required": []},
                ),
            }
            anthropic_tools.append(anthropic_tool)
        return anthropic_tools

    def _is_gemini_model(self) -> bool:
        model_lower = self.litellm_input_model_name.lower()
        return "gemini" in model_lower or "bison" in model_lower

    def _is_gemini_3_model(self) -> bool:
        """Check if this is a Gemini 3 series model."""
        model_lower = self.litellm_input_model_name.lower()
        return "gemini-3" in model_lower or "gemini/gemini-3" in model_lower

    def _simplify_schema_for_gemini(
        self, schema: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        if not isinstance(schema, dict):
            return schema or {}

        simplified: Dict[str, Any] = {}
        for key, value in schema.items():
            if key == "type" and isinstance(value, list):
                simplified[key] = value[0] if value else "string"
            elif key == "items" and isinstance(value, dict):
                simplified[key] = self._simplify_schema_for_gemini(value)
            elif key == "properties" and isinstance(value, dict):
                simplified[key] = {
                    prop_key: self._simplify_schema_for_gemini(prop_val)
                    for prop_key, prop_val in value.items()
                }
            elif isinstance(value, dict):
                simplified[key] = self._simplify_schema_for_gemini(value)
            elif isinstance(value, list) and key not in ("required", "enum"):
                simplified[key] = [
                    self._simplify_schema_for_gemini(item)
                    if isinstance(item, dict)
                    else item
                    for item in value
                ]
            else:
                simplified[key] = value
        return simplified

    def _convert_to_openai_format(
        self, tools: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        functions = []
        is_gemini = self._is_gemini_model()

        if is_gemini:
            logger.debug(
                "Detected Gemini model '%s' – simplifying tool schemas",
                self.litellm_input_model_name,
            )

        for tool in tools:
            input_schema = tool.get(
                "inputSchema", {"type": "object", "properties": {}, "required": []}
            )
            if is_gemini:
                simplified = self._simplify_schema_for_gemini(input_schema)
                if simplified != input_schema:
                    input_schema = simplified
                    logger.debug("Simplified schema for tool '%s'", tool.get("name"))

            functions.append(
                {
                    "name": tool.get("name"),
                    "description": tool.get("description", ""),
                    "parameters": input_schema,
                }
            )

        if is_gemini:
            logger.info("Converted %d tools for Gemini compatibility", len(functions))

        return functions
