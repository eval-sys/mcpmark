"""
MCPMark Agent Module
====================

Provides agent implementations and registry for MCPMark.
"""

from .base_agent import BaseMCPAgent
from .mcpmark_agent import MCPMarkAgent
from .react_agent import ReActAgent

AGENT_REGISTRY = {
    "mcpmark": MCPMarkAgent,
    "react": ReActAgent,
}

__all__ = ["BaseMCPAgent", "MCPMarkAgent", "ReActAgent", "AGENT_REGISTRY"]

