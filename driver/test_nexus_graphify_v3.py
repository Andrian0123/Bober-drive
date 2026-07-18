#!/usr/bin/env python3
"""Test suite for GraphifyEngineV3."""

import tempfile
import time
import unittest
from pathlib import Path

from core.event_bus import (
    EventBus,
    DocumentImportRequested,
    DocumentFormatDetected,
    DocumentParsed,
    DocumentSegmented,
    EntitiesExtracted,
    DocumentStoredEvent,
    DocumentError,
)
from nexus_graphify import GraphifyEngine, ParsedDocument
from nexus_graphify_v3 import GraphifyEngineV3, GraphifyEngineV3Config, GraphifyEngineAdapter


class TestGraphifyEngineV3Events(unittest.TestCase):
    """Test GraphifyEngineV3 event emission."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        self.doc_path = self.root / "sample.md"
        self.doc_path.write_text(
            "# Sample Document\n\n"
            "Contact test@example.com and visit https://example.com.\n\n"
            "## Section One\n\n"
            "This section mentions `code.py` and class Example.\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_import_document_emits_lifecycle_events(self):
        event_bus = EventBus()
        engine = GraphifyEngineV3(event_bus=event_bus)

        events = {
            "requested": [],
            "format": [],
            "parsed": [],
            "segmented": [],
            "entities": [],
        }
        event_bus.subscribe(DocumentImportRequested, lambda e: events["requested"].append(e))
        event_bus.subscribe(DocumentFormatDetected, lambda e: events["format"].append(e))
        event_bus.subscribe(DocumentParsed, lambda e: events["parsed"].append(e))
        event_bus.subscribe(DocumentSegmented, lambda e: events["segmented"].append(e))
        event_bus.subscribe(EntitiesExtracted, lambda e: events["entities"].append(e))

        parsed = engine.import_document(self.doc_path)

        self.assertIsInstance(parsed, ParsedDocument)
        self.assertEqual(len(events["requested"]), 1)
        self.assertEqual(len(events["format"]), 1)
        self.assertEqual(len(events["parsed"]), 1)
        self.assertEqual(len(events["segmented"]), 1)
        self.assertEqual(len(events["entities"]), 1)
        self.assertEqual(events["format"][0].format, "markdown")
        self.assertEqual(events["parsed"][0].document_id, parsed.document_id)
        self.assertGreaterEqual(events["entities"][0].keyword_count, 1)

    def test_local_subscribers_without_eventbus(self):
        engine = GraphifyEngineV3()
        parsed_events = []
        entity_events = []

        engine.on_document_parsed(lambda e: parsed_events.append(e))
        engine.on_entities_extracted(lambda e: entity_events.append(e))

        parsed = engine.import_document(self.doc_path)

        self.assertIsNotNone(parsed)
        self.assertEqual(len(parsed_events), 1)
        self.assertEqual(len(entity_events), 1)
        self.assertEqual(parsed_events[0].document_id, parsed.document_id)

    def test_document_error_emitted_for_missing_file(self):
        event_bus = EventBus()
        config = GraphifyEngineV3Config(async_event_processing=False)
        engine = GraphifyEngineV3(event_bus=event_bus, config=config)
        errors = []

        event_bus.subscribe(DocumentError, lambda e: errors.append(e))

        result = engine.import_document(self.root / "missing.md")

        self.assertIsNone(result)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].stage, "exists")

    def test_document_stored_event_when_vault_available(self):
        class FakeVault:
            def __init__(self):
                self.entries = []

            def store(self, entry):
                self.entries.append(entry)
                return True

        event_bus = EventBus()
        vault = FakeVault()
        engine = GraphifyEngineV3(vault_core=vault, event_bus=event_bus)
        stored_events = []

        event_bus.subscribe(DocumentStoredEvent, lambda e: stored_events.append(e))

        parsed = engine.import_document(self.doc_path)

        self.assertIsNotNone(parsed)
        self.assertGreaterEqual(len(vault.entries), 1)
        self.assertEqual(len(stored_events), 1)
        self.assertEqual(stored_events[0].document_id, parsed.document_id)

    def test_disable_events(self):
        event_bus = EventBus()
        engine = GraphifyEngineV3(event_bus=event_bus)
        requested_events = []
        event_bus.subscribe(DocumentImportRequested, lambda e: requested_events.append(e))

        engine.disable_events()
        parsed = engine.import_document(self.doc_path)
        self.assertIsNotNone(parsed)
        self.assertEqual(len(requested_events), 0)

        engine.enable_events()
        parsed = engine.import_document(self.doc_path)
        self.assertIsNotNone(parsed)
        self.assertEqual(len(requested_events), 1)

    def test_import_history_and_stats(self):
        engine = GraphifyEngineV3()

        engine.import_document(self.doc_path)
        engine.import_document(self.root / "missing.md")

        history = engine.get_import_history()
        stats = engine.get_stats()

        self.assertEqual(len(history), 2)
        self.assertEqual(stats["total_imports"], 2)
        self.assertEqual(stats["successful_imports"], 1)
        self.assertEqual(stats["failed_imports"], 1)
        self.assertEqual(stats["success_rate"], 0.5)

        engine.clear_import_history()
        self.assertEqual(len(engine.get_import_history()), 0)


class TestGraphifyEngineV3Compatibility(unittest.TestCase):
    """Test legacy compatibility and adapter."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        self.doc_path = self.root / "note.txt"
        self.doc_path.write_text("Paragraph one.\n\nParagraph two.", encoding="utf-8")

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_v3_preserves_import_document_api(self):
        engine = GraphifyEngineV3()
        parsed = engine.import_document(self.doc_path)

        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.format.value, "text")
        self.assertIn(parsed.document_id, engine.parsed_documents)

    def test_adapter_wraps_legacy_engine(self):
        legacy = GraphifyEngine()
        event_bus = EventBus()
        adapter = GraphifyEngineAdapter.wrap(legacy, event_bus=event_bus)
        parsed_events = []

        event_bus.subscribe(DocumentParsed, lambda e: parsed_events.append(e))
        parsed = adapter.import_document(self.doc_path)

        self.assertIsNotNone(parsed)
        self.assertEqual(len(parsed_events), 1)

    def test_batch_import_still_works(self):
        second = self.root / "second.txt"
        second.write_text("Another document", encoding="utf-8")
        engine = GraphifyEngineV3()

        docs = engine.batch_import(self.root, pattern="*.txt")

        self.assertEqual(len(docs), 2)
        self.assertEqual(engine.get_stats()["successful_imports"], 2)

    def test_event_overhead_is_small_for_markdown(self):
        baseline = GraphifyEngineV3(config=GraphifyEngineV3Config(enable_events=False))
        with_events = GraphifyEngineV3(config=GraphifyEngineV3Config(enable_events=True, async_event_processing=False))

        start = time.time()
        baseline.import_document(self.doc_path)
        baseline_ms = (time.time() - start) * 1000

        start = time.time()
        with_events.import_document(self.doc_path)
        event_ms = (time.time() - start) * 1000

        self.assertLess(event_ms - baseline_ms, 20.0)


if __name__ == "__main__":
    unittest.main()
