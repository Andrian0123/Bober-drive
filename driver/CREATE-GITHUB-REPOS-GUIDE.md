# 📝 Пошаговая инструкция по созданию GitHub репозиториев

## 🎯 Цель
Создать экосистему специализированных репозиториев для каждого компонента Nexus Driver.

---

## ✅ Чек-лист репозиториев для создания

### Фаза 1: Основные компоненты (Приоритет 🔴)

- [ ] **nexus-driver-core**
  - Описание: Core orchestration engine
  - README: `templates/nexus-driver-core-README.md`
  - Файлы для копирования из Bober-drive:
    - `driver/driver_core.py`
    - `driver/graph_router.py`
    - `driver/graph_search.py`
    - `driver/skill_loader.py`
    - `driver/skill_engine.py`
    - `driver/nexus_orchestrator_core.py`

- [ ] **nexus-memory-system**
  - Описание: Advanced persistent memory
  - README: `templates/nexus-memory-system-README.md`
  - Файлы для копирования:
    - `driver/vector_memory.py`
    - `driver/memory_store.py`
    - `driver/memory_enhanced.py`
    - `driver/structured_memory.py`
    - `driver/nexus_memory_graph.py`

- [ ] **nexus-mcp-toolkit**
  - Описание: MCP tool integration
  - README: `templates/nexus-mcp-toolkit-README.md`
  - Файлы для копирования:
    - `driver/mcp_server.py`
    - `driver/mcp_tool_registry.py`
    - `driver/nexus_rtk_proxy.py`
    - `driver/tool_runtime.py`

### Фаза 2: Специализированные компоненты (Приоритет 🟡)

- [ ] **nexus-browser-automation**
  - Описание: Browser automation engine
  - Файлы:
    - `driver/browser_automation.py`
    - `driver/command_proxy.py`

- [ ] **nexus-project-graph**
  - Описание: Project dependency visualization
  - Файлы:
    - `driver/driver_core.py` (ProjectGraphBuilder)
    - `driver/graph_router.py`
    - `driver/graph_search.py`

- [ ] **nexus-skills-system**
  - Описание: Skill management
  - Файлы:
    - `driver/skill_loader.py`
    - `driver/skill_engine.py`
    - `skills/` (директория)

### Фаза 3: Документация и примеры (Приоритет 🟢)

- [ ] **nexus-documentation**
  - Описание: Comprehensive documentation
  - Файлы:
    - Все `.md` файлы из `driver/`
    - Архитектурные диаграммы

- [ ] **nexus-examples**
  - Описание: Code examples
  - Файлы:
    - `driver/nexus_examples.py`
    - Примеры использования

- [ ] **nexus-dashboard**
  - Описание: Web dashboard (опционально)
  - Файлы:
    - `driver/unified_dashboard.py`

---

## 🚀 Пошаговый процесс создания (для каждого репозитория)

### Шаг 1: Создание на GitHub

1. Откройте https://github.com/new
2. Заполните:
   ```
   Repository name: nexus-{component-name}
   Description: [Скопировать из GITHUB-REPOS-DESCRIPTIONS.md]
   Public: ✅
   Add a README file: ✅
   Add .gitignore: ✅ (Python)
   Choose a license: MIT
   ```
3. Нажмите "Create repository"

### Шаг 2: Локальная подготовка

```bash
# Клонируйте репозиторий
git clone https://github.com/Andrian0123/nexus-{component-name}
cd nexus-{component-name}

# Скопируйте README
cp ../Bober-drive/driver/templates/nexus-{component-name}-README.md README.md
git add README.md
git commit -m "docs: Add comprehensive README"

# Скопируйте исходные файлы
cp ../Bober-drive/driver/{files}/* ./
```

### Шаг 3: Структура директорий

```
nexus-{component-name}/
├── README.md
├── LICENSE (MIT)
├── .gitignore
├── pyproject.toml
├── requirements.txt
├── setup.py
│
├── nexus_{}/ (пакет)
│   ├── __init__.py
│   ├── core.py
│   ├── config.py
│   └── utils.py
│
├── tests/
│   ├── __init__.py
│   ├── test_core.py
│   └── test_integration.py
│
├── docs/
│   ├── API_REFERENCE.md
│   ├── ARCHITECTURE.md
│   └── EXAMPLES.md
│
└── examples/
    └── basic_usage.py
```

### Шаг 4: Конфигурация pyproject.toml

