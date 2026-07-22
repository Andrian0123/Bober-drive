#!/usr/bin/env python3
"""
Orchestrator - Central coordinator for workflow execution
Manages command processing, execution planning, and error handling.
"""

import logging
import uuid
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from .event_bus import (
    Event, EventBus,
    WorkflowStarted, WorkflowCompleted, WorkflowFailed, WorkflowCancelled
)
from .dependency_injection import DIContainer

logger = logging.getLogger(__name__)


class CommandType(str, Enum):
    """Types of commands"""
    INGEST_DOCUMENT = "ingest_document"
    SEARCH = "search"
    VALIDATE = "validate"
    EXTRACT_ENTITIES = "extract_entities"
    BUILD_GRAPH = "build_graph"
    CUSTOM = "custom"


class ExecutionStatus(str, Enum):
    """Execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Command:
    """Represents a command to execute"""
    command_type: CommandType
    payload: Dict[str, Any]
    command_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    priority: int = 0  # Higher priority = execute first


@dataclass
class CommandResult:
    """Result of command execution"""
    command_id: str
    status: ExecutionStatus
    result: Any = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    elapsed_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionStage:
    """Represents a stage in execution plan"""
    stage_id: str
    name: str
    executor: Callable
    dependencies: List[str] = field(default_factory=list)
    timeout_ms: int = 5000
    retry_count: int = 0
    fallback_executor: Optional[Callable] = None


@dataclass
class ExecutionPlan:
    """Plan for executing a workflow"""
    plan_id: str
    stages: List[ExecutionStage] = field(default_factory=list)
    timeout_ms: int = 30000
    parallel: bool = False
    
    def add_stage(self, stage: ExecutionStage) -> None:
        """Add stage to plan"""
        self.stages.append(stage)


class RecoveryStrategy(str, Enum):
    """Error recovery strategies"""
    RETRY_EXPONENTIAL = "retry_exponential"
    CIRCUIT_BREAKER = "circuit_breaker"
    FALLBACK = "fallback"
    QUEUE_AND_RETRY = "queue_and_retry"
    NOTIFY_ADMIN = "notify_admin"


class Orchestrator:
    """Central orchestrator for workflow execution"""
    
    def __init__(self, event_bus: EventBus, di_container: DIContainer):
        """
        Initialize orchestrator.
        
        Args:
            event_bus: Central event bus for coordination
            di_container: DI container for resolving services
        """
        self.event_bus = event_bus
        self.container = di_container
        
        # Running workflows
        self._workflows: Dict[str, Dict[str, Any]] = {}
        self._workflow_lock = __import__('threading').Lock()
        
        # Statistics
        self._stats = {
            'total_commands': 0,
            'successful_commands': 0,
            'failed_commands': 0,
            'avg_latency_ms': 0.0,
            'total_latency_ms': 0.0
        }
        
        logger.info("Orchestrator initialized")
    
    def process_command(self, command: Command) -> CommandResult:
        """
        Process a command.
        
        Workflow:
        1. Validate command
        2. Emit WorkflowStarted
        3. Execute stages
        4. Emit WorkflowCompleted/Failed
        5. Return result
        
        Args:
            command: Command to process
            
        Returns:
            CommandResult
        """
        start_time = time.time()
        result = CommandResult(
            command_id=command.command_id,
            status=ExecutionStatus.PENDING
        )
        
        try:
            # Validate
            self._validate_command(command)
            
            # Emit start event
            workflow_started = WorkflowStarted(
                workflow_id=command.command_id,
                workflow_name=command.command_type.value,
                trace_id=command.trace_id
            )
            workflow_started.source = 'Orchestrator'
            self.event_bus.publish(workflow_started, async_mode=False)
            
            # Build execution plan
            plan = self._build_execution_plan(command)
            
            # Execute plan
            result.result = self._execute_plan(plan, command)
            result.status = ExecutionStatus.COMPLETED
            
            # Emit completion event
            elapsed_ms = (time.time() - start_time) * 1000
            workflow_completed = WorkflowCompleted(
                workflow_id=command.command_id,
                result=result.result,
                elapsed_ms=elapsed_ms
            )
            workflow_completed.source = 'Orchestrator'
            self.event_bus.publish(workflow_completed, async_mode=False)
            
        except Exception as e:
            logger.error(f"Command execution failed: {e}", exc_info=True)
            result.status = ExecutionStatus.FAILED
            result.error = str(e)
            result.error_type = type(e).__name__
            
            # Emit failure event
            elapsed_ms = (time.time() - start_time) * 1000
            workflow_failed = WorkflowFailed(
                workflow_id=command.command_id,
                error=str(e),
                error_type=type(e).__name__,
                elapsed_ms=elapsed_ms
            )
            workflow_failed.source = 'Orchestrator'
            self.event_bus.publish(workflow_failed, async_mode=False)
        
        # Update stats
        elapsed_ms = (time.time() - start_time) * 1000
        result.elapsed_ms = elapsed_ms
        self._update_stats(result)
        
        return result
    
    def _validate_command(self, command: Command) -> None:
        """Validate command structure"""
        if not command.command_type:
            raise ValueError("Command type is required")
        if not command.payload:
            raise ValueError("Command payload is required")
    
    def _build_execution_plan(self, command: Command) -> ExecutionPlan:
        """
        Build execution plan based on command type.
        
        For now, returns a simple plan. Can be extended with
        strategy pattern or command builders.
        """
        plan = ExecutionPlan(plan_id=str(uuid.uuid4()))
        
        # Delegate to command-specific handlers
        if command.command_type == CommandType.INGEST_DOCUMENT:
            self._plan_ingestion(plan, command)
        elif command.command_type == CommandType.SEARCH:
            self._plan_search(plan, command)
        else:
            self._plan_generic(plan, command)
        
        return plan
    
    def _plan_ingestion(self, plan: ExecutionPlan, command: Command) -> None:
        """Plan document ingestion workflow"""
        plan.stages = [
            ExecutionStage(
                stage_id="1",
                name="parse",
                executor=lambda: self._execute_parsing(command),
            ),
            ExecutionStage(
                stage_id="2",
                name="validate",
                executor=lambda: self._execute_validation(command),
                dependencies=["1"]
            ),
            ExecutionStage(
                stage_id="3",
                name="store",
                executor=lambda: self._execute_storage(command),
                dependencies=["2"]
            ),
        ]
    
    def _plan_search(self, plan: ExecutionPlan, command: Command) -> None:
        """Plan search workflow"""
        plan.stages = [
            ExecutionStage(
                stage_id="1",
                name="search",
                executor=lambda: self._execute_search(command),
            ),
        ]
    
    def _plan_generic(self, plan: ExecutionPlan, command: Command) -> None:
        """Plan generic workflow"""
        plan.stages = [
            ExecutionStage(
                stage_id="1",
                name="execute",
                executor=lambda: self._execute_generic(command),
            ),
        ]
    
    def _execute_plan(self, plan: ExecutionPlan, command: Command) -> Any:
        """Execute all stages in plan"""
        results = {}
        
        for stage in plan.stages:
            try:
                logger.info(f"Executing stage: {stage.name}")
                results[stage.stage_id] = stage.executor()
                logger.info(f"Stage completed: {stage.name}")
            except Exception as e:
                logger.error(f"Stage failed: {stage.name}: {e}")
                if stage.fallback_executor:
                    try:
                        results[stage.stage_id] = stage.fallback_executor()
                    except Exception as e2:
                        logger.error(f"Fallback also failed: {e2}")
                        raise
                else:
                    raise
        
        return results
    
    def _execute_parsing(self, command: Command) -> Dict[str, Any]:
        """Execute parsing stage"""
        # Placeholder - will be implemented when graphify integration complete
        return {"status": "parsed", "sections": []}
    
    def _execute_validation(self, command: Command) -> Dict[str, Any]:
        """Execute validation stage"""
        # Placeholder - will be implemented when rules integration complete
        return {"status": "validated", "violations": []}
    
    def _execute_storage(self, command: Command) -> Dict[str, Any]:
        """Execute storage stage"""
        # Placeholder - will be implemented when vault integration complete
        return {"status": "stored", "entry_id": str(uuid.uuid4())}
    
    def _execute_search(self, command: Command) -> Dict[str, Any]:
        """Execute search stage"""
        # Placeholder - will be implemented when neural reflex integration complete
        return {"status": "searched", "results": []}
    
    def _execute_generic(self, command: Command) -> Dict[str, Any]:
        """Execute generic command"""
        return {"status": "executed", "payload": command.payload}
    
    def _update_stats(self, result: CommandResult) -> None:
        """Update orchestrator statistics"""
        self._stats['total_commands'] += 1
        self._stats['total_latency_ms'] += result.elapsed_ms
        self._stats['avg_latency_ms'] = (
            self._stats['total_latency_ms'] / self._stats['total_commands']
        )
        
        if result.status == ExecutionStatus.COMPLETED:
            self._stats['successful_commands'] += 1
        else:
            self._stats['failed_commands'] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics"""
        return self._stats.copy()
    
    def reset_stats(self) -> None:
        """Reset statistics"""
        for key in self._stats:
            if isinstance(self._stats[key], int):
                self._stats[key] = 0
            else:
                self._stats[key] = 0.0
