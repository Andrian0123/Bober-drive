#!/usr/bin/env python3
"""
Nexus Orchestrator V3 - Central Coordination and Pipeline Management
Unified architecture with DI Container, Event Bus, and Processing Pipelines

Inspired by:
- spaCy: Pipeline architecture with sequential processing
- LangChain: Dependency injection and middleware patterns
- Elasticsearch: Ingest pipelines with composable processors
"""

import logging
import secrets
from typing import Dict, Any, Optional, List, Callable, Type
from dataclasses import dataclass
from pathlib import Path
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class PipelineStage(Enum):
    """Available pipeline stages"""
    SCAN = "scan"             # File system scanning
    PARSE = "parse"           # Document parsing
    VALIDATE = "validate"     # Rules validation
    EXTRACT = "extract"       # Entity extraction
    STORE = "store"           # Vault storage
    INDEX = "index"           # FTS5 indexing
    GRAPH = "graph"           # Graph building
    EXPORT = "export"         # External exports


@dataclass
class NexusConfig:
    """Unified configuration for Nexus Driver"""
    # Paths
    project_root: Path
    vault_path: Path
    
    # Features
    enable_events: bool = True
    enable_auto_update: bool = True
    enable_caching: bool = True
    
    # Performance
    max_workers: int = 4
    cache_size_mb: int = 512
    batch_size: int = 100
    
    # Auto-update
    update_check_days: int = 15
    auto_install_updates: bool = False
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[Path] = None
    
    # Advanced
    enable_profiling: bool = False
    enable_metrics: bool = True


