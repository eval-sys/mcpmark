"""
Pricing utilities for computing per-run cost from token usage.

All prices are specified per 1,000,000 tokens (M tokens) in USD.
"""

from __future__ import annotations

from typing import Dict, Optional


# Price map keyed by canonical model name (lowercased)
# Values are dicts with per-M token prices for input and output tokens
MODEL_PRICES_PER_M: Dict[str, Dict[str, float]] = {
    # Use exact actual_model_name keys (lowercased) provided by the user
    # Anthropic
    "claude-opus-4-1-20250805": {"input": 15.0, "output": 75.0},
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},

    # DeepSeek
    "deepseek-v3.1-non-think": {"input": 0.56, "output": 1.68},

    # Google Gemini
    "gemini-2.5-pro": {"input": 2.5, "output": 15.0},
    "gemini-2.5-flash": {"input": 0.3, "output": 2.5},

    # Z.AI
    "glm-4.5": {"input": 0.33, "output": 1.32},

    # OpenAI
    "gpt-5-2025-08-07": {"input": 1.25, "output": 10.0},
    "gpt-5-mini-2025-08-07": {"input": 0.25, "output": 2.0},
    "gpt-5-nano-2025-08-07": {"input": 0.05, "output": 0.4},
    "gpt-4.1-2025-04-14": {"input": 2.0, "output": 8.0},
    "gpt-4.1-mini-2025-04-14": {"input": 0.4, "output": 1.6},
    "gpt-4.1-nano-2025-04-14": {"input": 0.1, "output": 0.4},
    "o3-2025-04-16": {"input": 2.0, "output": 8.0},
    "o4-mini-2025-04-16": {"input": 1.1, "output": 4.4},
    "gpt-oss-120b": {"input": 0.072, "output": 0.28},

    # Qwen
    "qwen3-coder-480b-a35b-instruct": {"input": 0.2, "output": 0.8},
    "qwen3-max-preview": {"input": 1.2, "output": 6},
    
    # Xai
    "grok-4-0709": {"input": 3.0, "output": 15.0},
    "grok-code-fast-1": {"input": 0.2, "output": 1.5},

    # Moonshot
    "kimi-k2-0711-preview": {"input": 0.6, "output": 2.5},
    "kimi-k2-0905-preview": {"input": 0.6, "output": 2.5},
}


def normalize_model_name(model_name: str) -> str:
    """Normalize model name for pricing lookup.

    Lowercases only.
    """
    return (model_name or "").strip().lower()


def get_price_per_m(model_name: str) -> Optional[Dict[str, float]]:
    """Return per-M token prices for given model, or None if unknown."""
    key = normalize_model_name(model_name)
    return MODEL_PRICES_PER_M.get(key)


def compute_cost_usd(model_name: str, input_tokens: float, output_tokens: float) -> Optional[float]:
    """Compute cost in USD given token usage and model pricing.

    Prices are per 1,000,000 tokens. If pricing unknown, returns None.
    """
    prices = get_price_per_m(model_name)
    if not prices:
        return None
    input_cost = (input_tokens / 1_000_000.0) * prices["input"]
    output_cost = (output_tokens / 1_000_000.0) * prices["output"]
    return float(round(input_cost + output_cost, 6))


