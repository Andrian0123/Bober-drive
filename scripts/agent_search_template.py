#!/usr/bin/env python3
"""
agent_search_template.py — Универсальный шаблон поиска для агента

НАЗНАЧЕНИЕ:
  Этот скрипт показывает ПРАВИЛЬНЫЙ способ работы с Bober-Drive для агентов.
  
ИСПОЛЬЗОВАНИЕ:
  # Поиск по запросу
  python agent_search_template.py "cache configuration"
  
  # Поиск с указанием количества результатов
  python agent_search_template.py "daemon search" --limit 15
  
  # Импорт как модуль
  from agent_search_template import agent_search
  results = agent_search("my query", limit=10)
  
ПРАВИЛА:
  1. ВСЕГДА используй этот шаблон для поиска информации
  2. НЕ читай файлы напрямую, пока не попробуешь поиск в индексе
  3. ВСЕГДА останавливай демон через finally блок
  4. Используй Path для путей, а не строки
  5. Передавай аргументы отдельно, а не dict
"""

from driver.nexus_autonomous_daemon import create_autonomous_daemon, InitStrategy
from pathlib import Path
import sys
import argparse
import json


PROJECT_ROOT = Path("F:/Bober-Drive")


def load_project_config() -> dict:
    """Load persisted Bober-Drive config so agent uses the real project settings."""
    config_path = PROJECT_ROOT / ".bober-drive" / "config.json"
    if not config_path.exists():
        return {}

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def agent_search(query: str, limit: int = 10, verbose: bool = True):
    """
    Универсальная функция поиска для агента.
    
    Args:
        query: Поисковый запрос (например, "cache configuration")
        limit: Максимальное количество результатов (по умолчанию 10)
        verbose: Выводить подробную информацию (по умолчанию True)
    
    Returns:
        dict: Результаты поиска с ключами:
              - 'hits': список найденных документов
              - 'total': общее количество результатов
              - 'query': исходный запрос
        или None при ошибке
    
    Example:
        >>> results = agent_search("daemon configuration", limit=5)
        >>> if results and results['hits']:
        ...     for hit in results['hits']:
        ...         print(hit['file_path'])
    """
    daemon = None
    try:
        # ========================================
        # Шаг 1: Создать демон с правильным API
        # ========================================
        if verbose:
            print("⏳ Инициализирую Bober-Drive демон...")
        
        config = load_project_config()
        project_root = Path(config.get("project_root", str(PROJECT_ROOT)))
        vault_path = Path(config.get("vault_path", str(PROJECT_ROOT / "storage" / "index.vault")))
        checkpoint_path = Path(config.get("checkpoint_path", str(PROJECT_ROOT / ".nexus" / "checkpoint.json")))
        init_strategy = InitStrategy.FULL_SCAN if config.get("init_strategy", "FULL_SCAN") == "FULL_SCAN" else InitStrategy.INCREMENTAL

        daemon = create_autonomous_daemon(
            # ВАЖНО: Используй Path, не строки
            project_root=project_root,
            vault_path=vault_path,
            
            # ВАЖНО: Передавай аргументы напрямую, НЕ через dict
            enable_file_watch=config.get("enable_file_watch", False),
            init_strategy=init_strategy,
            checkpoint_path=checkpoint_path,
            file_extensions=config.get("supported_extensions"),
            ignore_patterns=config.get("ignore_patterns")
        )
        
        # ========================================
        # Шаг 2: Запустить демон
        # ========================================
        if not daemon.start():
            print("❌ Не удалось запустить демон")
            return None
        
        # ========================================
        # Шаг 3: Проверить статус
        # ========================================
        status = daemon.get_status()
        if verbose:
            print(f"✅ Демон запущен")
            print(f"   • State: {status.get('state', 'unknown')}")
            print(f"   • Indexed files: {status.get('files_indexed', status.get('indexed_files', 0))}")
            print(f"   • Vault size: {status.get('vault_size_mb', 0):.1f} MB")
            print()
        
        # ========================================
        # Шаг 4: Выполнить поиск
        # ========================================
        if verbose:
            print(f"🔍 Ищу: \"{query}\"")
            print(f"   Лимит результатов: {limit}")
            print()
        
        results = daemon.search(query, limit=limit)
        
        # ========================================
        # Шаг 5: Обработать результаты
        # ========================================
        hits = results.get('hits', [])
        
        if verbose:
            print(f"📊 Найдено: {len(hits)} результатов")
            print("=" * 70)
            print()
        
        if hits:
            for i, hit in enumerate(hits, 1):
                if verbose:
                    print(f"{i}. 📄 {hit.get('file_path', 'unknown')}")
                    print(f"   Score: {hit.get('score', 0):.2f}")
                    
                    # Показываем snippet, если есть
                    snippet = hit.get('snippet', '')
                    if snippet:
                        # Обрезаем до 100 символов
                        snippet_short = snippet[:100] + "..." if len(snippet) > 100 else snippet
                        print(f"   Snippet: {snippet_short}")
                    
                    print()
        else:
            if verbose:
                print("⚠️ Ничего не найдено в индексе")
                print("   Попробуй:")
                print("   • Использовать другие ключевые слова")
                print("   • Проверить, что файлы проиндексированы")
                print("   • Прочитать файлы напрямую (если знаешь путь)")
                print()
        
        # ========================================
        # Шаг 6: Показать метрики (опционально)
        # ========================================
        if verbose:
            metrics = daemon.get_metrics()
            print("=" * 70)
            print("📈 Метрики:")
            print(f"   • Total searches: {metrics.get('search_queries', metrics.get('total_searches', 0))}")
            print(f"   • Total reindexes: {metrics.get('total_files_reindexed', metrics.get('total_reindexes', 0))}")
            
            # Показываем статистику кэша, если доступна
            try:
                cache_stats = daemon.get_cache_stats()
                if cache_stats:
                    print(f"   • Cache entries: {cache_stats.get('entries', 0)}")
                    print(f"   • Cache hit rate: {cache_stats.get('hit_rate', 0):.1%}")
            except:
                pass  # Кэш может быть недоступен
            
            print()
        
        return results
        
    except Exception as e:
        print(f"❌ Ошибка при поиске: {e}")
        
        if verbose:
            print("\n🔧 Отладочная информация:")
            import traceback
            traceback.print_exc()
            
            print("\n💡 Возможные причины:")
            print("   • Драйвер не установлен (проверь F:/Bober-Drive/driver/)")
            print("   • Индекс не создан (проверь F:/Bober-Drive/storage/index.vault)")
            print("   • Неправильный путь проекта")
            print()
        
        return None
        
    finally:
        # ========================================
        # Шаг 7: ВСЕГДА останавливать демон
        # ========================================
        if daemon:
            daemon.stop(graceful=True)
            if verbose:
                print("✅ Демон остановлен")
                print()


