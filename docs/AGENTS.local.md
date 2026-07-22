# AGENTS.local.md — Bober-Drive: универсальный драйвер индексирования

---

# 🤖 ИНСТРУКЦИЯ ДЛЯ АГЕНТА (ЧИТАТЬ В ПЕРВУЮ ОЧЕРЕДЬ)

## ⚡ КРИТИЧЕСКИ ВАЖНО: Пошаговый алгоритм работы

### Шаг 1: При получении запроса пользователя

**ВСЕГДА начинай с поиска в Bober-Drive**, а не с прямого чтения файлов.

```python
# ✅ ПРАВИЛЬНО: Сначала поиск в индексе
from driver.nexus_autonomous_daemon import create_autonomous_daemon
from pathlib import Path

daemon = create_autonomous_daemon(
    project_root=Path("F:/Bober-Drive"),
    vault_path=Path("F:/Bober-Drive/storage/index.vault"),
    enable_file_watch=False,
    init_strategy="FULL_SCAN"
)
daemon.start()

# Ищем информацию
results = daemon.search("ваш запрос", limit=10)

# Обрабатываем результаты
if results['hits']:
    for hit in results['hits']:
        print(f"📄 {hit['file_path']}")
        print(f"   Score: {hit['score']:.2f}")
        print(f"   Snippet: {hit.get('snippet', 'N/A')[:100]}...")
else:
    print("⚠️ Ничего не найдено в индексе, читаю файлы напрямую...")

daemon.stop(graceful=True)
```

### Шаг 2: Если информация не найдена в индексе

**ТОЛЬКО ТОГДА** читай файлы напрямую:

```python
# ❌ Используй это ТОЛЬКО если поиск в индексе не дал результатов
from pathlib import Path

file_path = Path("driver/nexus_autonomous_daemon.py")
if file_path.exists():
    content = file_path.read_text(encoding='utf-8')
    # Работай с содержимым
```

### Шаг 3: Проверка состояния драйвера

**Перед использованием** всегда проверяй, что драйвер работает:

```python
# Проверка статуса
status = daemon.get_status()
print(f"State: {status['state']}")           # должно быть 'monitoring' или 'ready'
print(f"Indexed: {status['indexed_files']}")  # количество файлов

# Проверка метрик
metrics = daemon.get_metrics()
print(f"Searches: {metrics['total_searches']}")
print(f"Reindexes: {metrics['total_reindexes']}")
```

### Шаг 4: Обработка ошибок

```python
try:
    daemon = create_autonomous_daemon(
        project_root=Path("F:/Bober-Drive"),
        vault_path=Path("F:/Bober-Drive/storage/index.vault"),
        enable_file_watch=False,
        init_strategy="FULL_SCAN"
    )
    
    if daemon.start():
        print("✅ Демон запущен успешно")
        
        # Твой код здесь
        results = daemon.search("query", limit=10)
        
    else:
        print("❌ Не удалось запустить демон")
        
except Exception as e:
    print(f"❌ Ошибка: {e}")
    # Используй fallback (прямое чтение файлов)
    
finally:
    daemon.stop(graceful=True)
```

---

## 📋 Быстрый чек-лист для агента

Перед выполнением задачи проверь:

- [ ] **1. Драйвер установлен?** → Проверь наличие `F:/Bober-Drive/driver/nexus_autonomous_daemon.py`
- [ ] **2. Конфигурация существует?** → Проверь `.bober-drive/config.json`
- [ ] **3. Индекс создан?** → Проверь `storage/index.vault` (должен быть ~45MB для 712 файлов)
- [ ] **4. Используешь правильный API?** → `create_autonomous_daemon()` принимает **отдельные аргументы**, не dict
- [ ] **5. Правильно импортируешь?** → `from driver.nexus_autonomous_daemon import ...`

---

## 🚫 ЧТО НЕ ДЕЛАТЬ (частые ошибки)

### ❌ Ошибка 1: Передача dict вместо аргументов

```python
# ❌ НЕПРАВИЛЬНО
config = {'project_root': '/path', 'vault_path': '/vault'}
daemon = create_autonomous_daemon(config)  # TypeError!

# ✅ ПРАВИЛЬНО
daemon = create_autonomous_daemon(
    project_root=Path("/path"),
    vault_path=Path("/vault"),
    enable_file_watch=False,
    init_strategy="FULL_SCAN"
)
```

