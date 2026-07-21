# README_PROFIA_INTEGRATION.md — Быстрый старт Bober-Drive

**TL;DR:** Bober-Drive — это локальный индексер документации PROFI-A для поиска в 570+ markdown файлах.

---

## ⚡ 3 минуты: Запустить и использовать

### Шаг 1: Подготовка (1 минута)

```bash
cd f:/Bober-Drive

# Убедиться, что Python 3.11+ установлен
python --version

# Установить зависимости
pip install -r requirements.txt
```

### Шаг 2: Запуск демо (1 минута)

```bash
python quick_agent_start.py
```

**Что происходит:**
1. Демон инициализируется (сканирует `f:/PROFI-A/docs/`)
2. Создается индекс (`storage/profia_docs.vault`)
3. Выполняются 4 поиска-примера
4. Показываются метрики

**Ожидаемый результат:**
```
✅ Daemon initialized (Phase 1: INITIALIZING → Phase 2: READY)
📊 Indexed 573 files in 8.32 seconds
🔍 Search results for "MVVM":
   - docs/MVVM.md (score: 0.95)
   - docs/Architecture.md (score: 0.78)
...
📈 Metrics: avg_search_latency=12.5ms, vault_size=45.2MB
```

### Шаг 3: Использовать в коде (1 минута)

```python
from driver.nexus_autonomous_daemon import create_autonomous_daemon

# Инициализация
daemon = create_autonomous_daemon({
    'project_root': 'f:/PROFI-A/docs',
    'vault_path': 'storage/profia_docs.vault',
})

# Запуск
daemon.start()

# Поиск
results = daemon.search("3D сканер", limit=5)
for doc in results['hits']:
    print(f"{doc['file_path']}: {doc['title']}")

# Завершение
daemon.stop()
```

---

## 📚 Что это такое?

| Вопрос | Ответ |
|--------|-------|
| **Что такое Bober-Drive?** | Локальный индексер документации PROFI-A |
| **Где хранится индекс?** | `storage/profia_docs.vault` (локально) |
| **Какие файлы индексируются?** | Markdown файлы в `f:/PROFI-A/docs/` |
| **Это часть приложения PROFI-A?** | Нет. Это инструмент для разработчиков |
| **Может ли пользователь это использовать?** | Нет. Только разработчики (требует Python) |
| **Синхронизируется ли в облако?** | Нет. Полностью локально |

---

## 🎯 Основные возможности

### ✅ Работает сейчас

- **Полнотекстовый поиск (FTS5)** — поиск по названию и содержимому файлов
- **3-фазная архитектура** — автоматическая инициализация и мониторинг
- **Watchdog мониторинг** — автоматическое переиндексирование при изменении файлов
- **E2E тесты (9/9 passing)** — полная покрытие функциональности
- **gRPC адаптер** — возможность использования из других сервисов
- **VS Code расширение** — встроенный поиск в редакторе

### 🔄 В разработке

- Семантический поиск (ML embedding)
- Мультиязычная поддержка
- Веб-интерфейс для поиска

---

## 🚀 Типичные сценарии

### Сценарий 1: Я разработчик Android, нужна информация о MVVM

```
1. Открыть VS Code
2. Ctrl+Shift+P → "Search Documentation"
3. Ввести "MVVM"
4. Кликнуть результат → открыть документацию
5. Читать рядом с кодом
```

### Сценарий 2: Я backend-разработчик, нужно понять API контракты

```python
# В своем коде
from driver.nexus_autonomous_daemon import create_autonomous_daemon

daemon = create_autonomous_daemon({...})
daemon.start()

docs = daemon.search("API подписка", limit=10)
# Используешь информацию из docs в своем backend

daemon.stop()
```

### Сценарий 3: Я DevOps, нужно проверить статус индекса

```bash
# Проверить health gRPC сервиса
curl http://localhost:50051/health

# Получить метрики индексирования
curl http://localhost:50051/metrics
```

---

## 📖 Структура проекта

```
f:/Bober-Drive/
├── driver/                              # Основной код
│   ├── nexus_autonomous_daemon.py       # Демон (главный файл)
│   ├── nexus_orchestrator_v3.py         # Оркестратор (pipeline)
│   ├── nexus_graphify_v3.py            # Парсер markdown
│   ├── nexus_file_system_mapper_v3.py  # Сканер FS
│   └── lsp_server.py                    # LSP для IDE
│
├── storage/                             # Индекс (создается)
│   └── profia_docs.vault               # FTS5 база данных
│
├── vscode-extension/                    # VS Code plugin
│   ├── src/extension.ts                # TypeScript код
│   └── package.json
│
├── nexus_grpc_adapter.py                # gRPC адаптер
├── test_autonomous_daemon_e2e.py        # E2E тесты (9/9)
├── AGENTS.local.md                      # Локальные правила агента
├── INTEGRATION_WITH_PROFIA.md          # Подробная интеграция
└── quick_agent_start.py                 # Демонстрационный скрипт
```

---

## ❓ FAQ

**Q: Нужно ли устанавливать что-то еще кроме Python?**
A: Только зависимости: `pip install -r requirements.txt`

**Q: Сколько времени занимает первый индекс?**
A: 8-12 секунд для 570+ файлов на Windows 11

**Q: Что будет, если я отредактирую документацию?**
A: Демон автоматически переиндексирует изменённый файл в течение 0.5 сек

**Q: Как остановить демон?**
A: `daemon.stop()` в коде или `Ctrl+C` в терминале

**Q: Где посмотреть логи?**
A: `.nexus/daemon.log`

**Q: Можно ли использовать Bober-Drive на другом компьютере?**
A: Да, но только если там есть `f:/PROFI-A/docs/` и Python 3.11+

**Q: Это замедлит мой компьютер?**
A: Нет. Демон использует <50MB памяти и не замедляет систему

---

## 🔗 Полезные ссылки

- **Подробная документация:** `AGENTS.local.md`
- **Сценарии интеграции:** `INTEGRATION_WITH_PROFIA.md`
- **Исходный код демона:** `driver/nexus_autonomous_daemon.py`
- **E2E тесты:** `test_autonomous_daemon_e2e.py`
- **Технические тесты:** `test_integration.py`, `test_lsp_e2e.py`

---

## 🚀 Для агента (AI/LLM)

**Если ты читаешь это:**

1. Bober-Drive — инструмент поиска по документации, не часть основного приложения PROFI-A
2. Запусти `python quick_agent_start.py` чтобы увидеть живую работу
3. Читай `AGENTS.local.md` для полного понимания архитектуры
4. Используй `driver/nexus_autonomous_daemon.py` для встраивания в свой код

**Не путай с:**
- PROFI-A Android приложением (это отдельно)
- Backend сервисами (это отдельно)
- Cloud сервисами (индекс локальный)

---

## ✅ Статус

| Компонент | Версия | Статус |
|-----------|--------|--------|
| Autonomous Daemon | 3.0.0 | ✅ Ready |
| E2E тесты | 9/9 | ✅ Passing |
| VS Code расширение | 0.0.1 | ✅ Working |
| gRPC адаптер | 3.0.0 | ✅ Ready |
| Windows поддержка | - | ✅ Full |
| Linux поддержка | - | 🔄 Partial |
| macOS поддержка | - | 🔄 Partial |

**Платформа:** Windows 11, Python 3.11.15  
**Создано:** 2026-07-21  
**Последнее обновление:** 2026-07-21
