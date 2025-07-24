#!/usr/bin/env python3
"""
Filesystem Task Manager for MCPBench Evaluation Pipeline
========================================================

This module provides utilities for discovering, filtering, and managing
filesystem-based evaluation tasks using the filesystem MCP server.
"""

import asyncio
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from agents import (
    Agent,
    Model,
    ModelProvider,
    ModelSettings,
    OpenAIChatCompletionsModel,
    RunConfig,
    Runner,
    set_tracing_export_api_key,
)
from agents.mcp.server import MCPServerStdio, MCPServerStdioParams
from openai import AsyncOpenAI
from openai.types.responses import ResponseTextDeltaEvent

from src.base.task_manager import BaseTask, BaseTaskManager
from src.logger import get_logger
from src.results_reporter import TaskResult

logger = get_logger(__name__)

set_tracing_export_api_key(os.getenv("OPENAI_TRACE_API_KEY"))


@dataclass
class FilesystemTask(BaseTask):
    """Represents a single evaluation task for filesystem service."""
    # Filesystem-specific fields
    test_directory: Optional[str] = None
    expected_files: Optional[List[str]] = None
    expected_directories: Optional[List[str]] = None


class FilesystemTaskManager(BaseTaskManager):
    """Manages task discovery, filtering, and execution for filesystem-based MCPBench evaluation."""
    
    def __init__(self, tasks_root: Path = None, model_name: str = None, api_key: str = None,
                 base_url: str = None, test_directory: str = None, timeout: int = 600):
        """Initialize filesystem task manager with configuration.
        
        Args:
            tasks_root: Path to the tasks directory
            model_name: Name of the model to use for task execution
            api_key: API key for the model provider
            base_url: Base URL for the model provider
            test_directory: Directory for filesystem operations (from state manager)
            timeout: Task execution timeout in seconds
        """
        if tasks_root is None:
            tasks_root = Path(__file__).resolve().parents[3] / "tasks"
        
        # Call parent constructor
        super().__init__(tasks_root, service="filesystem")
        
        self._tasks_cache = None
        
        # Execution configuration
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url
        self.test_directory = test_directory
        self.timeout = timeout
        
        # Initialize model provider if configuration is provided
        self.model_provider = None
        if all([model_name, api_key, base_url]):
            self.model_provider = self._create_model_provider()
        
        # Ensure logs directory exists
        self.logs_dir = Path("./logs")
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Retry configuration
        self.max_retries: int = 3
        self.retry_backoff: float = 5.0
    
    def _create_model_provider(self) -> ModelProvider:
        base_url = self.base_url
        api_key = self.api_key
        model_name = self.model_name
        client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        
        class CustomModelProvider(ModelProvider):
            def get_model(self, model_name_override: str | None) -> Model:
                final_model_name = model_name_override or model_name
                return OpenAIChatCompletionsModel(
                    model=final_model_name, openai_client=client
                )
        
        return CustomModelProvider()
    
    # =========================================================================
    # Task Discovery and Management
    # =========================================================================
    
    def discover_all_tasks(self) -> List[FilesystemTask]:
        """Discover all available filesystem tasks in the tasks directory."""
        if self._tasks_cache is not None:
            return self._tasks_cache
        
        tasks = []
        if not self.tasks_root.exists():
            logger.warning("Tasks root directory does not exist: %s", self.tasks_root)
            return tasks
        
        # Look for filesystem service directory
        filesystem_tasks_dir = self.tasks_root / "filesystem"
        if not filesystem_tasks_dir.exists():
            logger.warning("Filesystem tasks directory does not exist: %s", filesystem_tasks_dir)
            return tasks
        
        # Scan categories
        for category_dir in filesystem_tasks_dir.iterdir():
            if not category_dir.is_dir():
                continue
            
            category_name = category_dir.name
            logger.info("Discovering tasks in category: %s", category_name)
            
            # Find all task files in this category
            for task_file in category_dir.glob("task_*.md"):
                task_id = self._extract_task_id(task_file.name)
                if task_id is None:
                    continue
                
                # Look for corresponding verification script
                verify_file = task_file.parent / f"task_{task_id}_verify.py"
                if not verify_file.exists():
                    logger.warning("No verification script found for task: %s", task_file)
                    continue
                
                task = FilesystemTask(
                    task_instruction_path=task_file,
                    task_verification_path=verify_file,
                    service="filesystem",
                    category=category_name,
                    task_id=task_id
                )
                tasks.append(task)
                logger.debug("Found task: %s", task.name)
        
        self._tasks_cache = sorted(tasks, key=lambda t: (t.category, t.task_id))
        logger.info("Discovered %d filesystem tasks across all categories", len(self._tasks_cache))
        return self._tasks_cache
    
    def _extract_task_id(self, filename: str) -> Optional[int]:
        """Extract task ID from filename like 'task_1.md'."""
        import re
        match = re.match(r'task_(\d+)\.md', filename)
        return int(match.group(1)) if match else None
    
    def get_categories(self) -> List[str]:
        """Get a list of all task categories."""
        tasks = self.discover_all_tasks()
        return sorted(list(set(task.category for task in tasks)))
    
    def filter_tasks(self, task_filter: str) -> List[FilesystemTask]:
        """Filter tasks based on category or task name pattern."""
        all_tasks = self.discover_all_tasks()
        
        if not task_filter or task_filter.lower() == "all":
            return all_tasks
        
        # Check if it's a category filter
        categories = self.get_categories()
        if task_filter in categories:
            return [task for task in all_tasks if task.category == task_filter]
        
        # Check if it's a specific task filter (e.g., "basic_operations/task_1")
        if "/" in task_filter:
            try:
                category, task_part = task_filter.split("/", 1)
                if task_part.startswith("task_"):
                    task_id = int(task_part.split("_")[1])
                    for task in all_tasks:
                        if task.category == category and task.task_id == task_id:
                            return [task]
            except (ValueError, IndexError):
                pass
        
        # Fallback: partial matching
        filtered_tasks = []
        for task in all_tasks:
            if (task_filter in task.category or 
                task_filter in task.name or 
                task_filter == str(task.task_id)):
                filtered_tasks.append(task)
        
        return filtered_tasks
    
    # =========================================================================
    # Task Execution
    # =========================================================================
    
    async def _create_mcp_server(self):
        """Create and return filesystem MCP server connection via stdio."""
        # Get test directory from task or use default
        if hasattr(self, 'current_task') and hasattr(self.current_task, 'test_directory'):
            allowed_dir = self.current_task.test_directory
        elif self.test_directory:
            allowed_dir = self.test_directory
        else:
            # Fallback to temp directory
            allowed_dir = tempfile.gettempdir()
        
        logger.info(f"Starting filesystem MCP server with allowed directory: {allowed_dir}")
        
        # Use NPX to run the filesystem MCP server
        params = MCPServerStdioParams(
            command="npx",
            args=[
                "-y",
                "@modelcontextprotocol/server-filesystem",
                allowed_dir  # Pass the allowed directory
            ],
            env={
                **os.environ,
                "NODE_ENV": "production"
            }
        )
        
        return MCPServerStdio(
            params=params,
            name="Filesystem MCP Server"
        )
    
    def _read_task_file(self, path: Path) -> str:
        """Return the full text content of a task file."""
        if not path.exists():
            raise FileNotFoundError(f"Task file '{path}' does not exist")
        
        content = path.read_text(encoding="utf-8")
        
        # If task has test directory, add it to the instruction
        if hasattr(self, 'current_task') and hasattr(self.current_task, 'test_directory'):
            content += f"\n\nNote: All filesystem operations should be performed within the test directory: {self.current_task.test_directory}"
        
        return content
    
    async def _run_single_task_async(self, agent: Agent, task_content: str) -> tuple[str, dict, int]:
        """Send task content to agent and stream the response."""
        # Prepare the conversation with task instruction
        conversation = [{"content": task_content, "role": "user"}]
        
        # Run the agent with filesystem MCP tools
        result = Runner.run_streamed(
            agent,
            max_turns=20,
            input=conversation,
            run_config=RunConfig(model_provider=self.model_provider)
        )
        
        # Add a small delay to ensure background task starts
        await asyncio.sleep(0.1)
        
        try:
            event_count = 0
            async for event in result.stream_events():
                event_count += 1
                logger.debug(f"Event {event_count}: {event}")
                
                # Check if event has type attribute
                if hasattr(event, 'type'):
                    logger.debug(f"Event type: {event.type}")
                    
                    if event.type == "raw_response_event":
                        if hasattr(event, 'data') and isinstance(event.data, ResponseTextDeltaEvent):
                            # Print token deltas as we receive them
                            delta_text = event.data.delta
                            print(delta_text, end="", flush=True)
                    elif event.type == "run_item_stream_event":
                        if hasattr(event, 'item'):
                            if hasattr(event.item, 'type'):
                                if event.item.type == "tool_call_item":
                                    tool_name = getattr(event.item.raw_item, 'name', 'Unknown') if hasattr(event.item, 'raw_item') else 'Unknown'
                                    logger.info(f"\n-- Calling Filesystem Tool: {tool_name}...")
            
            # Log token usage from raw_responses
            if hasattr(result, 'raw_responses') and result.raw_responses:
                total_input_tokens = 0
                total_output_tokens = 0
                total_tokens = 0
                for response in result.raw_responses:
                    if hasattr(response, 'usage') and response.usage:
                        total_input_tokens += response.usage.input_tokens
                        total_output_tokens += response.usage.output_tokens
                        total_tokens += response.usage.total_tokens
                logger.info(f"\nToken usage - Input: {total_input_tokens}, Output: {total_output_tokens}, Total: {total_tokens}")
            
            if hasattr(result, 'current_turn'):
                turn_count = result.current_turn
                logger.info(f"Turn count: {turn_count}")
                
        except Exception as e:
            logger.error(f"Error during streaming: {e}", exc_info=True)
            if result._run_impl_task:
                logger.error(f"Background task exception: {result._run_impl_task.exception()}")
        
        # Extract token usage before returning
        token_usage: dict = {}
        if hasattr(result, 'raw_responses') and result.raw_responses:
            total_input = 0
            total_output = 0
            total = 0
            for resp in result.raw_responses:
                if hasattr(resp, 'usage') and resp.usage:
                    total_input += resp.usage.input_tokens
                    total_output += resp.usage.output_tokens
                    total += resp.usage.total_tokens
            token_usage = {
                "input_tokens": total_input,
                "output_tokens": total_output,
                "total_tokens": total
            }
        
        # Extract turn count (number of conversational turns)
        turn_count = getattr(result, "current_turn", None)
        
        return result.to_input_list(), token_usage, turn_count
    
    def _run_single_task_file_once(self, task_file_path: str, timeout: int) -> Dict[str, Any]:
        """Run a single filesystem task file exactly once."""
        task_path = Path(task_file_path)
        
        try:
            async def _run() -> tuple[str, dict, int]:
                """Internal coroutine that performs the actual evaluation."""
                async with await self._create_mcp_server() as server:
                    agent = Agent(name="Filesystem Agent", mcp_servers=[server])
                    ModelSettings.tool_choice = "required"
                    
                    task_content = self._read_task_file(task_path)
                    
                    # Run the task with filesystem MCP tools
                    return await self._run_single_task_async(agent, task_content)
            
            # Execute with timeout handling
            assistant_response, token_usage, turn_count = asyncio.run(asyncio.wait_for(_run(), timeout=timeout))
            
            return {
                "success": True,
                "output": assistant_response,
                "error": None,
                "token_usage": token_usage,
                "turn_count": turn_count,
            }
            
        except asyncio.TimeoutError:
            return {
                "success": False,
                "output": "",
                "error": f"Task timed out after {timeout} seconds",
            }
        except Exception as exc:
            return {
                "success": False,
                "output": "",
                "error": str(exc),
            }
    
    def run_single_task_file(self, task_file_path: str, timeout: int = None) -> Dict[str, Any]:
        """Run a single filesystem task file with retry logic."""
        if timeout is None:
            timeout = self.timeout
        
        for attempt in range(self.max_retries):
            result = self._run_single_task_file_once(task_file_path, timeout)
            
            if result["success"] or attempt == self.max_retries - 1:
                return result
            
            # Check if this is a retryable error
            error = result.get("error", "")
            if "MCP" in error or "network" in error.lower():
                wait_time = self.retry_backoff * (attempt + 1)
                logger.warning(f"Filesystem MCP task failed (attempt {attempt + 1}/{self.max_retries}), retrying in {wait_time}s: {error}")
                time.sleep(wait_time)
            else:
                # Non-retryable error, return immediately
                return result
        
        return result
    
    def execute_task(self, task: FilesystemTask) -> TaskResult:
        """Execute a single filesystem task and return the result."""
        start_time = time.time()
        logger.info(f"Executing filesystem task: {task.name}")
        
        # Store current task for directory access
        self.current_task = task
        
        try:
            # Prepare task description with filesystem context
            task_description = task.get_task_instruction()
            
            # Create temporary task file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                f.write(task_description)
                temp_task_path = f.name
            
            try:
                # Run the task
                result = self.run_single_task_file(temp_task_path, timeout=self.timeout)
                
                # Check for MCP network errors
                if not result["success"] and "MCP" in result.get("error", ""):
                    execution_time = time.time() - start_time
                    return TaskResult(
                        task_name=task.name,
                        success=False,
                        execution_time=execution_time,
                        error_message="Filesystem MCP Network Error",
                        category=task.category,
                        task_id=task.task_id
                    )
                
                # Run verification
                logger.info(f"- Running verification for task: {task.name}")
                
                # Set environment variable for test directory if available
                env = os.environ.copy()
                if hasattr(task, 'test_directory'):
                    env['FILESYSTEM_TEST_DIR'] = task.test_directory
                
                verify_result = subprocess.run(
                    [sys.executable, str(task.task_verification_path)],
                    capture_output=True,
                    text=True,
                    timeout=90,
                    env=env
                )
                
                # Process results
                success = verify_result.returncode == 0
                error_message = verify_result.stderr if not success and verify_result.stderr else None
                execution_time = time.time() - start_time
                
                return TaskResult(
                    task_name=task.name,
                    success=success,
                    execution_time=execution_time,
                    error_message=error_message,
                    category=task.category,
                    task_id=task.task_id
                )
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_task_path):
                    os.unlink(temp_task_path)
                
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Task execution failed: {e}", exc_info=True)
            return TaskResult(
                task_name=task.name,
                success=False,
                execution_time=execution_time,
                error_message=str(e),
                category=task.category,
                task_id=task.task_id
            )
        finally:
            # Clear current task reference
            self.current_task = None
    
    def run_tasks(self, tasks: List[FilesystemTask], **kwargs) -> List[TaskResult]:
        """Run multiple filesystem tasks and return results."""
        results = []
        for task in tasks:
            result = self.execute_task(task)
            results.append(result)
            logger.info(f"Task {task.name}: {'PASS' if result.success else 'FAIL'}")
        
        return results