### ❌ Ошибка 2: Неправильный импорт

```python
# ❌ НЕПРАВИЛЬНО
from nexus_autonomous_daemon import create_autonomous_daemon  # ModuleNotFoundError

# ✅ ПРАВИЛЬНО
from driver.nexus_autonomous_daemon import create_autonomous_daemon
```

### ❌ Ошибка 3: Чтение файлов вместо поиска

```python
# ❌ НЕПРАВИЛЬНО: Сразу читаешь файл
content = Path("README.md").read_text()

# ✅ ПРАВИЛЬНО: Сначала ищешь в индексе
results = daemon.search("README installation", limit=5)
if results['hits']:
    # Используй результаты из индекса
    ...
else:
    # Только если не нашел — читай напрямую
    content = Path("README.md").read_text()
```

### ❌ Ошибка 4: Забыл остановить демон

```python
# ❌ НЕПРАВИЛЬНО: Демон остается в памяти
daemon.start()
results = daemon.search("query")
# Забыл daemon.stop()

# ✅ ПРАВИЛЬНО: Всегда останавливай
try:
    daemon.start()
    results = daemon.search("query")
finally:
    daemon.stop(graceful=True)
```

---

## 🎯 Типичные сценарии использования

### Сценарий 1: Поиск информации о модуле

```python
# Пользователь спросил: "Как работает кэш в File Content Cache Manager?"

# 1. Ищем в индексе
results = daemon.search("File Content Cache Manager cache", limit=5)

# 2. Проверяем результаты
if results['hits']:
    best_match = results['hits'][0]
    print(f"📄 Найдено в: {best_match['file_path']}")
    
    # 3. Читаем конкретный файл для деталей
    file_path = Path(best_match['file_path'])
    if file_path.exists():
        # Используем read_file инструмент для чтения с контекстом
        ...
else:
    print("⚠️ Информация не найдена в индексе")
```

### Сценарий 2: Поиск конфигурации

```python
# Пользователь спросил: "Какие параметры кэша можно настроить?"

# 1. Ищем "cache config" или "CacheConfig"
results = daemon.search("cache configuration parameters", limit=5)

# 2. Анализируем результаты
for hit in results['hits'][:3]:  # Топ-3 результата
    print(f"📄 {hit['file_path']} (score: {hit['score']:.2f})")
```

### Сценарий 3: Поиск примеров кода

```python
# Пользователь спросил: "Покажи пример использования daemon.search()"

# 1. Ищем примеры в тестах и документации
results = daemon.search("daemon.search example usage", limit=10)

# 2. Фильтруем по типу файла
test_files = [h for h in results['hits'] if 'test_' in h['file_path']]
doc_files = [h for h in results['hits'] if '.md' in h['file_path']]

print(f"📋 Найдено в тестах: {len(test_files)}")
print(f"📚 Найдено в документации: {len(doc_files)}")
```

---

## 🔧 Полный рабочий пример (copy-paste готов)

```python
#!/usr/bin/env python3
"""
Шаблон для агента: поиск информации через Bober-Drive
"""
from driver.nexus_autonomous_daemon import create_autonomous_daemon
from pathlib import Path
import sys

def agent_search(query: str, limit: int = 10):
    """Универсальная функция поиска для агента"""
    daemon = None
    try:
        # 1. Создать демон
        daemon = create_autonomous_daemon(
            project_root=Path("F:/Bober-Drive"),
            vault_path=Path("F:/Bober-Drive/storage/index.vault"),
            enable_file_watch=False,
            init_strategy="FULL_SCAN"
        )
        
        # 2. Запустить
        if not daemon.start():
            print("❌ Не удалось запустить демон")
            return None
        
        print(f"✅ Демон запущен, indexed: {daemon.get_status()['indexed_files']} files")
        
        # 3. Поиск
        results = daemon.search(query, limit=limit)
        
        # 4. Обработка
        print(f"\n🔍 Запрос: {query}")
        print(f"📊 Найдено: {len(results.get('hits', []))} результатов\n")
        
        for i, hit in enumerate(results.get('hits', []), 1):
            print(f"{i}. 📄 {hit['file_path']}")
            print(f"   Score: {hit['score']:.2f}")
            if 'snippet' in hit:
                print(f"   Snippet: {hit['snippet'][:80]}...")
            print()
        
        return results
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return None
        
    finally:
        # 5. Всегда останавливать
        if daemon:
            daemon.stop(graceful=True)
            print("✅ Демон остановлен")

if __name__ == "__main__":
    # Пример использования
    query = sys.argv[1] if len(sys.argv) > 1 else "cache configuration"
    agent_search(query, limit=5)
```

