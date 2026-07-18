# Nexus IDE Integration Guide v3.0.0

Полное руководство по интеграции Nexus Driver v3.0.0 с IDE для интеллектуального автодополнения кода и поиска по документации.

## Обзор архитектуры

```
┌─────────────────────────────────────────────────────────────┐
│                    IDE Integration Stack                     │
└─────────────────────────────────────────────────────────────┘

┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│   VS Code    │       │Android Studio│       │  IntelliJ    │
│  Extension   │       │    Plugin    │       │   Plugin     │
└──────┬───────┘       └──────┬───────┘       └──────┬───────┘
       │ LSP Client           │ LSP Client           │ LSP Client
       │                      │                      │
       └──────────────┬───────┴──────────────────────┘
                      │ JSON-RPC 2.0 (stdio)
                      ▼
            ┌─────────────────┐
            │   LSP Server    │ (driver/lsp_server.py)
            │   (Python)      │
            └────────┬────────┘
                     │ Method Calls
                     ▼
            ┌─────────────────┐
            │  gRPC Adapter   │ (nexus_grpc_adapter.py)
            │  (Port 50051)   │
            └────────┬────────┘
                     │
                     ▼
         ┌──────────────────────┐
         │ Nexus Orchestrator   │ (nexus_orchestrator_v3.py)
         │       v3.0.0         │
         └──────────┬───────────┘
                    │
         ┌──────────┼───────────┐
         ▼          ▼           ▼
    ┌────────┐ ┌────────┐ ┌─────────┐
    │ Vault  │ │ FTS5   │ │ Graph   │
    │ SQLite │ │ Index  │ │ Engine  │
    └────────┘ └────────┘ └─────────┘
```

## Компоненты

### 1. gRPC Adapter (nexus_grpc_adapter.py)

**Статус**: ✅ Полностью функционален (13/13 тестов проходят)

**Ответственность**:
- Предоставляет gRPC API для внешних интеграций
- Управляет жизненным циклом NexusOrchestrator
- Обрабатывает конфигурацию (auto-update отключен)
- Логирование операций

**API методы**:
```python
adapter.search(query, limit, search_type) → Dict[results, status, count]
adapter.ingest(file_path, content, metadata) → Dict[status, doc_id]
adapter.scan_project(project_root, deep_scan) → Dict[status, files_found, files_indexed]
adapter.health_check() → Dict[status, stats]
adapter.apply_config(config) → Dict[status]
adapter.shutdown(graceful) → Dict[status]
```

**Запуск**:
```bash
python nexus_grpc_adapter.py
# Слушает на порту 50051
```

**Тесты**:
```bash
python -m pytest test_integration.py -v
# 13 passed in 0.73s
```

### 2. LSP Server (driver/lsp_server.py)

**Статус**: ✅ Реализован, интегрирован с gRPC

**Ответственность**:
- Реализация Language Server Protocol
- Коммуникация по JSON-RPC 2.0 через stdio
- Делегирование поисковых запросов в gRPC Adapter
- Автоматическая индексация открытых файлов

**Поддерживаемые LSP методы**:
- `initialize`: Инициализация сервера
- `textDocument/didOpen`: Файл открыт (авто-индексация)
- `textDocument/didChange`: Файл изменён
- `textDocument/completion`: Автодополнение кода ✅
- `textDocument/hover`: Всплывающие подсказки ✅
- `textDocument/definition`: Переход к определению
- `textDocument/documentSymbol`: Структура документа
- `textDocument/rename`: Переименование
- `shutdown`: Завершение работы

**Логирование**:
```
~/.nexus/lsp_server.log
```

**Запуск вручную**:
```bash
python driver/lsp_server.py
# Ожидает JSON-RPC сообщения на stdin
```

### 3. VS Code Extension (vscode-extension/)

**Статус**: ✅ Реализовано, готово к компиляции

**Структура**:
```
vscode-extension/
├── package.json          # Манифест расширения
├── tsconfig.json         # TypeScript конфигурация
├── .eslintrc.json        # ESLint правила
├── src/
│   └── extension.ts      # Главный файл расширения
├── out/                  # Скомпилированный JS (после npm run compile)
└── README.md             # Документация
```

**Команды**:
- `searchDocumentation` (Ctrl+Shift+D): Поиск по документации
- `indexProject` (Ctrl+Shift+I): Индексация проекта
- `toggleCompletion`: Вкл/выкл автодополнения
- `showStats`: Статистика vault и токенов
- `openSettings`: Настройки расширения

**Настройки** (в VS Code settings.json):
```json
{
  "nexus.lspServerPath": "python",
  "nexus.lspServerScript": "driver/lsp_server.py",
  "nexus.completionEnabled": true,
  "nexus.hoverEnabled": true,
  "nexus.maxCompletionItems": 10,
  "nexus.tokenCountingEnabled": true,
  "nexus.vaultPath": "~/.nexus/integration/vault.db",
  "nexus.grpcPort": 50051
}
```