```toml
[build-system]
requires = ["setuptools>=65", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "nexus-{component-name}"
version = "0.1.0"
description = "{description}"
readme = "README.md"
license = {text = "MIT"}
authors = [{name = "Andrian0123"}]
requires-python = ">=3.12"
dependencies = [
    "python-dotenv>=1.0",
    # Специфичные зависимости
]

[project.urls]
Homepage = "https://github.com/Andrian0123/nexus-{component-name}"
Documentation = "https://github.com/Andrian0123/nexus-{component-name}/wiki"
Repository = "https://github.com/Andrian0123/nexus-{component-name}"
Issues = "https://github.com/Andrian0123/nexus-{component-name}/issues"

[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-cov", "black", "flake8"]
```

### Шаг 5: requirements.txt

```bash
# nexus-driver-core
python-dotenv>=1.0
pydantic>=2.0

# nexus-memory-system
sqlite-vec>=0.1.0
sentence-transformers>=2.2.0
sqlalchemy>=2.0

# nexus-mcp-toolkit
httpx>=0.25.0
anthropic>=0.20.0
```

### Шаг 6: .gitignore

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
pip-wheel-metadata/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual environments
venv/
ENV/
env/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Testing
.pytest_cache/
.coverage
htmlcov/

# Environment
.env
.env.local
.env.*.local

# Project specific
.nexus/
*.db
*.sqlite
```

### Шаг 7: GitHub Actions CI/CD

Создайте `.github/workflows/tests.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.12"]

    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e ".[dev]"
    
    - name: Run tests
      run: pytest --cov=nexus_{}
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

### Шаг 8: GitHub Labels & Issues

Настройте labels:
```
- bug (красный)
- feature (зелёный)
- documentation (синий)
- help wanted (оранжевый)
- good first issue (золотой)
```

### Шаг 9: GitHub Discussions

Включите в Settings → Features:
- ✅ Discussions

---

## 📋 Команды для автоматизации

### Создайте все репозитории (скрипт)

```bash
#!/bin/bash

# Массив репозиториев для создания
repos=(
    "nexus-driver-core"
    "nexus-memory-system"
    "nexus-mcp-toolkit"
    "nexus-browser-automation"
    "nexus-project-graph"
    "nexus-skills-system"
)

for repo in "${repos[@]}"; do
    echo "Creating $repo..."
    
    # Клонируйте пустой репозиторий (предварительно создайте на GitHub)
    git clone https://github.com/Andrian0123/$repo
    cd $repo
    
    # Скопируйте файлы
    # cp -r ../Bober-drive/driver/templates/$repo/* .
    
    git add .
    git commit -m "Initial commit: Nexus component setup"
    git push origin main
    
    cd ..
done

echo "✅ All repositories created!"
```

---

## 🔗 Связывание между репозиториями

### Добавьте cross-references в README:

```markdown
## Related Projects

- [nexus-driver-core](https://github.com/Andrian0123/nexus-driver-core)
- [nexus-memory-system](https://github.com/Andrian0123/nexus-memory-system)
- [nexus-mcp-toolkit](https://github.com/Andrian0123/nexus-mcp-toolkit)
- [Bober-drive](https://github.com/Andrian0123/Bober-drive) - Main monorepo
```

### Добавьте submodules (опционально):

```bash
cd Bober-drive

git submodule add https://github.com/Andrian0123/nexus-driver-core driver/modules/driver-core
git submodule add https://github.com/Andrian0123/nexus-memory-system driver/modules/memory-system
git submodule add https://github.com/Andrian0123/nexus-mcp-toolkit driver/modules/mcp-toolkit
```

---

## 📊 Рекомендуемый порядок создания

### Неделя 1: Основные компоненты
1. nexus-driver-core
2. nexus-memory-system
3. nexus-mcp-toolkit

### Неделя 2: Специализация
4. nexus-browser-automation
5. nexus-project-graph
6. nexus-skills-system

### Неделя 3: Документация
7. nexus-documentation
8. nexus-examples
9. nexus-dashboard (опционально)

---

## ✨ Финальная проверка

Для каждого репозитория проверьте:

- [ ] ✅ README.md presente and comprehensive
- [ ] ✅ LICENSE файл (MIT)
- [ ] ✅ pyproject.toml configured
- [ ] ✅ requirements.txt актуален
- [ ] ✅ .gitignore properly set
- [ ] ✅ GitHub Actions workflow создан
- [ ] ✅ Topics добавлены (ai, agent, nexus)
- [ ] ✅ Description заполнена
- [ ] ✅ Related projects linked
- [ ] ✅ First commit pushed

---

## 🎓 Результат

После завершения у вас будет:

✅ **3 основных компонента** (готовые к использованию)  
✅ **6 специализированных модулей** (расширяемые)  
✅ **2 документационных репозитория** (обучение)  
✅ **Unified ecosystem** (с перекрёстными ссылками)  

---

**Статус**: Готово к реализации  
**Дата**: 18.07.2026
