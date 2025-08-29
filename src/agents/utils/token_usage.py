"""
Token Usage Tracking Utilities
===============================
"""

from typing import Dict, Any


class TokenUsageTracker:
    """Track token usage across agent executions."""
    
    def __init__(self):
        """Initialize token usage tracker."""
        self.reset()
    
    def reset(self):
        """Reset all usage statistics."""
        self._stats = {
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_tokens": 0,
            "total_turns": 0,
            "total_execution_time": 0.0,
            "successful_executions": 0,
            "failed_executions": 0,
        }
    
    def update(self, success: bool, token_usage: Dict[str, int], 
               turn_count: int, execution_time: float):
        """
        Update usage statistics.
        
        Args:
            success: Whether execution was successful
            token_usage: Token usage dict with input_tokens, output_tokens, total_tokens
            turn_count: Number of conversation turns
            execution_time: Execution time in seconds
        """
        if success:
            self._stats["successful_executions"] += 1
        else:
            self._stats["failed_executions"] += 1
        
        self._stats["total_input_tokens"] += token_usage.get("input_tokens", 0)
        self._stats["total_output_tokens"] += token_usage.get("output_tokens", 0)
        self._stats["total_tokens"] += token_usage.get("total_tokens", 0)
        self._stats["total_turns"] += turn_count
        self._stats["total_execution_time"] += execution_time
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics with calculated averages.
        
        Returns:
            Dictionary containing usage statistics
        """
        stats = self._stats.copy()
        
        # Calculate averages
        total_executions = stats["successful_executions"] + stats["failed_executions"]
        if total_executions > 0:
            stats["avg_input_tokens"] = stats["total_input_tokens"] / total_executions
            stats["avg_output_tokens"] = stats["total_output_tokens"] / total_executions
            stats["avg_total_tokens"] = stats["total_tokens"] / total_executions
            stats["avg_turns"] = stats["total_turns"] / total_executions
            stats["avg_execution_time"] = stats["total_execution_time"] / total_executions
            stats["success_rate"] = (stats["successful_executions"] / total_executions * 100)
        else:
            stats.update({
                "avg_input_tokens": 0.0,
                "avg_output_tokens": 0.0,
                "avg_total_tokens": 0.0,
                "avg_turns": 0.0,
                "avg_execution_time": 0.0,
                "success_rate": 0.0,
            })
        
        return stats