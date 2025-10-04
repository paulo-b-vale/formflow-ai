# Agents Module - Restructured

This document describes the new, improved structure of the agents module for better maintainability and readability.

## 🏗️ New Structure

```
app/agents/
├── __init__.py              # Clean exports and public API
├── types.py                 # Type definitions and data structures
├── orchestrator.py          # Graph orchestration logic
├── base/
│   ├── __init__.py         # Base exports
│   ├── node.py             # Abstract base node class
│   └── utils.py            # State utilities and helpers
├── nodes/
│   ├── __init__.py         # Node exports
│   ├── router.py           # Request routing logic
│   ├── clarification.py    # Clarification handling
│   ├── form_filler.py      # Form completion workflow
│   └── error.py            # Error handling and recovery
└── README.md               # This documentation
```

## 🎯 Key Improvements

### **1. Separation of Concerns**
- **Router**: Intent classification and routing logic
- **Form Filler**: Form completion workflow
- **Clarification**: Handling unclear requests
- **Error**: Error handling and recovery
- **Orchestrator**: Graph management and execution

### **2. Better Type Safety**
```python
from app.agents.types import NodeResponse, FormState, NodeType

# Strongly typed responses
response = NodeResponse(
    final_response="Olá! Como posso ajudar?",
    is_complete=False,
    confidence_score=0.8
)
```

### **3. Consistent Base Class**
```python
from app.agents.base import BaseNode

class CustomNode(BaseNode):
    def __init__(self):
        super().__init__(NodeType.CUSTOM, "my_custom_node")

    async def execute(self, state: StateType) -> ResponseType:
        # Your logic here
        return NodeResponse(final_response="Done!")
```

### **4. Enhanced Error Handling**
- Automatic error catching and logging
- Standardized error responses
- Recovery suggestions for users

### **5. Better Testing**
- Individual nodes can be tested in isolation
- Mock dependencies easily
- Clear interfaces for unit testing

## 🚀 Usage Examples

### **Creating an Orchestrator**
```python
from app.agents import create_orchestrator
from app.sessions.session_manager import SessionManager

session_manager = SessionManager()
orchestrator = create_orchestrator(session_manager)

# Execute conversation
result = await orchestrator.invoke({
    "session_id": "123",
    "user_message": "Quero preencher um formulário",
    "user_id": "user456"
})
```

### **Using Individual Nodes**
```python
from app.agents.nodes import RouterNode
from app.agents.types import FormState

router = RouterNode(session_manager)
state = FormState({"user_message": "help", "session_id": "123"})

response = await router.run(state)
print(response.next_node)  # "clarification_handler"
```

### **State Management**
```python
from app.agents.base import state_get, state_set

# Safe state access
user_message = state_get(state, "user_message", "")
session_id = state_get(state, "session_id")

# State modification
state_set(state, "confidence_score", 0.9)
```

## 🔧 Migration Guide

### **From Old Structure**
```python
# Old way
from app.agents import ConversationGraphOrchestrator
from app.agents import _state_get as state_get

# New way
from app.agents import ConversationGraphOrchestrator, create_orchestrator
from app.agents.base import state_get
```

### **Backwards Compatibility**
The new structure maintains backwards compatibility:
```python
# These still work
from app.agents import EnhancedRouterNode  # → RouterNode
from app.agents import ClarificationHandlerNode  # → ClarificationNode
```

## 📝 Development Guidelines

### **Adding New Nodes**

1. **Create Node File**: `app/agents/nodes/my_node.py`
```python
from ..base import BaseNode
from ..types import StateType, ResponseType, NodeType

class MyNode(BaseNode):
    def __init__(self):
        super().__init__(NodeType.CUSTOM, "my_node")

    async def execute(self, state: StateType) -> ResponseType:
        # Implementation
        pass
```

2. **Update Exports**: Add to `app/agents/nodes/__init__.py`
```python
from .my_node import MyNode
__all__ = [..., 'MyNode']
```

3. **Add to Orchestrator**: Update `orchestrator.py` to include your node

### **Best Practices**

- **Single Responsibility**: Each node should have one clear purpose
- **Error Handling**: Always use try/catch and return proper error responses
- **Logging**: Use the node's logger for debugging
- **Type Hints**: Use proper type annotations
- **Documentation**: Add docstrings to all methods

### **Testing Nodes**
```python
import pytest
from app.agents.nodes import RouterNode
from app.agents.types import FormState

@pytest.mark.asyncio
async def test_router_node():
    router = RouterNode()
    state = FormState({"user_message": "test", "session_id": "123"})

    response = await router.run(state)
    assert response.next_node is not None
```

## 🐛 Troubleshooting

### **Common Issues**

1. **Import Errors**: Update imports to use new structure
2. **State Access**: Use `state_get()` instead of direct access
3. **Response Format**: Return `NodeResponse` objects

### **Debugging**
- Check logs for node execution details
- Use `_log_state_info()` in base class for state debugging
- Validate state keys with `_validate_state()`

## 🔄 Next Steps

### **Further Improvements**
- [ ] Move remaining nodes (`EnhancedFormPredictorNode`, etc.) to `nodes/`
- [ ] Add more comprehensive type checking
- [ ] Implement node dependency injection
- [ ] Add configuration-based node setup
- [ ] Create visual graph representation tools