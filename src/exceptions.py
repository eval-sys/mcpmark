#!/usr/bin/env python3
"""
MCPMark Custom Exception Classes
=================================

Provides a hierarchical exception system for better error handling,
classification, and debugging.
"""

from typing import Optional, Dict, Any


class MCPMarkException(Exception):
    """Base exception for all MCPMark errors."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        retryable: bool = False,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.context = context or {}
        self.retryable = retryable
        self.cause = cause
        
        # Preserve exception chain if cause is provided
        if cause:
            self.__cause__ = cause
    
    def __str__(self) -> str:
        """Return formatted error message with context."""
        msg = self.message
        if self.context:
            ctx_str = ", ".join(f"{k}={v}" for k, v in self.context.items() if v is not None)
            if ctx_str:
                msg = f"{msg} (Context: {ctx_str})"
        return msg
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for serialization."""
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "context": self.context,
            "retryable": self.retryable,
            "cause": str(self.cause) if self.cause else None,
        }


# Configuration Errors
class ConfigurationError(MCPMarkException):
    """Base class for configuration-related errors."""
    pass


class MissingConfigurationError(ConfigurationError):
    """Raised when required configuration is missing."""
    
    def __init__(self, config_key: str, service: Optional[str] = None, **kwargs):
        message = f"Missing required configuration: {config_key}"
        if service:
            message += f" for service: {service}"
        context = {"config_key": config_key}
        if service:
            context["service"] = service
        super().__init__(message, context=context, **kwargs)


class InvalidConfigurationError(ConfigurationError):
    """Raised when configuration value is invalid."""
    
    def __init__(self, config_key: str, value: Any, reason: Optional[str] = None, **kwargs):
        message = f"Invalid configuration value for '{config_key}': {value}"
        if reason:
            message += f" - {reason}"
        context = {"config_key": config_key, "value": str(value)}
        if reason:
            context["reason"] = reason
        super().__init__(message, context=context, **kwargs)


class ModelConfigurationError(ConfigurationError):
    """Raised when model configuration is invalid."""
    
    def __init__(self, model_name: str, reason: str, **kwargs):
        message = f"Model configuration error for '{model_name}': {reason}"
        context = {"model_name": model_name, "reason": reason}
        super().__init__(message, context=context, **kwargs)


# Service Errors
class ServiceError(MCPMarkException):
    """Base class for service-related errors."""
    pass


class MCPServiceError(ServiceError):
    """Base class for MCP service errors."""
    
    def __init__(self, message: str, service_name: str, **kwargs):
        context = kwargs.get("context", {})
        context["service_name"] = service_name
        kwargs["context"] = context
        super().__init__(message, **kwargs)


class MCPServiceUnavailableError(MCPServiceError):
    """Raised when MCP service is unavailable."""
    
    def __init__(self, service_name: str, reason: Optional[str] = None, **kwargs):
        message = f"MCP service '{service_name}' is unavailable"
        if reason:
            message += f": {reason}"
        super().__init__(message, service_name, retryable=True, **kwargs)


class MCPServiceTimeoutError(MCPServiceError):
    """Raised when MCP service operation times out."""
    
    def __init__(self, service_name: str, timeout: float, operation: Optional[str] = None, **kwargs):
        message = f"MCP service '{service_name}' operation timed out after {timeout}s"
        if operation:
            message += f" during {operation}"
        context = {"timeout": timeout}
        if operation:
            context["operation"] = operation
        super().__init__(message, service_name, context=context, retryable=True, **kwargs)


class MCPServiceAuthenticationError(MCPServiceError):
    """Raised when MCP service authentication fails."""
    
    def __init__(self, service_name: str, reason: Optional[str] = None, **kwargs):
        message = f"Authentication failed for MCP service '{service_name}'"
        if reason:
            message += f": {reason}"
        super().__init__(message, service_name, retryable=False, **kwargs)


class StateManagerError(ServiceError):
    """Base class for state manager errors."""
    pass


class StateSetupError(StateManagerError):
    """Raised when state setup fails."""
    
    def __init__(self, service_name: str, task_name: Optional[str] = None, reason: Optional[str] = None, **kwargs):
        message = f"State setup failed for service '{service_name}'"
        if task_name:
            message += f" (task: {task_name})"
        if reason:
            message += f": {reason}"
        context = {"service_name": service_name}
        if task_name:
            context["task_name"] = task_name
        if reason:
            context["reason"] = reason
        super().__init__(message, context=context, retryable=True, **kwargs)


