# AGENTS.local.md — Bober-Drive в экосистеме PROFI-A

## 🎯 Кратко: Что такое Bober-Drive?

**Bober-Drive** — это **локальный индексер документации** для разработчиков PROFI-A. Он **НЕ является частью** мобильного приложения или backend'а. Это инструмент для сканирования и поиска документации в папке `f:/PROFI-A/docs/`.

| Аспект | Значение |
|--------|----------|
| **Назначение** | Индексирование документации (570+ markdown файлов) |
| **Используется** | Разработчиками локально для поиска в документации |
| **Платформа** | Windows 11, Python 3.11+ (desktop tool) |
| **НЕ используется** | В PROFI-A Android/Kotlin приложении, backend'е, cloud |
| **Хранилище индекса** | `storage/profia_docs.vault` (локальное) |

---

## 🏗️ Архитектура: 3-фазная автономность

Bober-Drive работает в **3 фазах** (одна непрерывная на фоне):

### Phase 1: INITIALIZING (инициализация)
- Полный скан `f:/PROFI-A/docs/` (570+ файлов)
- Парсинг всех markdown файлов
- Создание индекса FTS5 и графа зависимостей
- Сохранение checkpoint'а для восстановления
- **Результат:** демон переходит в фазу READY

### Phase 2: READY (готов к работе)
- Демон активен, принимает запросы поиска
- API доступен для локальных скриптов и IDE
- Индекс полностью загружен в памяти
- **Результат:** можно искать в документации

### Phase 3: MONITORING (мониторинг)
- Watchdog следит за изменениями файлов в `f:/PROFI-A/docs/`
- При изменении — автоматическое переиндексирование
- Debounce-буфер (0.5 сек) предотвращает дублирование
- Фоновый reindex-worker обновляет индекс
- **Результат:** индекс всегда актуален

---

## 📁 Иерархия файлов

```
f:/PROFI-A/
├── docs/                          ← ЭТО индексируется Bober-Drive
│   ├── MVVM.md
│   ├── 3D-сканер.md
│   ├── Подписка.md
│   ├── Room-Database.md
│   └── ... (570+ файлов)
│
└── Bober-drive/                   ← ЭТО сам индексер
    ├── driver/
    │   ├── nexus_autonomous_daemon.py (демон)
    │   ├── nexus_orchestrator_v3.py
    │   ├── nexus_graphify_v3.py
    │   └── ...
    ├── storage/
    │   └── profia_docs.vault      ← индекс (создаётся здесь)
    ├── AGENTS.local.md            ← этот файл
    ├── quick_agent_start.py
    └── README_PROFIA_INTEGRATION.md
```

---

## 🔧 Как использовать

### Вариант 1: Python скрипт (локально)

```python
from driver.nexus_autonomous_daemon import create_autonomous_daemon

config = {
    'project_root': 'f:/PROFI-A/docs',
    'vault_path': 'storage/profia_docs.vault',
    'init_strategy': 'FULL_SCAN',
}

daemon = create_autonomous_daemon(config)
daemon.start()

# Поиск
results = daemon.search("MVVM паттерны")
print(results)

daemon.stop()
```

### Вариант 2: IDE (VS Code)

1. Установить расширение из `vscode-extension/`
2. Команда: `Ctrl+Shift+P` → "Search Documentation"
3. Ввести query, получить результаты прямо в редактор

### Вариант 3: gRPC (для других сервисов)

```python
from nexus_grpc_adapter import NexusGRPCAdapter
from driver.nexus_orchestrator_v3 import create_nexus_orchestrator

orch = create_nexus_orchestrator(config)
adapter = NexusGRPCAdapter(orch, port=50051)
adapter.start()  # слушает на localhost:50051
```

---

## 📊 Мониторинг статуса

```python
status = daemon.get_status()
# {
#   "state": "READY",
#   "indexed_files": 573,
#   "last_scan": "2026-07-21T09:50:00",
#   "vault_size_mb": 45.2
# }

metrics = daemon.get_metrics()
# {
#   "search_latency_ms": 12.5,
#   "reindex_count": 3,
#   "files_watched": 573
# }
```

---

## ⚠️ Важные ограничения

1. **Только документация** — индексируются только файлы в `f:/PROFI-A/docs/`
   - Не индексируется исходный код PROFI-A
   - Не индексируется backend
   - Не индексируется базы данных

2. **Только локально** — нет облачного синхронизации
   - Индекс существует только на машине разработчика
   - Нет передачи данных в cloud
   - Работает offline

3. **Для разработчиков** — инструмент, не часть production
   - Не встраивается в Android приложение
   - Не используется пользователями PROFI-A
   - Не критичен для работы сервиса

---

## 🚀 Быстрый старт (агент)

Если нужно немедленно понять, как работает Bober-Drive:

1. Прочитать этот файл (ты сейчас его читаешь ✓)
2. Запустить `python quick_agent_start.py` — увидишь живую работу
3. Проверить логи в `.nexus/daemon.log`

**Одна строка для запуска:**
```bash
cd f:/Bober-Drive && python quick_agent_start.py
```

---

## 🔗 Связанные файлы

- `INTEGRATION_WITH_PROFIA.md` — Как интегрировать в PROFI-A workflow
- `README_PROFIA_INTEGRATION.md` — User-friendly guide
- `test_autonomous_daemon_e2e.py` — E2E тесты (9/9 passing)
- `driver/nexus_autonomous_daemon.py` — Основной модуль демона

---

## 📝 Версия

- **Версия Bober-Drive:** v3.0.0
- **Индексер:** NexusAutonomousDaemon
- **Стратегия индексирования:** FULL_SCAN + INCREMENTAL (Watchdog)
- **Платформа:** Windows 11, Python 3.11.15
- **Статус:** Production-ready
