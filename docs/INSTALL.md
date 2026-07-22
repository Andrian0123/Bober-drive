# 🤖 Ollama Agent Hub - Установка завершена!

## ✅ Что установлено:

### Основные файлы:
- ✅ **ollama-manifest.json** - конфигурация всех агентов
- ✅ **plugins-config.json** - 16 плагинов для агентов
- ✅ **agent-router-config.json** - конфигурация автоматической маршрутизации
- ✅ **README.md** - полная документация

### Скрипты запуска:

**Windows:**
- ✅ **setup.bat** - первоначальная установка
- ✅ **launch-agent.bat** - простой запуск агента
- ✅ **ollama-manager.ps1** - продвинутое управление (PowerShell)
- ✅ **auto-agent.bat** - автоматический выбор агента
- ✅ **agent-router.ps1** - продвинутая маршрутизация (PowerShell)

**Linux/Mac:**
- ✅ **setup.sh** - первоначальная установка
- ✅ **ollama-manager.sh** - управление агентами
- ✅ **auto-agent.sh** - автоматический выбор агента
- ✅ **agent-router.sh** - продвинутая маршрутизация

### Конфигурации моделей (Modelfiles):
- ✅ **Modelfile.hermes** - Hermes Agent с плагинами
- ✅ **Modelfile.openclaw** - OpenClaw (100+ навыков)
- ✅ **Modelfile.opencode** - OpenCode (coding)
- ✅ **Modelfile.droid** - Droid (terminal/IDE)
- ✅ **Modelfile.pi** - Pi (extensible toolkit)

### Документация:
- ✅ **docs/QUICKSTART.md** - быстрый старт
- ✅ **docs/CUSTOM_PLUGINS.md** - создание плагинов
- ✅ **docs/COMPARISON.md** - сравнение агентов
- ✅ **docs/AUTO_ROUTING.md** - автоматическая маршрутизация запросов

### Тестовые скрипты:
- ✅ **test-installation.bat/sh** - проверка установки
- ✅ **test-auto-routing.bat/sh** - тест автоматической маршрутизации

