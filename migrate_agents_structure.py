#!/usr/bin/env python3
"""
Migration script to transition from old agents structure to new organized structure.
This script helps update imports and validate the new structure works correctly.
"""

import os
import asyncio
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def backup_old_init():
    """Backup the current __init__.py file."""
    current_init = Path("app/agents/__init__.py")
    backup_path = Path("app/agents/__init__.py.backup")

    if current_init.exists():
        logger.info(f"Backing up current __init__.py to {backup_path}")
        with open(current_init, 'r') as src, open(backup_path, 'w') as dst:
            dst.write(src.read())
        return True
    return False


def apply_new_structure():
    """Apply the new __init__.py structure."""
    new_init_path = Path("app/agents/new_init.py")
    current_init_path = Path("app/agents/__init__.py")

    if new_init_path.exists():
        logger.info("Applying new __init__.py structure")
        with open(new_init_path, 'r') as src, open(current_init_path, 'w') as dst:
            dst.write(src.read())
        return True
    else:
        logger.error("new_init.py not found!")
        return False


def validate_imports():
    """Validate that the new structure imports work correctly."""
    try:
        logger.info("Validating new imports...")

        # Test core imports
        from app.agents.types import NodeType, NodeResponse, FormState
        from app.agents.base import BaseNode, state_get, state_set
        from app.agents.orchestrator import ConversationGraphOrchestrator

        # Test node imports
        from app.agents.nodes import RouterNode, ClarificationNode, FormFillerNode, ErrorNode

        # Test backwards compatibility
        from app.agents import (
            ConversationGraphOrchestrator as ImportedOrchestrator,
            EnhancedRouterNode,
            ClarificationHandlerNode
        )

        logger.info("✅ All imports successful!")
        return True

    except ImportError as e:
        logger.error(f"❌ Import failed: {e}")
        return False


def test_basic_functionality():
    """Test basic functionality of the new structure."""
    try:
        logger.info("Testing basic functionality...")

        # Test state utilities
        from app.agents.base import state_get, state_set
        from app.agents.types import FormState

        state = FormState({"test_key": "test_value"})
        value = state_get(state, "test_key", "default")
        assert value == "test_value", f"Expected 'test_value', got {value}"

        state_set(state, "new_key", "new_value")
        new_value = state_get(state, "new_key")
        assert new_value == "new_value", f"Expected 'new_value', got {new_value}"

        # Test NodeResponse
        from app.agents.types import NodeResponse

        response = NodeResponse(
            final_response="Test response",
            is_complete=False,
            confidence_score=0.8
        )

        response_dict = response.to_dict()
        assert "final_response" in response_dict
        assert response_dict["confidence_score"] == 0.8

        logger.info("✅ Basic functionality tests passed!")
        return True

    except Exception as e:
        logger.error(f"❌ Functionality test failed: {e}")
        return False


async def test_node_creation():
    """Test creating and running nodes."""
    try:
        logger.info("Testing node creation and execution...")

        from app.agents.nodes import ClarificationNode
        from app.agents.types import FormState

        # Create a clarification node
        node = ClarificationNode()
        state = FormState({
            "session_id": "test_123",
            "user_message": "help me"
        })

        # Test node execution
        response = await node.run(state)
        assert hasattr(response, 'final_response'), "Response should have final_response"
        assert response.requires_clarification == True, "Should require clarification"

        logger.info("✅ Node creation and execution tests passed!")
        return True

    except Exception as e:
        logger.error(f"❌ Node test failed: {e}")
        return False


def show_structure_summary():
    """Show a summary of the new structure."""
    logger.info("""
🏗️  NEW AGENTS STRUCTURE SUMMARY
=====================================

📁 app/agents/
├── 📄 __init__.py              (Clean public API)
├── 📄 types.py                 (Type definitions)
├── 📄 orchestrator.py          (Graph orchestration)
├── 📁 base/
│   ├── 📄 node.py             (Abstract base class)
│   └── 📄 utils.py            (State utilities)
└── 📁 nodes/
    ├── 📄 router.py           (Request routing)
    ├── 📄 clarification.py    (Clarification handling)
    ├── 📄 form_filler.py      (Form workflow)
    └── 📄 error.py            (Error handling)

✨ KEY BENEFITS:
- Better separation of concerns
- Easier testing and maintenance
- Type safety with NodeResponse
- Consistent error handling
- Backwards compatibility maintained

📖 See app/agents/README.md for full documentation
""")


async def main():
    """Main migration process."""
    logger.info("🚀 Starting agents structure migration...")

    steps = [
        ("Backing up current structure", backup_old_init),
        ("Applying new structure", apply_new_structure),
        ("Validating imports", validate_imports),
        ("Testing basic functionality", test_basic_functionality),
        ("Testing node creation", test_node_creation),
    ]

    for step_name, step_func in steps:
        logger.info(f"📋 {step_name}...")

        if asyncio.iscoroutinefunction(step_func):
            success = await step_func()
        else:
            success = step_func()

        if not success:
            logger.error(f"❌ Migration failed at step: {step_name}")
            logger.info("💡 You can restore the backup from __init__.py.backup")
            return False

    logger.info("🎉 Migration completed successfully!")
    show_structure_summary()

    # Clean up
    new_init_path = Path("app/agents/new_init.py")
    if new_init_path.exists():
        os.remove(new_init_path)
        logger.info("🧹 Cleaned up temporary files")

    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    if success:
        print("\n✅ MIGRATION SUCCESSFUL!")
        print("📖 Check app/agents/README.md for usage guide")
    else:
        print("\n❌ MIGRATION FAILED!")
        print("🔧 Check logs for details")