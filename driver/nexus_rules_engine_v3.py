#!/usr/bin/env python3
"""
RulesEngineV3 - Phase 4 Implementation
Event-driven rules engine with lifecycle event emission, local subscribers, 
history tracking, and backward compatibility with ProjectRulesEngine.

Architecture:
- Inherits from ProjectRulesEngine for 100% API compatibility
- Emits events: RulesScanRequested, RulesLoaded, RuleParsed, RuleViolationDetected, RulesValidationCompleted, RulesValidationFailed
- Local subscribers (on_rules_loaded, on_validation_completed, on_validation_failed)
- Rule scan history (max 1000 items)
- Stats: total rules, by level/category, avg validation time, success rate
- Config: enable_events, async_event_processing, track_scan_history
"""

import re
import json
import logging
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
from uuid import uuid4

from nexus_project_rules import (
    ProjectRulesEngine, 
    ProjectRule, 
    RuleViolation, 
    RuleLevel, 
    RuleCategory
)
from core.event_bus import (
    Event, 
    EventBus,
    DocumentEvent
)

logger = logging.getLogger(__name__)


# ============================================================================
# EVENT DEFINITIONS (RulesEngine-specific lifecycle events)
# ============================================================================

class RulesScanRequested(DocumentEvent):
    """Emitted when rules scan is requested"""
    def __init__(self, scan_id: str, **kwargs):
        super().__init__(**kwargs)
        self.scan_id = scan_id
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({"scan_id": self.scan_id, "timestamp": self.timestamp})
        return d


class RulesLoaded(DocumentEvent):
    """Emitted when rules are successfully loaded"""
    def __init__(self, scan_id: str, rule_count: int, **kwargs):
        super().__init__(**kwargs)
        self.scan_id = scan_id
        self.rule_count = rule_count
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({"scan_id": self.scan_id, "rule_count": self.rule_count, "timestamp": self.timestamp})
        return d


class RuleParsed(DocumentEvent):
    """Emitted when a single rule is parsed"""
    def __init__(self, scan_id: str, rule_id: str, rule_title: str, **kwargs):
        super().__init__(**kwargs)
        self.scan_id = scan_id
        self.rule_id = rule_id
        self.rule_title = rule_title
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "scan_id": self.scan_id, 
            "rule_id": self.rule_id,
            "rule_title": self.rule_title,
            "timestamp": self.timestamp
        })
        return d


class RuleViolationDetected(DocumentEvent):
    """Emitted when a rule violation is detected"""
    def __init__(self, validation_id: str, rule_id: str, rule_title: str, 
                 severity: str, **kwargs):
        super().__init__(**kwargs)
        self.validation_id = validation_id
        self.rule_id = rule_id
        self.rule_title = rule_title
        self.severity = severity  # "error", "warning", "info"
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "validation_id": self.validation_id,
            "rule_id": self.rule_id,
            "rule_title": self.rule_title,
            "severity": self.severity,
            "timestamp": self.timestamp
        })
        return d


class RulesValidationCompleted(DocumentEvent):
    """Emitted when validation completes successfully"""
    def __init__(self, validation_id: str, violation_count: int, 
                 elapsed_ms: float, **kwargs):
        super().__init__(**kwargs)
        self.validation_id = validation_id
        self.violation_count = violation_count
        self.elapsed_ms = elapsed_ms
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "validation_id": self.validation_id,
            "violation_count": self.violation_count,
            "elapsed_ms": self.elapsed_ms,
            "timestamp": self.timestamp
        })
        return d


class RulesValidationFailed(DocumentEvent):
    """Emitted when validation fails"""
    def __init__(self, validation_id: str, error: str, **kwargs):
        super().__init__(**kwargs)
        self.validation_id = validation_id
        self.error = error
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "validation_id": self.validation_id,
            "error": self.error,
            "timestamp": self.timestamp
        })
        return d


# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class RulesEngineV3Config:
    """Configuration for RulesEngineV3"""
    enable_events: bool = True
    async_event_processing: bool = False
    track_scan_history: bool = True
    max_scan_history: int = 1000


# ============================================================================
# RULESENGINE V3 - EVENT-DRIVEN IMPLEMENTATION
# ============================================================================