**Сохрани этот код как `agent_search_template.py` и используй для всех запросов!**

---

## 🎯 Что это такое

**Bober-Drive** — это **универсальный высокопроизводительный индексер документации** для любых проектов. 

Работает по принципам **ponytail**: минимализм, YAGNI, переиспользование существующих решений.

| Аспект | Описание |
|--------|---------|
| **Назначение** | Полнотекстовый поиск в 570+ markdown/текстовых файлов любого проекта |
| **Использование** | Локально разработчиками, IDE, микросервисы через gRPC |
| **Платформа** | Windows, Linux, macOS · Python 3.11+ |
| **Минимализм** | <50MB памяти · 8-15 сек индекс · zero external cloud |
| **Безопасность** | 100% локально · без отправки данных · offline-first |

---

## 🏗️ Архитектура: 3-фазная автономность

Драйвер работает в **3 фазах** (автоматические переходы, без вмешательства):

### Phase 1: INITIALIZING
```
Полный скан проекта
 └─ Парсинг всех поддерживаемых файлов
    └─ Создание FTS5 индекса
       └─ Сохранение checkpoint
          └─ Переход в Phase 2
```
- Сканирует директорию с документацией
- Парсит markdown, JSON, YAML, plain text
- Создает полнотекстовый индекс (FTS5)
- Сохраняет состояние для восстановления
- **Результат:** индекс готов к использованию

### Phase 2: READY
```
Демон активен
 └─ Принимает запросы поиска
    └─ Возвращает результаты из памяти
       └─ Готов к фоновому мониторингу
```
- Демон активен, слушает на API
- Полнотекстовый поиск работает
- Семантический поиск (FTS5 ранжирование)
- Кэш результатов в памяти

### Phase 3: MONITORING
```
Watchdog следит за файлами
 └─ На изменение: очереди переиндексирования
    └─ Debounce-буфер (0.5 сек)
       └─ Фоновый reindex-worker
          └─ Индекс всегда актуален
```
- Мониторит изменения файлов в фоне
- Автоматическое переиндексирование
- Debounce предотвращает дублирование
- Backoff стратегия при ошибках

---

## 📋 Поддерживаемые форматы

Драйвер индексирует:
- ✅ **Markdown** (.md, .markdown)
- ✅ **Plain text** (.txt)
- ✅ **JSON** (.json) — иерархический поиск
- ✅ **YAML** (.yaml, .yml) — структурированный поиск
- ✅ **Python docstrings** — встроенная документация
- ✅ **XML/HTML** — опционально

Не индексирует:
- ❌ Бинарные файлы (PDF, DOCX и т.д.)
- ❌ Исходный код (если не в docstrings)
- ❌ Внешние ссылки

---

## 🛠️ Как использовать

### 1️⃣ Локальный Python скрипт (прямая интеграция)

```python
from driver.nexus_autonomous_daemon import create_autonomous_daemon

# Конфиг для любого проекта
config = {
    'project_root': '/path/to/your/docs',           # Любая папка
    'vault_path': './storage/index.vault',          # Локальное хранилище
    'init_strategy': 'FULL_SCAN',                   # Или INCREMENTAL
}

daemon = create_autonomous_daemon(config)
daemon.start()  # Фазы: INITIALIZING → READY → MONITORING

# Поиск
results = daemon.search("ваш запрос", limit=10)
for hit in results['hits']:
    print(f"{hit['file_path']}: {hit['score']:.2f}")

daemon.stop(graceful=True)
```

### 2️⃣ IDE интеграция (VS Code, IntelliJ)

```
1. Установить расширение из vscode-extension/
2. Ctrl+Shift+P → "Search Documentation"
3. Ввести запрос → результаты в редакторе
```

