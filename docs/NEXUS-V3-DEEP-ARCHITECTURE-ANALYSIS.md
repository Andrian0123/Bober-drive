# Nexus Driver v3 — Глубокий Архитектурный Анализ

## Executive Summary

После детального изучения референсных архитектур (spaCy, Neo4j, Elasticsearch, LangChain) и анализа текущего состояния Nexus Driver, выявлены **критические архитектурные проблемы**, которые необходимо устранить для поддержки больших и очень больших проектов.

**Ключевые находки:**
1. ❌ **Отсутствие Pipeline Architecture** - нет унифицированного потока обработки
2. ❌ **Tight Coupling** - модули жёстко связаны, невозможно масштабирование
3. ❌ **No Dependency Injection** - ручное управление зависимостями
4. ❌ **Слабая Event System** - события не покрывают все операции
5. ❌ **No Auto-Update Mechanism** - отсутствует система обновлений
6. ❌ **Limited Observability** - недостаточно метрик и трейсинга

---

## Часть 1: Референсные Архитектуры

### 1.1 spaCy Pipeline Architecture

**Что изучили:**
- **Модульная pipeline система** с компонентами (tokenizer → tagger → parser → ner)
- **Doc object** как центральный контейнер данных, передаваемый между компонентами
- **Custom components API** для расширения функциональности
- **Lazy loading** и эффективное управление памятью

**Применимо к Nexus:**
```python
# spaCy Style
nlp = spacy.load("en_core_web_sm")
doc = nlp("Text")  # Pipeline: tokenizer → tagger → parser → ner

# Nexus должен работать так:
nexus = NexusOrchestrator()
result = nexus.process_document(doc_path)
# Pipeline: scanner → parser → rules → vault → indexer → graph
```

**Ключевые паттерны:**
- ✅ Sequential pipeline processing
- ✅ Immutable data containers (Doc → NexusDocument)
- ✅ Component-based architecture
- ✅ Extensibility through custom components

### 1.2 Neo4j Design Patterns

**Что изучили:**
- **Intermediary Nodes** для сложных связей (hyperedges)
- **Index-free adjacency** для быстрого обхода графа
- **Relationship-first modeling** вместо JOIN операций
- **Flexible schema** без жёстких ограничений

**Применимо к Nexus:**
```python
# Neo4j Pattern: Intermediary Node
(:Person)-[:WORKS_AT]->(:Role)<-[:REQUIRES]-(:Company)

# Nexus Pattern: Document Relationships
(:Document)-[:REFERENCES]->(:Reference)<-[:MENTIONED_IN]-(:Entity)
(:Document)-[:VIOLATES]->(:RuleViolation)<-[:DEFINED_BY]-(:Rule)
```

**Ключевые паттерны:**
- ✅ Use relationships to store meaningful data
- ✅ Create intermediate nodes for complex associations
- ✅ Index nodes for fast lookups, traverse edges for queries
- ✅ Flexible schema evolution

### 1.3 Elasticsearch Ingest Pipelines

**Что изучили:**
- **Ingest Pipeline** для трансформации документов перед индексацией
- **Processors** цепочка (remove_field → extract_value → enrich_data)
- **Bulk API** для эффективной массовой обработки
- **Index lifecycle management** (ILM)

**Применимо к Nexus:**
```python
# Elasticsearch Ingest Pipeline
PUT _ingest/pipeline/my-pipeline {
  "processors": [
    {"set": {"field": "processed", "value": true}},
    {"lowercase": {"field": "title"}},
    {"remove": {"field": "temp_data"}}
  ]
}

# Nexus Processing Pipeline
class NexusIngestPipeline:
    def __init__(self):
        self.processors = [
            DocumentParser(),      # Extract content
            RulesValidator(),      # Check compliance
            EntityExtractor(),     # Extract entities
            FTS5Indexer(),         # Index for search
            GraphBuilder()         # Build relationships
        ]
```

