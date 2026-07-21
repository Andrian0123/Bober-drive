#!/usr/bin/env python3
"""
quick_agent_start.py — Демонстрация Bober-Drive для агентов

Этот скрипт показывает как работает Bober-Drive:
1. Инициализирует демон (скан документации)
2. Переходит через 3 фазы: INITIALIZING → READY → MONITORING
3. Выполняет поиск по документации
4. Показывает метрики и статистику
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

def main():
    print_header("🚀 Bober-Drive: Быстрый старт для агента")
    
    print(f"""
Этот скрипт демонстрирует полный жизненный цикл Bober-Drive:
    
  Phase 1: INITIALIZING
    └─ Сканируем f:/PROFI-A/docs/ (570+ markdown файлов)
    └─ Парсим содержимое
    └─ Создаем FTS5 индекс
    └─ Сохраняем checkpoint для восстановления
    
  Phase 2: READY
    └─ Демон готов к поиску
    └─ API доступен
    └─ Индекс загружен в памяти
    
  Phase 3: MONITORING
    └─ Watchdog следит за изменениями в docs/
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
            'project_root': 'f:/PROFI-A/docs',
            'vault_path': 'storage/profia_docs.vault',
            'checkpoint_path': '.nexus/checkpoint.json',
            'init_strategy': 'FULL_SCAN',
            'enable_file_watch': True,
            'watchdog_timeout_sec': 30,
            'reindex_debounce_sec': 0.5,
            'log_file': '.nexus/daemon.log',
        }
        
        for key, value in config.items():
            print(f"  • {key}: {value}")
        
        # Создание демона
        print("\n⏳ Создаем демон...")
        daemon = create_autonomous_daemon(config)
        print("✅ Демон создан")
        
        # Запуск
        print("\n⏳ Запускаем демон (это займет 8-15 сек)...")
        start_time = time.time()
        success = daemon.start()
        elapsed = time.time() - start_time
        
        if not success:
            print("❌ Ошибка при запуске демона")
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
            ("MVVM", "Архитектурный паттерн"),
            ("3D сканер", "Функция сканирования"),
            ("подписка", "Система подписок"),
            ("Room Database", "Локальное хранилище"),
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
                print(f"    (Нет результатов)")
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
        print_header("💡 Информация для агента")
        print("""
Ключевые файлы:
  • AGENTS.local.md — Определение роли Bober-drive (ЭТО главное!)
  • INTEGRATION_WITH_PROFIA.md — Сценарии использования
  • driver/nexus_autonomous_daemon.py — Исходный код демона
  • test_autonomous_daemon_e2e.py — E2E тесты (9/9 passing)

Главное, что нужно помнить:
  ✓ Bober-Drive индексирует документацию (570+ файлов)
  ✓ Это инструмент для разработчиков, не часть приложения
  ✓ Работает 100% локально, без облака
  ✓ Поддерживает 3 сценария: Python скрипт, IDE, gRPC
  ✓ E2E тесты гарантируют корректную работу (9/9 ✅)

Архитектура:
  Phase 1: INITIALIZING (сканирование и индексирование)
  Phase 2: READY (готов к работе, индекс в памяти)
  Phase 3: MONITORING (мониторинг изменений, автообновление)

Интеграция с PROFI-A:
  • ДА: Используется разработчиками для поиска в docs
  • НЕТ: Не встраивается в Android/Kotlin приложение
  • НЕТ: Не используется в backend
  • НЕТ: Не синхронизируется в облако
        """)
        
        # Завершение
        print_header("✅ Завершение")
        print("\n⏳ Остановка демона...")
        daemon.stop(graceful=True)
        print("✅ Демон остановлен\n")
        
        print("🎉 Демонстрация завершена успешно!")
        print(f"\n📝 Полные логи доступны в: .nexus/daemon.log")
        
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
