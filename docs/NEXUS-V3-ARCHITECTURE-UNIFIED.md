# Nexus Driver v3 — Unified Architecture

## Executive Summary

Текущая архитектура Nexus Driver работает как набор изолированных модулей. Этот документ описывает полную переработку в **unified event-driven ecosystem** с:

- **Event Bus** для асинхронной коммуникации между компонентами
- **Dependency Injection Container** для управления зависимостями
- **Unified Pipeline** с четкими этапами обработки
- **Observability Layer** для мониторинга и отладки
- **Plugin Architecture** для расширяемости

Архитектура основана на best practices из:
- **Neo4j**: graph patterns, index-free adjacency, semantic relationships
- **ESLint**: AST-based rule engine, visitor pattern, extensible rules
- **spaCy**: pipeline architecture, component-based NLP processing
- **Obsidian**: plugin system, hot-swapping, contract-based extensions

---

## Part 1: Current System Analysis

### Current Architecture Issues

```
User Application
    │
    ├─ Rules Engine ─┐          ❌ No coordination
    └─ File Mapper ──┤          ❌ Direct dependencies
                     ↓          ❌ No event flow
              Graphify Engine   ❌ No error recovery
                     ↓          ❌ No observability
                VaultCore       ❌ Monolithic design
                     ↓
    ┌────────────────┼─────────────┐
    │                │              │
Neural Reflex    FTS5 Ext    Trash Manager
```

**Проблемы:**
1. **Tight Coupling**: Модули жёстко привязаны друг к другу
2. **No Event Flow**: Нет асинхронного взаимодействия
3. **Monolithic VaultCore**: Слишком много ответственности
4. **No Error Handling**: Нет стратегии recovery
5. **Limited Extensibility**: Трудно добавлять новые компоненты

### Current Components Analysis

#### 1. VaultCore (822 строк)
- **Responsibility**: Persistent storage, encryption, versioning
- **Strengths**: SQLite schema, Fernet encryption, version control
- **Weaknesses**: Monolithic, no event notifications, tight coupling with consumers

#### 2. Neural Reflex Engine (604 строк)
- **Responsibility**: Parallel multi-level search
- **Strengths**: Semantic, lexical, syntactic levels
- **Weaknesses**: Direct access to Vault, no subscription model, hardcoded timeouts

#### 3. Graphify Engine (533 строк)
- **Responsibility**: Document parsing, entity extraction
- **Strengths**: Multi-format support
- **Weaknesses**: Tight coupling to Vault, no error recovery

#### 4. Project Rules Engine (523 строк)
- **Responsibility**: Rule parsing and enforcement
- **Strengths**: Multiple source support
- **Weaknesses**: Synchronous validation, no event model

#### 5. FTS5 Extension (363 строк)
- **Responsibility**: Full-text search indexing
- **Strengths**: Inverted index, BM25 ranking
- **Weaknesses**: Separate from Vault, no lifecycle management

#### 6. File System Mapper (568 строк)
- **Responsibility**: File analysis and categorization
- **Strengths**: AST-based analysis
- **Weaknesses**: Direct filesystem access, no caching

#### 7. Obsidian Bridge (478 строк)
- **Responsibility**: Integration with Obsidian
- **Strengths**: Markdown support
- **Weaknesses**: Polling-based, not event-driven

#### 8. Audio Generator (487 строк)
- **Responsibility**: Text-to-speech synthesis
- **Strengths**: Multiple TTS engines
- **Weaknesses**: Blocking calls, no queue management

#### 9. Trash Manager (480 строк)
- **Responsibility**: Soft deletion and recovery
- **Strengths**: Safe deletion model
- **Weaknesses**: Separate from Vault, no lifecycle events

---

## Part 2: Unified Ecosystem Design

### Core Architecture Pattern

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                        │
│           (User Applications, CLI, Plugins)                │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                  Orchestrator Service                       │
│              (Central Coordination Point)                   │
└──────┬──────────────────┬──────────────────┬───────────────┘
       │                  │                  │
┌──────▼───────┐  ┌───────▼────────┐  ┌────▼──────────┐
│  Event Bus   │  │    DI Container│  │Observability  │
│              │  │                │  │  (Metrics,    │
│ (Async Comm) │  │ (Dependencies) │  │   Logging,    │
│              │  │                │  │   Tracing)    │
└──────────────┘  └────────────────┘  └───────────────┘
                       │
       ┌───────────────┼────────────────┬──────────────────┐
       │               │                │                  │