**Установка и компиляция**:
```bash
cd vscode-extension
npm install
npm run compile
# Создаст out/extension.js
```

**Отладка**:
```bash
# Откройте vscode-extension/ в VS Code
# Нажмите F5
# Запустится Extension Development Host
```

**Создание .vsix пакета**:
```bash
npm install -g @vscode/vsce
vsce package
# Создаст nexus-code-3.0.0.vsix
code --install-extension nexus-code-3.0.0.vsix
```

### 4. Android Studio Integration (планируется)

**Статус**: ❌ Не реализовано

**Опции**:
1. **LSP Plugin** (рекомендуется):
   - Используем существующий LSP plugin для IntelliJ/Android Studio
   - Настраиваем на driver/lsp_server.py
   - Переиспользуем всю логику LSP сервера

2. **Java Bridge**:
   - Создаём Java-обёртку над gRPC adapter
   - Прямые вызовы API без LSP

3. **Kotlin Client**:
   - Нативный клиент для Android
   - Использует gRPC напрямую

**Рекомендация**: Вариант 1 (LSP Plugin) — минимум дублирования кода.

## Workflow: Как работает автодополнение

### Сценарий 1: Пользователь печатает код

```
1. User types "async" in editor
2. VS Code → LSP Client: textDocument/completion
3. LSP Client → LSP Server: JSON-RPC completion request
4. LSP Server → extracts word "async" from document
5. LSP Server → gRPC Adapter: adapter.search("async", limit=10)
6. gRPC Adapter → Orchestrator: orchestrator.search("async")
7. Orchestrator → FTS5 Index: search full-text
8. FTS5 → returns results from vault
9. Orchestrator → gRPC Adapter: results
10. gRPC Adapter → LSP Server: {"results": [...]}
11. LSP Server → formats as LSP CompletionItem[]
12. LSP Client ← LSP Server: [{"label": "async/await guide", ...}]
13. VS Code displays completion popup with documentation
```

### Сценарий 2: Пользователь наводит курсор

```
1. User hovers over "asyncio.run"
2. VS Code → LSP Server: textDocument/hover
3. LSP Server → gRPC Adapter: adapter.search("asyncio.run", limit=1)
4. gRPC Adapter → Vault: lookup
5. Vault → returns doc content
6. LSP Server → formats as Hover response
7. VS Code displays hover popup with documentation
```

### Сценарий 3: Пользователь открывает файл

```
1. User opens example.py
2. VS Code → LSP Server: textDocument/didOpen
3. LSP Server → auto-index trigger
4. LSP Server → gRPC Adapter: adapter.ingest("example.py", content)
5. gRPC Adapter → Orchestrator: ingest_document()
6. Orchestrator → Vault: store + FTS5 index
7. File now searchable for future completions
```

## Установка: Полный процесс

### Шаг 1: Убедитесь, что Nexus Driver установлен

```bash
# Проверьте версию
python -c "import driver.nexus_orchestrator_v3; print('OK')"

# Если ошибка, установите:
pip install -e .
```

### Шаг 2: Создайте vault директорию

```bash
mkdir -p ~/.nexus/integration
```

### Шаг 3: Запустите интеграционные тесты

```bash
python -m pytest test_integration.py -v
# Должно быть: 13 passed
```

### Шаг 4: Установите VS Code Extension

```bash
cd vscode-extension
npm install
npm run compile
```

### Шаг 5: Запустите в режиме отладки

```bash
# В VS Code:
# 1. Откройте vscode-extension/
# 2. Нажмите F5
# 3. Откроется Extension Development Host
# 4. Откройте любой проект Python/JS/TypeScript
# 5. Начните печатать — должно появиться автодополнение
```

### Шаг 6: Проверьте логи

```bash
# LSP Server logs
tail -f ~/.nexus/lsp_server.log

# VS Code Output
# View → Output → Nexus
```

## Тестирование end-to-end

### Тест 1: Автодополнение

1. Откройте VS Code с установленным расширением
2. Создайте новый файл `test.py`
3. Напечатайте `import asy`
4. **Ожидаемый результат**: Появится dropdown с подсказками из документации
5. Выберите подсказку — вставится полный текст

### Тест 2: Hover

1. Напишите код: `def async_example(): pass`
2. Наведите курсор на `async_example`
3. **Ожидаемый результат**: Всплывающее окно с документацией (если есть в vault)

### Тест 3: Индексация проекта

1. Нажмите `Ctrl+Shift+I`
2. Выберите "Да"
3. **Ожидаемый результат**: Уведомление "Проект проиндексирован"
4. Логи должны показать количество проиндексированных файлов

