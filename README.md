# Bober-Drive

Professional local single-agent workspace driver for building, exploring, and navigating large projects with a lightweight project graph, local memory, and request intelligence.

## 🌟 Новое: Nexus Extended Architecture v2.1

**Bober-Drive v2.1** - полноценный **локальный "мини-датацентр"** для управления проектами:

### Базовая архитектура (v2.0)
- 🗂️ **Multi-project isolation** - управление множеством проектов
- 🧠 **Enhanced semantic search** - TF-IDF поиск в памяти
- ⚡ **Smart command execution** - сжатие вывода, кеширование
- 🤖 **AI agent connector** - Ollama/OpenAI интеграция
- 📋 **Task orchestration** - workflow engine

### Расширенные компоненты (v2.1) 🆕
- 🌐 **Browser Automation** - Playwright/Selenium для веб-скрапинга
- 🔧 **Command Proxy** - кросс-платформенная нормализация команд
- 📦 **Token Compressor** - интеллектуальное сжатие больших выводов
- 🎯 **Skill Engine** - динамическая загрузка навыков (prompt/python/shell)
- 🔌 **MCP Tool Registry** - реестр инструментов по протоколу MCP
- 🗄️ **Structured Memory** - Entity-Relation граф знаний
- 🔍 **Vector Memory** - векторный семантический поиск
- 📊 **Unified Dashboard** - централизованный мониторинг

📖 [Базовая архитектура](docs/NEXUS-ARCHITECTURE.md) | 🚀 [Расширенная архитектура](docs/NEXUS-EXTENDED.md) | 🔄 [Миграция](docs/NEXUS-MIGRATION.md)

## What this project is

Bober-Drive is a local orchestration layer for working with a project from a single AI agent runtime. Instead of a swarm of agents, it keeps one local brain and gives it:

- a workspace-aware project graph
- persistent local memory with semantic search
- command execution with intelligent compression
- request-chain intelligence
- task orchestration and workflow management
- multi-project management from single registry

## Main capabilities

### Classic Features
- local project indexing and graph building
- semantic graph search across files and metadata
- request history grouping and alphabetic request web
- command execution through the local runtime
- MCP-style local HTTP bridge for tool access

### Nexus Features (v2.0 + v2.1)

**Базовые компоненты:**
- **ProjectRegistry** - централизованное управление проектами
- **EnhancedMemoryStore** - семантический поиск через TF-IDF
- **EnhancedToolRuntime** - сжатие вывода команд и кеширование
- **Orchestrator** - очереди задач и workflow engine
- **AgentConnector** - интеграция с AI моделями (Ollama/OpenAI)

**Расширенные компоненты (v2.1):**
- **BrowserAutomation** - автоматизация браузера (Playwright/Selenium)
- **CommandProxy** - нормализация команд для Windows/Linux/Mac
- **TokenCompressor** - 4 стратегии сжатия (truncate/summary/smart/hybrid)
- **SkillEngine** - навыки prompt/python/shell/composite
- **MCPToolRegistry** - реестр MCP-инструментов с валидацией
- **StructuredMemory** - Entity-Relation модель для графа знаний
- **VectorMemory** - векторные embeddings для точного поиска
- **UnifiedDashboard** - мониторинг всех проектов в реальном времени

## Project structure

- `driver/` — runtime and local orchestration code
  - **Classic (v1.x):**
    - `local_driver.py` — классический драйвер (совместимость)
    - `driver_core.py` — базовые компоненты
    - `memory_store.py` — простое key-value хранилище
    - `tool_runtime.py` — базовый tool runtime
  - **Nexus Base (v2.0):**
    - `project_registry.py` — реестр многопроектного окружения
    - `orchestrator.py` — система управления задачами
    - `memory_enhanced.py` — улучшенная память с TF-IDF
    - `tool_runtime_enhanced.py` — расширенный runtime с сжатием
    - `agent_connector.py` — подключение к AI агентам
    - `nexus_integration.py` — интеграция всех компонентов
    - `nexus_cli.py` — CLI для управления проектами
  - **Nexus Extended (v2.1):**
    - `browser_automation.py` — автоматизация браузера
    - `command_proxy.py` — кросс-платформенные команды
    - `token_compressor.py` — сжатие больших выводов
    - `skill_engine.py` — динамическая загрузка навыков
    - `mcp_tool_registry.py` — реестр MCP-инструментов
    - `structured_memory.py` — Entity-Relation граф
    - `vector_memory.py` — векторный поиск
    - `unified_dashboard.py` — централизованный dashboard