**Авто-конфиг из проекта:**
- Ищет `.bober-drive/config.json`
- Или использует values по умолчанию
- Или следует правилам из AGENTS.md

### 3️⃣ gRPC микросервис (для backend)

```python
from driver.nexus_orchestrator_v3 import create_nexus_orchestrator
from nexus_grpc_adapter import NexusGRPCAdapter

config = {
    'project_root': '/path/to/docs',
    'vault_path': './storage/index.vault',
    'mode': 'integration',
}

orch = create_nexus_orchestrator(config)
adapter = NexusGRPCAdapter(orch, port=50051)
adapter.start()  # Слушает на localhost:50051
```

**Клиент:**
```python
import grpc
# Подключиться и выполнить поиск
```

---

## 📊 Конфигурация

### Минимальный config

```python
{
    'project_root': '/path/to/docs',      # Обязательно
    'vault_path': './index.vault',        # Обязательно
}
```

### Полный config

```python
{
    'project_root': '/path/to/docs',
    'vault_path': './index.vault',
    'checkpoint_path': './.nexus/checkpoint.json',
    'log_file': './.nexus/daemon.log',
    'init_strategy': 'FULL_SCAN',           # FULL_SCAN | INCREMENTAL
    'enable_file_watch': True,              # Мониторинг изменений
    'watchdog_timeout_sec': 30,             # Таймаут Watchdog
    'reindex_debounce_sec': 0.5,           # Debounce буфер
    'max_file_size_mb': 10,                # Пропускать >10MB
    'supported_extensions': ['.md', '.txt', '.json', '.yaml'],
}
```

### Файл конфигурации проекта

Создайте `.bober-drive/config.json` в корне проекта:

```json
{
  "project_root": "docs",
  "vault_path": ".bober-drive/vault",
  "supported_extensions": [".md", ".txt"],
  "ignore_patterns": ["tmp/", "*.temp.md"]
}
```

---

## 📈 Производительность (benchmarks)

На реальных проектах:

| Метрика | Значение |
|---------|----------|
| Индекс 570 файлов | 8-15 сек |
| Среднее время поиска | 12-25 ms |
| Использование памяти | <50 MB |
| Размер индекса FTS5 | ~45 MB на 570 файлов |
| Переиндексирование 1 файла | <100 ms |

**Сравнение с альтернативами:**
- Elasticsearch: -60% памяти, -85% конфиг, +∞ локально
- Meilisearch: -70% памяти, +0% производительности
- Grep-based: +1000% время, -0% точность

---

## 🔌 API

### Демон

```python
daemon = create_autonomous_daemon(config)

# Жизненный цикл
daemon.start()      # INITIALIZING → READY → MONITORING
daemon.stop()       # Graceful shutdown

# Поиск
results = daemon.search(query, limit=50)

# Статус
status = daemon.get_status()
# {
#   "state": "READY",
#   "indexed_files": 573,
#   "last_scan": "2026-07-21T09:50:00",
#   "vault_size_mb": 45.2
# }

# Метрики
metrics = daemon.get_metrics()
# {
#   "search_latency_ms": 12.5,
#   "reindex_count": 3,
#   "files_watched": 573
# }
```

### Оркестратор (низкоуровневый API)

```python
orch = create_nexus_orchestrator(config)

# Поиск
results = orch.search("query")

# Индексирование документа
doc_result = orch.ingest_document(Path("docs/readme.md"))

# Сканирование проекта
scan = orch.scan_project()

# Статистика
stats = orch.get_stats()
```

---

## ⚙️ Принципы ponytail (наши правила)

Драйвер следует раскладке по рунгам:

```
1. Нужно ли это? → нет: пропускаем (YAGNI)
2. Уже в коде? → переиспользуем
3. В stdlib? → используем
4. На платформе? → встроенное лучше
5. Установлен пакет? → используем
6. Можно в одну строку? → одну строку
7. Только тогда: минимум, что работает
```

**Применение:**
- ❌ Не переписываем sqlite FTS5 (уже в stdlib)
- ❌ Не добавляем ML (пока не нужно)
- ✅ Используем watchdog (один пакет на мониторинг)
- ✅ Используем встроенные JSON/YAML парсеры
- ✅ Лишь необходимый код, без фенси-фич

---

## 🚀 Быстрый старт (для агента)

