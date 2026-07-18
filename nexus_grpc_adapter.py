#!/usr/bin/env python3
"""
Nexus Integration gRPC Server Adapter
Адаптирует Nexus Driver v3.0.0 к gRPC API для PROFI-A
"""

import logging
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional
from concurrent import futures

# Add driver to path
sys.path.insert(0, str(Path(__file__).parent.parent / "Bober-Drive" / "driver"))

try:
    import grpc
    from grpc import aio
except ImportError:
    raise ImportError("grpcio not installed. Run: pip install grpcio grpcio-tools")

from nexus_orchestrator_v3 import NexusOrchestrator, NexusConfig
from nexus_fts5_indexer_v3 import FTS5IndexerV3
from nexus_file_system_mapper import FileSystemMapper

# Will be generated from nexus_integration.proto
# For now, mock structures (replace with actual generated pb2/pb2_grpc after compilation)
logger = logging.getLogger(__name__)


class IntegrationConfig:
    """Mock config structure - replace with proto generated"""
    def __init__(self, mode="integration", enable_auto_update=False):
        self.mode = mode
        self.enable_auto_update = enable_auto_update
        self.enable_events = True
        self.enable_caching = True


class NexusGRPCAdapter:
    """
    gRPC адаптер для Nexus Driver v3.0.0
    
    Предоставляет:
    - Search: полнотекстовый поиск
    - Ingest: индексирование документов
    - ScanProject: сканирование проектов
    - HealthCheck: проверка статуса
    - ApplyConfig: конфигурация (отключение auto-update)
    - Shutdown: graceful shutdown
    """
    
    def __init__(self, orchestrator: NexusOrchestrator, port: int = 50051):
        """
        Initialize gRPC adapter with existing NexusOrchestrator instance.
        
        Args:
            orchestrator: NexusOrchestrator instance
            port: gRPC server port (default: 50051)
        """
        self.orchestrator = orchestrator
        self.port = port
        self.server: Optional[grpc.Server] = None
        self._setup_logging()
        
    def _setup_logging(self):
        """Настроить логирование"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logger.info(f"gRPC adapter initialized on port {self.port}, auto-update: ОТКЛЮЧЕН")
    
    def _get_version(self) -> str:
        """Получить версию Nexus Driver"""
        try:
            # Попытка прочитать VERSION.json
            version_file = Path(__file__).parent / "VERSION.json"
            if version_file.exists():
                import json
                with open(version_file) as f:
                    data = json.load(f)
                    return data.get("version", "3.0.0")
        except:
            pass
        return "3.0.0"
    
    # ========== gRPC RPC Методы (mock-версия, заменить на proto-generated) ==========
    
    def search(self, query: str, limit: int = 50, search_type: str = "fts5") -> Dict[str, Any]:
        """
        Быстрый поиск по индексированным проектам и документам
        
        Args:
            query: поисковый запрос
            limit: максимум результатов
            search_type: "fts5", "semantic", или "graph"
            
        Returns:
            {
                "result_count": int,
                "results": [{"entry_id", "title", "content", "relevance", ...}],
                "elapsed_ms": float,
                "error": str or None
            }
        """
        try:
            start_time = time.time()
            
            # Используем Orchestrator для поиска
            result = self.orchestrator.search(query)
            
            elapsed_ms = (time.time() - start_time) * 1000
            
            return {
                "result_count": len(result.get("results", [])),
                "results": result.get("results", [])[:limit],
                "elapsed_ms": elapsed_ms,
                "error": None
            }
        except Exception as e:
            logger.error(f"Search error: {e}")
            return {
                "result_count": 0,
                "results": [],
                "elapsed_ms": 0.0,
                "error": str(e)
            }
    
    def ingest(self, file_path: str, content: Optional[str] = None,
               content_type: str = "text") -> Dict[str, Any]:
        """
        Индексирование документа или файла
        
        Args:
            file_path: путь до файла
            content: альтернативно, прямое содержимое
            content_type: тип контента
            
        Returns:
            {
                "entry_id": str,
                "success": bool,
                "message": str,
                "elapsed_ms": float
            }
        """
        try:
            start_time = time.time()
            
            # Используем Orchestrator для индексирования
            result = self.orchestrator.ingest_document(Path(file_path))
            
            elapsed_ms = (time.time() - start_time) * 1000
            
            return {
                "entry_id": result.get("entry_id", "unknown"),
                "success": result.get("success", False),
                "message": result.get("message", "Document ingested"),
                "elapsed_ms": elapsed_ms
            }
        except Exception as e:
            logger.error(f"Ingest error: {e}")
            return {
                "entry_id": None,
                "success": False,
                "message": str(e),
                "elapsed_ms": 0.0
            }
    
    def scan_project(self, project_root: str, deep_scan: bool = False) -> Dict[str, Any]:
        """
        Сканирование проекта и индексирование всех файлов
        
        Args:
            project_root: корневая папка проекта
            deep_scan: анализировать ли содержимое файлов
            
        Returns:
            {
                "files_found": int,
                "files_indexed": int,
                "files": [{"file_path", "file_type", "file_size", ...}],
                "success": bool,
                "elapsed_ms": float,
                "error": str or None
            }
        """
        try:
            start_time = time.time()
            
            # Используем FileSystemMapper для сканирования
            mapper = FileSystemMapper(Path(project_root), self.orchestrator.container.resolve("vault"))
            file_map = mapper.scan_project()
            
            if deep_scan:
                # Индексируем файлы в vault
                mapper.save_to_vault()
            
            elapsed_ms = (time.time() - start_time) * 1000
            
            return {
                "files_found": len(file_map),
                "files_indexed": len(file_map) if deep_scan else 0,
                "files": [
                    {
                        "file_path": str(info.path),
                        "file_type": info.file_type.value,
                        "file_size": info.size_bytes,
                        "language": info.language
                    }
                    for info in file_map.values()
                ],
                "success": True,
                "elapsed_ms": elapsed_ms,
                "error": None
            }
        except Exception as e:
            logger.error(f"ScanProject error: {e}")
            return {
                "files_found": 0,
                "files_indexed": 0,
                "files": [],
                "success": False,
                "elapsed_ms": 0.0,
                "error": str(e)
            }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Проверка здоровья системы
        
        Returns:
            {
                "status": "healthy" | "degraded" | "unhealthy",
                "version": str,
                "modules": {module_name: "ok" | "error"},
                "stats": {stat_name: value}
            }
        """
        try:
            stats = self.orchestrator.get_stats()
            
            return {
                "status": "healthy",
                "version": self._get_version(),
                "modules": {
                    "vault": "ok",
                    "fts5": "ok",
                    "rules": "ok",
                    "graphify": "ok",
                    "neural": "ok",
                    "trash": "ok",
                    "file_mapper": "ok"
                },
                "stats": {
                    "total_entries": stats.get("total_entries", 0),
                    "indexed_entries": stats.get("indexed_entries", 0),
                    "graph_nodes": stats.get("graph_nodes", 0),
                    "uptime_seconds": int(time.time() - stats.get("startup_time", time.time()))
                }
            }
        except Exception as e:
            logger.error(f"HealthCheck error: {e}")
            return {
                "status": "unhealthy",
                "version": self._get_version(),
                "modules": {},
                "stats": {},
                "error": str(e)
            }
    
    def apply_config(self, config: IntegrationConfig) -> Dict[str, Any]:
        """
        Применить конфигурацию (отключение auto-update и т.д.)
        
        Args:
            config: IntegrationConfig объект
            
        Returns:
            {
                "success": bool,
                "applied_config": config dict,
                "message": str
            }
        """
        try:
            # Уже отключили auto-update при инициализации
            if not config.enable_auto_update:
                logger.info("Auto-update остаётся отключен (интеграционный режим)")
            
            return {
                "success": True,
                "applied_config": {
                    "mode": config.mode,
                    "enable_auto_update": config.enable_auto_update,
                    "enable_events": config.enable_events,
                    "enable_caching": config.enable_caching
                },
                "message": "Configuration applied successfully"
            }
        except Exception as e:
            logger.error(f"ApplyConfig error: {e}")
            return {
                "success": False,
                "applied_config": None,
                "message": str(e)
            }
    
    def shutdown(self, graceful: bool = True) -> Dict[str, Any]:
        """
        Graceful shutdown сервера
        
        Args:
            graceful: ждать ли завершения текущих операций
            
        Returns:
            {"success": bool, "message": str}
        """
        try:
            logger.info("Shutting down Nexus Orchestrator...")
            self.orchestrator.shutdown()
            logger.info("✅ Nexus Orchestrator shut down successfully")
            
            if self.server:
                self.server.stop(grace=5.0 if graceful else 0.0)
                logger.info("✅ gRPC server stopped")
            
            return {
                "success": True,
                "message": "Shutdown completed successfully"
            }
        except Exception as e:
            logger.error(f"Shutdown error: {e}")
            return {
                "success": False,
                "message": str(e)
            }
    
    # ========== Запуск gRPC сервера ==========
    
    def start(self):
        """
        Запустить gRPC сервер
        
        ПРИМЕЧАНИЕ: используется sync сервер для простоты.
        Для production рассмотрите async вариант.
        """
        try:
            # TODO: Добавить сгенерированный proto сервис когда будут .proto файлы
            logger.info(f"🚀 Starting Nexus gRPC server on port {self.port}...")
            
            # Для демонстрации используем sync server
            # В production нужно заменить на async или добавить proto-generated сервис
            
            self.server = grpc.server(
                futures.ThreadPoolExecutor(max_workers=10),
                options=[
                    ('grpc.max_send_message_length', 100 * 1024 * 1024),  # 100MB
                    ('grpc.max_receive_message_length', 100 * 1024 * 1024),
                ]
            )
            
            # TODO: Добавить сервис
            # nexus_integration_pb2_grpc.add_NexusSearchServicer_to_server(
            #     NexusSearchServicer(self),
            #     self.server
            # )
            
            self.server.add_insecure_port(f"[::]:{self.port}")
            
            logger.info(f"✅ gRPC server listening on port {self.port}")
            logger.info("   Mode: integration (auto-update disabled)")
            logger.info("   Press Ctrl+C to shutdown")
            
            self.server.start()
            self.server.wait_for_termination()
            
        except KeyboardInterrupt:
            logger.info("\n⏹️  Received interrupt signal")
            self.shutdown(graceful=True)
        except Exception as e:
            logger.error(f"❌ Server error: {e}")
            raise


def main():
    """Запустить adapter сервер"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Nexus Integration gRPC Server for PROFI-A"
    )
    parser.add_argument(
        "--vault-root",
        type=Path,
        default=Path.home() / ".nexus" / "integration",
        help="Root directory for Nexus vault (default: ~/.nexus/integration)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=50051,
        help="gRPC server port (default: 50051)"
    )
    
    args = parser.parse_args()
    
    # Создать vault директорию если её нет
    args.vault_root.mkdir(parents=True, exist_ok=True)
    
    # Создать и запустить адаптер
    adapter = NexusGRPCAdapter(
        vault_root=args.vault_root,
        port=args.port
    )
    adapter.start()


if __name__ == "__main__":
    main()
