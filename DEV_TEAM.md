# Команда Разработчиков Prometheus 👥

Autonomous AI development team with MCP-powered external tool access.

## 🎯 Команда

### 👨‍💼 **Петрович** - Senior Supervisor
- **Роль**: Team Lead & Validator  
- **Опыт**: 30 лет разработки
- **Темперамент**: Флегматичный, мудрый, методичный
- **Ответственность**: 
  - Анализ и декомпозиция задач
  - Валидация и ревью работы
  - Стратегическое руководство командой
  - НЕ кодит сам - направляет и валидирует

### 👨‍💻 **Вася** - Mid-level Developer  
- **Роль**: Implementation Specialist
- **Опыт**: 10 лет программирования
- **Темперамент**: Энтузиаст, инициативный, послушный
- **Ответственность**:
  - Реализация кода по заданиям
  - Инициатива в технических деталях
  - Следование guidance от Петровича
  - Качественная документация кода

### 👩‍💼 **Марина** - QA Specialist
- **Роль**: Quality Guardian
- **Опыт**: 6 лет тестирования  
- **Темперамент**: Внимательная к деталям, педантичная, дружелюбная
- **Ответственность**:
  - Комплексное тестирование
  - Поиск багов и edge cases
  - Валидация пользовательского опыта
  - Конструктивная обратная связь

## 🔄 Workflow

```
User Task → Петрович → Вася → Марина → Петрович → Done
            (analyze)  (code)  (test)   (approve)
```

1. **Пользователь** дает задачу **Петровичу**
2. **Петрович** анализирует и декомпозирует задачу
3. **Петрович** назначает имплементацию **Васе**
4. **Вася** реализует с использованием MCP tools
5. **Марина** тестирует и валидирует реализацию
6. **Петрович** делает финальное ревью и утверждение

## 🔌 MCP Возможности

Каждый агент имеет доступ к **24 внешним инструментам** через MCP:

### 📁 Filesystem (3 tools)
- `read_file()` - чтение файлов
- `write_file()` - запись файлов  
- `list_directory()` - список файлов

### 🔄 Git (8 tools)
- `git_status()` - статус репозитория
- `git_add()`, `git_commit()` - коммиты
- `git_push()`, `git_pull()` - синхронизация
- `git_branch()` - управление ветками
- `git_diff()`, `git_log()` - анализ изменений

### ⚡ Terminal (7 tools)  
- `execute_command()` - выполнение команд
- `run_script()` - запуск скриптов
- `get_env()`, `set_env()` - переменные среды
- `list_processes()` - процессы
- `which_command()`, `get_pwd()` - утилиты

### 🌐 Web (6 tools)
- `web_search()` - поиск в интернете
- `http_get()`, `http_post()` - HTTP запросы
- `scrape_text()` - извлечение текста
- `validate_url()`, `check_status()` - проверка URL

## 🚀 Использование

### Запуск отдельных агентов:

```bash
# Петрович - для получения и декомпозиции задач
poetry run python prometheus.py api --entity petrovich
poetry run python prometheus.py telegram --entity petrovich

# Вася - для программирования
poetry run python prometheus.py shell --entity vasya

# Марина - для тестирования  
poetry run python prometheus.py shell --entity marina
```

### Telegram Bot для Петровича:

```bash
# Запуск бота для Петровича
poetry run python prometheus.py telegram --entity petrovich

# В Telegram:
/start
"Нужно добавить функцию аутентификации в API"
```

### API использование:

```bash
# Задача для Петровича
curl 'localhost:8000/v1/chat?entity=petrovich' \
  -d '{"message":"Добавь logging middleware в FastAPI"}'

# Работа с Васей
curl 'localhost:8000/v1/chat?entity=vasya' \
  -d '{"message":"Реализуй функцию для логирования запросов"}'

# Тестирование с Мариной
curl 'localhost:8000/v1/chat?entity=marina' \
  -d '{"message":"Протестируй новый middleware на edge cases"}'
```

## 📊 Мониторинг

### Проверка регистрации:
```bash
poetry run python test_dev_team.py
```

### Проверка конфигурации:
```bash  
poetry run python test_dev_team_basic.py
```

### Статус команды:
```bash
# Проверка всех доступных агентов
poetry run python -c "
from entities import discover_entities
entities = discover_entities()
for name, info in entities.items():
    print(f'{name}: {info["role"]} - {info["description"][:50]}...')
"
```

## 🎛️ Конфигурация

### LLM Models:
- **Петрович**: GPT-4o (стратегическое мышление)
- **Вася**: Claude 3.5 Sonnet (программирование)  
- **Марина**: GPT-4o (анализ качества)

### Identity Files:
- `entities/supervisor/identity/identity.json` - Петрович
- `entities/vasya/identity/identity.json` - Вася
- `entities/marina/identity/identity.json` - Марина

## 🔮 Планы развития

### Краткосрочные:
- [ ] Telegram группа с всеми агентами
- [ ] Автоматическая передача задач между агентами
- [ ] Интеграция с task queue системой

### Долгосрочные:
- [ ] CI/CD интеграция для автодеплоя
- [ ] Расширение команды (DevOps, Security агенты)
- [ ] Интеграция с внешними системами (Jira, GitHub)

## 🚨 Troubleshooting

### Проблемы с БД:
Если видите ошибку `no such column: collections.topic`:
```bash
# Сбросить ChromaDB
rm -rf storage/chromadb/
```

### MCP серверы не запускаются:
```bash
# Проверить MCP dependencies
poetry install
poetry run python -c "import mcp; print('MCP OK')"
```

### Агенты не найдены:
```bash
# Проверить регистрацию
poetry run python test_dev_team.py
```

---

**🎉 Команда готова к автономной разработке с MCP-powered инструментами!** 