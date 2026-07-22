# 🚀 Bober-Drive Integration Guide для PROFI-A

**Версия**: 3.0.0  
**Дата**: Июль 2026  
**Платформы**: Desktop (Windows/Linux/macOS) + Backend (Node.js) + Android  
**Integration Mode**: gRPC (высокопроизводительный)

---

## 📋 Оглавление

1. [Требования](#требования)
2. [Быстрый старт](#быстрый-старт)
3. [Windows Bootstrap](#windows-bootstrap)
4. [架構 архитектура](#архитектура)
5. [API Контракт (gRPC)](#api-контракт-grpc)
6. [Использование в Node.js](#использование-в-nodejs)
7. [Тестирование](#тестирование)
8. [Production Checklist](#production-checklist)

---

## Требования

### Python Side (Nexus Driver)
- **Python 3.8+** (проверено на 3.8, 3.9, 3.10, 3.11)
- **pip** для управления зависимостями
- Зависимости из `requirements.txt`:
  - `pyyaml>=6.0` (конфигурация)
  - `numpy>=1.21.0` (векторные операции)
- **gRPC tools** для генерации из proto:
  ```bash
  pip install grpcio grpcio-tools
  ```

### Node.js Side (PROFI-A Backend)
- **Node.js 16+** (рекомендуется 18+)
- **npm** или **yarn**
- Зависимости:
  ```json
  {
    "dependencies": {
      "@grpc/grpc-js": "^1.9.0",
      "@grpc/proto-loader": "^0.7.0"
    }
  }
  ```

### Система
- **SQLite 3.27+** (встроен в Python)
- **Свободный порт**: 50051 (по умолчанию для gRPC)
- **Файловая система**: рекомендуется 1GB+ для vault

---

## Быстрый старт

### Шаг 1: Клонировать репозитории

```bash
# PROFI-A репозиторий
git clone https://github.com/your-org/PROFI-A.git
cd PROFI-A

# Nexus Driver v3.0.0
git clone https://github.com/Andrian0123/Bober-drive.git Bober-drive
```

### Шаг 2: Установить зависимости

**Python (Nexus Driver):**
```bash
cd Bober-drive
pip install -r requirements.txt
pip install grpcio grpcio-tools
```

**Node.js (PROFI-A Backend):**
```bash
cd ../backend
npm install @grpc/grpc-js @grpc/proto-loader
```

### Шаг 3: Сгенерировать gRPC сервис

```bash
# В директории Bober-drive
python -m grpc_tools.protoc \
  -I. \
  --python_out=. \
  --grpc_python_out=. \
  nexus_integration.proto
```

Должны быть созданы:
- `nexus_integration_pb2.py`
- `nexus_integration_pb2_grpc.py`

### Шаг 4: Запустить Nexus gRPC Server

```bash
python nexus_grpc_adapter.py \
  --vault-root ~/.nexus/integration \
  --port 50051
```

Ожидаемый вывод:
```
INFO:root:✅ Nexus Orchestrator инициализирован (версия: 3.0.0)
INFO:root:   Auto-update: ОТКЛЮЧЕН (интеграционный режим)
INFO:root:   Vault: ~/.nexus/integration/.nexus/vault.db
INFO:root:🚀 Starting Nexus gRPC server on port 50051...
INFO:root:✅ gRPC server listening on port 50051
INFO:root:   Mode: integration (auto-update disabled)
```

### Шаг 5: Использовать в Node.js

```javascript
const NexusSearchClient = require('./nexus_client');

const client = new NexusSearchClient('localhost', 50051);
client.connect();

// Поиск
const results = await client.search('authentication', {
  limit: 10,
  searchType: 'fts5'
});

console.log(`Найдено ${results.resultCount} результатов`);
```

---

## Windows Bootstrap

### Вариант A: Batch Script (автоматический)

Создать `bootstrap-nexus.bat` в `F:\PROFI-A\Bober-drive\`:

```batch
@echo off
REM Bootstrap Nexus Driver v3.0.0 Integration for PROFI-A
REM Запустить как Administrator

setlocal enabledelayedexpansion

echo ================================================
echo Nexus Driver v3.0.0 - Integration Bootstrap
echo Windows Setup
echo ================================================
echo.

REM Проверить Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found. Please install Python 3.8+
    exit /b 1
)
echo ✅ Python найден

REM Создать vault директорию
set VAULT_ROOT=%USERPROFILE%\.nexus\integration
if not exist "!VAULT_ROOT!" (
    mkdir "!VAULT_ROOT!"
    echo ✅ Vault директория создана: !VAULT_ROOT!
)

REM Установить зависимости
echo.
echo 📦 Installing dependencies...
pip install -r requirements.txt
pip install grpcio grpcio-tools

REM Сгенерировать proto сервис
echo.
echo 🔧 Generating gRPC protocol buffers...
python -m grpc_tools.protoc ^
  -I. ^
  --python_out=. ^
  --grpc_python_out=. ^
  nexus_integration.proto

if errorlevel 1 (
    echo ❌ Proto generation failed
    exit /b 1
)
echo ✅ Proto generation completed

REM Запустить сервер
echo.
echo 🚀 Starting Nexus gRPC Server...
echo    Vault: !VAULT_ROOT!
echo    Port: 50051
echo    Mode: integration (auto-update disabled)
echo.
echo Press Ctrl+C to shutdown
echo.

python nexus_grpc_adapter.py --vault-root "!VAULT_ROOT!" --port 50051

pause
endlocal
```

**Запустить:**
```bash
cd F:\PROFI-A\Bober-drive
bootstrap-nexus.bat
```

### Вариант B: PowerShell Script

Создать `bootstrap-nexus.ps1`:

```powershell
# Bootstrap Nexus Driver v3.0.0 Integration for PROFI-A
# Run as Administrator: Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Nexus Driver v3.0.0 - Integration Bootstrap" -ForegroundColor Cyan
Write-Host "Windows Setup (PowerShell)" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Проверить Python
$pythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $pythonExe) {
    Write-Host "❌ Python not found. Please install Python 3.8+" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Python найден: $pythonExe" -ForegroundColor Green

# Создать vault директорию
$vaultRoot = Join-Path $env:USERPROFILE ".nexus\integration"
if (-not (Test-Path $vaultRoot)) {
    New-Item -ItemType Directory -Force -Path $vaultRoot | Out-Null
    Write-Host "✅ Vault директория создана: $vaultRoot" -ForegroundColor Green
}

# Установить зависимости
Write-Host ""
Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt
pip install grpcio grpcio-tools

# Сгенерировать proto сервис
Write-Host ""
Write-Host "🔧 Generating gRPC protocol buffers..." -ForegroundColor Yellow
python -m grpc_tools.protoc `
  -I. `
  --python_out=. `
  --grpc_python_out=. `
  nexus_integration.proto

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Proto generation failed" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Proto generation completed" -ForegroundColor Green

# Запустить сервер
Write-Host ""
Write-Host "🚀 Starting Nexus gRPC Server..." -ForegroundColor Cyan
Write-Host "   Vault: $vaultRoot"
Write-Host "   Port: 50051"
Write-Host "   Mode: integration (auto-update disabled)"
Write-Host ""
Write-Host "Press Ctrl+C to shutdown" -ForegroundColor Yellow
Write-Host ""

& python nexus_grpc_adapter.py --vault-root $vaultRoot --port 50051
```

**Запустить:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
.\bootstrap-nexus.ps1
```

### Вариант C: Manual Setup (пошагово)

1. **Открыть Command Prompt:**
   ```cmd
   cmd.exe
   ```

2. **Перейти в Bober-drive:**
   ```cmd
   cd F:\PROFI-A\Bober-drive
   ```

3. **Установить Python зависимости:**
   ```cmd
   pip install -r requirements.txt
   pip install grpcio grpcio-tools
   ```

4. **Сгенерировать proto:**
   ```cmd
   python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. nexus_integration.proto
   ```

5. **Запустить сервер:**
   ```cmd
   python nexus_grpc_adapter.py --vault-root %USERPROFILE%\.nexus\integration --port 50051
   ```

---

## Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                        PROFI-A Backend                      │
│                     (Node.js + Express)                     │
│                    nexus_client.js (gRPC)                  │
│                    API Routes (REST → gRPC)                │
└─────────────────────────────────┬───────────────────────────┘
                                  │
                    gRPC (port 50051, protobuf)
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────┐
│              Nexus gRPC Adapter Server (Python)            │
│                  nexus_grpc_adapter.py                      │
│        NexusGRPCAdapter + NexusOrchestrator v3.0.0          │
│                                                             │
│  ┌────────────────────────────────────────────────────┐   │
│  │           NexusOrchestrator v3.0.0                │   │
│  │  ┌──────────────────────────────────────────────┐ │   │
│  │  │        Event-Driven Architecture           │ │   │
│  │  ├──────────────────────────────────────────────┤ │   │
│  │  │  • VaultCore (encrypted storage)           │ │   │
│  │  │  • FTS5Indexer (full-text search)          │ │   │
│  │  │  • RulesEngine (policy validation)         │ │   │
│  │  │  • Graphify (document processing)          │ │   │
│  │  │  • NeuralReflex (semantic search)          │ │   │
│  │  │  • FileSystemMapper (project scanning)     │ │   │
│  │  │  • TrashManager (safe deletion)            │ │   │
│  │  └──────────────────────────────────────────────┘ │   │
│  │                                                    │   │
│  │  Configuration:                                    │   │
│  │  • enable_auto_update = FALSE (КЛЮЧЕВОЙ!)         │   │
│  │  • enable_events = TRUE                           │   │
│  │  • enable_caching = TRUE                          │   │
│  └────────────────────────────────────────────────────┘   │
│                          │                                 │
│            Event Bus (pub/sub для модулей)               │
│                                                             │
│  ┌────────────────────────────────────────────────────┐   │
│  │              Storage Layer                        │   │
│  │  • vault.db (SQLite encrypted)                   │   │
│  │  • fts5.db (FTS5 indices)                        │   │
│  │  • metadata (project structure, rules)           │   │
│  └────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Ключевые особенности для интеграции:

1. **gRPC Interface**: Высокопроизводительный протокол, поддерживает потоковую передачу
2. **Auto-update отключен**: Явно устанавливается `enable_auto_update=False` при инициализации
3. **Event-Driven**: Все модули подключены через EventBus, обеспечивает наблюдаемость
4. **Кроссплатформенность**: Python работает на Windows, Linux, macOS, Android (Termux)
5. **Production-Ready**: Полное логирование, обработка ошибок, graceful shutdown

---

## API Контракт (gRPC)

### RPC Methods

#### 1. `Search` — Быстрый поиск
```protobuf
rpc Search(SearchRequest) returns (SearchResponse);

message SearchRequest {
  string query = 1;
  int32 limit = 2;
  string search_type = 3;  // "fts5", "semantic", "graph"
  map<string, string> filters = 4;
}

message SearchResponse {
  int32 result_count = 1;
  repeated SearchResult results = 2;
  float elapsed_ms = 3;
  string error = 4;
}
```

#### 2. `Ingest` — Индексирование документа
```protobuf
rpc Ingest(IngestRequest) returns (IngestResponse);

message IngestRequest {
  string file_path = 1;
  string content = 2;
  string content_type = 3;
  map<string, string> metadata = 4;
}
```

#### 3. `ScanProject` — Сканирование проекта
```protobuf
rpc ScanProject(ScanProjectRequest) returns (ScanProjectResponse);
```

#### 4. `HealthCheck` — Проверка статуса
```protobuf
rpc HealthCheck(HealthCheckRequest) returns (HealthCheckResponse);
```

#### 5. `ApplyConfig` — Применить конфигурацию
```protobuf
rpc ApplyConfig(ConfigRequest) returns (ConfigResponse);
```

#### 6. `Shutdown` — Graceful shutdown
```protobuf
rpc Shutdown(ShutdownRequest) returns (ShutdownResponse);
```

---

## Использование в Node.js

### Подключение в Express маршруты

```javascript
// routes/search.js
const NexusSearchClient = require('../nexus_client');
const express = require('express');
const router = express.Router();

// Глобальный клиент (инициализировать при startup)
let nexusClient = null;

// Инициализация
async function initNexus() {
  nexusClient = new NexusSearchClient('localhost', 50051);
  nexusClient.connect();
  console.log('✅ Connected to Nexus');
}

// Маршрут поиска
router.get('/search', async (req, res) => {
  try {
    const { query, limit = 50 } = req.query;
    
    if (!query) {
      return res.status(400).json({ error: 'query required' });
    }
    
    const results = await nexusClient.search(query, {
      limit: Math.min(limit, 100),
      searchType: 'fts5',
    });
    
    res.json({
      query,
      resultCount: results.resultCount,
      results: results.results,
      elapsedMs: results.elapsedMs,
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Маршрут индексирования
router.post('/ingest', async (req, res) => {
  try {
    const { filePath, content, contentType = 'text' } = req.body;
    
    const result = await nexusClient.ingest(filePath, {
      content,
      contentType,
    });
    
    res.json(result);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Маршрут health check
router.get('/health', async (req, res) => {
  try {
    const health = await nexusClient.healthCheck();
    res.json(health);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Инициализация при startup
initNexus().catch(console.error);

module.exports = router;
```

### Использование в приложении

```javascript
// app.js
const express = require('express');
const searchRoutes = require('./routes/search');

const app = express();

app.use(express.json());
app.use('/api/search', searchRoutes);

app.listen(3000, () => {
  console.log('PROFI-A backend listening on port 3000');
});
```

---

## Тестирование

### Запустить интеграционные тесты

```bash
cd F:\PROFI-A\Bober-drive
python -m pytest test_integration.py -v
```

Ожидаемый результат:
```
test_integration.py::TestIntegrationSetup::test_nexus_config_integration_mode PASSED
test_integration.py::TestIntegrationSetup::test_orchestrator_initializes_without_auto_update PASSED
test_integration.py::TestSearchIntegration::test_search_returns_empty_for_new_vault PASSED
...
========================== 25 passed in 3.45s ==========================
```

### Ручное тестирование (Node.js CLI)

```bash
node nexus_client.js
```

Должен:
1. Подключиться к серверу
2. Выполнить HealthCheck
3. Выполнить Search
4. Применить конфигурацию
5. Отключиться

---

## Production Checklist

Перед развертыванием убедиться:

- [ ] **Auto-update отключен**: `enable_auto_update=False` в `NexusConfig`
- [ ] **Порт 50051 открыт** (или использован другой явно указанный порт)
- [ ] **Vault директория недоступна из интернета** (только localhost или локальная сеть)
- [ ] **SQLite базы должны быть регулярно архивированы**
- [ ] **Логирование настроено** для audit trail
- [ ] **gRPC сервер запущен с `--graceful`**
- [ ] **Клиент переподключается при разрыве соединения**
- [ ] **Версионирование совпадает**: README, pyproject.toml, requirements.txt = v3.0.0
- [ ] **Тесты проходят**: `pytest test_integration.py`
- [ ] **HealthCheck периодически проверяется** (рекомендуется каждые 30 сек)

---

## Troubleshooting

### Ошибка: "ModuleNotFoundError: No module named 'grpc'"

```bash
pip install grpcio grpcio-tools
```

### Ошибка: "Failed to bind port 50051"

Порт уже занят. Проверить:
```bash
netstat -ano | findstr :50051
```

Использовать другой порт:
```bash
python nexus_grpc_adapter.py --port 50052
```

### Ошибка: "Auto-update все еще работает"

Убедиться, что `enable_auto_update=False` в `NexusConfig.__init__()`:
```python
config = NexusConfig(
    # ...
    enable_auto_update=False,  # ← ЭТА СТРОКА КРИТИЧНА
    # ...
)
```

### Бедная производительность поиска

1. Проверить статистику индексирования:
   ```javascript
   const health = await nexusClient.healthCheck();
   console.log(health.stats);
   ```

2. Убедиться, что документы индексированы:
   ```bash
   python -c "from nexus_grpc_adapter import *; ... # проверить vault.db"
   ```

3. Использовать gRPC compression для больших объемов данных

---

## Справочная информация

- **Nexus Driver Repository**: https://github.com/Andrian0123/Bober-drive
- **Latest Release**: v3.0.0
- **License**: MIT
- **Support**: Оригинальный репозиторий Nexus Driver

---

**Готово к production!** ✅
