"""
Reorganized agents module with improved structure and separation of concerns.

This module provides a clean, organized interface to the conversation agent system
with better maintainability and testability.
"""

# Core types and interfaces
from .types import NodeType, NodeResponse, FormState, StateType, ResponseType

# Base classes and utilities
from .base import BaseNode, state_get, state_set

# Individual node implementations
from .nodes import (
    RouterNode,
    ClarificationNode,
    FormFillerNode,
    ErrorNode
)

# External node imports (to be moved to nodes/ eventually)
from .enhanced_form_predictor_node import EnhancedFormPredictorNode
from .form_searcher_node import FormSearcherNode
from .report_generator_node import ReportGeneratorNode

# Main orchestrator
from .orchestrator import ConversationGraphOrchestrator

# Backwards compatibility aliases
EnhancedRouterNode = RouterNode
ClarificationHandlerNode = ClarificationNode
EnhancedFormFillerNode = FormFillerNode

# Clean public API
__all__ = [
    # Types
    'NodeType',
    'NodeResponse',
    'FormState',
    'StateType',
    'ResponseType',

    # Base classes
    'BaseNode',
    'state_get',
    'state_set',

    # Node implementations
    'RouterNode',
    'ClarificationNode',
    'FormFillerNode',
    'ErrorNode',
    'EnhancedFormPredictorNode',
    'FormSearcherNode',
    'ReportGeneratorNode',

    # Main orchestrator
    'ConversationGraphOrchestrator',

    # Backwards compatibility
    'EnhancedRouterNode',
    'ClarificationHandlerNode',
    'EnhancedFormFillerNode',
]


def create_orchestrator(session_manager):
    """
    Factory function to create a properly configured orchestrator.

    Args:
        session_manager: Session manager instance

    Returns:
        Configured ConversationGraphOrchestrator
    """
    return ConversationGraphOrchestrator(session_manager)


def get_available_nodes():
    """
    Get list of available node types.

    Returns:
        List of NodeType enums
    """
    return list(NodeType)


def validate_node_config(config: dict) -> bool:
    """
    Validate node configuration.

    Args:
        config: Node configuration dictionary

    Returns:
        True if valid, False otherwise
    """
    required_keys = ['type', 'name']
    return all(key in config for key in required_keys)