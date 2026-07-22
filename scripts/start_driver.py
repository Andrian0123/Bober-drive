#!/usr/bin/env python3
"""
start_driver.py — Быстрый запуск Nexus Driver с синхронизацией

Использование:
    python start_driver.py              # Использовать текущий проект
    python start_driver.py /path/docs   # Указать путь к документации
"""

import sys
from pathlib import Path
import json

# Корень проекта
PROJECT_ROOT = Path(__file__).parent.resolve()

# Добавить в sys.path
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def load_config():
    """Загрузить конфигурацию из .bober-drive/config.json"""
    config_file = PROJECT_ROOT / ".bober-drive" / "config.json"
    
    if not config_file.exists():
        print("❌ Ошибка: конфигурация не найдена")
        print("   Запустите: python install_driver_sync.py")
        sys.exit(1)
    
    with open(config_file, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    # Загрузить конфигурацию
    config = load_config()
    
    # Переопределить project_root если указан аргумент
    if len(sys.argv) > 1:
        docs_path = Path(sys.argv[1]).resolve()
        if not docs_path.exists():
            print(f"❌ Ошибка: путь не существует: {docs_path}")
            sys.exit(1)
        config['project_root'] = str(docs_path)
    
    print("=" * 70)
    print("  🚀 Nexus Driver — Автономный Демон")
    print("=" * 70)
    print(f"\n📍 Проект: {config['project_root']}")
    print(f"💾 Vault: {config['vault_path']}")
    print(f"📝 Checkpoint: {config['checkpoint_path']}")
    
    # Импортировать и запустить демон
    from driver.nexus_autonomous_daemon import create_autonomous_daemon, InitStrategy
    from pathlib import Path
    
    print("\n⏳ Создаю демон...")
    daemon = create_autonomous_daemon(
        project_root=Path(config['project_root']),
        vault_path=Path(config['vault_path']),
        enable_file_watch=config.get('enable_file_watch', True),
        init_strategy=InitStrategy.FULL_SCAN if config.get('init_strategy') == 'FULL_SCAN' else InitStrategy.INCREMENTAL,
        checkpoint_path=Path(config['checkpoint_path']) if config.get('checkpoint_path') else None,
        file_extensions=config.get('supported_extensions'),
        ignore_patterns=config.get('ignore_patterns')
    )
    
    print("\n🚀 Запускаю демон...")
    if daemon.start():
        print("\n✅ Демон запущен успешно")
        
        # Показать статус
        status = daemon.get_status()
        print(f"\n📊 Статус:")
        print(f"  • State: {status.get('state', 'N/A')}")
        print(f"  • Indexed files: {status.get('files_scanned', status.get('indexed_files', 0))}")
        print(f"  • Last scan: {status.get('last_scan', 'N/A')}")
        
        # Показать метрики
        metrics = daemon.get_metrics()
        print(f"\n📈 Метрики:")
        print(f"  • Total searches: {metrics.get('total_searches', 0)}")
        print(f"  • Total reindexes: {metrics.get('total_reindexes', 0)}")
        
        # Пример поиска
        print("\n🔍 Тестовый поиск...")
        results = daemon.search("nexus", limit=5)
        print(f"  Найдено результатов: {len(results.get('hits', []))}")
        
        for i, hit in enumerate(results.get('hits', [])[:3], 1):
            print(f"  {i}. {hit['file_path']} (score: {hit['score']:.2f})")
        
        # Остановить демон
        print("\n⏸️  Останавливаю демон...")
        daemon.stop(graceful=True)
        print("✅ Демон остановлен")
    else:
        print("\n❌ ОШИБКА: Не удалось запустить демон")
        sys.exit(1)

if __name__ == "__main__":
    main()
