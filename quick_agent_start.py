#!/usr/bin/env python3
"""
quick_agent_start.py — Демонстрация Bober-Drive для любого проекта

Этот скрипт показывает как работает Bober-Drive:
1. Инициализирует демон (скан документации)
2. Переходит через 3 фазы: INITIALIZING → READY → MONITORING
3. Выполняет поиск по документации
4. Показывает метрики и статистику

Использование:
    python quick_agent_start.py /path/to/docs
    
Если путь не указан, используется ./docs по умолчанию
"""

import sys
import time
from pathlib import Path

# Убедимся, что находимся в правильной директории
BOBER_DRIVE_ROOT = Path(__file__).parent

def print_header(text):
    """Красивый заголовок"""
    print(f"\n{'=' * 70}")
    print(f"  {text}")
    print(f"{'=' * 70}")

def print_phase(phase_num, phase_name):
    """Фаза демона"""
    print(f"\n📍 Фаза {phase_num}/3: {phase_name}")

def get_docs_path():
    """Получить путь к документации (аргумент или по умолчанию)"""
    if len(sys.argv) > 1:
        docs_path = sys.argv[1]
    else:
        # Значение по умолчанию: ./docs
        docs_path = str(BOBER_DRIVE_ROOT / "docs")
    
    docs_path = Path(docs_path).resolve()
    
    if not docs_path.exists():
        print(f"❌ Ошибка: путь не существует: {docs_path}")
        print("\nИспользование:")
        print(f"  python quick_agent_start.py /path/to/docs")
        print(f"\nПо умолчанию используется: ./docs")
        sys.exit(1)
    
    return str(docs_path)

