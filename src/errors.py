#!/usr/bin/env python3
"""
Simple Error Handling for MCPMark
==================================

Provides basic error standardization and retry logic.
"""

from typing import Optional, Set


# Retryable error patterns
RETRYABLE_PATTERNS = {
    "timeout", "timed out", "etimedout",
    "econnrefused", "connection refused",
    "network error", "mcp network error",
    "state duplication error", "already exists"
}


def is_retryable_error(error: str) -> bool:
    """Check if an error message indicates it should be retried."""
    error_lower = str(error).lower()
    return any(pattern in error_lower for pattern in RETRYABLE_PATTERNS)


def standardize_error_message(error: str, service: Optional[str] = None) -> str:
    """Standardize error messages for consistent reporting."""
    error_str = str(error).strip()
    
    # Common standardizations
    if "timeout" in error_str.lower():
        base_msg = "Operation timed out"
    elif "connection refused" in error_str.lower() or "econnrefused" in error_str.lower():
        base_msg = "Connection refused"
    elif "authentication" in error_str.lower() or "unauthorized" in error_str.lower():
        base_msg = "Authentication failed"
    elif "not found" in error_str.lower():
        base_msg = "Resource not found"
    elif "already exists" in error_str.lower():
        base_msg = "Resource already exists"
    elif "mcp" in error_str.lower() and "error" in error_str.lower():
        base_msg = "MCP service error"
    else:
        # Return original message if no standardization applies
        return error_str
    
    # Add service prefix if provided
    if service:
        return f"{service.title()} {base_msg}"
    
    return base_msg


def get_retry_delay(attempt: int, base_delay: int = 5) -> int:
    """Get exponential backoff delay for retries."""
    return min(base_delay * (2 ** (attempt - 1)), 60)  # Cap at 60 seconds