#!/usr/bin/env python3
"""
Graphify Engine V3 - Event-driven document ingestion and graph enrichment.

This module wraps the existing GraphifyEngine with event emission,
observability hooks, local subscribers, and an adapter for gradual migration.
The public import_document/batch_import/export_parsed API remains compatible
with the legacy GraphifyEngine.
"""

import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from nexus_graphify import GraphifyEngine, ParsedDocument, DocumentFormat
from core.event_bus import (
    EventBus,
    Event,
    DocumentImportRequested,
    DocumentFormatDetected,
    DocumentParsed,
    DocumentSegmented,
    EntitiesExtracted,
    DocumentStoredEvent,
    DocumentError,
)

logger = logging.getLogger(__name__)


@dataclass
class GraphifyEngineV3Config:
    """Configuration for GraphifyEngineV3."""
    enable_events: bool = True
    enable_observability: bool = True
    async_event_processing: bool = True
    track_import_history: bool = True
    max_history_items: int = 1000


class GraphifyEngineV3(GraphifyEngine):
    """
    Event-driven GraphifyEngine with backward-compatible document import API.

    Adds:
    - DocumentImportRequested / DocumentFormatDetected / DocumentParsed events
    - DocumentSegmented / EntitiesExtracted / DocumentStoredEvent events
    - DocumentError events for failed lifecycle stages
    - Local subscriber pattern for use without EventBus
    - Import history and basic statistics
    """

    def __init__(
        self,
        vault_core=None,
        fts5_extension=None,
        event_bus: Optional[EventBus] = None,
        config: Optional[GraphifyEngineV3Config] = None,
    ):
        super().__init__(vault_core=vault_core, fts5_extension=fts5_extension)
        self.event_bus = event_bus
        self.config = config or GraphifyEngineV3Config()
        self._local_subscribers: Dict[str, List[Callable]] = {
            "document_import_requested": [],
            "document_format_detected": [],
            "document_parsed": [],
            "document_segmented": [],
            "entities_extracted": [],
            "document_stored": [],
            "document_error": [],
        }
        self._import_history: List[Dict[str, Any]] = []
        self._history_lock = threading.Lock()

    def import_document(self, file_path: Path) -> Optional[ParsedDocument]:
        """Import and parse a document with event emission."""
        if not self.config.enable_events:
            return super().import_document(file_path)

        path = Path(file_path)
        start_time = time.time()
        self._emit_document_import_requested(path)

        try:
            if not path.exists():
                error = f"File not found: {path}"
                self._emit_document_error(str(path), error, "exists")
                self._track_import(str(path), None, 0, 0.0, "failed", error)
                return None

            fmt = self._detect_format(path)
            self._emit_document_format_detected(path, fmt)

            parsed = super().import_document(path)
            elapsed_ms = (time.time() - start_time) * 1000

            if not parsed:
                error = f"Document parser returned no result for {path}"
                self._emit_document_error(str(path), error, "parse")
                self._track_import(str(path), None, 0, elapsed_ms, "failed", error)
                return None

            self._emit_document_parsed(parsed, elapsed_ms)
            self._emit_document_segmented(parsed)
            self._emit_entities_extracted(parsed)

            if self.vault_core:
                self._emit_document_stored(parsed)

            if self.config.track_import_history:
                self._track_import(
                    str(path),
                    parsed.document_id,
                    len(parsed.sections),
                    elapsed_ms,
                    "completed",
                )

            return parsed

        except Exception as exc:
            elapsed_ms = (time.time() - start_time) * 1000
            self._emit_document_error(str(path), str(exc), "import")
            self._track_import(str(path), None, 0, elapsed_ms, "failed", str(exc))
            logger.error(f"GraphifyEngineV3 import failed for {path}: {exc}")
            raise

    def _detect_format(self, file_path: Path) -> DocumentFormat:
        """Detect document format using legacy Graphify rules."""
        suffix = file_path.suffix.lower()
        if suffix == ".pdf":
            return DocumentFormat.PDF
        if suffix == ".docx":
            return DocumentFormat.DOCX
        if suffix in [".md", ".markdown"]:
            return DocumentFormat.MARKDOWN
        if suffix == ".html":
            return DocumentFormat.HTML
        return DocumentFormat.TEXT

    def _emit_event(self, event: Event, local_key: str) -> None:
        """Emit event to EventBus and local subscribers."""
        if not self.config.enable_events:
            return

        try:
            event.source = "GraphifyEngineV3"
            if self.event_bus:
                self.event_bus.publish(event, async_mode=self.config.async_event_processing)

            for handler in self._local_subscribers.get(local_key, []):
                try:
                    handler(event)
                except Exception as exc:
                    logger.error(f"Local subscriber error for {local_key}: {exc}")
        except Exception as exc:
            logger.error(f"Failed to emit {local_key} event: {exc}")

    def _emit_document_import_requested(self, file_path: Path) -> None:
        self._emit_event(DocumentImportRequested(file_path=str(file_path)), "document_import_requested")

    def _emit_document_format_detected(self, file_path: Path, fmt: DocumentFormat) -> None:
        self._emit_event(
            DocumentFormatDetected(file_path=str(file_path), format=fmt.value),
            "document_format_detected",
        )

    def _emit_document_parsed(self, doc: ParsedDocument, elapsed_ms: float) -> None:
        self._emit_event(
            DocumentParsed(
                document_id=doc.document_id,
                format=doc.format.value,
                section_count=len(doc.sections),
                title=doc.title,
                source_path=doc.source_path,
                elapsed_ms=elapsed_ms,
            ),
            "document_parsed",
        )

    def _emit_document_segmented(self, doc: ParsedDocument) -> None:
        self._emit_event(
            DocumentSegmented(document_id=doc.document_id, section_count=len(doc.sections)),
            "document_segmented",
        )

    def _emit_entities_extracted(self, doc: ParsedDocument) -> None:
        entity_count = sum(len(values) for values in doc.entities.values())
        self._emit_event(
            EntitiesExtracted(
                document_id=doc.document_id,
                entity_count=entity_count,
                keyword_count=len(doc.keywords),
            ),
            "entities_extracted",
        )

    def _emit_document_stored(self, doc: ParsedDocument) -> None:
        self._emit_event(
            DocumentStoredEvent(
                document_id=doc.document_id,
                entry_id=doc.document_id,
                size_bytes=len(doc.content.encode("utf-8")),
                section_count=len(doc.sections),
            ),
            "document_stored",
        )

    def _emit_document_error(self, document_id: str, error: str, stage: str) -> None:
        self._emit_event(DocumentError(document_id=document_id, error=error, stage=stage), "document_error")

    def _subscribe_local(self, key: str, handler: Callable) -> str:
        self._local_subscribers[key].append(handler)
        return f"local_{key}_{id(handler)}"

    def on_document_import_requested(self, handler: Callable) -> str:
        return self._subscribe_local("document_import_requested", handler)

    def on_document_format_detected(self, handler: Callable) -> str:
        return self._subscribe_local("document_format_detected", handler)

    def on_document_parsed(self, handler: Callable) -> str:
        return self._subscribe_local("document_parsed", handler)

    def on_document_segmented(self, handler: Callable) -> str:
        return self._subscribe_local("document_segmented", handler)

    def on_entities_extracted(self, handler: Callable) -> str:
        return self._subscribe_local("entities_extracted", handler)

    def on_document_stored(self, handler: Callable) -> str:
        return self._subscribe_local("document_stored", handler)

    def on_document_error(self, handler: Callable) -> str:
        return self._subscribe_local("document_error", handler)

    def _track_import(
        self,
        file_path: str,
        document_id: Optional[str],
        section_count: int,
        elapsed_ms: float,
        status: str,
        error: Optional[str] = None,
    ) -> None:
        if not self.config.track_import_history:
            return

        with self._history_lock:
            self._import_history.append({
                "file_path": file_path,
                "document_id": document_id,
                "section_count": section_count,
                "elapsed_ms": elapsed_ms,
                "status": status,
                "error": error,
                "timestamp": time.time(),
            })
            if len(self._import_history) > self.config.max_history_items:
                self._import_history = self._import_history[-self.config.max_history_items:]

    def get_import_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent import history."""
        with self._history_lock:
            return self._import_history[-limit:]

    def clear_import_history(self) -> None:
        """Clear import history."""
        with self._history_lock:
            self._import_history.clear()

    def disable_events(self) -> None:
        """Temporarily disable event emission."""
        self.config.enable_events = False

    def enable_events(self) -> None:
        """Re-enable event emission."""
        self.config.enable_events = True

    def get_stats(self) -> Dict[str, Any]:
        """Get import statistics."""
        with self._history_lock:
            history = list(self._import_history)

        if not history:
            return {
                "total_imports": 0,
                "successful_imports": 0,
                "failed_imports": 0,
                "avg_sections": 0.0,
                "avg_duration_ms": 0.0,
                "success_rate": 0.0,
            }

        successful = [item for item in history if item["status"] == "completed"]
        failed = [item for item in history if item["status"] == "failed"]
        return {
            "total_imports": len(history),
            "successful_imports": len(successful),
            "failed_imports": len(failed),
            "avg_sections": sum(item["section_count"] for item in successful) / len(successful) if successful else 0.0,
            "avg_duration_ms": sum(item["elapsed_ms"] for item in history) / len(history),
            "success_rate": len(successful) / len(history),
        }


class GraphifyEngineAdapter:
    """Adapter for wrapping an existing GraphifyEngine instance."""

    @staticmethod
    def wrap(
        engine: GraphifyEngine,
        event_bus: Optional[EventBus] = None,
        config: Optional[GraphifyEngineV3Config] = None,
    ) -> "GraphifyEngineAdapter":
        return GraphifyEngineAdapter(engine, event_bus, config)

    @staticmethod
    def upgrade_path(vault_core=None, fts5_extension=None, event_bus: Optional[EventBus] = None) -> GraphifyEngineV3:
        return GraphifyEngineV3(vault_core=vault_core, fts5_extension=fts5_extension, event_bus=event_bus)

    def __init__(
        self,
        engine: GraphifyEngine,
        event_bus: Optional[EventBus] = None,
        config: Optional[GraphifyEngineV3Config] = None,
    ):
        self._engine = engine
        self._v3 = GraphifyEngineV3(
            vault_core=engine.vault_core,
            fts5_extension=engine.fts5_extension,
            event_bus=event_bus,
            config=config,
        )
        self._v3.parsed_documents = engine.parsed_documents

    def import_document(self, file_path: Path) -> Optional[ParsedDocument]:
        return self._v3.import_document(file_path)

    def batch_import(self, directory: Path, pattern: str = "*.md") -> List[ParsedDocument]:
        return self._v3.batch_import(directory, pattern)

    def export_parsed(self, output_path: Path) -> bool:
        return self._v3.export_parsed(output_path)

    def __getattr__(self, name: str):
        return getattr(self._v3, name)


def create_graphify_engine_v3(
    vault_core=None,
    fts5_extension=None,
    event_bus: Optional[EventBus] = None,
    config: Optional[GraphifyEngineV3Config] = None,
) -> GraphifyEngineV3:
    """Factory function to create GraphifyEngineV3."""
    return GraphifyEngineV3(
        vault_core=vault_core,
        fts5_extension=fts5_extension,
        event_bus=event_bus,
        config=config,
    )