**Ключевые паттерны:**
- ✅ Transform data before storage
- ✅ Composable processors
- ✅ Bulk operations for performance
- ✅ Lifecycle management

### 1.4 LangChain Architecture

**Что изучили:**
- **Dependency Injection** через middleware и context
- **StateGraph** для управления состоянием агентов
- **Circuit Breakers** для отказоустойчивости
- **Observability middleware** для трейсинга

**Применимо к Nexus:**
```python
# LangChain DI Pattern
class AgentExecutor:
    def __init__(self, llm, tools, memory):
        self.llm = llm
        self.tools = tools
        self.memory = memory

# Nexus DI Pattern
class NexusDIContainer:
    def __init__(self):
        self.services = {}
    
    def register(self, name: str, factory: Callable):
        self.services[name] = factory
    
    def resolve(self, name: str):
        return self.services[name](self)
```

**Ключевые паттерны:**
- ✅ Dependency injection for testability
- ✅ Middleware for cross-cutting concerns
- ✅ State management for workflows
- ✅ Error recovery strategies

---

## Часть 2: Критические Проблемы Текущей Архитектуры

### 2.1 Отсутствие Unified Pipeline

**Проблема:**
```python
# Сейчас: каждый модуль работает независимо
rules_engine = RulesEngineV3(...)
rules_engine.validate_against_rules(content)

fts5_indexer = FTS5IndexerV3(...)
fts5_indexer.fulltext_search(query)

# Нет координации между модулями!
```

**Должно быть:**
```python
# Pipeline orchestration
pipeline = NexusPipeline()
pipeline.add_stage("parse", GraphifyEngineV3)
pipeline.add_stage("validate", RulesEngineV3)
pipeline.add_stage("store", VaultCoreV3)
pipeline.add_stage("index", FTS5IndexerV3)
pipeline.add_stage("graph", GraphBuilder)

result = pipeline.execute(document)
```

### 2.2 Tight Coupling между модулями

**Проблема:**
```python
# VaultCore знает о всех потребителях
class VaultCore:
    def store(self, entry):
        # Direct dependencies
        self.fts5.index(entry)  # ❌
        self.graph.add_node(entry)  # ❌
        self.rules.validate(entry)  # ❌
```

**Должно быть:**
```python
# Event-driven loose coupling
class VaultCoreV3:
    def store(self, entry):
        stored = super().store(entry)
        # Emit event - let subscribers decide what to do
        self.event_bus.publish(EntryCreated(entry_id=entry.id))
        return stored

# Subscribers handle their logic
fts5_indexer.subscribe(EntryCreated, lambda e: fts5_indexer.index(e.entry_id))
graph_builder.subscribe(EntryCreated, lambda e: graph_builder.add_node(e.entry_id))
```

### 2.3 Ручное управление зависимостями

**Проблема:**
```python
# Создание всех зависимостей вручную
vault = VaultCore(db_path)
fts5 = FTS5IndexerV3(db_path)
rules = RulesEngineV3(project_root, vault)
mapper = FileSystemMapper(project_root, vault)
graphify = GraphifyEngine(vault, fts5)

# Много boilerplate, сложно тестировать
```

**Должно быть:**
```python
# Dependency Injection Container
container = NexusDIContainer()
container.register("vault", lambda c: VaultCore(c.config.db_path))
container.register("fts5", lambda c: FTS5IndexerV3(c.config.db_path))
container.register("rules", lambda c: RulesEngineV3(c.config.project_root, c.resolve("vault")))

# Auto-wiring
vault = container.resolve("vault")
```

### 2.4 Недостаточная Event Coverage

**Проблема:**
```python
# VaultCoreV3 - только CRUD события
# RulesEngineV3 - события валидации
# FTS5IndexerV3 - события поиска

# Нет событий для:
# - Жизненного цикла системы (startup, shutdown, health_check)
# - Batch операций (batch_import_started, batch_import_progress)
# - Ошибок и recovery (error_occurred, recovery_started)
# - Метрик (performance_degradation, memory_high)
```