class NexusDIContainer:
    """
    Dependency Injection Container
    
    Manages service lifecycle and dependencies.
    Inspired by LangChain's dependency management patterns.
    """
    
    def __init__(self, config: NexusConfig):
        self.config = config
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, Any] = {}
        self._instances: Dict[str, Any] = {}
        self._register_core_services()
    
    def _register_core_services(self):
        """Register core Nexus services"""
        # Import here to avoid circular dependencies
        from driver.core.event_bus import EventBus, EventBusConfig
        
        # Event Bus (singleton)
        self.register_singleton("event_bus", lambda c: EventBus(
            EventBusConfig(
                history_size=10000,
                async_mode=True
            )
        ))
        
        # VaultCore
        self.register("vault", self._create_vault)
        
        # FTS5 Indexer
        self.register("fts5", self._create_fts5)
        
        # Rules Engine
        self.register("rules", self._create_rules)
        
        # Graphify Engine
        self.register("graphify", self._create_graphify)
        
        # File System Mapper
        self.register("file_mapper", self._create_file_mapper)
        
        # Trash Manager
        self.register("trash", self._create_trash)
        
        # Neural Reflex Engine
        self.register("neural_reflex", self._create_neural_reflex)
        
        # Auto Updater
        if self.config.enable_auto_update:
            self.register_singleton("auto_updater", self._create_auto_updater)
    
    def _create_vault(self, container: 'NexusDIContainer') -> Any:
        """Create VaultCore instance"""
        from vault_core_v3 import VaultCoreV3, VaultCoreV3Config
        
        return VaultCoreV3(
            vault_path=container.config.vault_path,
            config=VaultCoreV3Config(
                enable_events=container.config.enable_events
            ),
            event_bus=container.resolve("event_bus")
        )
    
    def _create_fts5(self, container: 'NexusDIContainer') -> Any:
        """Create FTS5 Indexer instance"""
        from nexus_fts5_indexer_v3 import FTS5IndexerV3, FTS5IndexerV3Config
        
        return FTS5IndexerV3(
            db_path=container.config.vault_path,
            config=FTS5IndexerV3Config(
                enable_events=container.config.enable_events,
                event_bus=container.resolve("event_bus")
            )
        )
    
    def _create_rules(self, container: 'NexusDIContainer') -> Any:
        """Create Rules Engine instance"""
        from nexus_rules_engine_v3 import RulesEngineV3, RulesEngineV3Config
        
        return RulesEngineV3(
            project_root=container.config.project_root,
            vault_core=container.resolve("vault"),
            config=RulesEngineV3Config(
                enable_events=container.config.enable_events
            ),
            event_bus=container.resolve("event_bus")
        )
    
    def _create_graphify(self, container: 'NexusDIContainer') -> Any:
        """Create Graphify Engine instance"""
        try:
            from nexus_graphify_v3 import GraphifyEngineV3, GraphifyEngineV3Config
            
            return GraphifyEngineV3(
                vault_core=container.resolve("vault"),
                fts5_extension=container.resolve("fts5"),
                config=GraphifyEngineV3Config(
                    enable_events=container.config.enable_events
                ),
                event_bus=container.resolve("event_bus")
            )
        except ImportError:
            # Fallback to legacy version
            from nexus_graphify import GraphifyEngine
            return GraphifyEngine(
                vault_core=container.resolve("vault"),
                fts5_extension=container.resolve("fts5")
            )
    
    def _create_file_mapper(self, container: 'NexusDIContainer') -> Any:
        """Create File System Mapper instance"""
        try:
            from nexus_file_system_mapper_v3 import FileSystemMapperV3, FileSystemMapperV3Config
            
            return FileSystemMapperV3(
                project_root=container.config.project_root,
                vault_core=container.resolve("vault"),
                event_bus=container.resolve("event_bus"),
                config=FileSystemMapperV3Config(
                    enable_events=container.config.enable_events
                )
            )
        except ImportError:
            # Fallback to legacy version
            from nexus_file_system_mapper import FileSystemMapper
            return FileSystemMapper(
                project_root=container.config.project_root,
                vault_core=container.resolve("vault")
            )
    
    def _create_trash(self, container: 'NexusDIContainer') -> Any:
        """Create Trash Manager instance"""
        try:
            from nexus_trash_manager_v3 import TrashManagerV3, TrashManagerV3Config
            
            return TrashManagerV3(
                db_path=container.config.vault_path,
                event_bus=container.resolve("event_bus"),
                config=TrashManagerV3Config(
                    enable_events=container.config.enable_events
                )
            )
        except ImportError:
            # Fallback to legacy version
            from trash_manager import TrashManager
            return TrashManager(db_path=container.config.vault_path)
    
    def _create_neural_reflex(self, container: 'NexusDIContainer') -> Any:
        """Create Neural Reflex Engine instance"""
        from neural_reflex_engine_v3 import NeuralReflexEngineV3, NeuralReflexEngineV3Config
        
        return NeuralReflexEngineV3(
            vault_core=container.resolve("vault"),
            fts5_extension=container.resolve("fts5"),
            config=NeuralReflexEngineV3Config(
                enable_events=container.config.enable_events
            ),
            event_bus=container.resolve("event_bus")
        )
    
    def _create_auto_updater(self, container: 'NexusDIContainer') -> Any:
        """Create Auto Updater instance"""
        from nexus_auto_updater import AutoUpdater
        
        return AutoUpdater(
            check_interval_days=container.config.update_check_days,
            auto_install=container.config.auto_install_updates
        )
    
    def register(self, name: str, factory: Callable):
        """
        Register a service factory
        
        Args:
            name: Service name
            factory: Factory function that takes container as argument
        """
        self._factories[name] = factory
        logger.debug(f"Registered service: {name}")
    
    def register_singleton(self, name: str, factory: Callable):
        """
        Register a singleton service (created once and reused)
        
        Args:
            name: Service name
            factory: Factory function that takes container as argument
        """
        def singleton_factory(container):
            if name not in self._singletons:
                self._singletons[name] = factory(container)
            return self._singletons[name]
        
        self._factories[name] = singleton_factory
        logger.debug(f"Registered singleton service: {name}")
    
    def resolve(self, name: str) -> Any:
        """
        Resolve a service by name
        
        Args:
            name: Service name
            
        Returns:
            Service instance
            
        Raises:
            KeyError: If service not registered
        """
        if name not in self._factories:
            raise KeyError(f"Service '{name}' not registered")
        
        # Create or return cached instance
        if name not in self._instances:
            self._instances[name] = self._factories[name](self)
            logger.debug(f"Created service instance: {name}")
        
        return self._instances[name]
    
    def has(self, name: str) -> bool:
        """Check if service is registered"""
        return name in self._factories
    
    def get_all_services(self) -> List[str]:
        """Get list of all registered services"""
        return list(self._factories.keys())


