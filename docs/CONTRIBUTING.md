# 🤝 Contributing to FormFlow AI

Thank you for your interest in contributing to FormFlow AI! This document provides guidelines and instructions for contributing.

## 📋 Table of Contents
- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Testing](#testing)

---

## Code of Conduct

Be respectful, inclusive, and professional in all interactions.

---

## How Can I Contribute?

### 🐛 Reporting Bugs

1. Check if the bug is already reported in [Issues](https://github.com/YOUR_USERNAME/formflow-ai/issues)
2. Create a new issue with:
   - Clear, descriptive title
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Python version, etc.)
   - Screenshots if applicable

### 💡 Suggesting Features

1. Open an issue with the `enhancement` label
2. Describe the feature and its benefits
3. Provide examples or mockups if possible

### 🔧 Code Contributions

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write/update tests
5. Submit a pull request

---

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/formflow-ai.git
cd formflow-ai

# Add upstream remote
git remote add upstream https://github.com/ORIGINAL_OWNER/formflow-ai.git

# Create environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Run tests
pytest
```

---

## Coding Standards

### Python (Backend)

- Follow [PEP 8](https://pep8.org/)
- Use type hints
- Maximum line length: 100 characters
- Use Black for formatting
- Use isort for imports

```python
# Good example
async def process_message(
    user_id: str,
    message: str,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """Process user message and return AI response.

    Args:
        user_id: User identifier
        message: User's message text
        session_id: Optional session identifier

    Returns:
        Dict containing AI response and metadata
    """
    # Implementation here
```

### TypeScript/JavaScript (Frontend)

- Use ESLint + Prettier
- Prefer functional components
- Use TypeScript for type safety

```typescript
// Good example
interface MessageProps {
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
}

export const Message: React.FC<MessageProps> = ({ content, role, timestamp }) => {
  return (
    <div className={`message ${role}`}>
      <p>{content}</p>
      <span>{timestamp.toLocaleString()}</span>
    </div>
  );
};
```

---

## Commit Guidelines

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding/updating tests
- `chore`: Maintenance tasks

**Examples**:

```bash
feat(agents): add confidence tracking to form predictor

- Implemented ConfidenceTracker class
- Added reasoning chain support
- Updated tests

Closes #123
```

```bash
fix(api): resolve CORS issue in production

The ALLOWED_ORIGINS environment variable wasn't being parsed
correctly when containing multiple URLs.

Fixes #456
```

---

## Pull Request Process

1. **Update Documentation**: If you change functionality, update relevant docs
2. **Write Tests**: Ensure new code has test coverage
3. **Run Tests**: All tests must pass
4. **Update CHANGELOG**: Add your changes to CHANGELOG.md
5. **Create PR**:
   - Use a clear, descriptive title
   - Reference related issues
   - Describe changes in detail
   - Add screenshots for UI changes

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] Added new tests
- [ ] Manual testing completed

## Screenshots (if applicable)
Add screenshots here

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] No new warnings generated
```

---

## Testing

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Specific test file
pytest tests/test_agents.py

# Specific test
pytest tests/test_agents.py::test_form_prediction
```

### Writing Tests

```python
# tests/test_example.py
import pytest
from app.services.example_service import ExampleService

class TestExampleService:
    @pytest.fixture
    async def service(self):
        return ExampleService()

    async def test_example_method(self, service):
        """Test that example method works correctly."""
        result = await service.example_method("input")
        assert result == "expected_output"

    async def test_example_method_error(self, service):
        """Test error handling."""
        with pytest.raises(ValueError):
            await service.example_method(None)
```

---

## Questions?

Feel free to open a [Discussion](https://github.com/YOUR_USERNAME/formflow-ai/discussions) for any questions!

---

**Thank you for contributing to FormFlow AI! 🚀**