┌──────▼──────┐  ┌────▼──────┐  ┌─────▼─────┐  ┌────────▼─┐
│  Storage    │  │ Processing│  │ Integration│  │  Cache   │
│   Layer     │  │   Layer   │  │   Layer    │  │  Layer   │
│             │  │           │  │            │  │          │
│ - VaultCore │  │ - Rules   │  │ - Obsidian │  │ - Redis/ │
│ - FTS5      │  │ - Graphify│  │ - Audio    │  │   In-Mem │
│ - Trash     │  │ - Search  │  │ - External │  │          │
└─────────────┘  └───────────┘  └────────────┘  └──────────┘
       │               │                │              │
       └───────────────┼────────────────┴──────────────┘
                       │
       ┌───────────────┴────────────────────────────────┐
       │         Persistence & Infrastructure           │
       │ (SQLite, File System, Network, Encryption)     │
       └─────────────────────────────────────────────────┘
```

### Event-Driven Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                  APPLICATION TRIGGERS                      │
│          (User Action / API Call / Webhook)               │
└────────────────────┬────────────────────────────────────────┘
                     │
    ┌────────────────▼────────────────┐
    │   Orchestrator.process_command()│
    │                                  │
    │ 1. Validate input                │
    │ 2. Emit START event              │
    │ 3. Build execution plan          │
    └────────────────┬─────────────────┘
                     │
        ┌────────────▼───────────┐
        │   EVENT: workflow.START │
        └────────────┬────────────┘
                     │
    ┌────────────────▼────────────────────────┐
    │  Stage 1: INGESTION                     │
    │  - Graphify.parse_document()            │
    │  - NLP.extract_entities()               │
    │  - Emit: document.PARSED                │
    └────────────────┬─────────────────────────┘
                     │
        ┌────────────▼──────────────┐
        │ EVENT: document.PARSED    │
        └────────┬──────────────────┘
                 │
    ┌────────────▼──────────────────────────┐
    │  Stage 2: VALIDATION & ENRICHMENT     │
    │  - Rules.validate(document)           │
    │  - Search.find_related_entities()     │
    │  - Emit: document.VALIDATED           │
    └────────────┬──────────────────────────┘
                 │
        ┌────────▼────────────────────┐
        │ EVENT: document.VALIDATED   │
        └────────┬────────────────────┘
                 │
    ┌────────────▼────────────────────────┐
    │  Stage 3: STORAGE & INDEXING        │
    │  - VaultCore.store_entry()          │
    │  - FTS5.index_content()             │
    │  - Emit: vault.ENTRY_CREATED        │
    └────────────┬───────────────────────┘
                 │
        ┌────────▼───────────────────┐
        │ EVENT: vault.ENTRY_CREATED │
        └────────┬───────────────────┘
                 │
    ┌────────────▼──────────────────────┐
    │  Stage 4: GRAPH CONSTRUCTION      │
    │  - BuildGraph.create_relationships()│
    │  - UpdateCache.invalidate()        │
    │  - Emit: graph.UPDATED            │
    └────────────┬─────────────────────┘
                 │
        ┌────────▼──────────────────┐
        │ EVENT: graph.UPDATED      │
        └────────┬──────────────────┘
                 │
    ┌────────────▼──────────────────────────┐
    │  Stage 5: NOTIFICATIONS & HOOKS      │
    │  - ObsidianBridge.sync()             │
    │  - AudioGenerator.queue_if_needed()  │
    │  - Emit: workflow.COMPLETE           │
    └────────────┬──────────────────────────┘
                 │
        ┌────────▼─────────────────┐
        │ EVENT: workflow.COMPLETE │
        │                           │
        │ Return result to caller   │
        └─────────────────────────┘
```

---

## Part 3: Core Components Design

### 1. Event Bus (Observer Pattern + Pub/Sub)

```python
# Event types and hierarchy
WorkflowEvent (base)
├── WorkflowStarted
├── WorkflowCompleted
├── WorkflowFailed
└── WorkflowCancelled

DocumentEvent (base)
├── DocumentParsed
├── DocumentValidated
├── DocumentStoredEvent
└── DocumentError

VaultEvent (base)
├── EntryCreated
├── EntryUpdated
├── EntryDeleted
└── EntryVersioned

SearchEvent (base)
├── SearchTriggered
├── SearchCompleted
└── SearchFailed

GraphEvent (base)
├── RelationshipCreated
├── GraphRecomputed
└── GraphOptimized
```

