# nexus-mcp-toolkit

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Protocol](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-blue)](https://modelcontextprotocol.io)

🔌 **Model Context Protocol (MCP) toolkit for tool discovery & integration**

Nexus MCP Toolkit provides standardized MCP server management, auto-discovery from GitHub MCP Registry, and seamless tool integration for AI agents.

## Features

- 📋 **MCP Registry API**: Official GitHub MCP Registry integration
- 🔍 **Auto-Discovery**: Automatic server detection & metadata caching
- 🔧 **Tool Registry**: Unified tool management interface
- 📦 **Standard Wrapping**: Automatic MCP tool capability mapping
- 🌐 **Multi-Server**: Orchestrate multiple MCP servers
- ⚡ **Performance**: Smart caching & lazy loading
- 🔐 **Security**: Tool access control & validation

## Installation

```bash
pip install nexus-mcp-toolkit
```

## Quick Start

```python
from nexus_mcp_toolkit import MCPRegistry, ToolManager

# Initialize registry
registry = MCPRegistry()
registry.discover()  # Auto-discover from GitHub MCP Registry

# Get available servers
servers = registry.get_servers(search="filesystem")

# Connect to a server
tool_manager = ToolManager()
tool_manager.connect_server("filesystem-mcp")

# List available tools
tools = tool_manager.get_tools()
for tool in tools:
    print(f"{tool.name}: {tool.description}")

# Execute a tool
result = tool_manager.execute_tool(
    server="filesystem-mcp",
    tool="read_file",
    arguments={"path": "/path/to/file"}
)
```

## Architecture

```
┌────────────────────────────────────┐
│   MCP Toolkit                      │
├────────────────────────────────────┤
│                                    │
│  ├─ MCPRegistry                   │
│  │  ├─ GitHub MCP Registry API    │
│  │  ├─ Server discovery           │
│  │  └─ Metadata caching           │
│  │                                │
│  ├─ ToolManager                   │
│  │  ├─ Server connections         │
│  │  ├─ Tool execution             │
│  │  └─ Error handling             │
│  │                                │
│  ├─ CapabilityMapper              │
│  │  ├─ Tool introspection         │
│  │  ├─ Schema validation          │
│  │  └─ Type mapping               │
│  │                                │
│  └─ ServerRegistry                │
│     ├─ Connection pooling         │
│     ├─ Health checking            │
│     └─ Performance metrics        │
│                                    │
└────────────────────────────────────┘
```

## Components

### MCPRegistry
Manages MCP server discovery and metadata.

```python
from nexus_mcp_toolkit import MCPRegistry

registry = MCPRegistry()

# Discover all servers
all_servers = registry.discover()

# Search specific server
servers = registry.search(query="database")

# Get server details
server_info = registry.get_server("postgres-mcp")

# Cache management
registry.refresh_cache()
```

### ToolManager
Executes tools across multiple MCP servers.

```python
from nexus_mcp_toolkit import ToolManager

manager = ToolManager()

# Connect to server
manager.connect_server("filesystem-mcp")

# Get tools
tools = manager.get_tools(server="filesystem-mcp")

# Execute tool
result = manager.execute_tool(
    server="filesystem-mcp",
    tool="read_file",
    arguments={"path": "config.json"}
)

# Batch operations
results = manager.execute_batch([
    {
        "server": "filesystem-mcp",
        "tool": "read_file",
        "arguments": {"path": "file1.txt"}
    },
    {
        "server": "filesystem-mcp",
        "tool": "read_file",
        "arguments": {"path": "file2.txt"}
    }
])
```

### ServerRegistry
Manages MCP server connections and health.

```python
from nexus_mcp_toolkit import ServerRegistry

registry = ServerRegistry()

# Register server
registry.register_server(
    name="my-server",
    connection_string="stdio:python -m my_server"
)

# Check health
is_healthy = registry.check_health("my-server")

# Get metrics
metrics = registry.get_metrics("my-server")
```

## GitHub MCP Registry API

```python
from nexus_mcp_toolkit import MCPRegistry

registry = MCPRegistry()

# List all servers (paginated)
servers = registry.api_client.list_servers(limit=10)

# Search by category
db_servers = registry.api_client.search_servers(
    category="database",
    limit=20
)

# Get specific server with full metadata
server = registry.api_client.get_server_details("postgres-mcp")
print(server.installation_methods)
print(server.capabilities)
```

## Usage Examples

### 1. Auto-Discover & Connect

```python
from nexus_mcp_toolkit import MCPRegistry, ToolManager

# Discover
registry = MCPRegistry()
registry.discover()

# Connect to first filesystem server
manager = ToolManager()
fs_servers = registry.search("filesystem")
if fs_servers:
    manager.connect_server(fs_servers[0].name)
```

### 2. Build Tool Catalog

```python
from nexus_mcp_toolkit import MCPRegistry, ToolCatalog

registry = MCPRegistry()
registry.discover()

# Build comprehensive catalog
catalog = ToolCatalog()
for server in registry.get_all_servers():
    manager.connect_server(server.name)
    tools = manager.get_tools(server=server.name)
    catalog.add_tools(server.name, tools)

# Save catalog
catalog.export("tools_catalog.json")
```

### 3. Execute Tool from Any Server

```python
from nexus_mcp_toolkit import ToolManager

manager = ToolManager()

# Auto-connect and execute
result = manager.execute_tool(
    server="filesystem-mcp",
    tool="read_file",
    arguments={"path": "/etc/hostname"}
)
```

### 4. Custom Server Integration

```python
from nexus_mcp_toolkit import ServerRegistry, MCPServer

registry = ServerRegistry()

# Register custom server
registry.register_server(
    name="custom-agent",
    connection_type="stdio",
    command="python -m custom_agent_server",
    capabilities=["file-access", "web-search"]
)

# Use it
registry.execute_tool("custom-agent", "search_web", {"query": "AI news"})
```

### 5. Fallback & Error Handling

```python
from nexus_mcp_toolkit import ToolManager

manager = ToolManager()

try:
    result = manager.execute_tool(
        server="database-mcp",
        tool="query",
        arguments={"sql": "SELECT * FROM users"}
    )
except ServerUnavailableError:
    # Fallback to another server
    result = manager.execute_tool(
        server="backup-database-mcp",
        tool="query",
        arguments={"sql": "SELECT * FROM users"}
    )
```

## Configuration

```python
from nexus_mcp_toolkit import MCPConfig

config = MCPConfig(
    registry_url="https://registry.modelcontextprotocol.io",
    cache_dir=".nexus/mcp_cache",
    cache_ttl=3600,
    timeout=30,
    max_concurrent=5,
    enable_metrics=True
)

registry = MCPRegistry(config=config)
```

## Testing

```bash
# Unit tests
pytest tests/test_mcp_toolkit.py

# Integration tests with real servers
pytest tests/test_integration.py

# Registry API tests
pytest tests/test_registry_api.py
```

## Performance

| Operation | Time |
|-----------|------|
| Discover servers | ~500ms |
| Connect to server | ~100ms |
| Execute tool | ~50ms |
| Search registry | ~200ms |

## API Reference

See [API_REFERENCE.md](docs/API_REFERENCE.md) for detailed API documentation.

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT - See [LICENSE](LICENSE).

## References

- [Model Context Protocol](https://modelcontextprotocol.io)
- [MCP Registry](https://registry.modelcontextprotocol.io)
- [Official MCP Servers](https://github.com/modelcontextprotocol/servers)

## Related Projects

- [nexus-driver-core](https://github.com/Andrian0123/nexus-driver-core)
- [nexus-memory-system](https://github.com/Andrian0123/nexus-memory-system)

---

**Standard protocol for AI tool integration** 🔌✨
