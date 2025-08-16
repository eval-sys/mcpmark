#!/usr/bin/env python3
"""
MCP Service Factory for MCPMark
=================================

This module provides a simplified factory pattern for creating service-specific managers
with centralized configuration management.

Features:
- Dynamic service loading from definitions
- Centralized configuration
- Simplified service registration
"""

import importlib
from dataclasses import dataclass
from typing import Dict, Type

from src.base.login_helper import BaseLoginHelper
from src.base.state_manager import BaseStateManager
from src.base.task_manager import BaseTaskManager
from src.config.config_schema import ConfigRegistry
from src.services import get_service_definition, get_supported_mcp_services


@dataclass
class ServiceComponents:
    """All components required for an MCP service."""

    task_manager_class: Type[BaseTaskManager]
    state_manager_class: Type[BaseStateManager]
    login_helper_class: Type[BaseLoginHelper]
    config_mapping: Dict[str, Dict[str, str]]


def import_class(module_path: str):
    """Dynamically import a class from module path string."""
    if not module_path:
        return None
    module_name, class_name = module_path.rsplit(".", 1)
    module = importlib.import_module(module_name)
    return getattr(module, class_name)


def apply_config_mapping(config: dict, mapping: dict) -> dict:
    """Apply config mapping to transform config keys to constructor params."""
    if not mapping:
        return {}

    result = {}
    for param_name, config_key in mapping.items():
        if config_key in config:
            result[param_name] = config[config_key]
    return result


class ServiceRegistry:
    """Central registry that loads MCP services from definitions."""

    # Cache for loaded components
    _components_cache: Dict[str, ServiceComponents] = {}

    @classmethod
    def get_components(cls, service_name: str) -> ServiceComponents:
        """Get MCP service components from definition."""
        if service_name in cls._components_cache:
            return cls._components_cache[service_name]

        definition = get_service_definition(service_name)

        # Import classes dynamically
        components = ServiceComponents(
            task_manager_class=import_class(definition["components"]["task_manager"]),
            state_manager_class=import_class(definition["components"]["state_manager"]),
            login_helper_class=import_class(definition["components"]["login_helper"]),
            config_mapping=definition.get("config_mapping", {}),
        )

        cls._components_cache[service_name] = components
        return components


class GenericServiceFactory:
    """Generic factory that works with any MCP service."""

    def __init__(self, components: ServiceComponents, service_name: str):
        self.components = components
        self.service_name = service_name

    def create_task_manager(self, **kwargs) -> BaseTaskManager:
        """Create task manager instance."""
        return self.components.task_manager_class(**kwargs)

    def create_state_manager(self, config) -> BaseStateManager:
        """Create state manager with config mapping."""
        mapping = self.components.config_mapping.get("state_manager", {})
        # Handle both dict and config schema objects
        config_dict = config.get_all() if hasattr(config, "get_all") else config
        kwargs = apply_config_mapping(config_dict, mapping)
        return self.components.state_manager_class(**kwargs)

    def create_login_helper(self, config) -> BaseLoginHelper:
        """Create login helper with config mapping."""
        mapping = self.components.config_mapping.get("login_helper", {})
        # Handle both dict and config schema objects
        config_dict = config.get_all() if hasattr(config, "get_all") else config
        kwargs = apply_config_mapping(config_dict, mapping)
        
        # Special handling for GitHub login helper - it needs a single token
        if self.service_name == "github" and "token" in kwargs:
            tokens_list = kwargs["token"]
            if isinstance(tokens_list, list) and tokens_list:
                kwargs["token"] = tokens_list[0]  # Use first token for login helper
                
        return self.components.login_helper_class(**kwargs)


class MCPServiceFactory:
    """Main factory interface."""

    @classmethod
    def create_service_config(cls, service_name: str):
        """Create MCP service configuration (backward compatible)."""
        config = ConfigRegistry.get_config(service_name)

        # Create a backward-compatible ServiceConfig-like object
        class ServiceConfigCompat:
            def __init__(self, service_name: str, config_dict: dict):
                self.service_name = service_name
                self.config = config_dict
                self.api_key = config_dict.get("api_key")

        return ServiceConfigCompat(service_name, config.get_all())

    @classmethod
    def create_task_manager(cls, service_name: str, **kwargs) -> BaseTaskManager:
        """Create task manager for the specified MCP service."""
        components = ServiceRegistry.get_components(service_name)
        return components.task_manager_class(**kwargs)

    @classmethod
    def create_state_manager(cls, service_name: str, **kwargs) -> BaseStateManager:
        """Create state manager for the specified MCP service."""
        components = ServiceRegistry.get_components(service_name)
        config = ConfigRegistry.get_config(service_name).get_all()

        # Use provided kwargs or apply config mapping
        if not kwargs:
            mapping = components.config_mapping.get("state_manager", {})
            kwargs = apply_config_mapping(config, mapping)

        return components.state_manager_class(**kwargs)

    @classmethod
    def create_login_helper(cls, service_name: str, **kwargs) -> BaseLoginHelper:
        """Create login helper for the specified MCP service."""
        components = ServiceRegistry.get_components(service_name)
        config = ConfigRegistry.get_config(service_name).get_all()

        # Use provided kwargs or apply config mapping
        if not kwargs:
            mapping = components.config_mapping.get("login_helper", {})
            kwargs = apply_config_mapping(config, mapping)
            
            # Special handling for GitHub login helper - it needs a single token
            if service_name == "github" and "token" in kwargs:
                tokens_list = kwargs["token"]
                if isinstance(tokens_list, list) and tokens_list:
                    kwargs["token"] = tokens_list[0]  # Use first token for login helper

        return components.login_helper_class(**kwargs)

    @classmethod
    def get_supported_mcp_services(cls) -> list:
        """Get list of supported MCP services."""
        return get_supported_mcp_services()

    @classmethod
    def get_config_info(cls, service_name: str) -> dict:
        """Get detailed configuration information for debugging."""
        config = ConfigRegistry.get_config(service_name)
        return config.get_debug_info()

    @classmethod
    def export_config_template(cls, service_name: str, output_path: str) -> None:
        """Export a configuration template for an MCP service."""
        from pathlib import Path

        ConfigRegistry.export_template(service_name, Path(output_path))
