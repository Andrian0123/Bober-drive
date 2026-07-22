"""
Core foundation for Nexus Driver v3
Unified event-driven architecture with DI container and orchestration.
"""

from .event_bus import (
    Event,
    EventBus,
    EventBusConfig,
    # Workflow events
    WorkflowEvent,
    WorkflowStarted,
    WorkflowCompleted,
    WorkflowFailed,
    WorkflowCancelled,
    # Document events
    DocumentEvent,
    DocumentParsed,
    DocumentValidated,
    DocumentStoredEvent,
    DocumentError,
    # Vault events
    VaultEvent,
    EntryCreated,
    EntryUpdated,
    EntryDeleted,
    EntryVersioned,
    # Search events
    SearchEvent,
    SearchTriggered,
    SearchCompleted,
    SearchFailed,
    # Graph events
    GraphEvent,
    RelationshipCreated,
    GraphRecomputed,
    GraphOptimized,
)

from .dependency_injection import (
    DIContainer,
    DIScope,
    ServiceNotFoundError,
)

from .orchestrator import (
    Command,
    CommandResult,
    Orchestrator,
    ExecutionPlan,
    ExecutionStage,
)

__all__ = [
    # Event Bus
    'Event',
    'EventBus',
    'EventBusConfig',
    'WorkflowEvent',
    'WorkflowStarted',
    'WorkflowCompleted',
    'WorkflowFailed',
    'WorkflowCancelled',
    'DocumentEvent',
    'DocumentParsed',
    'DocumentValidated',
    'DocumentStoredEvent',
    'DocumentError',
    'VaultEvent',
    'EntryCreated',
    'EntryUpdated',
    'EntryDeleted',
    'EntryVersioned',
    'SearchEvent',
    'SearchTriggered',
    'SearchCompleted',
    'SearchFailed',
    'GraphEvent',
    'RelationshipCreated',
    'GraphRecomputed',
    'GraphOptimized',
    # DI Container
    'DIContainer',
    'DIScope',
    'ServiceNotFoundError',
    # Orchestrator
    'Command',
    'CommandResult',
    'Orchestrator',
    'ExecutionPlan',
    'ExecutionStage',
]
