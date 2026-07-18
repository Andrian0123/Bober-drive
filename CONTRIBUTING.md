# Contributing to Nexus Driver v3

Thank you for your interest in contributing to Nexus Driver! This document provides guidelines and instructions for contributing.

## 🤝 How to Contribute

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When creating a bug report, include:

- **Clear title** and description
- **Steps to reproduce** the problem
- **Expected behavior** vs actual behavior
- **Environment details** (OS, Python version, etc.)
- **Code samples** or error messages

### Suggesting Enhancements

Enhancement suggestions are welcome! Please include:

- **Clear use case** for the feature
- **Detailed description** of the proposed functionality
- **Example code** showing how it would work
- **Alternatives considered**

### Pull Requests

1. **Fork** the repository
2. **Create a branch** from `master`
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** following our code standards
4. **Add tests** for new functionality
5. **Update documentation** as needed
6. **Commit** with clear messages
   ```bash
   git commit -m "Add feature: description"
   ```
7. **Push** to your fork
   ```bash
   git push origin feature/your-feature-name
   ```
8. **Open a Pull Request** with a clear description

## 📝 Code Standards

### Python Style Guide

- Follow **PEP 8** style guide
- Use **type hints** for all function parameters and return values
- Write **docstrings** for all public modules, functions, classes, and methods
- Keep lines under **100 characters** where practical

### Example

```python
from typing import List, Optional

def process_data(items: List[str], max_items: Optional[int] = None) -> List[str]:
    """
    Process a list of items with optional limit.
    
    Args:
        items: List of strings to process
        max_items: Optional maximum number of items to return
        
    Returns:
        Processed list of strings
        
    Raises:
        ValueError: If items list is empty
    """
    if not items:
        raise ValueError("Items list cannot be empty")
    
    processed = [item.strip().lower() for item in items]
    
    if max_items:
        return processed[:max_items]
    return processed
```

### Testing Requirements

- Write **unit tests** for all new features
- Maintain **70%+ test coverage**
- Use **pytest** framework
- Include **docstrings** in tests

```python
def test_process_data_basic():
    """Test basic data processing functionality."""
    items = ["  Hello  ", "  WORLD  "]
    result = process_data(items)
    assert result == ["hello", "world"]
```

### Documentation

- Update **README.md** for user-facing changes
- Update **docstrings** for API changes
- Add **examples** for new features
- Create **guides** for complex features

## 🔍 Development Setup

### 1. Clone and Install

```bash
git clone https://github.com/Andrian0123/Bober-drive.git
cd Bober-drive
pip install -r requirements.txt
pip install pytest pytest-cov black mypy
```

### 2. Run Tests

```bash
# All tests
python -m pytest driver/ -v

# With coverage
python -m pytest driver/ --cov=driver --cov-report=html

# Specific module
python -m pytest driver/test_vault_core.py -v
```

### 3. Code Quality

```bash
# Format code
black driver/

# Type checking
mypy driver/

# Run linter
pylint driver/
```

## 📋 Commit Message Guidelines

Use clear, descriptive commit messages:

- **feat:** New feature
- **fix:** Bug fix
- **docs:** Documentation changes
- **style:** Code style changes (formatting, etc.)
- **refactor:** Code refactoring
- **test:** Adding or updating tests
- **chore:** Maintenance tasks

Examples:
```
feat: Add semantic search to Neural Reflex Engine
fix: Correct encryption key handling in VaultCore
docs: Update Quick Start guide with new examples
test: Add integration tests for Graphify Engine
```

## 🏗️ Project Structure

```
driver/
├── vault_core.py              # Core storage (DO NOT BREAK)
├── neural_reflex_engine.py    # Search engine (DO NOT BREAK)
├── vault_fts5_extension.py    # Full-text search
├── trash_manager.py           # Safe deletion
├── nexus_project_rules.py     # Rules engine
├── nexus_file_system_mapper.py # File scanner
├── nexus_graphify.py          # Document parser
├── nexus_obsidian_bridge.py   # Export module
├── nexus_audio_generator.py   # TTS module
└── context_extractor.py       # Context extraction
```

### Core Modules (DO NOT BREAK)

These modules are critical and any changes must maintain backward compatibility:

- `vault_core.py` — Foundation for all storage
- `neural_reflex_engine.py` — Core search functionality
- `vault_fts5_extension.py` — Full-text search
- `trash_manager.py` — Safe deletion system

## ✅ Review Process

### Pull Request Checklist

Before submitting, ensure:

- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] New tests added for new features
- [ ] Documentation updated
- [ ] No breaking changes (or clearly documented)
- [ ] Commit messages are clear
- [ ] Branch is up to date with master

### Review Criteria

Reviewers will check:

1. **Functionality** — Does it work as intended?
2. **Tests** — Are there adequate tests?
3. **Code Quality** — Is it clean and maintainable?
4. **Documentation** — Is it well documented?
5. **Performance** — Does it impact system performance?
6. **Security** — Are there security implications?

## 🐛 Debugging Tips

### Running with Verbose Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Common Issues

1. **Import errors** — Check `sys.path` includes driver directory
2. **Database locked** — Close all connections before tests
3. **Test failures** — Run tests individually to isolate issues
4. **Type errors** — Run `mypy driver/` to catch type issues early

## 📚 Resources

- [Python PEP 8](https://pep8.org/)
- [Type Hints](https://docs.python.org/3/library/typing.html)
- [Pytest Documentation](https://docs.pytest.org/)
- [SQLite Documentation](https://www.sqlite.org/docs.html)

## 🎯 Good First Issues

Looking for a place to start? Check issues labeled:

- `good first issue` — Simple tasks for newcomers
- `help wanted` — Features that need contributors
- `documentation` — Documentation improvements

## 💬 Questions?

- Open an [issue](https://github.com/Andrian0123/Bober-drive/issues)
- Start a [discussion](https://github.com/Andrian0123/Bober-drive/discussions)
- Check existing [documentation](DOCUMENTATION-INDEX-WEEK4-6.md)

---

Thank you for contributing to Nexus Driver! 🚀