def main():
    """CLI интерфейс для agent_search_template.py"""
    
    parser = argparse.ArgumentParser(
        description="Универсальный поиск через Bober-Drive",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  # Простой поиск
  python agent_search_template.py "cache configuration"
  
  # Поиск с лимитом
  python agent_search_template.py "daemon" --limit 20
  
  # Тихий режим (без подробностей)
  python agent_search_template.py "search" --quiet
  
  # Импорт как модуль
  from agent_search_template import agent_search
  results = agent_search("my query", limit=10)
"""
    )
    
    parser.add_argument(
        "query",
        type=str,
        help="Поисковый запрос (например: 'cache configuration')"
    )
    
    parser.add_argument(
        "-l", "--limit",
        type=int,
        default=10,
        help="Максимальное количество результатов (по умолчанию: 10)"
    )
    
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Тихий режим (только результаты, без подробностей)"
    )
    
    args = parser.parse_args()
    
    # Выполняем поиск
    results = agent_search(
        query=args.query,
        limit=args.limit,
        verbose=not args.quiet
    )
    
    # Возвращаем код выхода
    if results and results.get('hits'):
        sys.exit(0)  # Успех: результаты найдены
    else:
        sys.exit(1)  # Ошибка: ничего не найдено


if __name__ == "__main__":
    # Проверяем, что скрипт запущен из правильной директории
    project_root = Path("F:/Bober-Drive")
    if not project_root.exists():
        print("❌ ОШИБКА: Проект Bober-Drive не найден по пути F:/Bober-Drive")
        print()
        print("💡 Возможные решения:")
        print("   1. Измени путь в скрипте (project_root=Path('...'))")
        print("   2. Убедись, что драйвер установлен")
        print("   3. Запусти python install_driver_sync.py")
        print()
        sys.exit(1)
    
    # Запускаем CLI
    main()
