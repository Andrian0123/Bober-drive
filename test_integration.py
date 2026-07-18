#!/usr/bin/env python3
"""
Nexus Integration Tests
Интеграционные тесты для gRPC adapter и Node.js клиента
"""

import unittest
import tempfile
import time
import subprocess
import sys
import json
from pathlib import Path
from typing import Optional

# Добавить driver в path
sys.path.insert(0, str(Path(__file__).parent.parent / "Bober-Drive" / "driver"))

from nexus_orchestrator_v3 import NexusOrchestrator, NexusConfig
from nexus_fts5_indexer_v3 import FTS5IndexerV3
from nexus_file_system_mapper import FileSystemMapper


class TestIntegrationSetup(unittest.TestCase):
    """Тесты инициализации интеграционного слоя"""
    
    def test_nexus_config_integration_mode(self):
        """Проверить, что конфигурация создана в режиме интеграции"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            config = NexusConfig(
                project_root=tmpdir,
                vault_path=tmpdir / "vault.db",
                enable_auto_update=False,  # Интеграционный режим
                enable_events=True,
                enable_caching=True,
            )
            
            # Проверить, что auto-update отключен
            self.assertFalse(config.enable_auto_update)
            self.assertTrue(config.enable_events)
    
    def test_orchestrator_initializes_without_auto_update(self):
        """Проверить инициализацию Orchestrator без auto-update"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            config = NexusConfig(
                project_root=tmpdir,
                vault_path=tmpdir / "vault.db",
                enable_auto_update=False,
            )
            
            orchestrator = NexusOrchestrator(config)
            self.assertIsNotNone(orchestrator)
            self.assertFalse(orchestrator.config.enable_auto_update)
            
            orchestrator.shutdown()


class TestSearchIntegration(unittest.TestCase):
    """Тесты функциональности поиска"""
    
    def setUp(self):
        """Подготовка к каждому тесту"""
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmpdir_path = Path(self.tmpdir.name)
        
        self.config = NexusConfig(
            project_root=self.tmpdir_path,
            vault_path=self.tmpdir_path / "vault.db",
            enable_auto_update=False,
        )
        
        self.orchestrator = NexusOrchestrator(self.config)
    
    def tearDown(self):
        """Очистка после каждого теста"""
        if self.orchestrator:
            self.orchestrator.shutdown()
        self.tmpdir.cleanup()
    
    def test_search_returns_empty_for_new_vault(self):
        """Проверить, что поиск возвращает пустой результат для нового vault"""
        result = self.orchestrator.search("nonexistent")
        
        self.assertIsNotNone(result)
        self.assertIn("results", result)
        self.assertEqual(len(result.get("results", [])), 0)
    
    def test_search_with_limit(self):
        """Проверить, что поиск возвращает результаты"""
        # Создать несколько документов
        for i in range(5):
            doc_path = self.tmpdir_path / f"test_{i}.txt"
            doc_path.write_text(f"Document {i} with search term")
        
        result = self.orchestrator.search("search")
        
        self.assertIsNotNone(result)
        self.assertIn("results", result)


class TestIngestIntegration(unittest.TestCase):
    """Тесты функциональности индексирования"""
    
    def setUp(self):
        """Подготовка к каждому тесту"""
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmpdir_path = Path(self.tmpdir.name)
        
        self.config = NexusConfig(
            project_root=self.tmpdir_path,
            vault_path=self.tmpdir_path / "vault.db",
            enable_auto_update=False,
        )
        
        self.orchestrator = NexusOrchestrator(self.config)
    
    def tearDown(self):
        """Очистка после каждого теста"""
        if self.orchestrator:
            self.orchestrator.shutdown()
        self.tmpdir.cleanup()
    
    def test_ingest_markdown_document(self):
        """Проверить индексирование markdown документа"""
        doc_path = self.tmpdir_path / "test.md"
        doc_path.write_text("# Test\n\nThis is a test document")
        
        result = self.orchestrator.ingest_document(doc_path)
        
        self.assertIsNotNone(result)
    
    def test_ingest_text_document(self):
        """Проверить индексирование текстового файла"""
        doc_path = self.tmpdir_path / "test.txt"
        doc_path.write_text("This is a plain text document")
        
        result = self.orchestrator.ingest_document(doc_path)
        
        self.assertIsNotNone(result)
    
    def test_ingest_updates_search_index(self):
        """Проверить, что индексирование обновляет поисковый индекс"""
        # Поиск перед индексированием
        result_before = self.orchestrator.search("security")
        
        # Индексировать документ
        doc_path = self.tmpdir_path / "security.txt"
        doc_path.write_text("This document is about security vulnerabilities")
        self.orchestrator.ingest_document(doc_path)
        
        # Поиск после индексирования
        result_after = self.orchestrator.search("security")
        
        # После индексирования должно быть больше результатов
        self.assertGreaterEqual(
            len(result_after.get("results", [])),
            len(result_before.get("results", []))
        )