**EventBus Interface:**
```python
class EventBus:
    def subscribe(event_type: Type[Event], handler: Callable) -> str
    def unsubscribe(subscription_id: str) -> None
    def publish(event: Event, async_mode: bool = True) -> None
    def publish_batch(events: List[Event]) -> None
    def clear_handlers() -> None
    def get_subscription_count(event_type: Type) -> int
```

**Advantages:**
- Loose coupling between components
- Asynchronous communication
- Event replay for debugging
- Easy to add new subscribers

### 2. Dependency Injection Container

```python
class DIContainer:
    def register(name: str, factory: Callable, singleton: bool = True) -> None
    def get(name: str) -> Any
    def resolve(target_class: Type) -> Any  # Auto-wiring
    def create_scope() -> 'Scope'  # For request/transaction scope
    def configure_from_dict(config: Dict) -> None
```

**Registration Pattern:**
```python
# Initialization
container = DIContainer()

# Register services
container.register('vault_core', lambda: VaultCore('/path/to/vault'))
container.register('event_bus', lambda: EventBus(), singleton=True)
container.register('rules_engine', 
    lambda: RulesEngine(
        container.get('vault_core'),
        container.get('event_bus')
    ))

# Resolve with auto-wiring
rules = container.resolve(RulesEngine)
```

### 3. Unified Processing Pipeline

```
Input → Validation → Parsing → Enrichment → Storage → Indexing → 
Graph Building → Cache Invalidation → Notifications → Output

Each stage:
- Receives events from previous stage
- Processes independently
- Emits events for next stage
- Has error handling & recovery
```

### 4. Orchestrator Service

Central coordinator managing:
- Command/query reception
- Workflow execution
- Error recovery
- Resource cleanup

```python
class Orchestrator:
    async def process_command(cmd: Command) -> CommandResult:
        # 1. Validate
        # 2. Build execution plan
        # 3. Execute with event coordination
        # 4. Handle errors and recovery
        # 5. Return result

    async def execute_workflow(plan: ExecutionPlan) -> WorkflowResult:
        # Execute stages in order
        # Emit events
        # Coordinate subsystems
        # Handle cancellation
```

---

## Part 4: Best Practices from Industry Leaders

### From Neo4j: Knowledge Graph Patterns

1. **Index-Free Adjacency**: Store relationships directly with nodes
   - Faster traversal than join-based systems
   - Native relationship storage

2. **Semantic Relationships**: Types matter
   - Instead of generic "related", use specific types
   - E.g., `REFERENCES`, `DEPENDS_ON`, `CONFLICTS_WITH`

3. **Graph Algorithms**: Path finding, centrality
   - Find most important entities
   - Detect communities
   - Recommend relationships

### From ESLint: AST-Based Rule Engine

1. **Visitor Pattern**: Walk the tree systematically
   - Register callbacks for node types
   - Process nodes in order
   - Track context/state

2. **Extensible Rules**: Contract-based plugins
   - Provide AST access
   - Rules independent of each other
   - Configurable severity levels

3. **Fast Parsing**: Cache ASTs
   - Parse once, query many times
   - Version AST with source code

### From spaCy: Component Pipeline

1. **Pipeline Stages**: Each component has clear input/output
   - Tokenizer → Tagger → Parser → NER → Lemmatizer
   - Components can be chained
   - Easy to swap implementations

2. **Lazy Evaluation**: Only compute what's needed
   - Models load on-demand
   - Cache intermediate results
   - Skip components if not needed

3. **Statistical + Symbolic**: Mix approaches
   - ML models for heavy lifting
   - Rule-based for precise control
   - Combine results intelligently

### From Obsidian: Plugin System

1. **Hot Swapping**: Plugins load/unload at runtime
   - No restart needed
   - Changes isolated to plugin
   - Core system unaffected

2. **Contract-Based**: Plugins implement interfaces
   - Well-defined responsibilities
   - Versioning for compatibility
   - Predictable behavior

