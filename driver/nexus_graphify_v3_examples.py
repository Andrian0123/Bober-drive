#!/usr/bin/env python3
"""Examples for GraphifyEngineV3 event-driven document ingestion."""

import tempfile
from pathlib import Path

from core.event_bus import EventBus, DocumentParsed, EntitiesExtracted, DocumentError
from nexus_graphify_v3 import GraphifyEngineV3, GraphifyEngineAdapter
from nexus_graphify import GraphifyEngine


def example_with_event_bus() -> None:
    """Use GraphifyEngineV3 with central EventBus."""
    event_bus = EventBus()
    engine = GraphifyEngineV3(event_bus=event_bus)

    event_bus.subscribe(
        DocumentParsed,
        lambda event: print(f"parsed: {event.document_id}, sections={event.section_count}"),
    )
    event_bus.subscribe(
        EntitiesExtracted,
        lambda event: print(f"entities={event.entity_count}, keywords={event.keyword_count}"),
    )
    event_bus.subscribe(
        DocumentError,
        lambda event: print(f"error at {event.stage}: {event.error}"),
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "example.md"
        path.write_text("# Example\n\nEmail: demo@example.com\n\n## Notes\n\nUse `demo.py`.", encoding="utf-8")
        doc = engine.import_document(path)
        print(f"import result: {doc.document_id if doc else 'failed'}")


def example_local_subscribers() -> None:
    """Use local subscribers without EventBus."""
    engine = GraphifyEngineV3()
    engine.on_document_parsed(lambda event: print(f"local parsed: {event.document_id}"))
    engine.on_entities_extracted(lambda event: print(f"local keywords: {event.keyword_count}"))

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "note.txt"
        path.write_text("Nexus local-first knowledge graph example.", encoding="utf-8")
        engine.import_document(path)
        print(engine.get_stats())


def example_legacy_adapter() -> None:
    """Wrap an existing GraphifyEngine for gradual migration."""
    legacy = GraphifyEngine()
    event_bus = EventBus()
    adapted = GraphifyEngineAdapter.wrap(legacy, event_bus=event_bus)

    event_bus.subscribe(DocumentParsed, lambda event: print(f"adapter parsed: {event.document_id}"))

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "legacy.md"
        path.write_text("# Legacy migration\n\nSame API, new events.", encoding="utf-8")
        adapted.import_document(path)


if __name__ == "__main__":
    print("--- EventBus example ---")
    example_with_event_bus()
    print("\n--- Local subscriber example ---")
    example_local_subscribers()
    print("\n--- Legacy adapter example ---")
    example_legacy_adapter()