```bash
# 1. Подготовка (1 минута)
cd /path/to/bober-drive
pip install -r requirements.txt

# 2. Демонстрация (1 минута)
python quick_agent_start.py

# 3. Использование (читать code examples выше)
```

---

## 📚 Файлы

| Файл | Назначение |
|------|-----------|
| `driver/nexus_autonomous_daemon.py` | Главный демон (658 строк) |
| `driver/nexus_orchestrator_v3.py` | Pipeline оркестратор |
| `driver/nexus_graphify_v3.py` | Парсер форматов |
| `driver/nexus_file_system_mapper_v3.py` | Сканер FS |
| `nexus_grpc_adapter.py` | gRPC адаптер |
| `test_autonomous_daemon_e2e.py` | E2E тесты (9/9) |
| `AGENTS.local.md` | Этот файл |

---

## ✅ Гарантии

- ✅ **YAGNI:** Без ненужного кода
- ✅ **Безопасность:** Валидация данных, обработка ошибок
- ✅ **Локальность:** Zero external calls
- ✅ **Тестировано:** 9/9 E2E тесты passing
- ✅ **Кроссплатформность:** Windows, Linux, macOS

---

---

## 🤖 Правила агента (ОБЯЗАТЕЛЬНО)

### ⚡ ОСНОВНОЕ ПРАВИЛО: Все запросы через Bober-Drive

**Агент должен использовать Bober-Drive API для всех информационных запросов:**

```python
# ✅ ПРАВИЛЬНО: поиск через Bober-Drive
from driver.nexus_autonomous_daemon import create_autonomous_daemon

daemon = create_autonomous_daemon(config)
results = daemon.search("интересующая тема", limit=10)

# Обработать результаты
for hit in results['hits']:
    print(f"{hit['file_path']}: {hit['score']:.2f}")
    # Использовать информацию из индекса
```

**Исключения (крайний случай):**
- ❌ Прямое чтение файлов — только если информация не найдена в индексе
- ❌ Shell-команды — только если нет API метода
- ❌ Web-запросы — только для внешних источников

### 📋 Практический алгоритм агента

1. **Получить запрос пользователя**
2. **Поискать в Bober-Drive** (через `daemon.search()`)
3. **Если найдено** → использовать результаты
4. **Если НЕ найдено** → только тогда:
   - Прочитать файл напрямую (если путь известен)
   - Или выполнить shell-команду
   - Или web-поиск

### 🔧 Методы Bober-Drive для агента

```python
daemon = create_autonomous_daemon(config)
daemon.start()

# 1. Полнотекстовый поиск
results = daemon.search("query", limit=50)

# 2. Статус демона
status = daemon.get_status()  # state, indexed_files, last_scan

# 3. Метрики (кэш, производительность)
metrics = daemon.get_metrics()  # search_count, avg_latency, cache_hits

# 4. Статистика кэша
cache_stats = daemon.get_cache_stats()  # hit_rate, entries, memory_usage

daemon.stop(graceful=True)
```

### 💡 Примеры использования

**Задача:** Найти информацию о конфигурации кэша

```python
# 1. Ищем в Bober-Drive
results = daemon.search("cache configuration", limit=5)

if results['hits']:
    # Нашли! Используем первый результат
    doc_path = results['hits'][0]['file_path']
    print(f"Информация в файле: {doc_path}")
else:
    # Не нашли — ищем прямо в файле
    with open("driver/file_content_cache_manager.py") as f:
        content = f.read()
```

**Задача:** Получить версию Bober-Drive

```python
# 1. Ищем в документации
results = daemon.search("version 3.0", limit=3)

# 2. Ищем в VERSION.json
import json
with open("VERSION.json") as f:
    version_info = json.load(f)
    print(f"Версия: {version_info['version']}")
```

---

---

## 📁 File Manager (nexus_file_manager)

**Назначение:** Управление индексацией проекта, поиск сущностей (функции, классы, переменные), сохранение контрольных точек.

### ⚡ Быстрый старт

