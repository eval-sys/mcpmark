#!/usr/bin/env python3
"""
Error Handling for MCPMark
===========================

Provides error standardization, retry logic, and exception utilities.
"""

from typing import Optional, Union, Dict, Any
import asyncio

# Lazy import to avoid circular dependencies
try:
    from src.exceptions import MCPMarkException
except ImportError:
    # Fallback for when exceptions module is not available
    MCPMarkException = Exception


"""Retryable error detection via minimal substring matching (lower-case)."""

# Keep this list short and generic; aim to catch API/infrastructure issues only.
RETRYABLE_PATTERNS = {
    "ratelimit",              # e.g., RateLimitError, too many requests
    # "connection",             # connection refused/reset/error
    "agent execution failed",
    "unavailable",            # service unavailable
    # "execution timed out",    # timeout
    "internal server error",  # 500s
    "network error",          # generic network issue
    "quota",                  # budget/quota exceeded
    # "llm provider not provided",  # litellm error
    # pipeline infra signals
    "account balance",
    "mcp network error",
    "state duplication error",
}


def is_retryable_error(error: Union[str, Exception]) -> bool:
    """
    Determine if an error is retryable.
    
    Args:
        error: Error message string or Exception instance
        
    Returns:
        True if the error is retryable, False otherwise
    """
    # If it's an MCPMarkException, use its retryable flag
    if isinstance(error, MCPMarkException):
        return error.retryable
    
    # Otherwise, check error message against patterns
    error_str = str(error).lower()
    return any(pattern in error_str for pattern in RETRYABLE_PATTERNS)


def standardize_error_message(
    error: Union[str, Exception], 
    mcp_service: Optional[str] = None
) -> str:
    """
    Standardize error messages for consistent reporting.
    
    Args:
        error: Error message string or Exception instance
        mcp_service: Optional MCP service name for context
        
    Returns:
        Standardized error message
    """
    # If it's an MCPMarkException, use its formatted message
    if isinstance(error, MCPMarkException):
        error_msg = str(error)
        # Add service prefix if provided and not already in message
        if mcp_service and mcp_service.lower() not in error_msg.lower():
            return f"{mcp_service.title()} {error_msg}"
        return error_msg
    
    error_str = str(error).strip()

    # Common standardizations
    if "timeout" in error_str.lower():
        base_msg = "Operation timed out"
    elif (
        "connection refused" in error_str.lower() or "econnrefused" in error_str.lower()
    ):
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

    # Add MCP service prefix if provided
    if mcp_service:
        return f"{mcp_service.title()} {base_msg}"

    return base_msg


def extract_error_message(error: Union[str, Exception]) -> str:
    """
    Extract error message from exception or string.
    
    Args:
        error: Error message string or Exception instance
        
    Returns:
        Error message string
    """
    if isinstance(error, Exception):
        return str(error)
    return str(error)


def convert_to_mcpmark_exception(
    error: Exception,
    context: Optional[Dict[str, Any]] = None
) -> MCPMarkException:
    """
    Convert a standard exception to MCPMarkException.
    
    This function provides backward compatibility by converting
    existing exceptions to the new exception hierarchy.
    
    Args:
        error: Standard exception to convert
        context: Additional context information
        
    Returns:
        Appropriate MCPMarkException subclass
    """
    # Import here to avoid circular dependencies
    from src.exceptions import (
        MCPMarkException,
        ConfigurationError,
        ServiceError,
        MCPServiceTimeoutError,
        MCPServiceAuthenticationError,
        AgentTimeoutError,
    )
    
    error_str = str(error).lower()
    context = context or {}
    
    # Handle specific exception types
    if isinstance(error, ValueError):
        if "configuration" in error_str or "config" in error_str:
            return ConfigurationError(
                message=str(error),
                context=context,
                cause=error
            )
        elif "service" in error_str or "mcp" in error_str:
            service_name = context.get("service_name", "unknown")
            return ServiceError(
                message=str(error),
                context=context,
                cause=error
            )
    
    elif isinstance(error, RuntimeError):
        if "timeout" in error_str:
            service_name = context.get("service_name", "unknown")
            timeout = context.get("timeout", 0)
            return MCPServiceTimeoutError(
                service_name=service_name,
                timeout=timeout,
                cause=error
            )
        elif "authentication" in error_str or "unauthorized" in error_str:
            service_name = context.get("service_name", "unknown")
            return MCPServiceAuthenticationError(
                service_name=service_name,
                reason=str(error),
                cause=error
            )
    
    elif isinstance(error, FileNotFoundError):
        return ConfigurationError(
            message=f"File not found: {error}",
            context=context,
            cause=error
        )
    
    elif isinstance(error, asyncio.TimeoutError):
        agent_name = context.get("agent_name", "unknown")
        timeout = context.get("timeout", 0)
        return AgentTimeoutError(
            agent_name=agent_name,
            timeout=timeout,
            cause=error
        )
    
    # Default: wrap as generic MCPMarkException
    return MCPMarkException(
        message=str(error),
        context=context,
        cause=error
    )
