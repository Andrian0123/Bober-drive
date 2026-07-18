# nexus-memory-system

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

🧠 **Advanced persistent memory system for AI agents using local vector search**

Nexus Memory System implements a multi-level memory architecture enabling long-term AI agent cognition without cloud dependencies.

## Features

- 🔐 **Local-First**: 100% offline vector search with sqlite-vec
- 🧠 **Semantic Memory**: BM25 + vector hybrid search
- 📊 **Cognitive Graph**: Fact & decision tracking
- 💾 **Persistent Storage**: SQLite-based scalable storage
- 🔄 **Session Isolation**: Agent & user-specific memory
- ⚡ **Fast Retrieval**: Sub-millisecond semantic search
- 🎯 **Multi-Level**: Short-term, long-term, session-specific memory

## Installation

```bash
pip install nexus-memory-system
```

## Quick Start

```python
from nexus_memory_system import Brain, MemoryGraph

# Initialize persistent memory
brain = Brain(".nexus/agent.amem")

# Add facts
brain.add_fact(
    "User prefers Python over JavaScript",
    session=1,
    confidence=0.95
)

# Search semantically
results = brain.search("programming languages", top_k=5)

# Track decisions
brain.add_decision(
    "Recommended async/await - team knows Python well",
    session=1,
    reasoning_chain=chain
)

# Retrieve decision reasoning
chain = brain.get_decision_chain(decision_id)
```

## Architecture

```
┌─────────────────────────────────┐
│   Memory System                 │
├─────────────────────────────────┤
│                                 │
│  ├─ Brain (Main interface)      │
│  │                              │
│  ├─ Vector Store                │
│  │  ├─ sqlite-vec               │
│  │  └─ embeddings (768-dim)     │
│  │                              │
│  ├─ Semantic Search             │
│  │  ├─ BM25 ranking             │
│  │  └─ Vector similarity        │
│  │                              │
│  ├─ Cognitive Graph             │
│  │  ├─ Facts                    │
│  │  ├─ Decisions                │
│  │  └─ Reasoning chains         │
│  │                              │
│  └─ Session Manager             │
│     ├─ Session isolation        │
│     └─ Memory boundaries        │
│                                 │
└─────────────────────────────────┘
```

## Components

### Brain
Main memory interface.

```python
from nexus_memory_system import Brain

brain = Brain("memory.amem")

# Add & retrieve memories
brain.add_fact(fact, session=1, confidence=0.9)
brain.add_decision(decision, session=1)
results = brain.search(query, top_k=5)
```

### MemoryGraph
Cognitive graph for facts and decisions.

```python
from nexus_memory_system import MemoryGraph

graph = MemoryGraph()
graph.add_fact(fact_id, content, confidence)
graph.add_decision(decision_id, content, reasoning)
chain = graph.get_chain(decision_id)
```

### SemanticSearch
Hybrid BM25 + vector search.

```python
from nexus_memory_system import SemanticSearch

search = SemanticSearch(db_path="memory.db")
results = search.hybrid_search(
    query="async programming",
    bm25_weight=0.3,
    vector_weight=0.7,
    top_k=10
)
```

## Storage Format

```
.nexus/
├── memory.db (SQLite)
│   ├── facts (id, content, embedding, confidence)
│   ├── decisions (id, content, reasoning_chain)
│   ├── sessions (id, user_id, created_at)
│   └── embeddings (vector[768])
│
└── agent.amem (Binary cognitibe graph)
    ├── Facts: ~100 per session
    ├── Decisions: ~50 per session
    └── Chains: reasoning paths
```

## Usage Examples

### 1. Initialize Memory

```python
from nexus_memory_system import Brain

# Create persistent memory
brain = Brain(".nexus/agent.amem", db_path=".nexus/memory.db")
brain.initialize()
```

### 2. Add Semantic Facts

```python
# Store knowledge
brain.add_fact(
    fact="User is building a web framework",
    session=1,
    confidence=0.95,
    tags=["user", "project"]
)
```

### 3. Semantic Search

```python
# Search by semantic similarity
results = brain.search(
    query="What does user work on?",
    search_type="semantic",  # or "bm25" or "hybrid"
    top_k=5
)

for result in results:
    print(f"Confidence: {result.confidence}")
    print(f"Content: {result.content}")
```

### 4. Decision Tracking

```python
# Log decisions with reasoning
brain.add_decision(
    decision="Use FastAPI for REST API",
    reasoning="Team has FastAPI experience",
    session=1,
    confidence=0.9
)

# Retrieve why a decision was made
chain = brain.get_decision_chain(decision_id)
```

### 5. Cross-Session Learning

```python
# Memory persists across sessions
session_2_brain = Brain(".nexus/agent.amem")

# Can search facts from session 1
old_facts = session_2_brain.search("user preferences", session=1)
```

## Performance Benchmarks

| Operation | Time |
|-----------|------|
| Add fact | 2ms |
| Vector search (1000 facts) | 0.5ms |
| BM25 search (1000 facts) | 1ms |
| Hybrid search | 2ms |
| Decision chain retrieval | 1ms |

## Configuration

```python
from nexus_memory_system import MemoryConfig

config = MemoryConfig(
    db_path=".nexus/memory.db",
    vector_dim=768,
    chunk_size=512,
    embedding_batch_size=32,
    cache_size=100,
    similarity_threshold=0.6
)

brain = Brain(".nexus/agent.amem", config=config)
```

## Testing

```bash
pytest tests/test_memory_system.py

# With vector search benchmarks
pytest tests/test_performance.py -v

# Memory profiling
pytest tests/test_memory_system.py --profile
```

## Dependencies

- Python 3.12+
- sqlite-vec (local vector search)
- sentence-transformers (embeddings)
- sqlalchemy (ORM)

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT - See [LICENSE](LICENSE).

## Related Projects

- [nexus-driver-core](https://github.com/Andrian0123/nexus-driver-core)
- [nexus-mcp-toolkit](https://github.com/Andrian0123/nexus-mcp-toolkit)

---

**Built for AI agents that never forget** 🧠✨