3. **Resource Management**: Plugins manage their own lifecycle
   - Load/unload hooks
   - Cleanup on deactivation
   - Memory and file handle management

### From SQLite: FTS5 Best Practices

1. **Inverted Index**: Efficient term-based search
   - Maps terms → documents
   - BM25 ranking built-in
   - Handles large vocabularies

2. **Tokenizers**: Language-aware text processing
   - Multilingual support (ICU tokenizer)
   - Custom tokenizers for domain-specific needs
   - Normalization (case, diacritics)

3. **Phrase Search**: Support complex queries
   - Quoted phrases
   - Boolean operators
   - Proximity searches

---

## Part 5: Data Flow in Unified Architecture

### Search Query Example

```
1. User executes: search("neural network optimization")

2. Orchestrator.trigger_search()
   ├─ Emit: SearchTriggered event
   ├─ Validate query
   ├─ Check cache
   └─ If cached → return

3. NeuralReflex subscribes to SearchTriggered
   ├─ Semantic search (embeddings)
   │   └─ Emit: SemanticResultsReady
   ├─ Lexical search (FTS5)
   │   └─ Emit: LexicalResultsReady
   └─ Syntactic search (AST)
       └─ Emit: SyntacticResultsReady

4. ResultAggregator subscribes to all result events
   ├─ Wait for all three to complete (or timeout)
   ├─ Merge and rank results
   ├─ Apply Rules filters
   └─ Emit: SearchCompleted

5. Cache subscribes to SearchCompleted
   ├─ Store results
   └─ Set TTL

6. Metrics subscribes to SearchCompleted
   ├─ Record latency
   ├─ Count results
   └─ Track search patterns

7. Return results to user
```

### Document Ingestion Example

```
1. User uploads: "project-report.pdf"

2. Orchestrator.ingest_document()
   ├─ Emit: IngestionStarted
   ├─ Validate file
   └─ Enqueue for processing

3. Graphify subscribes to IngestionStarted
   ├─ Detect format (PDF)
   ├─ Parse sections
   ├─ Extract metadata
   ├─ Emit: DocumentParsed

4. NLP subscribes to DocumentParsed
   ├─ Extract entities (PERSON, ORG, PRODUCT)
   ├─ Extract keywords
   ├─ Calculate importance
   └─ Emit: EntitiesExtracted

5. Rules subscribes to EntitiesExtracted
   ├─ Check security rules
   ├─ Check naming conventions
   ├─ Check classification
   └─ Emit: RulesValidated

6. VaultCore subscribes to RulesValidated
   ├─ Create entry
   ├─ Encrypt sensitive data
   ├─ Store in DB
   ├─ Increment version
   └─ Emit: EntryStored

7. FTS5 subscribes to EntryStored
   ├─ Index content
   ├─ Update term frequencies
   ├─ Update BM25 scores
   └─ Emit: IndexUpdated

8. GraphBuilder subscribes to EntryStored + EntitiesExtracted
   ├─ Create nodes for entities
   ├─ Create relationships
   ├─ Update graph structure
   └─ Emit: GraphUpdated

9. Cache subscribes to GraphUpdated
   ├─ Invalidate related caches
   ├─ Precompute common queries
   └─ Emit: CacheInvalidated

10. ObsidianBridge subscribes to EntryStored
    ├─ Create note in vault
    ├─ Link to related notes
    └─ Emit: ObsidianSynced

11. Audio subscribes to EntryStored (if configured)
    ├─ Queue for TTS
    ├─ Generate audio
    └─ Store as attachment

12. Emit: IngestionCompleted → Return to user
```

---

## Part 6: Error Handling & Recovery

### Recovery Strategies

```python
class RecoveryStrategy:
    RETRY_EXPONENTIAL    # Exponential backoff (1s, 2s, 4s, 8s...)
    CIRCUIT_BREAKER      # Stop calling failing service
    FALLBACK            # Use alternative implementation
    QUEUE_AND_RETRY     # Queue for later retry
    NOTIFY_ADMIN        # Alert on critical failures
```

### Event Error Handling

```python
class EventBus:
    def publish(event: Event) -> Result:
        try:
            # Call all handlers
            for handler in handlers[event_type]:
                try:
                    result = handler(event)
                except Exception as e:
                    logger.error(f"Handler failed: {e}")
                    # Emit ErrorEvent
                    # Apply recovery strategy
                    # Continue with next handler
        except Exception as e:
            # Log, alert, recover
            emit(SystemErrorEvent(error=e))
```