class RulesEngineV3(ProjectRulesEngine):
    """
    Event-driven Rules Engine with lifecycle events, local subscribers,
    and history tracking. 100% backward compatible with ProjectRulesEngine.
    """

    def __init__(
        self,
        project_root: Path,
        vault_core=None,
        event_bus: Optional[EventBus] = None,
        config: Optional[RulesEngineV3Config] = None
    ):
        """
        Initialize RulesEngineV3
        
        Args:
            project_root: Root path of project
            vault_core: Optional VaultCore instance
            event_bus: Optional EventBus for event publishing
            config: Optional RulesEngineV3Config
        """
        super().__init__(project_root, vault_core)
        
        self.config = config or RulesEngineV3Config()
        self.event_bus = event_bus
        
        # Local subscribers (no EventBus needed)
        self._on_rules_loaded_handlers: Dict[str, Callable] = {}
        self._on_rule_parsed_handlers: Dict[str, Callable] = {}
        self._on_violation_detected_handlers: Dict[str, Callable] = {}
        self._on_validation_completed_handlers: Dict[str, Callable] = {}
        self._on_validation_failed_handlers: Dict[str, Callable] = {}
        
        # History and stats
        self._scan_history: List[Dict[str, Any]] = []
        self._validation_history: List[Dict[str, Any]] = []
        self._history_lock = threading.Lock()
        
        self._stats = {
            "total_scans": 0,
            "successful_scans": 0,
            "failed_scans": 0,
            "total_validations": 0,
            "successful_validations": 0,
            "failed_validations": 0,
            "total_violations_found": 0,
            "avg_scan_duration_ms": 0.0,
            "avg_validation_duration_ms": 0.0,
            "avg_violations_per_validation": 0.0
        }
        self._stats_lock = threading.Lock()
        
        logger.info(f"RulesEngineV3 initialized for {self.project_root}")

    # ========================================================================
    # OVERRIDE: scan_rules() - WITH EVENT EMISSION
    # ========================================================================

    def scan_rules(self) -> Dict[str, ProjectRule]:
        """
        Scan project for rule files and parse them (with event emission)
        
        Returns:
            Dictionary of rule_id -> ProjectRule
        """
        import time
        
        scan_id = str(uuid4())[:8]
        start_time = time.time()
        
        try:
            # Emit RulesScanRequested
            self._emit_scan_requested(scan_id)
            
            # Call parent implementation
            rules = super().scan_rules()
            
            # Track individual rules parsed
            for rule_id, rule in rules.items():
                self._emit_rule_parsed(scan_id, rule_id, rule.title)
            
            elapsed_ms = (time.time() - start_time) * 1000
            
            # Emit RulesLoaded
            self._emit_rules_loaded(scan_id, len(rules), elapsed_ms)
            
            # Track history
            self._track_scan(scan_id, True, len(rules), elapsed_ms)
            
            return rules
            
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            logger.error(f"Rules scan failed: {error_msg}")
            
            # Track failure
            self._track_scan(scan_id, False, 0, elapsed_ms, error=error_msg)
            
            # Emit failure (we don't have a specific event, so just log)
            raise

    # ========================================================================
    # OVERRIDE: validate_against_rules() - WITH EVENT EMISSION
    # ========================================================================

    def validate_against_rules(
        self, 
        content: str, 
        rules_or_language="all"
    ) -> List[RuleViolation]:
        """
        Check content against applicable rules (with event emission)
        
        Args:
            content: Text to validate
            rules_or_language: Language string or list of ProjectRule objects
            
        Returns:
            List of RuleViolation objects
        """
        import time
        
        validation_id = str(uuid4())[:8]
        start_time = time.time()
        
        try:
            # Call parent implementation
            violations = super().validate_against_rules(content, rules_or_language)
            
            # Emit individual violation events
            for violation in violations:
                self._emit_violation_detected(
                    validation_id,
                    violation.rule_id,
                    violation.rule_title,
                    violation.severity
                )
            
            elapsed_ms = (time.time() - start_time) * 1000
            
            # Emit completion event
            self._emit_validation_completed(validation_id, len(violations), elapsed_ms)
            
            # Track history
            self._track_validation(validation_id, True, len(violations), elapsed_ms)
            
            return violations
            
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            logger.error(f"Validation failed: {error_msg}")
            
            # Emit failure event
            self._emit_validation_failed(validation_id, error_msg)
            
            # Track failure
            self._track_validation(validation_id, False, 0, elapsed_ms, error=error_msg)
            
            raise

    # ========================================================================
    # EVENT EMISSION METHODS
    # ========================================================================

    def _emit_scan_requested(self, scan_id: str) -> None:
        """Emit RulesScanRequested event to EventBus and local subscribers"""
        if not self.config.enable_events:
            return
        
        try:
            event = RulesScanRequested(scan_id=scan_id)
            
            # Publish to EventBus if available
            if self.event_bus:
                self.event_bus.publish(
                    event, 
                    async_mode=self.config.async_event_processing
                )
            
            # Call local subscribers
            for handler in self._on_rules_loaded_handlers.values():
                try:
                    handler(event)
                except Exception as e:
                    logger.warning(f"Local subscriber failed: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to emit RulesScanRequested: {e}")

    def _emit_rules_loaded(self, scan_id: str, rule_count: int, 
                          elapsed_ms: float) -> None:
        """Emit RulesLoaded event"""
        if not self.config.enable_events:
            return
        
        try:
            event = RulesLoaded(scan_id=scan_id, rule_count=rule_count)
            
            if self.event_bus:
                self.event_bus.publish(
                    event,
                    async_mode=self.config.async_event_processing
                )
            
            for handler in self._on_rules_loaded_handlers.values():
                try:
                    handler(event)
                except Exception as e:
                    logger.warning(f"Local subscriber failed: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to emit RulesLoaded: {e}")

    def _emit_rule_parsed(self, scan_id: str, rule_id: str, 
                         rule_title: str) -> None:
        """Emit RuleParsed event"""
        if not self.config.enable_events:
            return
        
        try:
            event = RuleParsed(scan_id=scan_id, rule_id=rule_id, rule_title=rule_title)
            
            if self.event_bus:
                self.event_bus.publish(
                    event,
                    async_mode=self.config.async_event_processing
                )
            
            for handler in self._on_rule_parsed_handlers.values():
                try:
                    handler(event)
                except Exception as e:
                    logger.warning(f"Local subscriber failed: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to emit RuleParsed: {e}")

    def _emit_violation_detected(self, validation_id: str, rule_id: str,
                                rule_title: str, severity: str) -> None:
        """Emit RuleViolationDetected event"""
        if not self.config.enable_events:
            return
        
        try:
            event = RuleViolationDetected(
                validation_id=validation_id,
                rule_id=rule_id,
                rule_title=rule_title,
                severity=severity
            )
            
            if self.event_bus:
                self.event_bus.publish(
                    event,
                    async_mode=self.config.async_event_processing
                )
            
            for handler in self._on_violation_detected_handlers.values():
                try:
                    handler(event)
                except Exception as e:
                    logger.warning(f"Local subscriber failed: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to emit RuleViolationDetected: {e}")

    def _emit_validation_completed(self, validation_id: str, violation_count: int,
                                  elapsed_ms: float) -> None:
        """Emit RulesValidationCompleted event"""
        if not self.config.enable_events:
            return
        
        try:
            event = RulesValidationCompleted(
                validation_id=validation_id,
                violation_count=violation_count,
                elapsed_ms=elapsed_ms
            )
            
            if self.event_bus:
                self.event_bus.publish(
                    event,
                    async_mode=self.config.async_event_processing
                )
            
            for handler in self._on_validation_completed_handlers.values():
                try:
                    handler(event)
                except Exception as e:
                    logger.warning(f"Local subscriber failed: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to emit RulesValidationCompleted: {e}")

    def _emit_validation_failed(self, validation_id: str, error: str) -> None:
        """Emit RulesValidationFailed event"""
        if not self.config.enable_events:
            return
        
        try:
            event = RulesValidationFailed(validation_id=validation_id, error=error)
            
            if self.event_bus:
                self.event_bus.publish(
                    event,
                    async_mode=self.config.async_event_processing
                )
            
            for handler in self._on_validation_failed_handlers.values():
                try:
                    handler(event)
                except Exception as e:
                    logger.warning(f"Local subscriber failed: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to emit RulesValidationFailed: {e}")

    # ========================================================================
    # LOCAL SUBSCRIBER METHODS
    # ========================================================================

    def on_rules_loaded(self, handler: Callable) -> str:
        """Register handler for RulesLoaded event. Returns subscription ID."""
        sub_id = str(uuid4())
        self._on_rules_loaded_handlers[sub_id] = handler
        return sub_id

    def on_rule_parsed(self, handler: Callable) -> str:
        """Register handler for RuleParsed event. Returns subscription ID."""
        sub_id = str(uuid4())
        self._on_rule_parsed_handlers[sub_id] = handler
        return sub_id

    def on_violation_detected(self, handler: Callable) -> str:
        """Register handler for RuleViolationDetected event. Returns subscription ID."""
        sub_id = str(uuid4())
        self._on_violation_detected_handlers[sub_id] = handler
        return sub_id

    def on_validation_completed(self, handler: Callable) -> str:
        """Register handler for RulesValidationCompleted event. Returns subscription ID."""
        sub_id = str(uuid4())
        self._on_validation_completed_handlers[sub_id] = handler
        return sub_id

    def on_validation_failed(self, handler: Callable) -> str:
        """Register handler for RulesValidationFailed event. Returns subscription ID."""
        sub_id = str(uuid4())
        self._on_validation_failed_handlers[sub_id] = handler
        return sub_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from any local event. Returns True if found."""
        handlers_list = [
            self._on_rules_loaded_handlers,
            self._on_rule_parsed_handlers,
            self._on_violation_detected_handlers,
            self._on_validation_completed_handlers,
            self._on_validation_failed_handlers
        ]
        
        for handlers in handlers_list:
            if subscription_id in handlers:
                del handlers[subscription_id]
                return True
        
        return False

    # ========================================================================
    # HISTORY & TRACKING
    # ========================================================================

    def _track_scan(self, scan_id: str, success: bool, rule_count: int,
                   elapsed_ms: float, error: Optional[str] = None) -> None:
        """Track rule scan in history"""
        if not self.config.track_scan_history:
            return
        
        with self._history_lock:
            # Update stats
            with self._stats_lock:
                self._stats["total_scans"] += 1
                if success:
                    self._stats["successful_scans"] += 1
                    # Update avg scan duration
                    if self._stats["avg_scan_duration_ms"] == 0:
                        self._stats["avg_scan_duration_ms"] = elapsed_ms
                    else:
                        self._stats["avg_scan_duration_ms"] = (
                            self._stats["avg_scan_duration_ms"] * 0.9 + elapsed_ms * 0.1
                        )
                else:
                    self._stats["failed_scans"] += 1
            
            # Add to history
            self._scan_history.append({
                "scan_id": scan_id,
                "success": success,
                "rule_count": rule_count,
                "elapsed_ms": elapsed_ms,
                "error": error,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Keep history limited
            if len(self._scan_history) > self.config.max_scan_history:
                self._scan_history = self._scan_history[-self.config.max_scan_history:]

    def _track_validation(self, validation_id: str, success: bool, 
                         violation_count: int, elapsed_ms: float,
                         error: Optional[str] = None) -> None:
        """Track rule validation in history"""
        if not self.config.track_scan_history:
            return
        
        with self._history_lock:
            # Update stats
            with self._stats_lock:
                self._stats["total_validations"] += 1
                if success:
                    self._stats["successful_validations"] += 1
                    self._stats["total_violations_found"] += violation_count
                    # Update avg metrics
                    if self._stats["avg_validation_duration_ms"] == 0:
                        self._stats["avg_validation_duration_ms"] = elapsed_ms
                    else:
                        self._stats["avg_validation_duration_ms"] = (
                            self._stats["avg_validation_duration_ms"] * 0.9 + elapsed_ms * 0.1
                        )
                    
                    if self._stats["successful_validations"] > 0:
                        self._stats["avg_violations_per_validation"] = (
                            self._stats["total_violations_found"] / 
                            self._stats["successful_validations"]
                        )
                else:
                    self._stats["failed_validations"] += 1
            
            # Add to history
            self._validation_history.append({
                "validation_id": validation_id,
                "success": success,
                "violation_count": violation_count,
                "elapsed_ms": elapsed_ms,
                "error": error,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Keep history limited
            if len(self._validation_history) > self.config.max_scan_history:
                self._validation_history = self._validation_history[-self.config.max_scan_history:]

    def get_scan_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent scan history"""
        with self._history_lock:
            return self._scan_history[-limit:]

    def get_validation_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent validation history"""
        with self._history_lock:
            return self._validation_history[-limit:]

    def clear_scan_history(self) -> None:
        """Clear all scan history"""
        with self._history_lock:
            self._scan_history.clear()

    def clear_validation_history(self) -> None:
        """Clear all validation history"""
        with self._history_lock:
            self._validation_history.clear()

    # ========================================================================
    # STATISTICS & CONFIGURATION
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics"""
        with self._stats_lock:
            try:
                parent_stats = super().get_stats()
            except (AttributeError, KeyError):
                # Parent has a bug with string vs enum keys - use safe defaults
                parent_stats = {
                    "total_rules": len(self.rules),
                    "by_level": {},
                    "by_category": {},
                    "by_language": {}
                }
            
            return {
                **parent_stats,
                "engine_version": "V3",
                "scans": {
                    "total": self._stats["total_scans"],
                    "successful": self._stats["successful_scans"],
                    "failed": self._stats["failed_scans"],
                    "avg_duration_ms": round(self._stats["avg_scan_duration_ms"], 2)
                },
                "validations": {
                    "total": self._stats["total_validations"],
                    "successful": self._stats["successful_validations"],
                    "failed": self._stats["failed_validations"],
                    "avg_duration_ms": round(self._stats["avg_validation_duration_ms"], 2),
                    "total_violations_found": self._stats["total_violations_found"],
                    "avg_violations_per_validation": round(
                        self._stats["avg_violations_per_validation"], 2
                    )
                },
                "history_size": {
                    "scans": len(self._scan_history),
                    "validations": len(self._validation_history)
                }
            }

    def enable_events(self, enabled: bool = True) -> None:
        """Enable or disable event emission"""
        self.config.enable_events = enabled
        logger.info(f"Event emission {'enabled' if enabled else 'disabled'}")

    def set_event_bus(self, event_bus: Optional[EventBus]) -> None:
        """Set or replace the EventBus instance"""
        self.event_bus = event_bus
        logger.info(f"EventBus {'attached' if event_bus else 'detached'}")

    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            f"RulesEngineV3(project={self.project_root.name}, "
            f"rules={stats['total_rules']}, "
            f"scans={stats['scans']['total']}, "
            f"validations={stats['validations']['total']}, "
            f"events={'enabled' if self.config.enable_events else 'disabled'})"
        )