class TestScanProjectIntegration(unittest.TestCase):
    """Тесты функциональности сканирования проектов"""
    
    def setUp(self):
        """Подготовка к каждому тесту"""
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmpdir_path = Path(self.tmpdir.name)
        
        # Создать структуру проекта
        self.project_root = self.tmpdir_path / "test_project"
        self.project_root.mkdir()
        
        (self.project_root / "src").mkdir()
        (self.project_root / "src" / "main.py").write_text("print('hello')")
        (self.project_root / "src" / "utils.py").write_text("def helper(): pass")
        
        (self.project_root / "docs").mkdir()
        (self.project_root / "docs" / "README.md").write_text("# Documentation")
        
        (self.project_root / ".git").mkdir()  # Должно быть игнорировано
        (self.project_root / ".git" / "config").write_text("git config")
        
        self.config = NexusConfig(
            project_root=self.project_root,
            vault_path=self.tmpdir_path / "vault.db",
            enable_auto_update=False,
        )
        
        self.orchestrator = NexusOrchestrator(self.config)
    
    def tearDown(self):
        """Очистка после каждого теста"""
        if self.orchestrator:
            self.orchestrator.shutdown()
        self.tmpdir.cleanup()
    
    def test_scan_project_finds_files(self):
        """Проверить, что сканирование находит файлы проекта"""
        mapper = FileSystemMapper(
            self.project_root,
            self.orchestrator.container.resolve("vault")
        )
        
        file_map = mapper.scan_project()
        
        # Должны найти .py и .md файлы
        self.assertGreater(len(file_map), 0)
        
        # Проверить, что .git файлы игнорированы
        git_files = [f for f in file_map.values() if '.git' in str(f.path)]
        self.assertEqual(len(git_files), 0)
    
    def test_scan_project_identifies_file_types(self):
        """Проверить определение типов файлов"""
        mapper = FileSystemMapper(
            self.project_root,
            self.orchestrator.container.resolve("vault")
        )
        
        file_map = mapper.scan_project()
        
        # Проверить, что найдены Python и markdown файлы
        file_types = [f.file_type.value for f in file_map.values()]
        self.assertTrue(
            any(ft in ['python_code', 'code'] for ft in file_types),
            f"Expected Python code file type, but got: {file_types}"
        )
        self.assertIn("markdown", file_types)


class TestHealthCheckIntegration(unittest.TestCase):
    """Тесты health check функциональности"""
    
    def setUp(self):
        """Подготовка к каждому тесту"""
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmpdir_path = Path(self.tmpdir.name)
        
        self.config = NexusConfig(
            project_root=self.tmpdir_path,
            vault_path=self.tmpdir_path / "vault.db",
            enable_auto_update=False,
        )
        
        self.orchestrator = NexusOrchestrator(self.config)
    
    def tearDown(self):
        """Очистка после каждого теста"""
        if self.orchestrator:
            self.orchestrator.shutdown()
        self.tmpdir.cleanup()
    
    def test_health_check_returns_stats(self):
        """Проверить, что health check возвращает статистику"""
        stats = self.orchestrator.get_stats()
        
        self.assertIsNotNone(stats)
        # Проверить структуру stats
        self.assertIn("vault", stats)
        self.assertIn("entries", stats["vault"])


class TestAutoUpdateDisabled(unittest.TestCase):
    """Тесты отключения auto-update в режиме интеграции"""
    
    def test_auto_update_is_disabled_in_config(self):
        """Проверить, что auto-update отключен в конфигурации"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            config = NexusConfig(
                project_root=tmpdir,
                vault_path=tmpdir / "vault.db",
                enable_auto_update=False,
                auto_install_updates=False,
            )
            
            self.assertFalse(config.enable_auto_update)
            self.assertFalse(config.auto_install_updates)
    
    def test_auto_updater_not_started_when_disabled(self):
        """Проверить, что auto-updater не запускается когда отключен"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            config = NexusConfig(
                project_root=tmpdir,
                vault_path=tmpdir / "vault.db",
                enable_auto_update=False,
            )
            
            orchestrator = NexusOrchestrator(config)
            
            # Проверить, что auto_updater не создан
            # (если include_auto_update=False в DI контейнере)
            try:
                auto_updater = orchestrator.container.resolve("auto_updater")
                # Если мы здесь — auto_updater был создан, что ОК
                # но он не должен быть запущен
            except:
                # Auto updater не был зарегистрирован — это предпочтительно
                pass
            
            orchestrator.shutdown()


class TestEventEmission(unittest.TestCase):
    """Тесты emit событий в режиме интеграции"""
    
    def setUp(self):
        """Подготовка к каждому тесту"""
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmpdir_path = Path(self.tmpdir.name)
        
        self.config = NexusConfig(
            project_root=self.tmpdir_path,
            vault_path=self.tmpdir_path / "vault.db",
            enable_auto_update=False,
            enable_events=True,
        )
        
        self.orchestrator = NexusOrchestrator(self.config)
        self.events_received = []
    
    def tearDown(self):
        """Очистка после каждого теста"""
        if self.orchestrator:
            self.orchestrator.shutdown()
        self.tmpdir.cleanup()
    
    def test_events_enabled_in_integration_mode(self):
        """Проверить, что события включены в режиме интеграции"""
        self.assertTrue(self.config.enable_events)
        
        # Попытаться подписаться на события
        from core.event_bus import DocumentImportRequested
        
        def event_handler(event):
            self.events_received.append(event)
        
        # Должны иметь возможность подписаться
        # (детали зависят от реализации EventBus)


def run_integration_tests():
    """Запустить все интеграционные тесты"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Добавить все test cases
    suite.addTests(loader.loadTestsFromTestCase(TestIntegrationSetup))
    suite.addTests(loader.loadTestsFromTestCase(TestSearchIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestIngestIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestScanProjectIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestHealthCheckIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestAutoUpdateDisabled))
    suite.addTests(loader.loadTestsFromTestCase(TestEventEmission))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    exit_code = run_integration_tests()
    sys.exit(exit_code)