**Должно быть:**
```python
# Comprehensive event system
class SystemEvents:
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_READY = "system.ready"
    SYSTEM_SHUTDOWN = "system.shutdown"
    HEALTH_CHECK_FAILED = "system.health_check_failed"

class BatchEvents:
    BATCH_STARTED = "batch.started"
    BATCH_PROGRESS = "batch.progress"
    BATCH_COMPLETED = "batch.completed"
    BATCH_FAILED = "batch.failed"

class ErrorEvents:
    ERROR_OCCURRED = "error.occurred"
    RECOVERY_STARTED = "error.recovery_started"
    RECOVERY_COMPLETED = "error.recovery_completed"
```

---

## Часть 3: Улучшенная Архитектура

### 3.1 Unified Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                            │
│              (CLI, API, GUI, Plugins)                           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                  NEXUS ORCHESTRATOR                             │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  DI Container  │  Event Bus  │  Pipeline Manager       │    │
│  └────────────────────────────────────────────────────────┘    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
    ┌────▼────┐       ┌────▼────┐      ┌────▼────┐
    │ Ingest  │       │Process  │      │ Query   │
    │Pipeline │       │Pipeline │      │Pipeline │
    └────┬────┘       └────┬────┘      └────┬────┘
         │                 │                 │
    ┌────▼─────────────────▼─────────────────▼────┐
    │          COMPONENT REGISTRY                  │
    │  ┌──────────────────────────────────────┐   │
    │  │ VaultCore │ FTS5 │ Rules │ Graph    │   │
    │  │ Mapper │ Trash │ Audio │ Obsidian   │   │
    │  └──────────────────────────────────────┘   │
    └───────────────────┬──────────────────────────┘
                        │
    ┌───────────────────▼──────────────────────────┐
    │         INFRASTRUCTURE LAYER                 │
    │  (SQLite, FileSystem, Cache, Encryption)    │
    └──────────────────────────────────────────────┘
```

### 3.2 NexusOrchestrator - Центральная Координация

```python
# driver/nexus_orchestrator_v3.py

from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from pathlib import Path
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class PipelineStage(Enum):
    """Available pipeline stages"""
    SCAN = "scan"           # File scanning
    PARSE = "parse"         # Document parsing
    VALIDATE = "validate"   # Rules validation
    STORE = "store"         # Vault storage
    INDEX = "index"         # FTS5 indexing
    GRAPH = "graph"         # Graph building
    EXPORT = "export"       # External exports


@dataclass
class NexusConfig:
    """Unified configuration"""
    project_root: Path
    vault_path: Path
    enable_events: bool = True
    enable_auto_update: bool = True
    update_check_days: int = 15
    max_workers: int = 4
    cache_size_mb: int = 512
    log_level: str = "INFO"


