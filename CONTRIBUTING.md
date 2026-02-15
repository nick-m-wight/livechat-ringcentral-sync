# Contributing to LiveChat-RingCentral Sync

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to this project.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Coding Standards](#coding-standards)

## Code of Conduct

This project follows a Code of Conduct to ensure a welcoming environment for all contributors. Please be respectful and constructive in all interactions.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/yourusername/livechat-ringcentral-sync.git
   cd livechat-ringcentral-sync
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/original/livechat-ringcentral-sync.git
   ```

## Development Setup

### Prerequisites

- Python 3.11 or higher
- Poetry for dependency management
- Docker and Docker Compose (optional but recommended)

### Installation

1. **Install dependencies:**
   ```bash
   poetry install
   ```

2. **Set up environment variables:**
   ```bash
   cp .env.template .env
   # Edit .env with your test credentials
   ```

3. **Start services with Docker:**
   ```bash
   docker-compose up -d
   ```

4. **Run database migrations:**
   ```bash
   poetry run alembic upgrade head
   ```

5. **Seed test data:**
   ```bash
   poetry run python scripts/seed_data.py
   ```

## Making Changes

### Branch Naming

Use descriptive branch names:
- `feature/add-new-webhook` - For new features
- `fix/agent-state-bug` - For bug fixes
- `docs/update-readme` - For documentation updates
- `refactor/simplify-client` - For refactoring

### Commit Messages

Write clear, descriptive commit messages:

```
<type>: <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Example:**
```
feat: add conversation filtering to data API

- Add query parameters for status, type, and platform
- Implement pagination with limit and offset
- Update API documentation

Closes #123
```

## Testing

### Run Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=app tests/

# Run specific test file
poetry run pytest tests/test_webhooks.py -v
```

### Manual Testing

Use the demo webhook trigger to test integrations:

```bash
poetry run python scripts/demo_webhook_trigger.py
```

Open the dashboard at `http://localhost:8000/demo/` to verify changes visually.

## Submitting Changes

### Before Submitting

1. **Ensure code quality:**
   ```bash
   # Format code
   poetry run black app/ tests/

   # Check linting
   poetry run ruff check app/ tests/

   # Type checking
   poetry run mypy app/
   ```

2. **Run tests:**
   ```bash
   poetry run pytest tests/ -v
   ```

3. **Update documentation** if needed:
   - Update README.md for user-facing changes
   - Update CHANGELOG.md with your changes
   - Add docstrings to new functions/classes

### Pull Request Process

1. **Update your branch:**
   ```bash
   git fetch upstream
   git rebase upstream/master
   ```

2. **Push to your fork:**
   ```bash
   git push origin your-branch-name
   ```

3. **Create a Pull Request** on GitHub with:
   - Clear title describing the change
   - Description of what changed and why
   - Reference to related issues (e.g., "Closes #123")
   - Screenshots for UI changes

4. **Address review feedback** promptly

5. **Ensure CI passes** - All tests and checks must pass

## Coding Standards

### Python Code Style

- Follow [PEP 8](https://peps.python.org/pep-0008/)
- Use [Black](https://github.com/psf/black) for formatting (line length: 100)
- Use [Ruff](https://github.com/astral-sh/ruff) for linting
- Add type hints to all functions

### Code Organization

```python
"""Module docstring explaining the purpose."""

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Agent
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def my_function(param: str, optional: Optional[int] = None) -> dict:
    """
    Function docstring.

    Args:
        param: Description of param
        optional: Description of optional param

    Returns:
        Description of return value
    """
    # Implementation
    pass
```

### Documentation

- Add docstrings to all public functions, classes, and modules
- Keep comments concise and meaningful
- Update README.md for significant changes
- Add examples for new API endpoints

### Database Changes

- Create Alembic migrations for schema changes:
  ```bash
  poetry run alembic revision --autogenerate -m "Add new field"
  ```
- Test both upgrade and downgrade paths
- Document any manual migration steps

### Frontend Changes

- Keep JavaScript modular and well-organized
- Test across different browsers
- Ensure responsive design works on mobile
- Update CSS classes meaningfully

## Questions?

If you have questions or need help:
- Open an issue on GitHub
- Review existing documentation
- Check closed issues for similar questions

Thank you for contributing! 🎉
