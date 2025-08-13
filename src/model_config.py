#!/usr/bin/env python3
"""
Model Configuration for MCPMark
================================

This module provides configuration management for different LLM models,
automatically detecting the required API keys and base URLs based on the model name.
"""

import os
from typing import Dict, List

from src.logger import get_logger

# Initialize logger
logger = get_logger(__name__)


class ModelConfig:
    """
    Configuration container for a specific model.
    It loads the necessary API key and base URL from environment variables.
    """

    # Model configuration mapping
    MODEL_CONFIGS = {
        # OpenAI models
        "gpt-4o": {
            "provider": "openai",
            "api_key_var": "OPENAI_API_KEY",
            "base_url_var": "OPENAI_BASE_URL",
            "actual_model_name": "gpt-4o",
        },
        "gpt-4.1": {
            "provider": "openai",
            "api_key_var": "OPENAI_API_KEY",
            "base_url_var": "OPENAI_BASE_URL",
            "actual_model_name": "gpt-4.1",
        },
        "gpt-4.1-mini": {
            "provider": "openai",
            "api_key_var": "OPENAI_API_KEY",
            "base_url_var": "OPENAI_BASE_URL",
            "actual_model_name": "gpt-4.1-mini",
        },
        "gpt-5": {
            "provider": "openai",
            "api_key_var": "OPENAI_API_KEY",
            "base_url_var": "OPENAI_BASE_URL",
            "actual_model_name": "gpt-5",
        },
        "gpt-5-mini": {
            "provider": "openai",
            "api_key_var": "OPENAI_API_KEY",
            "base_url_var": "OPENAI_BASE_URL",
            "actual_model_name": "gpt-5-mini",
        },
        "gpt-5-nano": {
            "provider": "openai",
            "api_key_var": "OPENAI_API_KEY",
            "base_url_var": "OPENAI_BASE_URL",
            "actual_model_name": "gpt-5-nano",
        },
        "o3": {
            "provider": "openai",
            "api_key_var": "OPENAI_API_KEY",
            "base_url_var": "OPENAI_BASE_URL",
            "actual_model_name": "o3",
        },
        "o4-mini": {
            "provider": "openai",
            "api_key_var": "OPENAI_API_KEY",
            "base_url_var": "OPENAI_BASE_URL",
            "actual_model_name": "o4-mini",
        },
        # DeepSeek models
        "deepseek-chat": {
            "provider": "deepseek",
            "api_key_var": "DEEPSEEK_API_KEY",
            "base_url_var": "DEEPSEEK_BASE_URL",
            "actual_model_name": "deepseek-chat",
        },
        "deepseek-reasoner": {
            "provider": "deepseek",
            "api_key_var": "DEEPSEEK_API_KEY",
            "base_url_var": "DEEPSEEK_BASE_URL",
            "actual_model_name": "deepseek-reasoner",
        },
        # Anthropic models
        "claude-3-7-sonnet": {
            "provider": "anthropic",
            "api_key_var": "ANTHROPIC_API_KEY",
            "base_url_var": "ANTHROPIC_BASE_URL",
            "actual_model_name": "claude-3-7-sonnet-20250219",
        },
        "claude-4-sonnet": {
            "provider": "anthropic",
            "api_key_var": "ANTHROPIC_API_KEY",
            "base_url_var": "ANTHROPIC_BASE_URL",
            "actual_model_name": "claude-sonnet-4-20250514",
        },
        "claude-4-opus": {
            "provider": "anthropic",
            "api_key_var": "ANTHROPIC_API_KEY",
            "base_url_var": "ANTHROPIC_BASE_URL",
            "actual_model_name": "claude-opus-4-20250514",
        },
        # Google models
        "gemini-2.5-pro": {
            "provider": "google",
            "api_key_var": "GEMINI_API_KEY",
            "base_url_var": "GEMINI_BASE_URL",
            "actual_model_name": "gemini-2.5-pro",
        },
        "gemini-2.5-flash": {
            "provider": "google",
            "api_key_var": "GEMINI_API_KEY",
            "base_url_var": "GEMINI_BASE_URL",
            "actual_model_name": "gemini-2.5-flash",
        },
        # Moonshot models
        "k2": {
            "provider": "moonshot",
            "api_key_var": "MOONSHOT_API_KEY",
            "base_url_var": "MOONSHOT_BASE_URL",
            "actual_model_name": "kimi-k2-0711-preview",
        },
        # Grok models
        "grok-4": {
            "provider": "moonshot",
            "api_key_var": "GROK_API_KEY",
            "base_url_var": "GROK_BASE_URL",
            "actual_model_name": "grok-4-0709",
        },
    }

    def __init__(self, model_name: str):
        """
        Initializes the model configuration.

        Args:
            model_name: The name of the model (e.g., 'gpt-4o', 'deepseek-chat').

        Raises:
            ValueError: If the model is not supported or environment variables are missing.
        """
        self.model_name = model_name
        model_info = self._get_model_info(model_name)

        # Load API key and base URL from environment variables
        self.api_key = os.getenv(model_info["api_key_var"])
        if not self.api_key:
            raise ValueError(
                f"Missing required environment variable: {model_info['api_key_var']}"
            )

        self.base_url = os.getenv(model_info["base_url_var"])
        if not self.base_url:
            raise ValueError(
                f"Missing required environment variable: {model_info['base_url_var']}"
            )

        # Store provider and the actual model name for the API
        self.provider = model_info["provider"]
        self.actual_model_name = model_info.get("actual_model_name", model_name)

    def _get_model_info(self, model_name: str) -> Dict[str, str]:
        """
        Retrieves the configuration details for a given model name.
        For unsupported models, defaults to using OPENAI_BASE_URL and OPENAI_API_KEY.
        """
        if model_name not in self.MODEL_CONFIGS:
            logger.warning(
                f"Model '{model_name}' not in supported list. Using default OpenAI configuration."
            )
            # Return default configuration for unsupported models
            return {
                "provider": "openai",
                "api_key_var": "OPENAI_API_KEY",
                "base_url_var": "OPENAI_BASE_URL",
                "actual_model_name": model_name,
            }
        return self.MODEL_CONFIGS[model_name]

    @classmethod
    def get_supported_models(cls) -> List[str]:
        """Returns a list of all supported model names."""
        return list(cls.MODEL_CONFIGS.keys())


def main():
    """Example usage of the ModelConfig class."""
    logger.info("Supported models: %s", ModelConfig.get_supported_models())

    try:
        # Example: Create a model config for DeepSeek
        model_config = ModelConfig("deepseek-chat")
        logger.info("✅ DeepSeek model config created successfully.")
        logger.info("Provider: %s", model_config.provider)
        logger.info("Actual model name: %s", model_config.actual_model_name)
        logger.info("API key loaded: %s", bool(model_config.api_key))
        logger.info("Base URL: %s", model_config.base_url)

    except ValueError as e:
        logger.error("⚠️  Configuration error: %s", e)


if __name__ == "__main__":
    main()