class NexusPipeline:
    """
    Processing pipeline with sequential stages
    
    Inspired by spaCy's pipeline architecture where
    data flows through components sequentially.
    """
    
    def __init__(self, name: str, container: NexusDIContainer):
        self.name = name
        self.container = container
        self.event_bus = container.resolve("event_bus")
        self.stages: List[tuple] = []
    
    def add_stage(
        self,
        name: str,
        processor: Callable[[Any, NexusDIContainer], Dict[str, Any]]
    ) -> 'NexusPipeline':
        """
        Add a processing stage to the pipeline
        
        Args:
            name: Stage name
            processor: Function that processes data and returns result dict
            
        Returns:
            Self for method chaining
        """
        self.stages.append((name, processor))
        logger.debug(f"Added pipeline stage: {name}")
        return self
    
    def execute(self, input_data: Any) -> Dict[str, Any]:
        """
        Execute pipeline with input data
        
        Args:
            input_data: Initial data to process
            
        Returns:
            Dictionary with results from all stages
        """
        from driver.core.event_bus import WorkflowStarted, WorkflowCompleted, WorkflowFailed
        
        workflow_id = f"pipeline_{self.name}_{secrets.token_hex(4)}"
        start_time = datetime.now()
        
        result = {
            "workflow_id": workflow_id,
            "pipeline_name": self.name,
            "stages": {},
            "success": False,
            "error": None
        }
        
        try:
            # Emit start event
            self.event_bus.publish(WorkflowStarted(
                workflow_id=workflow_id,
                workflow_name=self.name
            ))
            
            # Execute stages sequentially
            current_data = input_data
            
            for stage_name, processor in self.stages:
                stage_start = datetime.now()
                logger.info(f"[{self.name}] Executing stage: {stage_name}")
                
                try:
                    stage_result = processor(current_data, self.container)
                    stage_elapsed = (datetime.now() - stage_start).total_seconds() * 1000
                    
                    result["stages"][stage_name] = {
                        "success": True,
                        "elapsed_ms": stage_elapsed,
                        **stage_result
                    }
                    
                    # Update current_data for next stage
                    current_data = stage_result.get("output", current_data)
                    
                    logger.info(f"[{self.name}] Stage {stage_name} completed in {stage_elapsed:.2f}ms")
                    
                except Exception as e:
                    stage_elapsed = (datetime.now() - stage_start).total_seconds() * 1000
                    logger.error(f"[{self.name}] Stage {stage_name} failed: {e}")
                    
                    result["stages"][stage_name] = {
                        "success": False,
                        "error": str(e),
                        "elapsed_ms": stage_elapsed
                    }
                    raise
            
            # Calculate total time
            total_elapsed = (datetime.now() - start_time).total_seconds() * 1000
            result["success"] = True
            result["elapsed_ms"] = total_elapsed
            result["output"] = current_data
            
            # Emit completion event
            self.event_bus.publish(WorkflowCompleted(
                workflow_id=workflow_id,
                result=result
            ))
            
            logger.info(f"[{self.name}] Pipeline completed successfully in {total_elapsed:.2f}ms")
            return result
            
        except Exception as e:
            total_elapsed = (datetime.now() - start_time).total_seconds() * 1000
            result["error"] = str(e)
            result["elapsed_ms"] = total_elapsed
            
            # Emit failure event
            self.event_bus.publish(WorkflowFailed(
                workflow_id=workflow_id,
                error=str(e)
            ))
            
            logger.error(f"[{self.name}] Pipeline failed after {total_elapsed:.2f}ms: {e}")
            return result