class NexusDIContainer:
    """Dependency Injection Container"""
    
    def __init__(self, config: NexusConfig):
        self.config = config
        self._services: Dict[str, Callable] = {}
        self._instances: Dict[str, Any] = {}
        self._register_core_services()
    
    def _register_core_services(self):
        """Register core services"""
        from core.event_bus import EventBus, EventBusConfig
        from vault_core_v3 import VaultCoreV3
        from nexus_fts5_indexer_v3 import FTS5IndexerV3
        from nexus_rules_engine_v3 import RulesEngineV3
        from nexus_graphify_v3 import GraphifyEngineV3
        
        # Event Bus (singleton)
        self.register_singleton("event_bus", lambda c: EventBus(
            EventBusConfig(max_history=10000)
        ))
        
        # VaultCore
        self.register("vault", lambda c: VaultCoreV3(
            vault_path=c.config.vault_path,
            event_bus=c.resolve("event_bus")
        ))
        
        # FTS5 Indexer
        self.register("fts5", lambda c: FTS5IndexerV3(
            db_path=c.config.vault_path,
            event_bus=c.resolve("event_bus")
        ))
        
        # Rules Engine
        self.register("rules", lambda c: RulesEngineV3(
            project_root=c.config.project_root,
            vault_core=c.resolve("vault"),
            event_bus=c.resolve("event_bus")
        ))
        
        # Graphify Engine
        self.register("graphify", lambda c: GraphifyEngineV3(
            vault_core=c.resolve("vault"),
            fts5_extension=c.resolve("fts5"),
            event_bus=c.resolve("event_bus")
        ))
    
    def register(self, name: str, factory: Callable):
        """Register a service factory"""
        self._services[name] = factory
    
    def register_singleton(self, name: str, factory: Callable):
        """Register a singleton service"""
        def singleton_factory(container):
            if name not in self._instances:
                self._instances[name] = factory(container)
            return self._instances[name]
        
        self._services[name] = singleton_factory
    
    def resolve(self, name: str) -> Any:
        """Resolve a service by name"""
        if name not in self._services:
            raise KeyError(f"Service '{name}' not registered")
        return self._services[name](self)
    
    def has(self, name: str) -> bool:
        """Check if service is registered"""
        return name in self._services


class NexusPipeline:
    """Processing pipeline with stages"""
    
    def __init__(self, container: NexusDIContainer):
        self.container = container
        self.event_bus = container.resolve("event_bus")
        self.stages: List[tuple] = []
    
    def add_stage(self, name: str, processor: Callable) -> 'NexusPipeline':
        """Add a processing stage"""
        self.stages.append((name, processor))
        return self
    
    def execute(self, input_data: Any) -> Dict[str, Any]:
        """Execute pipeline"""
        from core.event_bus import WorkflowStarted, WorkflowCompleted, WorkflowFailed
        
        workflow_id = f"pipeline_{secrets.token_hex(4)}"
        result = {"workflow_id": workflow_id, "stages": {}}
        
        try:
            # Emit start event
            self.event_bus.publish(WorkflowStarted(
                workflow_id=workflow_id,
                workflow_name="nexus_pipeline"
            ))
            
            # Execute stages sequentially
            current_data = input_data
            for stage_name, processor in self.stages:
                logger.info(f"Executing stage: {stage_name}")
                stage_result = processor(current_data, self.container)
                result["stages"][stage_name] = stage_result
                current_data = stage_result.get("output", current_data)
            
            # Emit completion event
            self.event_bus.publish(WorkflowCompleted(
                workflow_id=workflow_id,
                result=result
            ))
            
            return result
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            self.event_bus.publish(WorkflowFailed(
                workflow_id=workflow_id,
                error=str(e)
            ))
            raise