# ============================================================================
# ADAPTER PATTERN FOR LEGACY CODE
# ============================================================================

class RulesEngineAdapter:
    """
    Adapter to wrap legacy ProjectRulesEngine and add V3 features.
    Enables gradual migration without rewriting existing code.
    """
    
    def __init__(self, engine_v3: RulesEngineV3):
        self.v3 = engine_v3

    @staticmethod
    def wrap(
        engine: ProjectRulesEngine,
        event_bus: Optional[EventBus] = None
    ) -> 'RulesEngineV3':
        """
        Wrap a legacy ProjectRulesEngine with V3 features.
        
        Usage:
            legacy_engine = ProjectRulesEngine(project_root)
            v3_engine = RulesEngineAdapter.wrap(legacy_engine, event_bus)
        """
        # Create V3 engine pointing to same project
        v3 = RulesEngineV3(
            engine.project_root,
            vault_core=engine.vault_core,
            event_bus=event_bus
        )
        
        # Copy existing rules if any
        if hasattr(engine, 'rules'):
            v3.rules = engine.rules
            v3._build_index()
        
        return v3

    @staticmethod
    def upgrade_path(
        project_root: Path,
        event_bus: Optional[EventBus] = None
    ) -> 'RulesEngineV3':
        """
        Direct upgrade path: create V3 engine directly.
        
        Usage:
            v3_engine = RulesEngineAdapter.upgrade_path(project_root, event_bus)
            rules = v3_engine.scan_rules()
        """
        return RulesEngineV3(project_root, event_bus=event_bus)


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def create_rules_engine_v3(
    project_root: Path,
    vault_core=None,
    event_bus: Optional[EventBus] = None,
    enable_events: bool = True,
    track_history: bool = True
) -> RulesEngineV3:
    """
    Factory function to create RulesEngineV3 with standard config.
    
    Usage:
        engine = create_rules_engine_v3(
            Path("."),
            event_bus=my_event_bus,
            enable_events=True
        )
    """
    config = RulesEngineV3Config(
        enable_events=enable_events,
        async_event_processing=False,
        track_scan_history=track_history
    )
    return RulesEngineV3(
        project_root,
        vault_core=vault_core,
        event_bus=event_bus,
        config=config
    )