- `.nexus/` — project state, cache, graph, request chain, and local memory
- `~/.nexus/projects/` — centralised multi-project registry (Nexus)
- `docs/` — architecture, guidelines, manuals, and intelligence docs
  - `NEXUS-ARCHITECTURE.md` — базовая архитектура v2.0
  - `NEXUS-EXTENDED.md` — расширенная архитектура v2.1
  - `NEXUS-MIGRATION.md` — руководство по миграции
  - `NEXUS-QUICKREF.md` — API quick reference


## Quick start

### Classic Driver (Single Project)

#### Initialize driver workspace

```powershell
python .\driver\local_driver.py init
```

#### Build the project graph

```powershell
python .\driver\local_driver.py scan
```

#### Search the graph

```powershell
python .\driver\local_driver.py search --search "driver graph"
```

#### Inspect structured request intelligence

```powershell
python .\driver\local_driver.py requests
```

### Nexus Multi-Project (New!)

#### Initialize a new project

```bash
python driver/nexus_cli.py init my-project --workspace ./my-project-dir
```

#### List all projects

```bash
python driver/nexus_cli.py list
```

#### Activate a project

```bash
python driver/nexus_cli.py activate my-project
```

#### Get project status

```bash
python driver/nexus_cli.py status my-project
```

#### Run full integration demo

```bash
python driver/nexus_integration.py
```

### Programmatic Usage

```python
from pathlib import Path
from driver.nexus_integration import NexusOrchestrator
from driver.orchestrator import TaskPriority

# Initialize orchestrator
nexus = NexusOrchestrator(
    project_name="my-app",
    workspace=Path("./my-app-dir")
)

# Save to memory
nexus.save_to_memory(
    key="feature-001",
    kind="task",
    content="Implement authentication system with JWT"
)

# Semantic search
results = nexus.search_memory("authentication", limit=5)

# Create and execute task
task_id = nexus.create_task_with_plan(
    description="Build and test application",
    steps=[
        {"description": "Install deps", "tool": "command", "params": {"command": "npm install"}},
        {"description": "Run tests", "tool": "command", "params": {"command": "npm test"}}
    ],
    priority=TaskPriority.HIGH
)

result = nexus.execute_task_with_tools(task_id)
stats = nexus.get_system_stats()
```

## Documentation

### Classic Architecture
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/LOCAL_DRIVER_GUIDE.md](docs/LOCAL_DRIVER_GUIDE.md)
- [docs/REQUEST_INTELLIGENCE.md](docs/REQUEST_INTELLIGENCE.md)
- [docs/OPERATION_MANUAL.md](docs/OPERATION_MANUAL.md)

### Nexus Architecture (New!)
- [docs/NEXUS-ARCHITECTURE.md](docs/NEXUS-ARCHITECTURE.md) - полная документация
- [docs/NEXUS-MIGRATION.md](docs/NEXUS-MIGRATION.md) - руководство по миграции

## Operational notes

The runtime is designed to work locally with Ollama. The model endpoint is configured in the local runtime config and points to the local Ollama API.

**Nexus features** require:
- Python 3.8+
- PyYAML (`pip install pyyaml`)
- Ollama (optional, for AI features)

## Project entrypoints

### Classic Driver
- [driver/local_driver.py](driver/local_driver.py) - main driver
- [driver/driver_core.py](driver/driver_core.py) - core components
- [driver/mcp_server.py](driver/mcp_server.py) - HTTP bridge

### Nexus System
- [driver/nexus_integration.py](driver/nexus_integration.py) - main orchestrator
- [driver/nexus_cli.py](driver/nexus_cli.py) - CLI interface
- [driver/project_registry.py](driver/project_registry.py) - project management
- [driver/orchestrator.py](driver/orchestrator.py) - task orchestration
- [driver/memory_enhanced.py](driver/memory_enhanced.py) - semantic memory
- [driver/tool_runtime_enhanced.py](driver/tool_runtime_enhanced.py) - command execution
- [driver/agent_connector.py](driver/agent_connector.py) - AI integration

## Architecture Comparison

