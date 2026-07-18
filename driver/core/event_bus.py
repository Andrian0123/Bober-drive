#!/usr/bin/env python3
"""
Event Bus - Central pub/sub system for Nexus Driver v3
Enables loose coupling between components through event-driven architecture.
"""

import asyncio
import logging
import uuid
from typing import Dict, List, Callable, Type, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import json
from queue import Queue
import threading

logger = logging.getLogger(__name__)


# ============================================================================
# Event Base Classes and Hierarchy
# ============================================================================

class Event:
    """Base class for all events in the system"""
    
    def __init__(self):
        self.event_id: str = str(uuid.uuid4())
        self.timestamp: str = datetime.utcnow().isoformat()
        self.trace_id: Optional[str] = None
        self.source: Optional[str] = None
        self.metadata: Dict[str, Any] = {}
    
    @property
    def event_type(self) -> str:
        """Get event type name"""
        return self.__class__.__name__
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'timestamp': self.timestamp,
            'trace_id': self.trace_id,
            'source': self.source,
            'metadata': self.metadata
        }
    
    def to_json(self) -> str:
        """Convert to JSON"""
        return json.dumps(self.to_dict(), default=str)


# Workflow Events
class WorkflowEvent(Event):
    """Base class for workflow events"""
    pass


class WorkflowStarted(WorkflowEvent):
    """Emitted when a workflow begins"""
    def __init__(self, workflow_id: str, workflow_name: str, **kwargs):
        super().__init__()
        self.workflow_id = workflow_id
        self.workflow_name = workflow_name
        self.metadata.update(kwargs)


class WorkflowCompleted(WorkflowEvent):
    """Emitted when a workflow completes successfully"""
    def __init__(self, workflow_id: str, result: Any = None, **kwargs):
        super().__init__()
        self.workflow_id = workflow_id
        self.result = result
        self.metadata.update(kwargs)


class WorkflowFailed(WorkflowEvent):
    """Emitted when a workflow fails"""
    def __init__(self, workflow_id: str, error: str, error_type: str = "unknown", **kwargs):
        super().__init__()
        self.workflow_id = workflow_id
        self.error = error
        self.error_type = error_type
        self.metadata.update(kwargs)


class WorkflowCancelled(WorkflowEvent):
    """Emitted when a workflow is cancelled"""
    def __init__(self, workflow_id: str, reason: str = "user_cancelled", **kwargs):
        super().__init__()
        self.workflow_id = workflow_id
        self.reason = reason
        self.metadata.update(kwargs)


# Document Events
class DocumentEvent(Event):
    """Base class for document events"""
    pass


class DocumentImportRequested(DocumentEvent):
    """Emitted when document import is requested"""
    def __init__(self, file_path: str, **kwargs):
        super().__init__()
        self.file_path = file_path
        self.metadata.update(kwargs)


class DocumentFormatDetected(DocumentEvent):
    """Emitted when document format is detected"""
    def __init__(self, file_path: str, format: str, **kwargs):
        super().__init__()
        self.file_path = file_path
        self.format = format
        self.metadata.update(kwargs)


class DocumentParsed(DocumentEvent):
    """Emitted when a document is parsed"""
    def __init__(self, document_id: str, format: str, section_count: int, **kwargs):
        super().__init__()
        self.document_id = document_id
        self.format = format
        self.section_count = section_count
        self.metadata.update(kwargs)


class DocumentSegmented(DocumentEvent):
    """Emitted when document sections are available"""
    def __init__(self, document_id: str, section_count: int, **kwargs):
        super().__init__()
        self.document_id = document_id
        self.section_count = section_count
        self.metadata.update(kwargs)


class EntitiesExtracted(DocumentEvent):
    """Emitted when document entities and keywords are extracted"""
    def __init__(self, document_id: str, entity_count: int, keyword_count: int, **kwargs):
        super().__init__()
        self.document_id = document_id
        self.entity_count = entity_count
        self.keyword_count = keyword_count
        self.metadata.update(kwargs)


class DocumentValidated(DocumentEvent):
    """Emitted when a document passes validation"""
    def __init__(self, document_id: str, violations: List[str] = None, **kwargs):
        super().__init__()
        self.document_id = document_id
        self.violations = violations or []
        self.metadata.update(kwargs)


class DocumentStoredEvent(DocumentEvent):
    """Emitted when a document is stored in vault"""
    def __init__(self, document_id: str, entry_id: str, size_bytes: int, **kwargs):
        super().__init__()
        self.document_id = document_id
        self.entry_id = entry_id
        self.size_bytes = size_bytes
        self.metadata.update(kwargs)


class DocumentError(DocumentEvent):
    """Emitted when document processing fails"""
    def __init__(self, document_id: str, error: str, stage: str, **kwargs):
        super().__init__()
        self.document_id = document_id
        self.error = error
        self.stage = stage
        self.metadata.update(kwargs)


# Vault Events
class VaultEvent(Event):
    """Base class for vault events"""
    pass


