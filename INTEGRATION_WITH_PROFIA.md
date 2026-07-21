# INTEGRATION_WITH_PROFIA.md — Интеграция Bober-Drive в PROFI-A

## 📌 Обзор

Этот документ описывает, как Bober-Drive интегрируется в экосистему PROFI-A как **инструмент поиска по документации для разработчиков**, не затрагивая основное приложение (Android/Kotlin) или backend.

---

## 🎯 Сценарии использования

### Сценарий 1: Локальный Python скрипт (разработчик)

**Когда:** Разработчик хочет использовать Bober-Drive из своего Python кода

**Как:**
```python
from driver.nexus_autonomous_daemon import create_autonomous_daemon

# Конфигурация
config = {
    'project_root': 'f:/PROFI-A/docs',              # Путь к документации
    'vault_path': 'f:/Bober-Drive/storage/profia_docs.vault',
    'checkpoint_path': 'f:/Bober-Drive/.nexus/checkpoint.json',
    'init_strategy': 'FULL_SCAN',                  # Полный скан при старте
    'enable_file_watch': True,                     # Мониторинг изменений
    'watchdog_timeout_sec': 30,
    'reindex_debounce_sec': 0.5,
}

# Инициализация демона
daemon = create_autonomous_daemon(config)

# Запуск (автоматически проходит 3 фазы: INITIALIZING → READY → MONITORING)
daemon.start()

# Поиск в документации
results = daemon.search("MVVM паттерны", limit=10)
for doc in results['hits']:
    print(f"{doc['file_path']}: {doc['title']}")

# Получение статуса
status = daemon.get_status()
print(f"Статус: {status['state']}, файлов индексировано: {status['indexed_files']}")

# Корректное завершение
daemon.stop(graceful=True)
```

**Результаты:** 
- Полнотекстовый поиск в 570+ markdown файлах
- Поддержка семантического поиска (скоро)
- Кэширование результатов

---

### Сценарий 2: VS Code IDE

**Когда:** Разработчик хочет искать документацию прямо из редактора

**Как:**

1. **Установка расширения:**
   ```bash
   cd vscode-extension/
   npm install
   npm run build
   code --install-extension ./nexus-search-extension-0.0.1.vsix
   ```

2. **Использование:**
   - Нажать `Ctrl+Shift+P` (macOS: `Cmd+Shift+P`)
   - Выбрать "Search Documentation"
   - Ввести поисковый запрос
   - Клик на результат открывает документ в редакторе

3. **Дополнительные команды:**
   - "Index Project" — ручное переиндексирование
   - "Show Search Statistics" — показать метрики
   - "Toggle Documentation Search" — вкл/выкл

**Результаты:**
- Встроенный поиск в VS Code
- Синтаксис подсветки markdown
- Интеграция с Hover и Completion

---

### Сценарий 3: gRPC микросервис

**Когда:** Другой сервис хочет искать в документации через сеть

**Конфигурация сервера:**
```python
from driver.nexus_orchestrator_v3 import create_nexus_orchestrator
from nexus_grpc_adapter import NexusGRPCAdapter

config = {
    'project_root': 'f:/PROFI-A/docs',
    'vault_path': 'f:/Bober-Drive/storage/profia_docs.vault',
    'mode': 'integration',
    'enable_auto_update': False,  # Отключено в production
}

# Создать оркестратор
orch = create_nexus_orchestrator(config)

# Запустить gRPC адаптер
adapter = NexusGRPCAdapter(orch, port=50051)
adapter.start()  # слушает на localhost:50051
```

**Клиентский код:**
```python
import grpc
from nexus_grpc_adapter import NexusGRPCAdapter

channel = grpc.aio.secure_channel('localhost:50051', ...)
stub = NexusSearchStub(channel)

response = await stub.Search(SearchRequest(query="3D сканер", limit=5))
for hit in response.hits:
    print(f"{hit.file_path}: {hit.score}")
```

**Результаты:**
- Асинхронный поиск через gRPC
- Масштабируемость (множество клиентов)
- Шифрование (TLS опционально)