| Feature | Classic | Nexus |
|---------|---------|-------|
| Projects | Single | Multiple with isolation |
| Memory | Basic key-value | TF-IDF semantic search |
| Commands | 4KB output limit | 60-90% compression |
| Tasks | Manual execution | Orchestrated workflows |
| AI | Direct HTTP | Unified connector + fallback |
| Cache | Basic context | Multi-layer with TTL |

## Next evolution path

The project is already positioned as a professional local driver and can be extended with:

- richer semantic search
- web UI for request graph visualization
- richer task dependency links
- more structured local memory persistence

### 1. Установка Ollama

#### Windows:
```powershell
# Скачайте с официального сайта
https://ollama.ai/download/windows

# Или через winget
winget install Ollama.Ollama
```

#### Linux:
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

### 2. Запуск Ollama сервера

```bash
ollama serve
```

Сервер запустится на `http://localhost:11434`

### 3. Использование агентов

#### Вариант А: Простой запуск (Windows CMD)
```cmd
launch-agent.bat hermes
```

#### Вариант Б: Продвинутое управление (PowerShell)
```powershell
# Список всех агентов
.\ollama-manager.ps1 list

# Список плагинов
.\ollama-manager.ps1 plugins

# Плагины для конкретного агента
.\ollama-manager.ps1 plugins hermes

# Установка агента
.\ollama-manager.ps1 install hermes

# Запуск агента
.\ollama-manager.ps1 launch hermes

# Статус системы
.\ollama-manager.ps1 status
```

## 🔌 Плагины

Система включает 16 плагинов:

1. **code-review** - Автоматический ревью кода
2. **refactor** - Рефакторинг и оптимизация
3. **debug** - Помощь в отладке
4. **web-search** - Поиск в интернете
5. **memory** - Долговременная память
6. **tools** - Выполнение внешних инструментов
7. **file-ops** - Операции с файлами
8. **git** - Интеграция с Git
9. **linting** - Линтинг и форматирование
10. **testing** - Генерация тестов
11. **shell-suggest** - Подсказки команд терминала
12. **vscode** - Интеграция с VS Code
13. **custom-plugins** - Создание своих плагинов
14. **api** - Работа с внешними API
15. **database** - Работа с БД
16. **web-scraping** - Извлечение данных

## 📦 Примеры использования

### 1. Hermes Agent - Универсальный помощник
```bash
ollama run nous-hermes-2
```

**Что умеет:**
- Самообучение и улучшение
- Логическое рассуждение
- Кодирование
- Долговременная память

**Плагины:** memory, tools, planning

### 2. OpenClaw - 100+ навыков
```bash
ollama run openclaw
```

**Что умеет:**
- Работа с файлами
- Web scraping
- Вызовы API
- Работа с базами данных
- Автоматизация задач

**Плагины:** file-ops, web-scraping, api-calls, database

### 3. OpenCode - Coding assistant
```bash
ollama run opencode
```

**Что умеет:**
- Написание кода
- Отладка
- Генерация тестов
- Интеграция с Git
- Документация

**Плагины:** git, linting, testing, docs

### 4. Droid - IDE интеграция
```bash
ollama run droid
```

**Что умеет:**
- Работа в VS Code
- Терминальные операции
- Управление workspace
- Мультиплатформенность

**Плагины:** vscode, terminal-ops, workspace

### 5. Pi - Extensible toolkit
```bash
ollama run pi-agent
```

**Что умеет:**
- Легковесный
- Система плагинов
- Расширяемость
- Хуки и API

**Плагины:** custom-plugins, api, hooks

## ⚙️ Конфигурация

### Основной манифест: `ollama-manifest.json`
```json
{
  "settings": {
    "ollama_host": "http://localhost:11434",
    "default_timeout": 120,
    "max_concurrent_agents": 3,
    "auto_update": true,
    "log_level": "info"
  }
}
```

### Конфигурация плагинов: `plugins-config.json`
Содержит описание всех плагинов, их команды и совместимость с агентами.

## 🎯 Рекомендации по выбору агента

### Для программирования:
- **OpenCode** - лучший выбор для coding
- **Droid** - если нужна интеграция с IDE

### Для автоматизации:
- **OpenClaw** - самый многофункциональный
- **Pi** - если нужна кастомизация

### Для обучения и анализа:
- **Hermes** - self-improving AI
- **OpenClaw** - широкие возможности

### Для работы с терминалом:
- **Droid** - специализируется на терминале
- **Pi** - минимализм и скорость