### Idempotency Guarantees

- All operations should be idempotent
- Store operation ID + timestamp
- Detect duplicates
- Re-run safely

---

## Part 7: Observability & Monitoring

### Logging Strategy

```python
# Structured logging
logger.info("document_ingested", 
    extra={
        "document_id": doc_id,
        "size_bytes": size,
        "format": fmt,
        "processing_time_ms": elapsed,
        "entities_count": count
    })
```

### Metrics Collection

- Latency: min, max, avg, p50, p95, p99
- Throughput: events/sec, documents/sec
- Error rates: by type, by stage
- Resource usage: memory, CPU, disk
- Cache hit rates

### Distributed Tracing

```python
# Each operation gets a trace ID
trace_id = generate_id()

# Passed through event chain
event.trace_id = trace_id

# Recorded at each stage
span = tracer.start_span("stage.name", trace_id=trace_id)
```

---

## Part 8: Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
- [ ] Implement EventBus
- [ ] Implement DIContainer
- [ ] Create base Event classes
- [ ] Create Orchestrator skeleton

### Phase 2: Core Services (Week 3-4)
- [ ] Refactor VaultCore with events
- [ ] Refactor NeuralReflex with events
- [ ] Refactor Graphify with events
- [ ] Refactor Rules with events

### Phase 3: Integration (Week 5-6)
- [ ] Connect all components to EventBus
- [ ] Implement Orchestrator workflows
- [ ] Add error handling & recovery
- [ ] Add observability layer

### Phase 4: Optimization (Week 7-8)
- [ ] Add caching layer
- [ ] Optimize hot paths
- [ ] Add performance monitoring
- [ ] Document API

---

## Part 9: API Contracts

### VaultCore Interface (Refactored)

```python
class VaultCore:
    async def store_entry(entry: VaultEntry) -> VaultEntry:
        """Store entry and emit vault.EntryCreated"""
        
    async def get_entry(entry_id: str) -> VaultEntry:
        """Retrieve entry by ID"""
        
    async def query_entries(filters: QueryFilter) -> List[VaultEntry]:
        """Query with filters"""
        
    async def create_relationship(source: str, target: str, 
                                  rel_type: str) -> VaultEdge:
        """Create relationship and emit graph.RelationshipCreated"""
        
    async def search(query: str) -> SearchResult:
        """Coordinated search across all indices"""
```

### Rules Engine Interface (Refactored)

```python
class RulesEngine:
    def validate_entry(entry: VaultEntry) -> ValidationResult:
        """Validate entry against rules, emit RulesValidated"""
        
    def validate_query(query: str) -> bool:
        """Check if query matches security rules"""
        
    def get_applicable_rules(context: Context) -> List[Rule]:
        """Get rules for specific context"""
```

### Search Engine Interface (Refactored)

```python
class SearchCoordinator:
    async def search(query: str, timeout_ms: int = 500) -> SearchResult:
        """Coordinated search with timeout"""
        
    async def semantic_search(query: str) -> List[Match]:
        """Embedding-based search"""
        
    async def lexical_search(query: str) -> List[Match]:
        """FTS5-based search"""
        
    async def syntactic_search(query: str) -> List[Match]:
        """AST-based search"""
```

---

## Part 10: Testing Strategy

### Unit Tests
- Test each component in isolation
- Mock EventBus and dependencies
- Test error paths

### Integration Tests
- Test EventBus coordination
- Test full workflows
- Test error recovery

### End-to-End Tests
- Complete ingestion-to-search workflow
- Performance benchmarks
- Failure scenarios

### Performance Tests
- Latency under load
- Memory usage profiling
- Cache effectiveness

---

## Conclusion

This unified architecture transforms Nexus Driver from a collection of isolated modules into a cohesive, event-driven ecosystem. Key benefits:

✅ **Loose Coupling**: Components communicate via events
✅ **Scalability**: Easy to add new components
✅ **Observability**: Full visibility into workflows
✅ **Resilience**: Error handling and recovery at each stage
✅ **Testability**: Easy to mock and test components
✅ **Performance**: Async processing, caching, optimization

The design follows proven patterns from industry leaders while maintaining simplicity and clarity.