---

## ✅ Чек-лист интеграции

### Шаг 1: Подготовка путей
- [ ] `f:/PROFI-A/docs/` существует и содержит 570+ markdown файлов
- [ ] `f:/Bober-Drive/` имеет права на запись для создания индекса
- [ ] Python 3.11+ установлен

### Шаг 2: Проверка зависимостей
```bash
cd f:/Bober-Drive
pip install -r requirements.txt
```
- [ ] Все зависимости установлены без ошибок

### Шаг 3: Первый запуск
```bash
python quick_agent_start.py
```
- [ ] Демон стартует и доходит до фазы READY
- [ ] Индекс создан в `storage/profia_docs.vault`
- [ ] Поиск работает с результатами

### Шаг 4: Верификация поиска
```python
from driver.nexus_autonomous_daemon import create_autonomous_daemon

daemon = create_autonomous_daemon({
    'project_root': 'f:/PROFI-A/docs',
    'vault_path': 'storage/profia_docs.vault',
})
daemon.start()

# Проверить поиск одного из документов
results = daemon.search("MVVM")
assert len(results['hits']) > 0, "Поиск не вернул результаты"
print(f"✅ Найдено {len(results['hits'])} результатов")

daemon.stop()
```
- [ ] Поиск возвращает релевантные результаты

### Шаг 5: Запуск E2E тестов
```bash
pytest test_autonomous_daemon_e2e.py -v
```
- [ ] Все 9 тестов проходят (9/9 ✅)

---

## 🔌 Интеграция в PROFI-A рабочий процесс

### Для разработчиков Android/Kotlin

**Использование:** Когда нужно быстро найти деталь архитектуры или API

```
1. Открыть VS Code (или IDE с расширением)
2. Ctrl+Shift+P → "Search Documentation"
3. Ввести "Room Database"
4. Кликнуть на результат "Room-Database.md"
5. Читать документацию рядом с кодом
```

### Для backend-разработчиков

**Использование:** Понять структуру данных и API контрактов

```python
# В своем backend сервисе
from nexus_grpc_adapter import NexusGRPCAdapter

# Поиск по документации
docs = search_docs("API контракты подписка")

# Использовать в документации API
for doc in docs:
    print(f"Смотри: {doc['file_path']}")
```

### Для DevOps

**Мониторинг:** Проверить статус индекса документации

```bash
# Проверить health
curl http://localhost:50051/health

# Получить метрики
curl http://localhost:50051/metrics
```

---

## 🚨 Часто задаваемые вопросы

**Q: Bober-Drive — это часть PROFI-A приложения?**
A: Нет. Это инструмент для разработчиков. Не встраивается в Android/backend, работает только локально.

**Q: Может ли пользователь PROFI-A использовать Bober-Drive?**
A: Нет. Это desktop tool для разработчиков, требует Python 3.11+.

**Q: Синхронизируется ли индекс в облако?**
A: Нет. Индекс хранится локально и не передается куда-либо.

**Q: Что будет, если я удалю `storage/profia_docs.vault`?**
A: Демон пересоздаст его при следующем старте (фаза INITIALIZING).

**Q: Совместим ли Bober-Drive с Windows/Linux/Mac?**
A: Windows полностью поддерживается. Linux/Mac требуют установки watchdog, но код кроссплатформный.

---

## 📋 Контрольные сроки

| Фаза | Описание | Статус |
|------|---------|--------|
| v3.0.0 | Autonomous daemon (3 фазы, E2E тесты 9/9) | ✅ |
| v3.1.0 | IDE интеграция (VS Code, IntelliJ) | 🔄 In Progress |
| v3.2.0 | Семантический поиск (ML embedding) | 📅 Planned |
| v4.0.0 | Multi-repo support (несколько проектов) | 📅 Planned |

---

## 📞 Поддержка

- **Документация:** `/AGENTS.local.md`
- **Быстрый старт:** `python quick_agent_start.py`
- **Тесты:** `pytest test_autonomous_daemon_e2e.py`
- **Логи:** `.nexus/daemon.log`