## 🔧 Создание своих плагинов (Pi Agent)

```javascript
// custom-plugin.js
module.exports = {
  name: "my-plugin",
  version: "1.0.0",
  commands: {
    myCommand: async (args) => {
      // Ваша логика
      return result;
    }
  }
};
```

Загрузка:
```bash
ollama run pi-agent
> load-plugin custom-plugin.js
```

## 📊 Сравнение агентов

| Агент | Размер | Скорость | Функционал | Плагины |
|-------|--------|----------|------------|---------|
| Hermes | ~4GB | Средняя | Универсальный | 3 |
| OpenClaw | ~6GB | Высокая | 100+ навыков | 4 |
| OpenCode | ~3GB | Высокая | Coding | 4 |
| Droid | ~2GB | Очень высокая | IDE/Terminal | 3 |
| Pi | ~500MB | Максимальная | Extensible | 3 |

## 🐛 Устранение неполадок

### Ollama не запускается
```bash
# Проверьте порт
netstat -ano | findstr :11434

# Перезапустите службу (Windows)
net stop Ollama
net start Ollama
```

### Модель не скачивается
```bash
# Проверьте подключение
curl http://localhost:11434/api/version

# Принудительное скачивание
ollama pull <model-name> --insecure
```

### Агент работает медленно
- Уменьшите размер контекста
- Используйте более легкую модель (Pi, Droid)
- Проверьте загрузку CPU/RAM

## 🔐 Безопасность

- Все агенты работают локально
- Данные не отправляются в облако (кроме платных)
- Для платных агентов храните API ключи в `.env`

## 📚 Дополнительные ресурсы

- [Документация Ollama](https://github.com/ollama/ollama)
- [Nous Research (Hermes)](https://nousresearch.com/)
- [OpenClaw GitHub](https://github.com/openclaw)
- [Community Discord](https://discord.gg/ollama)

## 🧪 Тестирование системы

### Быстрая проверка

```cmd
# Windows
test_nexus.bat

# Linux/macOS
chmod +x test_nexus.sh
./test_nexus.sh
```

### Ручной запуск

```bash
# 1. Проверка зависимостей
py -3 check_dependencies.py

# 2. Комплексные тесты (7 тестовых блоков)
py -3 test_nexus_full.py
```

### Что тестируется

- ✅ **Импорты модулей** (16 компонентов)
- ✅ **ProjectRegistry** (создание/активация проектов)
- ✅ **Orchestrator** (управление задачами)
- ✅ **Memory** (Enhanced/Structured/Vector)
- ✅ **Tools** (CommandProxy/TokenCompressor/SkillEngine/MCPToolRegistry)
- ✅ **UnifiedDashboard** (мониторинг системы)
- ✅ **NexusIntegration** (полная интеграция)

**Подробнее:** [docs/NEXUS-TESTING.md](docs/NEXUS-TESTING.md)

### Установка зависимостей

```bash
# Минимальная (рекомендуется)
py -3 -m pip install pyyaml numpy

# Полная (с опциональными компонентами)
py -3 -m pip install -r requirements.txt
```

## 📦 Сборка и Распространение

### Быстрая сборка ZIP-дистрибутива

```cmd
# Windows
build.bat

# Linux/macOS
chmod +x build.sh
./build.sh
```

**Результат:** `dist/nexus-v2.1.0.zip` готов к распространению

### Сборка pip-пакета

```bash
# Установить build (если нужно)
pip install build

# Создать wheel и source distribution
python -m build
```

**Результат:** `dist/nexus-extended-2.1.0-*.whl` готов к установке

### Установка из pip-пакета

```bash
# Базовая установка
pip install dist/nexus_extended-2.1.0-py3-none-any.whl

# С опциональными компонентами
pip install "nexus-extended[all]"
```

**После установки доступны команды:**
- `nexus` - основной CLI
- `nexus-dashboard` - web-интерфейс
- `nexus-test` - запуск тестов

**Подробнее:** [docs/BUILD.md](docs/BUILD.md) | [BUILD-COMPLETE.md](BUILD-COMPLETE.md)

## 🤝 Вклад

Добавляйте свои плагины и агенты:
1. Форкните репозиторий
2. Создайте конфигурацию в `plugins-config.json`
3. Отправьте pull request

## 📝 Лицензия

MIT License - используйте свободно

---

**Создано для Bober-Drive** | 2026