class StateCleanupError(StateManagerError):
    """Raised when state cleanup fails."""
    
    def __init__(self, service_name: str, task_name: Optional[str] = None, reason: Optional[str] = None, **kwargs):
        message = f"State cleanup failed for service '{service_name}'"
        if task_name:
            message += f" (task: {task_name})"
        if reason:
            message += f": {reason}"
        context = {"service_name": service_name}
        if task_name:
            context["task_name"] = task_name
        if reason:
            context["reason"] = reason
        super().__init__(message, context=context, retryable=False, **kwargs)


class StateDuplicationError(StateManagerError):
    """Raised when state duplication fails (e.g., resource already exists)."""
    
    def __init__(self, service_name: str, resource: Optional[str] = None, **kwargs):
        message = f"State duplication error for service '{service_name}'"
        if resource:
            message += f" (resource: {resource})"
        context = {"service_name": service_name}
        if resource:
            context["resource"] = resource
        super().__init__(message, context=context, retryable=True, **kwargs)


class TaskManagerError(ServiceError):
    """Base class for task manager errors."""
    pass


class TaskNotFoundError(TaskManagerError):
    """Raised when a task is not found."""
    
    def __init__(self, task_name: str, service: Optional[str] = None, **kwargs):
        message = f"Task not found: {task_name}"
        if service:
            message += f" (service: {service})"
        context = {"task_name": task_name}
        if service:
            context["service"] = service
        super().__init__(message, context=context, retryable=False, **kwargs)


class TaskVerificationError(TaskManagerError):
    """Raised when task verification fails."""
    
    def __init__(self, task_name: str, reason: Optional[str] = None, **kwargs):
        message = f"Task verification failed for '{task_name}'"
        if reason:
            message += f": {reason}"
        context = {"task_name": task_name}
        if reason:
            context["reason"] = reason
        super().__init__(message, context=context, retryable=False, **kwargs)


# Agent Errors
class AgentError(MCPMarkException):
    """Base class for agent execution errors."""
    pass


class AgentExecutionError(AgentError):
    """Raised when agent execution fails."""
    
    def __init__(self, agent_name: str, reason: Optional[str] = None, **kwargs):
        message = f"Agent '{agent_name}' execution failed"
        if reason:
            message += f": {reason}"
        context = {"agent_name": agent_name}
        if reason:
            context["reason"] = reason
        super().__init__(message, context=context, retryable=True, **kwargs)


class AgentTimeoutError(AgentError):
    """Raised when agent execution times out."""
    
    def __init__(self, agent_name: str, timeout: float, **kwargs):
        message = f"Agent '{agent_name}' execution timed out after {timeout}s"
        context = {"agent_name": agent_name, "timeout": timeout}
        super().__init__(message, context=context, retryable=True, **kwargs)


class LLMError(AgentError):
    """Base class for LLM-related errors."""
    pass


class LLMRateLimitError(LLMError):
    """Raised when LLM rate limit is exceeded."""
    
    def __init__(self, model_name: str, **kwargs):
        message = f"Rate limit exceeded for model '{model_name}'"
        context = {"model_name": model_name}
        super().__init__(message, context=context, retryable=True, **kwargs)


class LLMQuotaExceededError(LLMError):
    """Raised when LLM quota is exceeded."""
    
    def __init__(self, model_name: str, **kwargs):
        message = f"Quota exceeded for model '{model_name}'"
        context = {"model_name": model_name}
        super().__init__(message, context=context, retryable=False, **kwargs)


class LLMContextWindowExceededError(LLMError):
    """Raised when LLM context window is exceeded."""
    
    def __init__(self, model_name: str, **kwargs):
        message = f"Context window exceeded for model '{model_name}'"
        context = {"model_name": model_name}
        super().__init__(message, context=context, retryable=False, **kwargs)


# Task Execution Errors
class TaskExecutionError(MCPMarkException):
    """Base class for task execution errors."""
    pass


class TaskSetupError(TaskExecutionError):
    """Raised when task setup fails."""
    
    def __init__(self, task_name: str, reason: Optional[str] = None, **kwargs):
        message = f"Task setup failed for '{task_name}'"
        if reason:
            message += f": {reason}"
        context = {"task_name": task_name}
        if reason:
            context["reason"] = reason
        super().__init__(message, context=context, retryable=True, **kwargs)


class TaskCleanupError(TaskExecutionError):
    """Raised when task cleanup fails."""
    
    def __init__(self, task_name: str, reason: Optional[str] = None, **kwargs):
        message = f"Task cleanup failed for '{task_name}'"
        if reason:
            message += f": {reason}"
        context = {"task_name": task_name}
        if reason:
            context["reason"] = reason
        super().__init__(message, context=context, retryable=False, **kwargs)

