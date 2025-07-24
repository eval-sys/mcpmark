#!/usr/bin/env python3
"""
MCP Service Factory for MCPBench
=================================

This module provides a factory pattern for creating service-specific managers
and configurations for different MCP services like Notion, GitHub, and PostgreSQL.
"""

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional, Type

from dotenv import load_dotenv

from src.base.login_helper import BaseLoginHelper
from src.base.state_manager import BaseStateManager
from src.base.task_manager import BaseTaskManager
from src.logger import get_logger

# Initialize logger
logger = get_logger(__name__)


class ServiceConfig:
    """
    Configuration container for a specific MCP service.
    It loads the required API keys and other settings from environment variables.
    """

    def __init__(
        self,
        service_name: str,
        api_key_var: Optional[str] = None,
        additional_vars: Optional[Dict[str, str]] = None,
    ):
        self.service_name = service_name
        self.api_key_var = api_key_var
        self.additional_vars = additional_vars or {}

        # Load environment variables from .mcp_env file
        load_dotenv(dotenv_path=".mcp_env", override=False)

        # Primary API key (optional for services that define multiple keys explicitly)
        self.api_key: Optional[str] = None
        if api_key_var is not None:
            self.api_key = os.getenv(api_key_var)
            if not self.api_key:
                raise ValueError(f"Missing required environment variable: {api_key_var}")

        # Load any additional configuration variables (mandatory)
        self.config: Dict[str, str] = {}
        for var_name, env_var in self.additional_vars.items():
            value = os.getenv(env_var)
            if value is None:
                raise ValueError(f"Missing required environment variable: {env_var}")
            self.config[var_name] = value


class ServiceFactory(ABC):
    """Abstract base factory for creating service-specific managers."""

    @abstractmethod
    def create_task_manager(self, config: ServiceConfig, **kwargs) -> BaseTaskManager:
        """Create a task manager for this service."""
        pass

    @abstractmethod
    def create_state_manager(self, config: ServiceConfig, **kwargs) -> BaseStateManager:
        """Create a state manager for this service."""
        pass

    @abstractmethod
    def create_login_helper(self, config: ServiceConfig, **kwargs) -> BaseLoginHelper:
        """Create a login helper for this service."""
        pass


class NotionServiceFactory(ServiceFactory):
    """Factory for creating Notion-specific managers."""

    def create_task_manager(self, config: ServiceConfig, **kwargs) -> BaseTaskManager:
        from src.mcp_services.notion.notion_task_manager import NotionTaskManager

        return NotionTaskManager(
            tasks_root=kwargs.get("tasks_root"),
            model_name=kwargs.get("model_name"),
            api_key=kwargs.get("api_key"),
            base_url=kwargs.get("base_url"),
            notion_key=config.config["eval_api_key"],
            timeout=kwargs.get("timeout", 600),
        )

    def create_state_manager(self, config: ServiceConfig, **kwargs) -> BaseStateManager:
        from src.mcp_services.notion.notion_state_manager import NotionStateManager

        return NotionStateManager(
            source_notion_key=config.config["source_api_key"],
            eval_notion_key=config.config["eval_api_key"],
            model_name=kwargs.get("model_name", "default"),
            headless=kwargs.get("headless", True),
            browser=kwargs.get("browser", "firefox"),
            eval_parent_page_title=config.config["eval_parent_page_title"],
        )

    def create_login_helper(self, config: ServiceConfig, **kwargs) -> BaseLoginHelper:
        from src.mcp_services.notion.notion_login_helper import NotionLoginHelper

        return NotionLoginHelper(
            url=kwargs.get("url"),
            headless=kwargs.get("headless", True),
            browser=kwargs.get("browser", "firefox"),
            state_path=kwargs.get("state_path"),
        )


class GitHubServiceFactory(ServiceFactory):
    """Factory for creating GitHub-specific managers."""

    def create_task_manager(self, config: ServiceConfig, **kwargs) -> BaseTaskManager:
        from src.mcp_services.github.github_task_manager import GitHubTaskManager

        return GitHubTaskManager(
            tasks_root=kwargs.get("tasks_root"),
            model_name=kwargs.get("model_name"),
            api_key=kwargs.get("api_key"),
            base_url=kwargs.get("base_url"),
            github_token=config.api_key,  # GitHub uses the primary API key
            timeout=kwargs.get("timeout", 600),
        )

    def create_state_manager(self, config: ServiceConfig, **kwargs) -> BaseStateManager:
        from src.mcp_services.github.github_state_manager import GitHubStateManager

        return GitHubStateManager(
            github_token=config.api_key,
            base_repo_owner="mcpbench",  # 使用默认值
            test_org="mcpbench-eval",    # 使用默认值
        )

    def create_login_helper(self, config: ServiceConfig, **kwargs) -> BaseLoginHelper:
        from src.mcp_services.github.github_login_helper import GitHubLoginHelper

        return GitHubLoginHelper(
            token=config.api_key,
            state_path=kwargs.get("state_path"),
        )


class PostgreSQLServiceFactory(ServiceFactory):
    """Factory for creating PostgreSQL-specific managers."""

    def create_task_manager(self, config: ServiceConfig, **kwargs) -> BaseTaskManager:
        raise NotImplementedError("PostgreSQL task manager not yet implemented.")

    def create_state_manager(self, config: ServiceConfig, **kwargs) -> BaseStateManager:
        raise NotImplementedError("PostgreSQL state manager not yet implemented.")

    def create_login_helper(self, config: ServiceConfig, **kwargs) -> BaseLoginHelper:
        raise NotImplementedError("PostgreSQL login helper not yet implemented.")


