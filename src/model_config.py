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
            "actual_model_name": "gpt-4o",
            "litellm_model": "openai/gpt-4o",
        },
        "gpt-4.1": {
            "provider": "openai",
            "api_key_var": "OPENAI_API_KEY",
            "actual_model_name": "gpt-4.1",
            "litellm_model": "openai/gpt-4.1",
        },
        "gpt-4.1-mini": {
            "provider": "openai",
            "api_key_var": "OPENAI_API_KEY",
            "actual_model_name": "gpt-4.1-mini",
            "litellm_model": "openai/gpt-4.1-mini",
        },
        "gpt-5": {
            "provider": "openai",
            "api_key_var": "OPENAI_API_KEY",
            "actual_model_name": "gpt-5",
            "litellm_model": "openai/gpt-5",
        },
        "gpt-5-mini": {
            "provider": "openai",
            "api_key_var": "OPENAI_API_KEY",
            "actual_model_name": "gpt-5-mini",
            "litellm_model": "openai/gpt-5-mini",
        },
        "gpt-5-nano": {
            "provider": "openai",
            "api_key_var": "OPENAI_API_KEY",
            "actual_model_name": "gpt-5-nano",
            "litellm_model": "openai/gpt-5-nano",
        },
        "o3": {
            "provider": "openai",
            "api_key_var": "OPENAI_API_KEY",
            "actual_model_name": "o3",
            "litellm_model": "openai/o3",
        },
        "o4-mini": {
            "provider": "openai",
            "api_key_var": "OPENAI_API_KEY",
            "actual_model_name": "o4-mini",
            "litellm_model": "openai/o4-mini",
        },
        "gpt-oss-120b": {
            "provider": "openai",
            "api_key_var": "OPENROUTER_API_KEY",
            "actual_model_name": "openai/gpt-oss-120b",
            "litellm_model": "openrouter/openai/gpt-oss-120b",
        },
        # DeepSeek models
        "deepseek-chat": {
            "provider": "deepseek",
            "api_key_var": "DEEPSEEK_API_KEY",
            "actual_model_name": "deepseek-chat",
            "litellm_model": "deepseek/deepseek-chat",
        },
        "deepseek-reasoner": {
            "provider": "deepseek",
            "api_key_var": "DEEPSEEK_API_KEY",
            "actual_model_name": "deepseek-reasoner",
            "litellm_model": "deepseek/deepseek-reasoner",
        },
        # Anthropic models
        "claude-3-7-sonnet": {
            "provider": "anthropic",
            "api_key_var": "ANTHROPIC_API_KEY",
            "actual_model_name": "claude-3-7-sonnet-20250219",
            "litellm_model": "anthropic/claude-3-7-sonnet-20250219",
        },
        "claude-4-sonnet": {
            "provider": "anthropic",
            "api_key_var": "ANTHROPIC_API_KEY",
            "actual_model_name": "claude-sonnet-4-20250514",
            "litellm_model": "anthropic/claude-sonnet-4-20250514",
        },
        "claude-4-opus": {
            "provider": "anthropic",
            "api_key_var": "ANTHROPIC_API_KEY",
            "actual_model_name": "claude-opus-4-20250514",
            "litellm_model": "anthropic/claude-opus-4-20250514",
        },
        "claude-4.1-opus": {
            "provider": "anthropic",
            "api_key_var": "ANTHROPIC_API_KEY",
            "actual_model_name": "claude-opus-4-1-20250805",
            "litellm_model": "anthropic/claude-opus-4-1-20250805",
        },
        # Google models
        "gemini-2.5-pro": {
            "provider": "google",
            "api_key_var": "GEMINI_API_KEY",
            "actual_model_name": "gemini-2.5-pro",
            "litellm_model": "gemini/gemini-2.5-pro",
        },
        "gemini-2.5-flash": {
            "provider": "google",
            "api_key_var": "GEMINI_API_KEY",
            "actual_model_name": "gemini-2.5-flash",
            "litellm_model": "gemini/gemini-2.5-flash",
        },
        # Moonshot models
        "k2": {
            "provider": "moonshot",
            "api_key_var": "MOONSHOT_API_KEY",
            "actual_model_name": "kimi-k2-0711-preview",
            "litellm_model": "moonshot/kimi-k2-0711-preview",
        },
        # Grok models
        "grok-4": {
            "provider": "xai",
            "api_key_var": "GROK_API_KEY",
            "actual_model_name": "grok-4-0709",
            "litellm_model": "xai/grok-4-0709",
        },
        # Qwen models
        "qwen-3-coder": {
            "provider": "qwen",
            "api_key_var": "OPENROUTER_API_KEY",
            "actual_model_name": "qwen/qwen3-coder",
            "litellm_model": "openrouter/qwen/qwen3-coder",
        },
        "qwen-3-coder-plus": {
            "provider": "qwen",
            "api_key_var": "DASHSCOPE_API_KEY",
            "actual_model_name": "qwen3-coder-plus",
            "litellm_model": "dashscope/qwen3-coder-plus",
        },
        # Zhipu
        "glm-4.5": {
            "provider": "zhipu",
            "api_key_var": "OPENROUTER_API_KEY",
            "actual_model_name": "z-ai/glm-4.5",
            "litellm_model": "openrouter/z-ai/glm-4.5",
        }
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

        # Store provider and the actual model name for the API
        self.provider = model_info["provider"]
        self.actual_model_name = model_info.get("actual_model_name", model_name)
        self.litellm_model = model_info.get("litellm_model", model_name)

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