### Тест 4: Поиск

1. Нажмите `Ctrl+Shift+D`
2. Введите "asyncio"
3. **Ожидаемый результат**: Уведомление с результатами поиска

### Тест 5: Статистика

1. Кликните на "Nexus" в status bar (внизу справа)
2. **Ожидаемый результат**: Popup с количеством документов, токенов и т.д.

## Token Counting (планируется)

**Статус**: ❌ Не реализовано

**План реализации**:

1. **Middleware в gRPC Adapter**:
   ```python
   @track_tokens
   def search(self, query, limit, search_type):
       # Auto-count tokens in query
       # Track if result came from vault vs LLM API
       # Save metrics
   ```

2. **Метрики**:
   - `tokens_used`: Токены, использованные LLM API
   - `tokens_saved`: Токены, сэкономленные через vault lookup
   - `cache_hit_rate`: Процент запросов, обслуженных из vault
   - `llm_api_calls`: Количество вызовов внешнего API

3. **Хранение**:
   ```sql
   CREATE TABLE token_metrics (
       timestamp INTEGER,
       query TEXT,
       source TEXT,  -- 'vault' | 'llm_api'
       tokens_used INTEGER,
       tokens_saved INTEGER
   );
   ```

4. **API метод**:
   ```python
   adapter.get_token_stats() → {
       "total_queries": 1250,
       "vault_hits": 980,
       "llm_calls": 270,
       "tokens_used": 12500,
       "tokens_saved": 48000,
       "savings_percent": 79.3
   }
   ```

## Устранение проблем

### Проблема: LSP сервер не запускается

**Симптомы**: В Output панели "ОШИБКА запуска: [Errno 2] No such file or directory: 'python'"

**Решение**:
```json
// settings.json
{
  "nexus.lspServerPath": "C:\\Python311\\python.exe"  // Windows
  // или
  "nexus.lspServerPath": "/usr/bin/python3"  // Linux/Mac
}
```

### Проблема: Не появляется автодополнение

**Причины**:
1. LSP сервер не подключён (проверьте логи)
2. Vault пустой (проиндексируйте проект: Ctrl+Shift+I)
3. Автодополнение отключено (проверьте `nexus.completionEnabled`)

**Диагностика**:
```bash
# Проверьте логи
tail -f ~/.nexus/lsp_server.log

# Должно быть:
# [LSP Server] LSP сервер готов
# [LSP Server] Completion request: ...
```

### Проблема: Permission denied при создании vault

**Решение**:
```bash
# Создайте директорию вручную
mkdir -p ~/.nexus/integration
chmod 755 ~/.nexus/integration
```

### Проблема: ModuleNotFoundError: driver.core.event_bus

**Решение**: ✅ **Исправлено** в этой версии
- Все импорты обновлены с `from core.event_bus` на `from driver.core.event_bus`

## Следующие шаги

### Приоритет 1: Android Studio Plugin

1. Установить IntelliJ LSP plugin
2. Настроить на `driver/lsp_server.py`
3. Протестировать в Android Studio
4. Создать документацию

### Приоритет 2: Token Counting Middleware

1. Добавить декоратор `@track_tokens` в gRPC adapter
2. Создать таблицу `token_metrics` в vault
3. Реализовать `get_token_stats()` API
4. Обновить VS Code Extension для отображения метрик

### Приоритет 3: Улучшения LSP

1. Реализовать `textDocument/definition` (jump to def)
2. Реализовать `textDocument/documentSymbol` (outline)
3. Добавить semantic search (вместо только FTS5)
4. Кеширование результатов для ускорения

## Архитектурные решения

### Почему gRPC?

- **Производительность**: Бинарный протокол, быстрее JSON REST
- **Типизация**: Protobuf схемы обеспечивают контракт API
- **Streaming**: Поддержка streaming для больших результатов
- **Кросс-платформенность**: Клиенты на любых языках (Python, Java, Kotlin, JS)

### Почему LSP?

- **Стандарт**: Поддерживается всеми современными IDE
- **Переиспользование**: Один LSP сервер работает с VS Code, IntelliJ, Vim, Emacs
- **Богатый функционал**: Completion, hover, definition, rename, outline

### Почему SQLite FTS5?

- **Скорость**: Полнотекстовый поиск за миллисекунды
- **Простота**: Нет внешних зависимостей, работает везде
- **Надёжность**: Промышленная база данных, используется в Chrome, Android

## Ссылки

- [LSP Specification](https://microsoft.github.io/language-server-protocol/)
- [VS Code Extension API](https://code.visualstudio.com/api)
- [gRPC Python Guide](https://grpc.io/docs/languages/python/)
- [SQLite FTS5](https://www.sqlite.org/fts5.html)

## Версия

Документ актуален для Nexus Driver v3.0.0 (2026-07-18)