class FilesystemServiceFactory(ServiceFactory):
    """Factory for creating Filesystem-specific managers."""

    def create_task_manager(self, config: ServiceConfig, **kwargs) -> BaseTaskManager:
        from src.mcp_services.filesystem.filesystem_task_manager import FilesystemTaskManager

        return FilesystemTaskManager(
            tasks_root=kwargs.get("tasks_root"),
            model_name=kwargs.get("model_name"),
            api_key=kwargs.get("api_key"),
            base_url=kwargs.get("base_url"),
            test_directory=config.config.get("test_root"),
            timeout=kwargs.get("timeout", 600),
        )

    def create_state_manager(self, config: ServiceConfig, **kwargs) -> BaseStateManager:
        from src.mcp_services.filesystem.filesystem_state_manager import FilesystemStateManager

        test_root = None
        if "test_root" in config.config:
            test_root = Path(config.config["test_root"])

        return FilesystemStateManager(
            test_root=test_root,
            cleanup_on_exit=kwargs.get("cleanup_on_exit", True),
        )

    def create_login_helper(self, config: ServiceConfig, **kwargs) -> BaseLoginHelper:
        from src.mcp_services.filesystem.filesystem_login_helper import FilesystemLoginHelper

        return FilesystemLoginHelper(
            state_path=kwargs.get("state_path"),
        )


class MCPServiceFactory:
    """
    Main factory for creating MCP service components.
    This class maps service names to their respective factories and configurations.
    """

    SERVICE_CONFIGS = {
        # Notion now uses two distinct keys: SOURCE & EVAL.
        "notion": {
            "api_key_var": None,  # handled via additional_vars
            "additional_vars": {
                "eval_api_key": "EVAL_NOTION_API_KEY",
                "source_api_key": "SOURCE_NOTION_API_KEY",
                "eval_parent_page_title": "EVAL_PARENT_PAGE_TITLE",
            },
        },
        "github": {
            "api_key_var": "GITHUB_TOKEN",
            "additional_vars": {
                # These are optional for basic testing
            },
        },
        "postgres": {
            "api_key_var": "POSTGRES_PASSWORD",
            "additional_vars": {
                "host": "POSTGRES_HOST",
                "port": "POSTGRES_PORT",
                "database": "POSTGRES_DATABASE",
                "username": "POSTGRES_USERNAME",
            },
        },
        "filesystem": {
            "api_key_var": None,  # No authentication needed
            "additional_vars": {
                "test_root": "FILESYSTEM_TEST_ROOT",  # Optional: root directory for tests
            },
        },
    }

    SERVICE_FACTORIES = {
        "notion": NotionServiceFactory(),
        "github": GitHubServiceFactory(),
        "filesystem": FilesystemServiceFactory(),
        # "postgres": PostgreSQLServiceFactory(),
    }

    @classmethod
    def get_supported_services(cls) -> list:
        """Returns a list of supported service names."""
        return list(cls.SERVICE_CONFIGS.keys())

    @classmethod
    def create_service_config(cls, service_name: str) -> ServiceConfig:
        """
        Creates a configuration object for a given service.

        Args:
            service_name: The name of the service.

        Returns:
            A ServiceConfig instance.

        Raises:
            ValueError: If the service is not supported.
        """
        if service_name not in cls.SERVICE_CONFIGS:
            supported = ", ".join(cls.get_supported_services())
            raise ValueError(
                f"Unsupported service '{service_name}'. Supported services: {supported}"
            )

        config_info = cls.SERVICE_CONFIGS[service_name]
        return ServiceConfig(
            service_name=service_name,
            api_key_var=config_info["api_key_var"],
            additional_vars=config_info["additional_vars"],
        )

    @classmethod
    def _get_factory(cls, service_name: str) -> ServiceFactory:
        """Retrieves the factory for a given service."""
        if service_name not in cls.SERVICE_FACTORIES:
            raise ValueError(f"No factory registered for service: {service_name}")
        return cls.SERVICE_FACTORIES[service_name]

    @classmethod
    def create_task_manager(cls, service_name: str, **kwargs) -> BaseTaskManager:
        """Creates a task manager for the specified service."""
        config = cls.create_service_config(service_name)
        factory = cls._get_factory(service_name)
        return factory.create_task_manager(config, **kwargs)

    @classmethod
    def create_state_manager(cls, service_name: str, **kwargs) -> BaseStateManager:
        """Creates a state manager for the specified service."""
        config = cls.create_service_config(service_name)
        factory = cls._get_factory(service_name)
        return factory.create_state_manager(config, **kwargs)

    @classmethod
    def create_login_helper(cls, service_name: str, **kwargs) -> BaseLoginHelper:
        """Creates a login helper for the specified service."""
        config = cls.create_service_config(service_name)
        factory = cls._get_factory(service_name)
        return factory.create_login_helper(config, **kwargs)

    @classmethod
    def get_service_api_key(cls, service_name: str) -> str:
        """Retrieves the API key for a specific service."""
        config = cls.create_service_config(service_name)
        return config.api_key


def main():
    """Example usage of the service factory."""
    logger.info("Supported services: %s", MCPServiceFactory.get_supported_services())

    try:
        # Create Notion service components
        notion_config = MCPServiceFactory.create_service_config("notion")
        logger.info("Notion API key loaded: %s", bool(notion_config.api_key))

        # Example: Create a task manager for Notion
        task_manager = MCPServiceFactory.create_task_manager(
            "notion",
            model_name="gpt-4",
            api_key="test-key",
            base_url="https://api.example.com",
            timeout=300,
        )
        logger.info("Created task manager: %s", type(task_manager).__name__)

    except ValueError as e:
        logger.error("Configuration error: %s", e)


if __name__ == "__main__":
    main()
