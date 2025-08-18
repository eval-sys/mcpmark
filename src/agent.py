"""
Unified Agent Implementation for MCPMark
=========================================

This module provides a unified agent implementation that handles LLM and MCP server
management. The agent is responsible for:
- Model provider creation and management
- MCP server creation for different services
- LLM inference execution with streaming response
- Token usage tracking and statistics

The agent does NOT handle task-specific logic - that's the responsibility of task managers.
"""

# Python stdlib
import asyncio
import os
import time
from typing import Any, Dict, Callable

# Third-party dependencies
from agents import (
    Agent,
    Model,
    ModelProvider,
    ModelSettings,
    OpenAIChatCompletionsModel,
    RunConfig,
    Runner,
    set_tracing_disabled,
)
from openai import AsyncOpenAI
from openai.types.responses import ResponseTextDeltaEvent

# MCP server classes (stdio & HTTP) from agents SDK
from agents.mcp.server import (
    MCPServerStdio,
    MCPServerStreamableHttp,
    MCPServerStreamableHttpParams,
)

from src.logger import get_logger

# Initialize logger
logger = get_logger(__name__)
import nest_asyncio

nest_asyncio.apply()


class MCPAgent:
    """
    Unified agent for LLM and MCP server management.

    This agent handles the integration of:
    - Model: LLM configuration (model name, API key, base URL)
    - Agent Framework: Currently supports OpenAI Agents SDK
    - Service: MCP service type (notion, github, postgres)
    """

    def __init__(
        self,
        model_name: str,
        api_key: str,
        base_url: str,
        mcp_service: str,
        agent_framework: str = "openai_agents",
        timeout: int = 600,
        max_retries: int = 3,
        retry_backoff: float = 5.0,
        service_config: dict | None = None,
        service_config_provider: "Callable[[], dict] | None" = None,
    ):
        """
        Initialize the MCP agent.

        Args:
            model_name: Name of the LLM model to use
            api_key: API key for the model provider
            base_url: Base URL for the model provider
            mcp_service: MCP service type (notion, github, postgres)
            agent_framework: Agent framework to use (default: openai_agents)
            timeout: Execution timeout in seconds
            max_retries: Maximum number of retries for transient errors
            retry_backoff: Backoff time for retries in seconds
        """
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url
        self.mcp_service = mcp_service
        self.agent_framework = agent_framework
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        # Persisted service-specific configuration (e.g., notion_key, browser, test_directory)
        self.service_config: dict[str, Any] = service_config or {}
        # Store optional provider for dynamic config refresh
        self._service_config_provider = service_config_provider

        # Initialize model provider
        self.model_provider = self._create_model_provider()

        # Usage statistics
        self._usage_stats = {
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_tokens": 0,
            "total_turns": 0,
            "total_execution_time": 0.0,
            "successful_executions": 0,
            "failed_executions": 0,
        }

        logger.debug(
            f"Initialized MCPAgent for mcp service '{mcp_service}' with model '{model_name}'"
        )
        # Disable tracing to avoid warnings and unnecessary uploads
        set_tracing_disabled(True)

    def _create_model_provider(self) -> ModelProvider:
        """Create and return a model provider for the specified model."""
        client = AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            default_headers={ "App-Code": "LobeHub", 'HTTP-Referer': 'https://lobehub.com', 'X-Title': 'LobeHub' }
        )
        agent_model_name = self.model_name  # Capture the model name from the agent

        class CustomModelProvider(ModelProvider):
            def get_model(self, model_name_override: str | None) -> Model:
                final_model_name = model_name_override or agent_model_name
                return OpenAIChatCompletionsModel(
                    model=final_model_name, openai_client=client
                )

        return CustomModelProvider()

    def _refresh_service_config(self) -> None:
        """Refresh self.service_config from the provider, if one was supplied."""
        if self._service_config_provider is None:
            return
        try:
            latest_cfg = self._service_config_provider() or {}
            # New values override existing ones
            self.service_config.update(latest_cfg)
        except Exception as exc:
            logger.warning("Failed to refresh service config via provider: %s", exc)

    async def _create_mcp_server(self) -> Any:
        """Create and return an MCP server instance for the current service using self.service_config."""

        cfg = self.service_config  # shorthand

        # Services that use npx or pipx and need startup delay
        NPX_BASED_SERVICES = ["notion", "filesystem", "playwright", "playwright_webarena"]
        PIPX_BASED_SERVICES = ["postgres"]
        
        # Add startup delay for npx-based and pipx-based services to ensure proper initialization
        if self.mcp_service in NPX_BASED_SERVICES or self.mcp_service in PIPX_BASED_SERVICES:
            logger.debug(f"Adding startup delay for service: {self.mcp_service}")
            await asyncio.sleep(5)

        if self.mcp_service == "notion":
            notion_key = cfg.get("notion_key")
            if not notion_key:
                raise ValueError(
                    "Notion API key (notion_key) is required for Notion MCP server"
                )

            return MCPServerStdio(
                params={
                    "command": "npx",
                    "args": ["-y", "@notionhq/notion-mcp-server"],
                    "env": {
                        "OPENAPI_MCP_HEADERS": (
                            '{"Authorization": "Bearer ' + notion_key + '", '
                            '"Notion-Version": "2022-06-28"}'
                        )
                    },
                },
                client_session_timeout_seconds=120,
                cache_tools_list=True,
            )

        elif self.mcp_service == "github":
            github_token = cfg.get("github_token")
            if not github_token:
                raise ValueError(
                    "GitHub token (github_token) is required for GitHub MCP server"
                )

            params = MCPServerStreamableHttpParams(
                url="https://api.githubcopilot.com/mcp/",
                headers={
                    "Authorization": f"Bearer {github_token}",
                    "User-Agent": "MCPMark/1.0",
                },
                timeout_seconds=30,
            )

            return MCPServerStreamableHttp(
                params=params,
                cache_tools_list=True,
                name="GitHub MCP Server",
                client_session_timeout_seconds=120,
            )

        elif self.mcp_service == "filesystem":
            # Filesystem MCP server
            test_directory = cfg.get("test_directory")
            if not test_directory:
                raise ValueError(
                    "filesystem service requires 'test_directory' in service_config"
                )

            return MCPServerStdio(
                params={
                    "command": "npx",
                    "args": [
                        "-y",
                        "@modelcontextprotocol/server-filesystem",
                        str(test_directory),
                    ],
                },
                client_session_timeout_seconds=120,
                cache_tools_list=True,
            )

        elif self.mcp_service == "playwright":
            # Playwright MCP server
            browser = cfg.get("browser", "chromium")
            headless = cfg.get("headless", True)
            viewport_width = cfg.get("viewport_width", 1280)
            viewport_height = cfg.get("viewport_height", 720)

            args = ["-y", "@playwright/mcp@latest"]
            if headless:
                args.append("--headless")
            args.append("--isolated")
            args.append("--no-sandbox")  # Required for Docker
            args.extend(
                [
                    "--browser",
                    browser,
                    "--viewport-size",
                    f"{viewport_width},{viewport_height}",
                ]
            )

            return MCPServerStdio(
                params={
                    "command": "npx",
                    "args": args,
                },
                client_session_timeout_seconds=120,
                cache_tools_list=True,
            )

        elif self.mcp_service == "playwright_webarena":
            # Playwright WebArena MCP server (same as playwright but with base_url support)
            browser = cfg.get("browser", "chromium")
            headless = cfg.get("headless", True)
            viewport_width = cfg.get("viewport_width", 1280)
            viewport_height = cfg.get("viewport_height", 720)

            args = ["-y", "@playwright/mcp@latest"]
            if headless:
                args.append("--headless")
            args.append("--isolated")
            args.extend(
                [
                    "--browser",
                    browser,
                    "--viewport-size",
                    f"{viewport_width},{viewport_height}",
                ]
            )

            return MCPServerStdio(
                params={
                    "command": "npx",
                    "args": args,
                },
                client_session_timeout_seconds=120,
                cache_tools_list=True,
            )

        elif self.mcp_service == "postgres":
            host = cfg.get("host", "localhost")
            port = cfg.get("port", 5432)
            username = cfg.get("username")
            password = cfg.get("password")

            database = cfg.get("current_database") or cfg.get("database")

            if not all([username, password, database]):
                raise ValueError(
                    "PostgreSQL service requires username, password, and database in service_config"
                )

            database_url = (
                f"postgresql://{username}:{password}@{host}:{port}/{database}"
            )

            return MCPServerStdio(
                params={
                    "command": "pipx",
                    "args": ["run", "postgres-mcp", "--access-mode=unrestricted"],
                    "env": {
                        "DATABASE_URI": database_url,
                    },
                },
                client_session_timeout_seconds=120,
                cache_tools_list=True,
            )

        else:
            raise ValueError(f"Unsupported MCP service: {self.mcp_service}")

    async def _execute_with_streaming(self, instruction: str) -> Dict[str, Any]:
        """
        Execute instruction with agent using streaming response.

        Args:
            instruction: The instruction/prompt to execute
            (Service configuration is taken from self.service_config)

        Returns:
            Dictionary containing execution results
        """
        start_time = time.time()

        try:
            # Refresh service configuration before each execution
            self._refresh_service_config()

            # Create MCP server
            async with await self._create_mcp_server() as server:
                # Create agent
                agent = Agent(
                    name=f"{self.mcp_service.title()} Agent", mcp_servers=[server]
                )

                # Configure model settings
                ModelSettings.tool_choice = "required"

                # Service secrets are injected via environment variables inside _create_mcp_server.

                # Prepare conversation
                conversation = [{"content": instruction, "role": "user"}]

                # Run agent with streaming
                result = Runner.run_streamed(
                    agent,
                    max_turns=50,
                    input=conversation,
                    run_config=RunConfig(model_provider=self.model_provider),
                )

                # Add small delay to ensure background task starts
                await asyncio.sleep(0.1)

                # Process streaming events
                event_count = 0
                # Prefix each assistant output line with '| '
                line_prefix = "| "
                at_line_start = True
                last_event_type = None  # Track the previous event type
                async for event in result.stream_events():
                    event_count += 1
                    logger.debug(f"Event {event_count}: {event}")

                    if hasattr(event, "type"):
                        logger.debug(f"Event type: {event.type}")

                        if event.type == "raw_response_event":
                            if hasattr(event, "data") and isinstance(
                                event.data, ResponseTextDeltaEvent
                            ):
                                delta_text = event.data.delta or ""
                                # Stream with line prefix, handling chunked newlines
                                for chunk in delta_text.splitlines(True):  # keepends=True
                                    if at_line_start:
                                        print(line_prefix, end="", flush=True)
                                    print(chunk, end="", flush=True)
                                    at_line_start = chunk.endswith("\n")

                            last_event_type = "text_output"

                        elif event.type == "run_item_stream_event":
                            if (
                                hasattr(event, "item")
                                and getattr(event.item, "type", "") == "tool_call_item"
                            ):
                                if last_event_type == "text_output":
                                    # Add newline if text wasn't already on a new line
                                    if not at_line_start:
                                        print("\n", end="", flush=True)
                                        at_line_start = True

                                tool_name = getattr(
                                    getattr(event.item, "raw_item", None),
                                    "name",
                                    "Unknown",
                                )

                                arguments = getattr(getattr(event.item, "raw_item", None), 'arguments', None)

                                if isinstance(arguments, str):
                                    display_arguments = arguments[:140] + "..." if len(arguments) > 140 else arguments
                                else:
                                    display_arguments = arguments
                                logger.info(
                                    f"| \033[1m{tool_name}\033[0m \033[2;37m{display_arguments}\033[0m"
                                )

                                last_event_type = "tool_call"

                # Extract token usage from raw responses
                token_usage = {}
                if hasattr(result, "raw_responses") and result.raw_responses:
                    total_input_tokens = 0
                    total_output_tokens = 0
                    total_tokens = 0
                    for response in result.raw_responses:
                        if hasattr(response, "usage") and response.usage:
                            total_input_tokens += response.usage.input_tokens
                            total_output_tokens += response.usage.output_tokens
                            total_tokens += response.usage.total_tokens

                    token_usage = {
                        "input_tokens": total_input_tokens,
                        "output_tokens": total_output_tokens,
                        "total_tokens": total_tokens,
                    }

                # Extract turn count
                turn_count = getattr(result, "current_turn", None)

                # Pretty usage block (prefixed lines)
                if token_usage:
                    total_input_tokens = token_usage.get("input_tokens", 0)
                    total_output_tokens = token_usage.get("output_tokens", 0)
                    total_tokens = token_usage.get("total_tokens", 0)

                    lines = [
                        "\n| ────────────────────────────────────────────────",
                        "| \033[1mToken usage\033[0m",
                        "|",
                        f"| Total: {total_tokens:,} | Input: {total_input_tokens:,} | Output: {total_output_tokens:,}",
                    ]
                    if turn_count is not None:
                        lines.append("| ────────────────────────────────────────────────")
                        lines.append(f"| \033[1mTurns\033[0m: {turn_count}")
                        lines.append("| ────────────────────────────────────────────────")
                    logger.info("\n".join(lines))

                # Extract conversation output
                conversation_output = result.to_input_list()

                execution_time = time.time() - start_time

                # Update usage statistics
                self._usage_stats["total_input_tokens"] += token_usage.get(
                    "input_tokens", 0
                )
                self._usage_stats["total_output_tokens"] += token_usage.get(
                    "output_tokens", 0
                )
                self._usage_stats["total_tokens"] += token_usage.get("total_tokens", 0)
                self._usage_stats["total_turns"] += turn_count or 0
                self._usage_stats["total_execution_time"] += execution_time
                self._usage_stats["successful_executions"] += 1

                return {
                    "success": True,
                    "output": conversation_output,
                    "token_usage": token_usage,
                    "turn_count": turn_count,
                    "execution_time": execution_time,
                    "error": None,
                }

        except Exception as e:
            execution_time = time.time() - start_time
            self._usage_stats["failed_executions"] += 1
            self._usage_stats["total_execution_time"] += execution_time

            logger.error(f"| Agent execution failed: {e}", exc_info=True)
            return {
                "success": False,
                "output": "",
                "token_usage": {},
                "turn_count": 0,
                "execution_time": execution_time,
                "error": str(e),
            }

    async def execute(self, instruction: str) -> Dict[str, Any]:
        """
        Execute instruction with automatic retries on transient errors.

        Args:
            instruction: The instruction/prompt to execute
            (Service configuration is taken from self.service_config)

        Returns:
            Dictionary containing:
            - success: bool
            - output: conversation output (list of messages)
            - token_usage: dict with token statistics
            - turn_count: number of conversational turns
            - execution_time: execution time in seconds
            - error: error message if failed
        """

        for attempt in range(1, self.max_retries + 1):
            # Merge default config with any overrides supplied at call time

            result = await asyncio.wait_for(
                self._execute_with_streaming(instruction), timeout=self.timeout
            )

            # Success - return immediately
            if result["success"]:
                return result

            # Standardize error message
            from src.errors import (
                standardize_error_message,
                is_retryable_error,
                get_retry_delay,
            )

            error_msg = standardize_error_message(
                result["error"] or "Unknown error", mcp_service=self.mcp_service
            )
            result["error"] = error_msg

            if is_retryable_error(result["error"]) and attempt < self.max_retries:
                wait_seconds = get_retry_delay(attempt)
                logger.warning(
                    f"[Retry] Attempt {attempt}/{self.max_retries} failed. "
                    f"Waiting {wait_seconds}s before retrying: {error_msg}"
                )
                await asyncio.sleep(wait_seconds)
                continue  # Retry

            # Non-transient error or out of retry attempts - return last result
            return result

        # Should never reach here, but return the last result as fallback
        return result

    def execute_sync(self, instruction: str) -> Dict[str, Any]:
        """
        Synchronous wrapper for execute method.

        Args:
            instruction: The instruction/prompt to execute
            (Service configuration is taken from self.service_config)

        Returns:
            Dictionary containing execution results
        """
        try:
            return asyncio.run(self.execute(instruction))
        except asyncio.TimeoutError:
            self._usage_stats["failed_executions"] += 1
            return {
                "success": False,
                "output": "",
                "token_usage": {},
                "turn_count": 0,
                "execution_time": self.timeout,
                "error": f"Execution timed out after {self.timeout} seconds",
            }

    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics for this agent.

        Returns:
            Dictionary containing usage statistics
        """
        stats = self._usage_stats.copy()

        # Calculate averages
        total_executions = stats["successful_executions"] + stats["failed_executions"]
        if total_executions > 0:
            stats["avg_input_tokens"] = stats["total_input_tokens"] / total_executions
            stats["avg_output_tokens"] = stats["total_output_tokens"] / total_executions
            stats["avg_total_tokens"] = stats["total_tokens"] / total_executions
            stats["avg_turns"] = stats["total_turns"] / total_executions
            stats["avg_execution_time"] = (
                stats["total_execution_time"] / total_executions
            )
            stats["success_rate"] = (
                stats["successful_executions"] / total_executions * 100
            )
        else:
            stats.update(
                {
                    "avg_input_tokens": 0.0,
                    "avg_output_tokens": 0.0,
                    "avg_total_tokens": 0.0,
                    "avg_turns": 0.0,
                    "avg_execution_time": 0.0,
                    "success_rate": 0.0,
                }
            )

        return stats

    def reset_usage_stats(self):
        """Reset usage statistics."""
        self._usage_stats = {
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_tokens": 0,
            "total_turns": 0,
            "total_execution_time": 0.0,
            "successful_executions": 0,
            "failed_executions": 0,
        }

    def __repr__(self):
        return (
            f"MCPAgent(mcp_service='{self.mcp_service}', model='{self.model_name}', "
            f"framework='{self.agent_framework}')"
        )


def main():
    """Example usage of the MCPAgent."""
    from dotenv import load_dotenv

    # Load environment variables
    load_dotenv(dotenv_path=".mcp_env", override=False)

    # Example: Create a Notion agent
    agent = MCPAgent(
        model_name="gpt-4o",
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
        service="notion",
    )

    # Example execution
    instruction = "List all pages in my Notion workspace"

    result = agent.execute_sync(instruction)
    print(f"Success: {result['success']}")
    print(f"Token usage: {result['token_usage']}")
    print(f"Usage stats: {agent.get_usage_stats()}")


if __name__ == "__main__":
    main()