### Дополнительно:
- ✅ **docker-compose.yml** - Docker конфигурация
- ✅ **.env.example** - пример переменных окружения
- ✅ **.gitignore** - обновлен для Ollama проекта
- ✅ **agents/** - директория для конфигураций

---

## 🚀 Быстрый старт:

### 1. Установите Ollama (если еще не установлен):

**Windows:**
```powershell
winget install Ollama.Ollama
```
Или скачайте: https://ollama.ai/download/windows

**Linux/Mac:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

### 2. Запустите Ollama сервер:

Откройте отдельный терминал:
```bash
ollama serve
```

### 3. Запустите setup (первый раз):

**Windows:**
```cmd
setup.bat
```

**Linux/Mac:**
```bash
chmod +x setup.sh
./setup.sh
```

### 4. Запустите агента:

**Windows (простой способ):**
```cmd
launch-agent.bat hermes
```

**Windows (продвинутый):**
```powershell
# Список агентов
.\ollama-manager.ps1 list

# Список плагинов
.\ollama-manager.ps1 plugins

# Запуск агента
.\ollama-manager.ps1 launch hermes
```

**Linux/Mac:**
```bash
chmod +x ollama-manager.sh
./ollama-manager.sh launch hermes
```

---

## 🤖 Доступные бесплатные агенты:

1. **Hermes** (~4GB) - Универсальный self-improving AI
   - Плагины: memory, tools, planning
   - Запуск: `launch-agent.bat hermes`

2. **OpenClaw** (~6GB) - 100+ навыков
   - Плагины: file-ops, web-scraping, api, database
   - Запуск: `launch-agent.bat openclaw`

3. **OpenCode** (~3GB) - Специализация на коде
   - Плагины: git, linting, testing, docs
   - Запуск: `launch-agent.bat opencode`

4. **Droid** (~2GB) - Terminal & IDE
   - Плагины: vscode, terminal-ops, workspace
   - Запуск: `launch-agent.bat droid`

5. **Pi** (~500MB) - Легковесный расширяемый
   - Плагины: custom-plugins, api, hooks
   - Запуск: `launch-agent.bat pi`

---

## 🔌 16 плагинов:

1. **code-review** - Ревью кода
2. **refactor** - Рефакторинг
3. **debug** - Отладка
4. **web-search** - Поиск в интернете
5. **memory** - Долговременная память
6. **tools** - Выполнение инструментов
7. **file-ops** - Операции с файлами
8. **git** - Git интеграция
9. **linting** - Линтинг
10. **testing** - Генерация тестов
11. **shell-suggest** - Подсказки терминала
12. **vscode** - VS Code интеграция
13. **custom-plugins** - Создание плагинов
14. **api** - Работа с API
15. **database** - Работа с БД
16. **web-scraping** - Парсинг веб-страниц

---

## 📚 Документация:

- **README.md** - полное руководство
- **docs/QUICKSTART.md** - быстрый старт с примерами
- **docs/CUSTOM_PLUGINS.md** - создание своих плагинов для Pi
- **docs/COMPARISON.md** - детальное сравнение агентов
- **docs/AUTO_ROUTING.md** - ⭐ автоматическая маршрутизация запросов между агентами

---

## 🔄 Автоматическая маршрутизация (НОВОЕ!):

Теперь вам не нужно выбирать агента вручную! Система автоматически определит, какой агент лучше подходит для вашего запроса.

**Windows (простой способ):**
```cmd
auto-agent.bat "Напиши функцию сортировки на Python"
```

**Windows (продвинутый):**
```powershell
.\agent-router.ps1 -Query "Напиши unit-тесты для функции"
```

**Linux/Mac:**
```bash
./auto-agent.sh "Найди все файлы .txt в директории"
```

**Примеры:**
- "Напиши функцию..." → автоматически выберет **OpenCode**
- "Найди файлы..." → автоматически выберет **OpenClaw**
- "Команда терминала..." → автоматически выберет **Droid**
- "Создай плагин..." → автоматически выберет **Pi**

**Тестирование:**
```cmd
# Windows
test-auto-routing.bat

# Linux/Mac
./test-auto-routing.sh
```

📖 **Полная документация:** docs/AUTO_ROUTING.md

---

## 🎯 Рекомендации:

### Для программирования:
→ **OpenCode**

### Для автоматизации:
→ **OpenClaw**

### Для универсальных задач:
→ **Hermes**

### Для терминала:
→ **Droid**

### Для слабого ПК:
→ **Pi** (всего 500MB!)

### Для кастомизации:
→ **Pi** (создавайте свои плагины)

---

## 🐛 Устранение неполадок:

### Ollama не запускается:
```powershell
# Windows
net stop Ollama
net start Ollama

# Linux/Mac
sudo systemctl restart ollama
```

### Проверка статуса:
```powershell
.\ollama-manager.ps1 status
```

### Список установленных моделей:
```bash
ollama list
```

---

## 💡 Примеры использования:

### Hermes - Универсальный помощник:
```
>>> Создай план задач для веб-приложения
>>> Объясни как работает async/await
>>> Помоги отладить эту ошибку
```

### OpenClaw - Автоматизация:
```
>>> Найди все файлы .js в директории
>>> Извлеки данные с сайта example.com
>>> Подключись к БД и выполни SELECT
```

### OpenCode - Разработка:
```
>>> Напиши unit-тесты для этой функции
>>> Сделай code review
>>> Создай коммит с описанием
```

### Pi - Расширяемость:
```
>>> load-plugin my-plugin.js
>>> run my-plugin.hello
>>> plugin.list
```

---

## 🔐 Безопасность:

✅ Все агенты работают **локально**  
✅ Данные **не уходят в облако**  
✅ **Полный контроль** над моделями  
✅ **Бесплатно** (кроме Claude, ChatGPT, Copilot - требуют API ключи)

---

## 📊 Системные требования:

### Минимум (Pi):
- CPU: 2 cores
- RAM: 4GB
- Диск: 2GB

### Рекомендуется (Hermes, OpenCode):
- CPU: 4+ cores
- RAM: 16GB
- Диск: 10GB

---

## 🚀 Следующие шаги:

1. ✅ Запустите `setup.bat` (или `setup.sh`)
2. ✅ Установите первого агента (рекомендуем **Hermes**)
3. ✅ Попробуйте разные команды
4. ✅ Изучите документацию в `docs/`
5. ✅ Создайте свой плагин для Pi (docs/CUSTOM_PLUGINS.md)

---

## 🤝 Поддержка:

- GitHub Issues: https://github.com/ollama/ollama/issues
- Discord: https://discord.gg/ollama
- Docs: https://github.com/ollama/ollama/tree/main/docs

---

**Готово! Теперь у вас есть полнофункциональная система локальных AI-агентов! 🎉**

Начните с: `setup.bat` (Windows) или `./setup.sh` (Linux/Mac)