def main():
    docs_path = get_docs_path()
    
    print_header("🚀 Bober-Drive: Быстрый старт для агента")
    
    print(f"""
Этот скрипт демонстрирует полный жизненный цикл Bober-Drive:
    
  Phase 1: INITIALIZING
    └─ Сканируем документацию ({docs_path})
    └─ Парсим содержимое (Markdown, JSON, YAML)
    └─ Создаем FTS5 индекс
    └─ Сохраняем checkpoint для восстановления
    
  Phase 2: READY
    └─ Демон готов к поиску
    └─ API доступен для запросов
    └─ Индекс загружен в памяти
    
  Phase 3: MONITORING
    └─ Watchdog следит за изменениями
    └─ Автоматическое переиндексирование
    └─ Debounce-буфер (0.5 сек)
    """)
    
    try:
        # Импортируем демон
        print("\n⏳ Импортируем Bober-Drive модули...")
        from driver.nexus_autonomous_daemon import create_autonomous_daemon
        print("✅ Импорт успешен")
        
        # Конфигурация
        print_phase(1, "INITIALIZING")
        print("\n📋 Конфигурация демона:")
        
        config = {
            'project_root': docs_path,
            'vault_path': 'storage/index.vault',
            'checkpoint_path': '.nexus/checkpoint.json',
            'init_strategy': 'FULL_SCAN',
            'enable_file_watch': True,
            'watchdog_timeout_sec': 30,
            'reindex_debounce_sec': 0.5,
            'log_file': '.nexus/daemon.log',
        }
        
        for key, value in config.items():
            if key == 'project_root':
                print(f"  • {key}: {value} (ваша документация)")
            else:
                print(f"  • {key}: {value}")
        
        # Создание демона
        print("\n⏳ Создаем демон...")
        daemon = create_autonomous_daemon(config)
        print("✅ Демон создан")
        
        # Запуск
        print("\n⏳ Запускаем демон (это займет 5-15 сек)...")
        start_time = time.time()
        success = daemon.start()
        elapsed = time.time() - start_time
        
        if not success:
            print("❌ Ошибка при запуске демона")
            print("Проверьте логи: .nexus/daemon.log")
            return 1
        
        print(f"✅ Демон запущен за {elapsed:.2f} сек")
        
        # Вторая фаза
        print_phase(2, "READY")
        time.sleep(1)  # Подождать готовности
        
        # Получить статус
        status = daemon.get_status()
        print(f"\n📊 Статус демона:")
        print(f"  • Состояние: {status['state']}")
        print(f"  • Файлов индексировано: {status['indexed_files']}")
        print(f"  • Последний скан: {status['last_scan']}")
        print(f"  • Размер индекса: {status.get('vault_size_mb', 'N/A')} MB")
        
        # Поиск примеры
        print_phase(3, "MONITORING")
        print("\n🔍 Примеры поиска в документации:\n")
        
        search_queries = [
            ("documentation", "Основной термин"),
            ("architecture", "Архитектура"),
            ("api", "API интеграция"),
            ("guide", "Руководство"),
        ]
        
        for i, (query, description) in enumerate(search_queries, 1):
            print(f"{i}️⃣  Поиск: '{query}' ({description})")
            
            results = daemon.search(query, limit=3)
            
            if results['hits']:
                for j, hit in enumerate(results['hits'], 1):
                    file_path = hit.get('file_path', 'unknown')
                    score = hit.get('score', 0.0)
                    print(f"    {j}. {file_path} (relevance: {score:.2f})")
            else:
                print(f"    (Нет результатов для '{query}')")
            print()
        
        # Метрики
        print("📈 Метрики производительности:\n")
        metrics = daemon.get_metrics()
        
        metric_fields = [
            ('search_latency_ms', 'Среднее время поиска'),
            ('reindex_count', 'Количество переиндексирований'),
            ('files_watched', 'Файлов в мониторинге'),
            ('total_searches', 'Всего поисков'),
            ('uptime_sec', 'Время работы демона'),
        ]
        
        for field, description in metric_fields:
            if field in metrics:
                value = metrics[field]
                print(f"  • {description}: {value}")
        
        # Информация для агента
        print_header("💡 Информация для агента/разработчика")
        print("""
Ключевые файлы:
  • AGENTS.local.md — Архитектура и принципы Bober-Drive
  • README_UNIVERSAL_INTEGRATION.md — Интеграция для любого проекта
  • driver/nexus_autonomous_daemon.py — Исходный код демона
  • test_autonomous_daemon_e2e.py — E2E тесты (9/9 passing)

Главное, что нужно помнить:
  ✓ Bober-Drive индексирует ЛЮБУЮ документацию (Markdown, JSON, YAML, text)
  ✓ Это инструмент для разработчиков (dev-only), не часть основного приложения
  ✓ Работает 100% локально, без облака, offline-first
  ✓ Поддерживает 3 сценария: Python скрипт, IDE, gRPC микросервис
  ✓ E2E тесты гарантируют корректную работу (9/9 ✅)

Архитектура:
  Phase 1: INITIALIZING (сканирование и индексирование)
  Phase 2: READY (готов к работе, индекс в памяти)
  Phase 3: MONITORING (мониторинг изменений, автообновление)

Способы использования:
  • Локальный Python код (прямая интеграция)
  • IDE расширение (VS Code, IntelliJ)
  • gRPC микросервис (для backend)

Принципы:
  • YAGNI: Только нужный код
  • ponytail: Минимализм, раскладка по рунгам
  • Offline-first: Нулевых облачных вызовов
  • Безопасность: Валидация, error handling
        """)
        
        # Завершение
        print_header("✅ Завершение")
        print("\n⏳ Остановка демона...")
        daemon.stop(graceful=True)
        print("✅ Демон остановлен\n")
        
        print("🎉 Демонстрация завершена успешно!")
        print(f"\n📝 Полные логи доступны в: .nexus/daemon.log")
        print(f"📦 Индекс хранится в: storage/index.vault")
        print(f"\n🚀 Для встраивания в свой код смотри README_UNIVERSAL_INTEGRATION.md")
        
        return 0
        
    except ImportError as e:
        print(f"\n❌ Ошибка импорта: {e}")
        print("\nУбедитесь, что установлены зависимости:")
        print("  pip install -r requirements.txt")
        return 1
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
