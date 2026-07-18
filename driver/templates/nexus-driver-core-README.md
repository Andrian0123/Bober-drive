# nexus-driver-core

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

🎯 **Core orchestration engine for Nexus AI agent driver**

Nexus Driver Core contains the central orchestration logic, project graph building, context caching, and request routing for single-agent AI workflows.

## Features

- 🤖 **Single-Agent Orchestration**: One LLM brain with many tools
- 📊 **Project Dependency Graph**: AST-based code analysis
- 💾 **Context Cache**: Token-efficient prompt management
- 🔗 **Graph Router**: Intent-based task routing
- 📚 **Skill System**: Dynamic SKILL.md loading
- 🔧 **MCP Integration**: Tool registry management
- 📈 **Request Chaining**: Historical request web tracking

## Installation

```bash
pip install nexus-driver-core
```

Or from source:

```bash
git clone https://github.com/Andrian0123/nexus-driver-core
cd nexus-driver-core
pip install -e .
```

## Quick Start

```python
from nexus_driver_core import DriverCore, ProjectGraphBuilder

# Initialize the driver
driver = DriverCore(workspace_path="/path/to/project")
driver.initialize()

# Build project graph
graph = ProjectGraphBuilder(driver.workspace).build()
print(f"Found {len(graph.nodes)} files with {len(graph.edges)} dependencies")

# Execute a task
result = driver.execute_task(
    prompt="Fix the authentication module",
    skills=["code_review", "refactoring"]
)
print(result)
```

## Architecture

```
┌────────────────────────────────┐
│   DriverCore (Orchestrator)    │
├────────────────────────────────┤
│                                │
│  ├─ driver_core.py            │
│  ├─ driver_logic.py           │
│  ├─ intent_analyzer.py        │
│  │                             │
│  ├─ ProjectGraphBuilder       │
│  │  └─ graph_router.py        │
│  │  └─ graph_search.py        │
│  │                             │
│  ├─ ContextCache              │
│  │  └─ context_manager.py     │
│  │  └─ token_compressor.py    │
│  │                             │
│  └─ SkillLoader               │
│     └─ skill_engine.py        │
│                                │
└────────────────────────────────┘
```

## Components

### DriverCore
Main orchestration engine coordinating all components.

```python
driver = DriverCore(workspace_path, config=None)
driver.initialize()
driver.scan()
result = driver.execute_task(prompt, skills)
```

### ProjectGraphBuilder
Builds AST-based dependency graphs for code analysis.

```python
from nexus_driver_core import ProjectGraphBuilder

builder = ProjectGraphBuilder(workspace_path)
graph = builder.build()
graph.save_to_file("graph.json")
```

### ContextCache
Manages token-efficient context caching.

```python
from nexus_driver_core import ContextCache

cache = ContextCache()
cache.set("auth_module", file_content, summary="Authentication logic")
cached = cache.get("auth_module")
```

### SkillLoader
Dynamically loads SKILL.md files.

```python
from nexus_driver_core import SkillLoader

loader = SkillLoader("./skills")
skills = loader.load_all()
specific_skill = loader.load("code_review")
```

## Configuration

Create `.nexus/config.json`:

```json
{
  "workspace_path": "./",
  "context_cache_size": 50,
  "graph_depth": 10,
  "model": "deepseek",
  "api_type": "ollama",
  "api_base": "http://localhost:11434"
}
```

## Usage Examples

### 1. Initialize Project

```bash
python -m nexus_driver_core init
```

### 2. Scan Workspace

```bash
python -m nexus_driver_core scan --depth 10
```

### 3. Build Project Graph

```bash
python -m nexus_driver_core graph --format json
```

### 4. Execute Task

```bash
python -m nexus_driver_core execute \
  --prompt "Refactor the authentication system" \
  --skills code_review,refactoring
```

### 5. Interactive Mode

```bash
python -m nexus_driver_core repl
```

## Testing

```bash
# Run all tests
pytest

# Run specific test
pytest tests/test_driver_core.py

# With coverage
pytest --cov=nexus_driver_core
```

## Performance

- Graph building: ~100ms for 1000 files
- Context cache lookup: ~1ms
- Skill loading: ~50ms per skill

## Requirements

- Python 3.12+
- SQLite3
- See `requirements.txt` for dependencies

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - See [LICENSE](LICENSE) for details.

## Citation

```bibtex
@software{nexus_driver_2026,
  title = {Nexus Driver Core},
  author = {Andrian0123},
  year = {2026},
  url = {https://github.com/Andrian0123/nexus-driver-core}
}
```

## Related Projects

- [nexus-memory-system](https://github.com/Andrian0123/nexus-memory-system) - Advanced memory management
- [nexus-mcp-toolkit](https://github.com/Andrian0123/nexus-mcp-toolkit) - MCP tool integration
- [nexus-project-graph](https://github.com/Andrian0123/nexus-project-graph) - Graph visualization
- [Bober-drive](https://github.com/Andrian0123/Bober-drive) - Main monorepo

## Support

- 📖 [Documentation](https://github.com/Andrian0123/nexus-driver-core/wiki)
- 🐛 [Issues](https://github.com/Andrian0123/nexus-driver-core/issues)
- 💬 [Discussions](https://github.com/Andrian0123/nexus-driver-core/discussions)

---

**Made with ❤️ by the Nexus team**
