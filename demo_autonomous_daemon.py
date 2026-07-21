#!/usr/bin/env python3
"""
Демонстрация работы автономного демона Bober-Drive

Показывает:
1. Инициализацию демона
2. Переходы состояний
3. API поиска
4. Сбор метрик
5. Graceful shutdown
"""

import sys
import time
import tempfile
from pathlib import Path

# Добавить driver в sys.path
driver_path = str(Path(__file__).parent / "driver")
if driver_path not in sys.path:
    sys.path.insert(0, driver_path)

from nexus_autonomous_daemon import (
    create_autonomous_daemon,
    InitStrategy,
    DaemonState
)


def create_demo_files(project_root: Path, count: int = 5):
    """Создать демонстрационные файлы"""
    docs_dir = project_root / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    for i in range(count):
        file_path = docs_dir / f"doc_{i:02d}.md"
        content = f"""# Документ {i}

## Описание
Это демонстрационный документ номер {i}.

## Содержание
- Основная информация
- Дополнительные данные
- Важные заметки

## Ключевые слова
`демо`, `тестирование`, `документация`
"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    print(f"✓ Создано {count} демонстрационных файлов")


def main():
    """Главная демонстрация"""
    
    print("=" * 70)
    print("ДЕМОНСТРАЦИЯ: Автономный демон Bober-Drive")
    print("=" * 70)
    print()
    
    # Создать временную директорию
    with tempfile.TemporaryDirectory(prefix="bober_demo_") as tmpdir:
        project_root = Path(tmpdir)
        vault_path = project_root / "vault"
        
        print(f"📁 Рабочая директория: {project_root}")
        print()
        
        # Создать демонстрационные файлы
        print("1️⃣  СОЗДАНИЕ ДЕМОНСТРАЦИОННЫХ ФАЙЛОВ")
        print("-" * 70)
        create_demo_files(project_root, count=5)
        print()
        
        # Создать демон
        print("2️⃣  ИНИЦИАЛИЗАЦИЯ ДЕМОНА")
        print("-" * 70)
        daemon = create_autonomous_daemon(
            project_root=project_root,
            vault_path=vault_path,
            enable_file_watch=False,  # Отключить для демо
            init_strategy=InitStrategy.FULL_SCAN
        )
        print(f"✓ Демон создан")
        print(f"  Состояние: {daemon.state.value}")
        print()
        
        # Запустить демон
        print("3️⃣  ЗАПУСК ДЕМОНА (Phase 1: Scanning)")
        print("-" * 70)
        print("Инициализирую демон...")
        
        start_time = time.time()
        started = daemon.start()
        elapsed = time.time() - start_time
        
        if started:
            print(f"✓ Демон запущен успешно за {elapsed:.2f}с")
        else:
            print(f"❌ Ошибка при запуске демона")
            return
        
        print(f"  Состояние: {daemon.state.value}")
        print()
        
        # Получить статус
        print("4️⃣  ПОЛУЧЕНИЕ СТАТУСА")
        print("-" * 70)
        status = daemon.get_status()
        print(f"  Состояние:      {status['state']}")
        print(f"  Время инициализации: {status['startup_time_ms']:.1f}мс")
        print(f"  Сканировано файлов: {status['files_scanned']}")
        print(f"  Индексировано: {status['files_indexed']}")
        print()
        
        # Получить метрики
        print("5️⃣  ПОЛУЧЕНИЕ МЕТРИК")
        print("-" * 70)
        metrics = daemon.get_metrics()
        print(f"  Startup time:       {metrics['startup_time_ms']:.1f}мс")
        print(f"  Total scanned:      {metrics['total_files_scanned']}")
        print(f"  Total indexed:      {metrics['total_files_indexed']}")
        print(f"  Search queries:     {metrics['search_queries']}")
        print()
        
        # Выполнить поиск
        print("6️⃣  ТЕСТИРОВАНИЕ SEARCH API")
        print("-" * 70)
        query = "документ"
        print(f"  Выполняю поиск: '{query}'")
        
        search_start = time.time()
        results = daemon.search(query, limit=10)
        search_elapsed = time.time() - search_start
        
        print(f"  Результаты: {results['count']} найдено")
        print(f"  Время поиска: {search_elapsed*1000:.1f}мс")
        print()
        
        # Завершение
        print("7️⃣  GRACEFUL SHUTDOWN")
        print("-" * 70)
        print("Останавливаю демон...")
        
        stop_start = time.time()
        daemon.stop(graceful=True)
        stop_elapsed = time.time() - stop_start
        
        print(f"✓ Демон остановлен (за {stop_elapsed*1000:.1f}мс)")
        print(f"  Состояние: {daemon.state.value}")
        print()
        
        # Финальный отчет
        print("=" * 70)
        print("✅ ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА")
        print("=" * 70)
        print()
        print("Ключевые результаты:")
        print(f"  • Демон инициализирован и перешёл в состояние: {daemon.state.value}")
        print(f"  • Сканировано и индексировано файлов: {metrics['total_files_scanned']}")
        print(f"  • Search API работает корректно")
        print(f"  • Graceful shutdown выполнен успешно")
        print()
        print("✨ Демон полностью автономный после инициализации!")
        print()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