class NexusOrchestrator:
    """
    Central orchestrator for Nexus Driver
    
    Coordinates all components through:
    - Dependency Injection Container
    - Event Bus for async communication
    - Processing Pipelines for workflows
    - Auto-update mechanism
    """
    
    def __init__(self, config: NexusConfig):
        self.config = config
        self._setup_logging()
        
        # Initialize core systems
        self.container = NexusDIContainer(config)
        self.event_bus = self.container.resolve("event_bus")
        
        # Start auto-updater if enabled
        if config.enable_auto_update:
            self.auto_updater = self.container.resolve("auto_updater")
            self.auto_updater.start()
        
        logger.info("NexusOrchestrator initialized")
    
    def _setup_logging(self):
        """Configure logging"""
        log_config = {
            'level': getattr(logging, self.config.log_level),
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        }
        
        if self.config.log_file:
            log_config['filename'] = str(self.config.log_file)
        
        logging.basicConfig(**log_config)
    
    # Pipeline Factories
    
    def create_ingest_pipeline(self) -> NexusPipeline:
        """Create document ingestion pipeline"""
        return (NexusPipeline("ingest", self.container)
            .add_stage("parse", self._stage_parse_document)
            .add_stage("validate", self._stage_validate_rules)
            .add_stage("extract", self._stage_extract_entities)
            .add_stage("store", self._stage_store_vault)
            .add_stage("index", self._stage_index_fts5)
            .add_stage("graph", self._stage_build_graph)
        )
    
    def create_search_pipeline(self) -> NexusPipeline:
        """Create search pipeline"""
        return (NexusPipeline("search", self.container)
            .add_stage("parse_query", self._stage_parse_query)
            .add_stage("fts5_search", self._stage_search_fts5)
            .add_stage("semantic_search", self._stage_search_semantic)
            .add_stage("merge_results", self._stage_merge_results)
            .add_stage("rank_results", self._stage_rank_results)
        )
    
    def create_scan_pipeline(self) -> NexusPipeline:
        """Create file system scan pipeline"""
        return (NexusPipeline("scan", self.container)
            .add_stage("scan_files", self._stage_scan_files)
            .add_stage("classify_files", self._stage_classify_files)
            .add_stage("analyze_folders", self._stage_analyze_folders)
            .add_stage("detect_patterns", self._stage_detect_patterns)
            .add_stage("save_metadata", self._stage_save_metadata)
        )
    
    # Pipeline Stages
    
    def _stage_parse_document(self, data: Dict, container: NexusDIContainer) -> Dict:
        """Parse document stage"""
        graphify = container.resolve("graphify")
        doc_path = Path(data.get("document_path"))
        
        parsed_doc = graphify.import_document(doc_path)
        
        return {
            "output": parsed_doc,
            "document_id": parsed_doc.document_id if parsed_doc else None,
            "section_count": len(parsed_doc.sections) if parsed_doc else 0
        }
    
    def _stage_validate_rules(self, data: Any, container: NexusDIContainer) -> Dict:
        """Validate against rules stage"""
        rules = container.resolve("rules")
        
        violations = rules.validate_against_rules(
            content=data.content if hasattr(data, 'content') else str(data)
        )
        
        return {
            "output": data,
            "violations": violations,
            "violation_count": len(violations)
        }
    
    def _stage_extract_entities(self, data: Any, container: NexusDIContainer) -> Dict:
        """Extract entities stage"""
        # Entity extraction done by graphify
        return {
            "output": data,
            "entities_extracted": True
        }
    
    def _stage_store_vault(self, data: Any, container: NexusDIContainer) -> Dict:
        """Store in vault stage"""
        vault = container.resolve("vault")
        
        # Convert parsed document to vault entry
        from vault_core import VaultEntry, VaultEntryType
        
        entry = VaultEntry(
            id=data.document_id,
            type=VaultEntryType.DOCUMENT,
            title=data.title if hasattr(data, 'title') else "Untitled",
            content=data.content if hasattr(data, 'content') else str(data),
            embedding=[],
            tags=data.tags if hasattr(data, 'tags') else []
        )
        
        success = vault.store(entry)
        
        return {
            "output": entry.id,
            "stored": success,
            "entry_id": entry.id
        }
    
    def _stage_index_fts5(self, data: Any, container: NexusDIContainer) -> Dict:
        """Index with FTS5 stage"""
        # FTS5 indexing happens automatically via events
        return {
            "output": data,
            "indexed": True
        }
    
    def _stage_build_graph(self, data: Any, container: NexusDIContainer) -> Dict:
        """Build graph relationships stage"""
        # Graph building happens automatically via events
        return {
            "output": data,
            "graph_updated": True
        }
    
    def _stage_parse_query(self, data: Dict, container: NexusDIContainer) -> Dict:
        """Parse query stage"""
        query = data.get("query", "")
        
        return {
            "output": {"query": query, "parsed": True},
            "query_length": len(query)
        }
    
    def _stage_search_fts5(self, data: Dict, container: NexusDIContainer) -> Dict:
        """FTS5 search stage"""
        fts5 = container.resolve("fts5")
        query = data.get("query", "")
        
        results = fts5.fulltext_search(query, limit=50)
        
        return {
            "output": {"query": query, "fts5_results": results},
            "result_count": len(results)
        }
    
    def _stage_search_semantic(self, data: Dict, container: NexusDIContainer) -> Dict:
        """Semantic search stage"""
        neural = container.resolve("neural_reflex")
        query = data.get("query", "")
        
        response = neural.trigger_reflex(query, timeout_ms=1000)
        
        return {
            "output": {
                **data,
                "semantic_results": response.semantic_results
            },
            "semantic_count": len(response.semantic_results)
        }
    
    def _stage_merge_results(self, data: Dict, container: NexusDIContainer) -> Dict:
        """Merge search results stage"""
        fts5_results = data.get("fts5_results", [])
        semantic_results = data.get("semantic_results", [])
        
        # Simple merge (deduplicate by entry_id)
        seen = set()
        merged = []
        
        for result in fts5_results + semantic_results:
            entry_id = result.get("entry_id") or result.get("id")
            if entry_id and entry_id not in seen:
                seen.add(entry_id)
                merged.append(result)
        
        return {
            "output": {"query": data.get("query"), "results": merged},
            "merged_count": len(merged)
        }
    
    def _stage_rank_results(self, data: Dict, container: NexusDIContainer) -> Dict:
        """Rank results stage"""
        results = data.get("results", [])
        
        # Simple ranking by score
        ranked = sorted(
            results,
            key=lambda r: r.get("score", 0),
            reverse=True
        )
        
        return {
            "output": {"query": data.get("query"), "results": ranked},
            "result_count": len(ranked)
        }
    
    def _stage_scan_files(self, data: Dict, container: NexusDIContainer) -> Dict:
        """Scan files stage"""
        mapper = container.resolve("file_mapper")
        
        files = mapper.scan_project()
        
        return {
            "output": files,
            "file_count": len(files)
        }
    
    def _stage_classify_files(self, data: Dict, container: NexusDIContainer) -> Dict:
        """Classify files stage"""
        # Classification done during scan
        return {
            "output": data,
            "classified": True
        }
    
    def _stage_analyze_folders(self, data: Dict, container: NexusDIContainer) -> Dict:
        """Analyze folders stage"""
        # Folder analysis done during scan
        return {
            "output": data,
            "analyzed": True
        }
    
    def _stage_detect_patterns(self, data: Dict, container: NexusDIContainer) -> Dict:
        """Detect patterns stage"""
        # Pattern detection done during scan
        return {
            "output": data,
            "patterns_detected": True
        }
    
    def _stage_save_metadata(self, data: Dict, container: NexusDIContainer) -> Dict:
        """Save metadata stage"""
        mapper = container.resolve("file_mapper")
        mapper.save_to_vault()
        
        return {
            "output": data,
            "metadata_saved": True
        }
    
    # High-level operations
    
    def ingest_document(self, doc_path: Path) -> Dict[str, Any]:
        """
        Ingest a document through the full pipeline
        
        Args:
            doc_path: Path to document
            
        Returns:
            Pipeline execution result
        """
        pipeline = self.create_ingest_pipeline()
        return pipeline.execute({"document_path": doc_path})
    
    def search(self, query: str) -> Dict[str, Any]:
        """
        Execute unified search
        
        Args:
            query: Search query
            
        Returns:
            Search results with metadata
        """
        pipeline = self.create_search_pipeline()
        result = pipeline.execute({"query": query})
        
        return {
            "query": query,
            "results": result.get("output", {}).get("results", []),
            "metadata": {
                "pipeline_id": result["workflow_id"],
                "elapsed_ms": result.get("elapsed_ms", 0),
                "stages": result.get("stages", {})
            }
        }
    
    def scan_project(self) -> Dict[str, Any]:
        """
        Scan project file system
        
        Returns:
            Scan results with metadata
        """
        pipeline = self.create_scan_pipeline()
        return pipeline.execute({})
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics"""
        stats = {
            "orchestrator": {
                "config": {
                    "project_root": str(self.config.project_root),
                    "vault_path": str(self.config.vault_path),
                    "events_enabled": self.config.enable_events,
                    "auto_update_enabled": self.config.enable_auto_update
                },
                "services": self.container.get_all_services()
            }
        }
        
        # Get stats from each service
        for service_name in self.container.get_all_services():
            try:
                service = self.container.resolve(service_name)
                if hasattr(service, 'get_stats'):
                    stats[service_name] = service.get_stats()
            except Exception as e:
                logger.warning(f"Could not get stats from {service_name}: {e}")
        
        return stats
    
    def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down NexusOrchestrator...")
        
        # Stop auto-updater
        if hasattr(self, 'auto_updater'):
            self.auto_updater.stop()
        
        # Stop event bus
        self.event_bus.stop_async_processing()
        
        # Close vault connections
        try:
            vault = self.container.resolve("vault")
            vault.shutdown()
        except Exception as e:
            logger.warning(f"Error closing vault: {e}")
        
        logger.info("NexusOrchestrator shutdown complete")


# Factory function
def create_nexus_orchestrator(
    project_root: Path,
    vault_path: Optional[Path] = None,
    **kwargs
) -> NexusOrchestrator:
    """
    Create NexusOrchestrator with default config
    
    Args:
        project_root: Project root directory
        vault_path: Path to vault database (default: project_root/.nexus/vault.db)
        **kwargs: Additional config options
        
    Returns:
        Configured NexusOrchestrator instance
    """
    if vault_path is None:
        vault_path = project_root / ".nexus" / "vault.db"
    
    vault_path.parent.mkdir(parents=True, exist_ok=True)
    
    config = NexusConfig(
        project_root=project_root,
        vault_path=vault_path,
        **kwargs
    )
    
    return NexusOrchestrator(config)


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Create orchestrator
    orchestrator = create_nexus_orchestrator(
        project_root=Path("/path/to/project"),
        enable_auto_update=True,
        update_check_days=15
    )
    
    try:
        # Ingest document
        result = orchestrator.ingest_document(Path("document.md"))
        print(f"Ingest result: {result['success']}")
        
        # Search
        search_results = orchestrator.search("query text")
        print(f"Found {len(search_results['results'])} results")
        
        # Get stats
        stats = orchestrator.get_stats()
        print(f"System stats: {stats}")
        
    finally:
        orchestrator.shutdown()