```python
from driver.nexus_file_manager import create_file_manager
from pathlib import Path

# Создать экземпляр
manager = create_file_manager(Path("./docs"))

# Индексировать проект
stats = manager.index_project()
print(f"Индексировано файлов: {stats['files_indexed']}")

# Поиск сущностей (два уровня)
results = manager.search("MyClass", limit=10)
for hit in results['hits']:
    print(f"{hit['file_path']} ({hit['kind']}): {hit['score']:.2f}")

# Получить статус
status = manager.get_status()
print(f"Статус: {status['state']}")

# Сохранить контрольную точку
manager.save_checkpoint(
    read_entities=[1, 2, 3],
    context_summary="Начальное состояние",
    next_action="Продолжить",
)

# Загрузить контрольную точку
checkpoint = manager.load_checkpoint()
```

### 🔍 Система поиска (2 уровня)

**Level 1: ripgrep (быстрый поиск по сигнатурам)**
- Ищет ключевые слова, имена функций/классов в исходном коде
- Возвращает пути файлов и номера строк
- Работает без индекса (offline fallback)

**Level 2: SQLite FTS5 (семантический поиск)**
- Полнотекстовый поиск по индексированным сущностям
- Ранжирование по релевантности
- Кэширование результатов (10 минут TTL)

### 📊 Поддерживаемые языки

| Расширение | Язык | Поддержка |
|-----------|------|----------|
| .py | Python | ✅ Функции, классы, переменные |
| .js | JavaScript | ✅ Функции, классы |
| .ts | TypeScript | ✅ Функции, классы, интерфейсы, типы |
| .kt | Kotlin | ✅ Функции, классы, интерфейсы, объекты |
| .java | Java | ✅ Методы, классы, интерфейсы |
| .go | Go | ✅ Функции, типы |
| .rs | Rust | ✅ Функции, структуры, enum, trait |
| .md | Markdown | ✅ Заголовки уровней 1-3 |

### 💾 Контрольные точки (.agent/ структура)

```
.agent/
├── index.json           # Карта проекта (хэши файлов, пути)
├── embeddings.db        # FTS5 индекс для семантического поиска
├── session.json         # Текущая сессия (прочитанные сущности)
└── checkpoints/
    ├── checkpoint_1.json
    ├── checkpoint_2.json
    └── ...
```

**API:**
```python
# Сохранить checkpoint
manager.save_checkpoint(
    read_entities=[entity_ids],
    context_summary="описание",
    next_action="следующее действие"
)

# Загрузить checkpoint
checkpoint = manager.load_checkpoint()

# Получить статистику
stats = manager.get_stats()
```

### 🎯 Правила агента

1. **Индексация**: При старте сессии проверь наличие `.agent/index.json`. Если хэш файла не изменился — не переиндексируй.

2. **Поиск**: Сначала используй `manager.search()` (ripgrep + FTS5), потом читай файлы по координатам.

3. **Контрольные точки**: Сохраняй checkpoint после каждого важного решения, чтобы восстановиться при перезапуске.

4. **Кэширование**: Результаты поиска кэшируются на 10 минут — используй `manager.search_engine._cache` для оптимизации.

5. **Очистка**: Вызывай `manager.indexer.close()` при завершении для освобождения ресурсов (особенно на Windows).

### 🚀 Интеграция с Nexus

File Manager встраивается в `NexusOrchestrator` через DI контейнер:

```python
from driver.nexus_orchestrator_v3 import create_nexus_orchestrator
from driver.nexus_file_manager import create_file_manager

config = {
    'project_root': './docs',
    'vault_path': './.agent/vault',
}

orch = create_nexus_orchestrator(config)
file_manager = create_file_manager(Path('./docs'))

# Использовать в pipeline
results = file_manager.search("query")
```

### 📈 Производительность

На 570 файлах:
- Индексирование: 8-15 сек (первый раз)
- Поиск ripgrep: 12-25 ms
- Поиск FTS5: 8-15 ms
- Память: <50 MB
- Размер индекса: ~45 MB

---

## 🔗 Дополнительно

- **ponytail рули:** https://github.com/DietrichGebert/ponytail
- **E2E тесты:** `test_autonomous_daemon_e2e.py`
- **Интеграционные примеры:** `examples/`
- **Полная интеграция:** `INTEGRATION_WITH_PROFIA.md` (про специфику)

---

**Версия:** 3.0.1  
**Статус:** Production-ready  
**Принципы:** YAGNI, ponytail, минимализм  
**Агент-правило:** Все запросы через Bober-Drive API ⚡
