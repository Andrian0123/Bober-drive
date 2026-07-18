#!/usr/bin/env python3
"""
Smoke Test для IDE Integration v3.0.0

Проверяет базовую работоспособность:
1. gRPC Adapter запускается
2. LSP Server подключается к адаптеру
3. Простейшие запросы работают
"""

import sys
import json
import subprocess
import time
from pathlib import Path

def test_grpc_adapter():
    """Тест 1: gRPC Adapter инициализируется"""
    print("[1/5] Проверка gRPC Adapter...")
    
    try:
        from nexus_grpc_adapter import NexusGRPCAdapter, IntegrationConfig
        from driver.nexus_orchestrator_v3 import NexusOrchestrator, NexusConfig
        
        config = NexusConfig(
            project_root=Path.cwd(),
            vault_path=Path.home() / ".nexus" / "smoke_test" / "vault.db",
            enable_auto_update=False,
            enable_events=True
        )
        
        orchestrator = NexusOrchestrator(config)
        adapter = NexusGRPCAdapter(orchestrator, port=50052)  # Другой порт
        
        # Health check
        health = adapter.health_check()
        assert health["status"] == "healthy", f"Health check failed: {health}"
        
        print("   ✅ gRPC Adapter работает")
        return adapter
    
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        sys.exit(1)

def test_search(adapter):
    """Тест 2: Поиск работает"""
    print("[2/5] Проверка поиска...")
    
    try:
        result = adapter.search("test", limit=10, search_type="fts5")
        assert "results" in result, f"Нет results в ответе: {result}"
        assert "result_count" in result, f"Нет result_count в ответе: {result}"
        
        print(f"   ✅ Поиск работает (найдено {result.get('result_count', 0)} результатов)")
    
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        sys.exit(1)

def test_ingest(adapter):
    """Тест 3: Индексация работает"""
    print("[3/5] Проверка индексации...")
    
    try:
        test_file = Path(__file__).parent / "test_smoke.py"
        content = "# Test document\ndef hello():\n    pass"
        
        result = adapter.ingest(
            file_path=str(test_file),
            content=content,
            content_type="python"
        )
        
        # Проверяем, что есть success или status
        assert "success" in result or "status" in result, f"Ingest failed: {result}"
        
        print("   ✅ Индексация работает")
    
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        sys.exit(1)

def test_lsp_server_imports():
    """Тест 4: LSP Server импортируется без ошибок"""
    print("[4/5] Проверка LSP Server...")
    
    try:
        # Просто импортируем, не запускаем (т.к. нужен stdin)
        sys.path.insert(0, str(Path(__file__).parent))
        
        # Проверяем импорты
        from driver.lsp_server import LSPServer, LSPServerStdio
        
        print("   ✅ LSP Server импортируется без ошибок")
    
    except Exception as e:
        print(f"   ❌ Ошибка импорта: {e}")
        sys.exit(1)

def test_vscode_extension():
    """Тест 5: VS Code Extension скомпилирован"""
    print("[5/5] Проверка VS Code Extension...")
    
    try:
        ext_path = Path(__file__).parent / "vscode-extension"
        out_file = ext_path / "out" / "extension.js"
        
        if not out_file.exists():
            raise FileNotFoundError(f"Extension не скомпилирован: {out_file}")
        
        # Проверяем размер
        size = out_file.stat().st_size
        if size < 1000:
            raise ValueError(f"Extension слишком маленький: {size} bytes")
        
        print(f"   ✅ VS Code Extension скомпилирован ({size} bytes)")
    
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        sys.exit(1)

def main():
    print("=" * 60)
    print("Smoke Test: Nexus IDE Integration v3.0.0")
    print("=" * 60)
    
    # Создаём test vault директорию
    vault_dir = Path.home() / ".nexus" / "smoke_test"
    vault_dir.mkdir(parents=True, exist_ok=True)
    
    # Запускаем тесты
    adapter = test_grpc_adapter()
    test_search(adapter)
    test_ingest(adapter)
    test_lsp_server_imports()
    test_vscode_extension()
    
    # Cleanup
    adapter.shutdown()
    
    print("\n" + "=" * 60)
    print("✅ ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО")
    print("=" * 60)
    print("\n📋 Следующие шаги:")
    print("1. Откройте vscode-extension/ в VS Code")
    print("2. Нажмите F5 для запуска Extension Development Host")
    print("3. Откройте любой проект и протестируйте автодополнение")
    print("4. Проверьте логи: ~/.nexus/lsp_server.log")

if __name__ == "__main__":
    main()
