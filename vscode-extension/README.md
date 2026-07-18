# Nexus Code - VS Code Extension v3.0.0

Интеллектуальное автодополнение кода и поиск по документации на основе Nexus Driver v3.0.0.

## Возможности

- 🚀 **Умное автодополнение**: Контекстные подсказки из индексированной документации
- 🔍 **Быстрый поиск**: Поиск по всей документации проекта (Ctrl+Shift+D)
- 📚 **Авто-индексация**: Автоматическая индексация открытых файлов
- 💡 **Всплывающие подсказки**: Мгновенная информация при наведении
- 📊 **Учёт токенов**: Мониторинг использования LLM API и экономии
- ⚡ **Скорость**: Работает на gRPC и SQLite FTS5

## Требования

- Python 3.8+ (для LSP сервера)
- Nexus Driver v3.0.0
- VS Code 1.75.0+

## Установка

### 1. Установите зависимости

```bash
cd vscode-extension
npm install
```

### 2. Скомпилируйте TypeScript

```bash
npm run compile
```

### 3. Запустите в режиме отладки

- Откройте VS Code в папке `vscode-extension`
- Нажмите F5 для запуска Extension Development Host

### 4. Или соберите .vsix пакет

```bash
npm install -g @vscode/vsce
vsce package
code --install-extension nexus-code-3.0.0.vsix
```

## Использование

### Команды

- **Ctrl+Shift+D** (Cmd+Shift+D на Mac): Поиск по документации
- **Ctrl+Shift+I**: Индексация текущего проекта
- **Nexus: Toggle Completion**: Включить/выключить автодополнение
- **Nexus: Show Statistics**: Показать статистику vault и токенов
- **Nexus: Open Settings**: Открыть настройки расширения

### Настройки

- `nexus.lspServerPath`: Путь к Python (по умолчанию: `python`)
- `nexus.lspServerScript`: Путь к LSP серверу (по умолчанию: `driver/lsp_server.py`)
- `nexus.completionEnabled`: Включить автодополнение (по умолчанию: `true`)
- `nexus.hoverEnabled`: Включить всплывающие подсказки (по умолчанию: `true`)
- `nexus.maxCompletionItems`: Максимум элементов автодополнения (по умолчанию: `10`)
- `nexus.tokenCountingEnabled`: Учёт токенов (по умолчанию: `true`)
- `nexus.vaultPath`: Путь к базе vault (по умолчанию: `~/.nexus/integration/vault.db`)
- `nexus.grpcPort`: Порт gRPC (по умолчанию: `50051`)

## Архитектура

```
VS Code Extension
    ↓ (LSP Client)
LSP Server (Python)
    ↓ (вызовы методов)
gRPC Adapter
    ↓ (оркестрация)
Nexus Orchestrator v3
    ↓ (хранилище)
SQLite Vault + FTS5 Index
```

## Разработка

```bash
# Установка зависимостей
npm install

# Компиляция TypeScript
npm run compile

# Режим watch (авто-пересборка)
npm run watch

# Линтинг
npm run lint

# Запуск в режиме отладки
# Нажмите F5 в VS Code
```

## Устранение проблем

**LSP сервер не запускается:**
- Проверьте, что Python в PATH
- Проверьте настройку `nexus.lspServerPath`
- Смотрите панель вывода: View → Output → Nexus

**Не появляется автодополнение:**
- Убедитесь, что `nexus.completionEnabled` = `true`
- Сначала проиндексируйте проект: Ctrl+Shift+I
- Проверьте логи LSP сервера: `~/.nexus/lsp_server.log`

**Ошибки прав доступа:**
- Убедитесь, что директория vault существует: `~/.nexus/integration/`
- Проверьте права на запись

## Лицензия

MIT

## Ссылки

- [GitHub Repository](https://github.com/Bober-Drive/Bober-drive)
- [Nexus Driver Documentation](https://github.com/Bober-Drive/Bober-drive)
