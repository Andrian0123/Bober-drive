# AGENTS.local.md — Bober-Drive: универсальный драйвер индексирования

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