class EntryCreated(VaultEvent):
    """Emitted when an entry is created in vault"""
    def __init__(self, entry_id: str, entry_type: str, title: str, **kwargs):
        super().__init__()
        self.entry_id = entry_id
        self.entry_type = entry_type
        self.title = title
        self.metadata.update(kwargs)


class EntryUpdated(VaultEvent):
    """Emitted when an entry is updated"""
    def __init__(self, entry_id: str, version: int, changes: Dict[str, Any], **kwargs):
        super().__init__()
        self.entry_id = entry_id
        self.version = version
        self.changes = changes
        self.metadata.update(kwargs)


class EntryDeleted(VaultEvent):
    """Emitted when an entry is deleted"""
    def __init__(self, entry_id: str, soft_delete: bool = True, **kwargs):
        super().__init__()
        self.entry_id = entry_id
        self.soft_delete = soft_delete
        self.metadata.update(kwargs)


class EntryVersioned(VaultEvent):
    """Emitted when an entry version is created"""
    def __init__(self, entry_id: str, version_number: int, change_summary: str, **kwargs):
        super().__init__()
        self.entry_id = entry_id
        self.version_number = version_number
        self.change_summary = change_summary
        self.metadata.update(kwargs)


# Search Events
class SearchEvent(Event):
    """Base class for search events"""
    pass


class SearchTriggered(SearchEvent):
    """Emitted when a search is initiated"""
    def __init__(self, query: str, search_type: str = "general", **kwargs):
        super().__init__()
        self.query = query
        self.search_type = search_type
        self.metadata.update(kwargs)


class SearchCompleted(SearchEvent):
    """Emitted when search completes"""
    def __init__(self, query: str, result_count: int, elapsed_ms: float, **kwargs):
        super().__init__()
        self.query = query
        self.result_count = result_count
        self.elapsed_ms = elapsed_ms
        self.metadata.update(kwargs)


class SearchFailed(SearchEvent):
    """Emitted when search fails"""
    def __init__(self, query: str, error: str, **kwargs):
        super().__init__()
        self.query = query
        self.error = error
        self.metadata.update(kwargs)


# Graph Events
class GraphEvent(Event):
    """Base class for graph events"""
    pass


class RelationshipCreated(GraphEvent):
    """Emitted when a relationship is created"""
    def __init__(self, source_id: str, target_id: str, rel_type: str, weight: float = 1.0, **kwargs):
        super().__init__()
        self.source_id = source_id
        self.target_id = target_id
        self.rel_type = rel_type
        self.weight = weight
        self.metadata.update(kwargs)


class GraphRecomputed(GraphEvent):
    """Emitted when the graph is recomputed"""
    def __init__(self, nodes_count: int, edges_count: int, elapsed_ms: float, **kwargs):
        super().__init__()
        self.nodes_count = nodes_count
        self.edges_count = edges_count
        self.elapsed_ms = elapsed_ms
        self.metadata.update(kwargs)


class GraphOptimized(GraphEvent):
    """Emitted when graph optimizations are applied"""
    def __init__(self, optimization_type: str, items_optimized: int, **kwargs):
        super().__init__()
        self.optimization_type = optimization_type
        self.items_optimized = items_optimized
        self.metadata.update(kwargs)


# ============================================================================
# Event Bus Implementation
# ============================================================================

@dataclass
class EventBusConfig:
    """Configuration for EventBus"""
    async_mode: bool = True
    max_queue_size: int = 10000
    worker_threads: int = 4
    enable_history: bool = True
    history_size: int = 1000