class NexusOrchestrator:
    """Main orchestrator for Nexus Driver"""
    
    def __init__(self, config: NexusConfig):
        self.config = config
        self.container = NexusDIContainer(config)
        self.event_bus = self.container.resolve("event_bus")
        self._setup_logging()
        self._start_auto_update_checker()
    
    def _setup_logging(self):
        """Configure logging"""
        logging.basicConfig(
            level=getattr(logging, self.config.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def _start_auto_update_checker(self):
        """Start auto-update checker"""
        if self.config.enable_auto_update:
            from nexus_auto_updater import AutoUpdater
            self.updater = AutoUpdater(
                check_interval_days=self.config.update_check_days
            )
            self.updater.start()
    
    def create_ingest_pipeline(self) -> NexusPipeline:
        """Create document ingestion pipeline"""
        return (NexusPipeline(self.container)
            .add_stage("scan", self._scan_stage)
            .add_stage("parse", self._parse_stage)
            .add_stage("validate", self._validate_stage)
            .add_stage("store", self._store_stage)
            .add_stage("index", self._index_stage)
            .add_stage("graph", self._graph_stage)
        )
    
    def create_search_pipeline(self) -> NexusPipeline:
        """Create search pipeline"""
        return (NexusPipeline(self.container)
            .add_stage("parse_query", self._parse_query_stage)
            .add_stage("search_fts5", self._search_fts5_stage)
            .add_stage("search_semantic", self._search_semantic_stage)
            .add_stage("merge_results", self._merge_results_stage)
        )
    
    def _scan_stage(self, input_data: Dict, container: NexusDIContainer) -> Dict:
        """File scanning stage"""
        mapper = container.resolve("file_mapper")
        files = mapper.scan_project()
        return {"output": files, "file_count": len(files)}
    
    def _parse_stage(self, input_data: Dict, container: NexusDIContainer) -> Dict:
        """Document parsing stage"""
        graphify = container.resolve("graphify")
        parsed = []
        for file_path in input_data:
            doc = graphify.import_document(file_path)
            if doc:
                parsed.append(doc)
        return {"output": parsed, "parsed_count": len(parsed)}
    
    def _validate_stage(self, input_data: Dict, container: NexusDIContainer) -> Dict:
        """Rules validation stage"""
        rules = container.resolve("rules")
        violations = []
        for doc in input_data:
            v = rules.validate_against_rules(doc.content)
            if v:
                violations.extend(v)
        return {"output": input_data, "violations": violations}
    
    def _store_stage(self, input_data: Dict, container: NexusDIContainer) -> Dict:
        """Vault storage stage"""
        vault = container.resolve("vault")
        stored_ids = []
        for doc in input_data:
            entry_id = vault.store(doc)
            stored_ids.append(entry_id)
        return {"output": stored_ids, "stored_count": len(stored_ids)}
    
    def _index_stage(self, input_data: Dict, container: NexusDIContainer) -> Dict:
        """FTS5 indexing stage"""
        fts5 = container.resolve("fts5")
        # Indexing happens automatically via events
        return {"output": input_data, "indexed": True}
    
    def _graph_stage(self, input_data: Dict, container: NexusDIContainer) -> Dict:
        """Graph building stage"""
        # Graph relationships built automatically via events
        return {"output": input_data, "graph_updated": True}
    
    def process_document(self, doc_path: Path) -> Dict[str, Any]:
        """Process a single document"""
        pipeline = self.create_ingest_pipeline()
        return pipeline.execute({"document_path": doc_path})
    
    def search(self, query: str) -> Dict[str, Any]:
        """Execute search across all engines"""
        pipeline = self.create_search_pipeline()
        return pipeline.execute({"query": query})
    
    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        return {
            "vault": self.container.resolve("vault").get_stats(),
            "fts5": self.container.resolve("fts5").get_stats(),
            "rules": self.container.resolve("rules").get_stats(),
            "event_bus": self.event_bus.get_stats()
        }
    
    def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down Nexus Orchestrator")
        self.event_bus.stop_async_processing()
        if hasattr(self, 'updater'):
            self.updater.stop()


# Factory function
def create_nexus_orchestrator(
    project_root: Path,
    vault_path: Path,
    **kwargs
) -> NexusOrchestrator:
    """Create NexusOrchestrator with default config"""
    config = NexusConfig(
        project_root=project_root,
        vault_path=vault_path,
        **kwargs
    )
    return NexusOrchestrator(config)
```

---

## Часть 4: Система Авто-Обновлений

```python
# driver/nexus_auto_updater.py

import threading
import time
import requests
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import subprocess
import sys

logger = logging.getLogger(__name__)

GITHUB_API_URL = "https://api.github.com/repos/Andrian0123/Bober-drive"
CURRENT_VERSION = "3.0.0"


@dataclass
class UpdateInfo:
    """Information about available update"""
    version: str
    release_date: str
    download_url: str
    changelog: str
    critical: bool = False


class AutoUpdater:
    """Automatic update checker and installer"""
    
    def __init__(self, check_interval_days: int = 15):
        self.check_interval_days = check_interval_days
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.last_check: Optional[datetime] = None
        self._load_state()
    
    def _load_state(self):
        """Load updater state from file"""
        state_file = Path.home() / ".nexus" / "updater_state.json"
        if state_file.exists():
            try:
                with open(state_file) as f:
                    state = json.load(f)
                    self.last_check = datetime.fromisoformat(state.get("last_check", ""))
            except Exception as e:
                logger.warning(f"Could not load updater state: {e}")
    
    def _save_state(self):
        """Save updater state to file"""
        state_file = Path.home() / ".nexus" / "updater_state.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(state_file, 'w') as f:
                json.dump({
                    "last_check": self.last_check.isoformat() if self.last_check else None,
                    "current_version": CURRENT_VERSION
                }, f)
        except Exception as e:
            logger.warning(f"Could not save updater state: {e}")
    
    def check_for_updates(self) -> Optional[UpdateInfo]:
        """Check GitHub for new releases"""
        try:
            response = requests.get(
                f"{GITHUB_API_URL}/releases/latest",
                timeout=10
            )
            response.raise_for_status()
            
            release = response.json()
            latest_version = release["tag_name"].lstrip("v")
            
            if self._is_newer_version(latest_version, CURRENT_VERSION):
                return UpdateInfo(
                    version=latest_version,
                    release_date=release["published_at"],
                    download_url=release["zipball_url"],
                    changelog=release["body"],
                    critical=release.get("prerelease", False)
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to check for updates: {e}")
            return None
    
    def _is_newer_version(self, version1: str, version2: str) -> bool:
        """Compare version strings"""
        v1_parts = [int(x) for x in version1.split('.')]
        v2_parts = [int(x) for x in version2.split('.')]
        return v1_parts > v2_parts
    
    def install_update(self, update_info: UpdateInfo) -> bool:
        """Download and install update"""
        try:
            logger.info(f"Installing update {update_info.version}")
            
            # Download update
            response = requests.get(update_info.download_url, stream=True)
            response.raise_for_status()
            
            update_file = Path.home() / ".nexus" / f"nexus-{update_info.version}.zip"
            update_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(update_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Run update script
            if sys.platform == "win32":
                update_script = Path(__file__).parent / "update-nexus.bat"
            else:
                update_script = Path(__file__).parent / "update-nexus.sh"
            
            subprocess.Popen([str(update_script), str(update_file)])
            
            logger.info("Update installed successfully. Restart required.")
            return True
            
        except Exception as e:
            logger.error(f"Failed to install update: {e}")
            return False
    
    def _update_loop(self):
        """Background update checker loop"""
        while self.running:
            try:
                # Check if it's time to check for updates
                if self.last_check is None or \
                   (datetime.now() - self.last_check).days >= self.check_interval_days:
                    
                    logger.info("Checking for updates...")
                    update_info = self.check_for_updates()
                    
                    if update_info:
                        logger.info(f"New version available: {update_info.version}")
                        
                        if update_info.critical:
                            logger.warning("Critical update available! Installing...")
                            self.install_update(update_info)
                        else:
                            logger.info("Update available. Set auto_install=True to enable automatic updates.")
                    
                    self.last_check = datetime.now()
                    self._save_state()
                
                # Sleep for 1 hour before next check
                time.sleep(3600)
                
            except Exception as e:
                logger.error(f"Error in update loop: {e}")
                time.sleep(3600)
    
    def start(self):
        """Start background update checker"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._update_loop, daemon=True)
        self.thread.start()
        logger.info(f"Auto-updater started (check every {self.check_interval_days} days)")
    
    def stop(self):
        """Stop background update checker"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Auto-updater stopped")
```

Продолжу создание остальных компонентов улучшенной архитектуры?