class EventBus:
    """Central event pub/sub system"""
    
    def __init__(self, config: Optional[EventBusConfig] = None):
        self.config = config or EventBusConfig()
        
        # Handler registry: event_type -> [handlers]
        self._handlers: Dict[Type[Event], List[tuple]] = {}
        
        # Subscriptions for tracking
        self._subscriptions: Dict[str, tuple] = {}
        
        # Event history for debugging
        self._history: List[Event] = []
        self._history_lock = threading.Lock()
        
        # Event queue for async processing
        self._event_queue: Queue = Queue(maxsize=self.config.max_queue_size)
        
        # Worker threads
        self._workers: List[threading.Thread] = []
        self._running = False
        
        # Statistics
        self._stats = {
            'events_published': 0,
            'events_processed': 0,
            'errors': 0,
            'handlers_called': 0
        }
        self._stats_lock = threading.Lock()
        
        logger.info(f"EventBus initialized with config: async={self.config.async_mode}")
    
    def subscribe(self, event_type: Type[Event], handler: Callable, 
                  error_handler: Optional[Callable] = None) -> str:
        """
        Subscribe to events of a specific type.
        
        Args:
            event_type: Event class to subscribe to
            handler: Callable that receives event
            error_handler: Optional handler for errors
            
        Returns:
            subscription_id for later unsubscribe
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        
        subscription_id = str(uuid.uuid4())
        handler_info = (handler, error_handler, subscription_id)
        
        self._handlers[event_type].append(handler_info)
        self._subscriptions[subscription_id] = (event_type, handler_info)
        
        logger.debug(f"Subscribed to {event_type.__name__}: {subscription_id}")
        return subscription_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """Remove subscription"""
        if subscription_id not in self._subscriptions:
            return False
        
        event_type, handler_info = self._subscriptions[subscription_id]
        if handler_info in self._handlers.get(event_type, []):
            self._handlers[event_type].remove(handler_info)
        del self._subscriptions[subscription_id]
        
        logger.debug(f"Unsubscribed: {subscription_id}")
        return True
    
    def publish(self, event: Event, async_mode: Optional[bool] = None, 
                wait_for_completion: bool = False) -> None:
        """
        Publish an event to all subscribers.
        
        Args:
            event: Event to publish
            async_mode: Override default async mode
            wait_for_completion: Wait for all handlers (sync mode only)
        """
        async_mode = async_mode if async_mode is not None else self.config.async_mode
        
        with self._stats_lock:
            self._stats['events_published'] += 1
        
        if self.config.enable_history:
            with self._history_lock:
                self._history.append(event)
                if len(self._history) > self.config.history_size:
                    self._history.pop(0)
        
        if async_mode and self._running:
            try:
                self._event_queue.put((event, None), block=False)
            except Exception as e:
                logger.error(f"Failed to queue event: {e}")
                self._call_handlers_sync(event)
        else:
            self._call_handlers_sync(event)
    
    def publish_batch(self, events: List[Event], async_mode: Optional[bool] = None) -> None:
        """Publish multiple events"""
        for event in events:
            self.publish(event, async_mode=async_mode)
    
    def _call_handlers_sync(self, event: Event) -> None:
        """Call handlers synchronously"""
        event_type = type(event)
        
        # Get handlers for this event type and parent types
        handlers = self._get_handlers_for_event(event_type)
        
        for handler, error_handler, sub_id in handlers:
            try:
                with self._stats_lock:
                    self._stats['handlers_called'] += 1
                
                handler(event)
                
                with self._stats_lock:
                    self._stats['events_processed'] += 1
                    
            except Exception as e:
                logger.error(f"Handler error: {e}", exc_info=True)
                with self._stats_lock:
                    self._stats['errors'] += 1
                
                if error_handler:
                    try:
                        error_handler(event, e)
                    except Exception as e2:
                        logger.error(f"Error handler failed: {e2}")
    
    def _get_handlers_for_event(self, event_type: Type[Event]) -> List[tuple]:
        """Get handlers for event type including inherited types"""
        handlers = []
        
        # Get direct handlers
        if event_type in self._handlers:
            handlers.extend(self._handlers[event_type])
        
        # Get parent class handlers
        for base_type in event_type.__mro__[1:]:
            if base_type in self._handlers and base_type != Event:
                handlers.extend(self._handlers[base_type])
        
        return handlers
    
    def clear_handlers(self, event_type: Optional[Type[Event]] = None) -> None:
        """Clear all or specific event handlers"""
        if event_type is None:
            self._handlers.clear()
            self._subscriptions.clear()
            logger.info("Cleared all handlers")
        else:
            if event_type in self._handlers:
                self._handlers[event_type].clear()
                logger.info(f"Cleared handlers for {event_type.__name__}")
    
    def get_subscription_count(self, event_type: Optional[Type[Event]] = None) -> int:
        """Get number of subscriptions"""
        if event_type is None:
            return len(self._subscriptions)
        else:
            return len(self._handlers.get(event_type, []))
    
    def get_event_history(self, event_type: Optional[Type[Event]] = None, 
                         limit: int = 100) -> List[Event]:
        """Get recent event history for debugging"""
        with self._history_lock:
            if event_type is None:
                return self._history[-limit:]
            else:
                return [e for e in self._history[-limit:] if isinstance(e, event_type)]
    
    def start_async_processing(self) -> None:
        """Start worker threads for async event processing"""
        if self._running:
            return
        
        self._running = True
        for i in range(self.config.worker_threads):
            worker = threading.Thread(target=self._worker_loop, daemon=True)
            worker.start()
            self._workers.append(worker)
        
        logger.info(f"Started {self.config.worker_threads} worker threads")
    
    def stop_async_processing(self) -> None:
        """Stop worker threads"""
        self._running = False
        
        # Wait for threads to finish
        for worker in self._workers:
            worker.join(timeout=2.0)
        
        self._workers.clear()
        logger.info("Stopped async processing")
    
    def _worker_loop(self) -> None:
        """Worker thread loop"""
        while self._running:
            try:
                event, _ = self._event_queue.get(timeout=1.0)
                self._call_handlers_sync(event)
            except Exception:
                pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics"""
        with self._stats_lock:
            return self._stats.copy()
    
    def reset_stats(self) -> None:
        """Reset statistics"""
        with self._stats_lock:
            for key in self._stats:
                self._stats[key] = 0
