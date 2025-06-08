#!/usr/bin/env python3
"""
Демонстрация работы команды разработчиков
Показывает как Петрович, Вася и Марина взаимодействуют в реальных задачах
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию в path
sys.path.insert(0, str(Path(__file__).parent))

async def demo_vasya_coding():
    """Демонстрация программирования Васи"""
    print("👨‍💻 Демонстрация программирования Васи")
    print("=" * 50)
    
    # Симулируем задачу кодирования без полной инициализации
    from entities.vasya import VasyaEntity
    
    # Создаем временный экземпляр только для демонстрации identity
    temp_vasya = object.__new__(VasyaEntity)
    
    try:
        identity = temp_vasya._load_identity()
        
        # Показываем личность Васи
        name = identity.get('name', 'Вася')
        role = identity.get('personality', {}).get('role', 'программист')
        experience = identity.get('personality', {}).get('experience', 'опытный')
        
        print(f"Агент: {name}")
        print(f"Роль: {role}")
        print(f"Опыт: {experience}")
        print(f"Модель: {identity['external_llms']['providers']['anthropic']['model']}")
        
        # Симулируем задачу
        task = """
        Создай функцию для валидации email адресов.
        Функция должна проверять:
        1. Наличие символа @
        2. Корректный формат домена
        3. Отсутствие запрещенных символов
        """
        
        print(f"\nЗадача: {task.strip()}")
        print("\nВася бы ответил:")
        print("✅ Анализирую требования...")
        print("✅ Проектирую решение...")
        print("✅ Пишу чистый код с документацией...")
        print("✅ Добавляю обработку edge cases...")
        
        # Показываем ключевые черты Васи
        traits = identity.get('personality', {}).get('traits', [])
        print(f"\nКлючевые черты:")
        for trait in traits[:5]:
            print(f"• {trait}")
            
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

async def demo_marina_testing():
    """Демонстрация тестирования Марины"""
    print("\n👩‍💼 Демонстрация тестирования Марины")
    print("=" * 50)
    
    from entities.marina import MarinaEntity
    
    temp_marina = object.__new__(MarinaEntity)
    
    try:
        identity = temp_marina._load_identity()
        
        name = identity.get('name', 'Марина')
        role = identity.get('personality', {}).get('role', 'QA')
        experience = identity.get('personality', {}).get('experience', 'опытная')
        
        print(f"Агент: {name}")
        print(f"Роль: {role}")
        print(f"Опыт: {experience}")
        print(f"Модель: {identity['external_llms']['providers']['openai']['model']}")
        
        test_case = """
        Протестируй функцию валидации email от Васи:
        - Проверь граничные случаи
        - Найди возможные баги
        - Создай тест-кейсы
        """
        
        print(f"\nЗадача: {test_case.strip()}")
        print("\nМарина бы ответила:")
        print("✅ Анализирую код на предмет уязвимостей...")
        print("✅ Создаю комплексные тест-кейсы...")
        print("✅ Проверяю edge cases: пустые строки, спецсимволы...")
        print("✅ Тестирую пользовательский опыт...")
        print("✅ Документирую найденные проблемы...")
        
        testing_expertise = identity.get('testing_expertise', {})
        testing_types = testing_expertise.get('testing_types', [])
        print(f"\nСпециализация в тестировании:")
        for test_type in testing_types[:4]:
            print(f"• {test_type}")
            
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

async def demo_petrovich_supervision():
    """Демонстрация руководства Петровича"""
    print("\n👨‍💼 Демонстрация руководства Петровича")
    print("=" * 50)
    
    from entities.supervisor import SupervisorEntity
    
    temp_petrovich = object.__new__(SupervisorEntity)
    
    try:
        identity = temp_petrovich._load_identity()
        
        name = identity.get('name', 'Петрович')
        role = identity.get('personality', {}).get('role', 'руководитель')
        experience = identity.get('personality', {}).get('experience', '30 лет')
        
        print(f"Агент: {name}")
        print(f"Роль: {role}")
        print(f"Опыт: {experience}")
        print(f"Модель: {identity['external_llms']['providers']['openai']['model']}")
        
        project_task = """
        Пользователь просит добавить систему аутентификации:
        - OAuth2 интеграция
        - JWT токены
        - Роли пользователей
        - Защита API endpoints
        """
        
        print(f"\nГлобальная задача: {project_task.strip()}")
        print("\nПетрович бы ответил:")
        print("✅ Анализирую архитектурные требования...")
        print("✅ Разбиваю на атомарные подзадачи...")
        print("✅ Назначаю задачи:")
        print("  • Васе: Реализация JWT middleware")
        print("  • Васе: OAuth2 провайдеры")
        print("  • Марине: Тестирование безопасности")
        print("  • Марине: Интеграционные тесты")
        print("✅ Устанавливаю критерии приемки...")
        print("✅ Планирую валидацию результата...")
        
        core_principles = identity.get('core_principles', [])
        print(f"\nПринципы руководства:")
        for principle in core_principles[:4]:
            print(f"• {principle}")
            
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

async def demo_team_workflow():
    """Демонстрация workflow команды"""
    print("\n🔄 Демонстрация workflow команды")
    print("=" * 50)
    
    print("Сценарий: Добавление функции поиска в проект")
    print("\n1️⃣ Пользователь → Петрович:")
    print("   'Нужна функция поиска с фильтрами и сортировкой'")
    
    print("\n2️⃣ Петрович анализирует и планирует:")
    print("   ✅ Разбивает на подзадачи")
    print("   ✅ Определяет архитектуру")
    print("   ✅ Ставит задачи команде")
    
    print("\n3️⃣ Петрович → Вася:")
    print("   'Реализуй поисковый API с REST endpoints'")
    
    print("\n4️⃣ Вася кодит:")
    print("   ✅ Создает FastAPI endpoints")
    print("   ✅ Добавляет ElasticSearch интеграцию")
    print("   ✅ Пишет документацию API")
    print("   ✅ Коммитит в Git")
    
    print("\n5️⃣ Вася → Марина:")
    print("   'Готов поисковый API, проверь качество'")
    
    print("\n6️⃣ Марина тестирует:")
    print("   ✅ Функциональное тестирование")
    print("   ✅ Тестирование производительности")
    print("   ✅ Проверка edge cases")
    print("   ✅ Валидация API документации")
    
    print("\n7️⃣ Марина → Петрович:")
    print("   'Найдена проблема с pagination, остальное ОК'")
    
    print("\n8️⃣ Петрович принимает решение:")
    print("   ✅ Анализирует отчет Марины")
    print("   ✅ Решает исправить pagination")
    print("   ✅ Дает дополнительное задание Васе")
    
    print("\n9️⃣ Цикл повторяется до готовности")
    
    print("\n🎯 Результат:")
    print("   ✅ Качественная функция поиска")
    print("   ✅ Все edge cases покрыты")
    print("   ✅ Код протестирован и задокументирован")
    print("   ✅ Готово к продакшену")
    
    return True

async def demo_mcp_capabilities():
    """Демонстрация MCP возможностей"""
    print("\n🔌 Демонстрация MCP возможностей")
    print("=" * 50)
    
    print("Каждый агент имеет доступ к 24 внешним инструментам:")
    
    capabilities = {
        "📁 Filesystem (3 tools)": [
            "read_file() - чтение файлов",
            "write_file() - запись файлов",
            "list_directory() - просмотр директорий"
        ],
        "🔄 Git (8 tools)": [
            "git_status() - статус репозитория",
            "git_add() - добавление файлов",
            "git_commit() - создание коммитов",
            "git_push() - отправка в remote",
            "git_pull() - получение изменений",
            "git_branch() - управление ветками",
            "git_diff() - просмотр различий",
            "git_log() - история изменений"
        ],
        "⚡ Terminal (7 tools)": [
            "execute_command() - выполнение команд",
            "run_script() - запуск скриптов",
            "get_env() - переменные окружения",
            "list_processes() - список процессов",
            "which_command() - поиск команд",
            "get_pwd() - текущая директория"
        ],
        "🌐 Web (6 tools)": [
            "web_search() - поиск в интернете",
            "http_get() - HTTP GET запросы",
            "http_post() - HTTP POST запросы",
            "scrape_text() - извлечение текста",
            "validate_url() - проверка URL",
            "check_status() - проверка статуса"
        ]
    }
    
    for category, tools in capabilities.items():
        print(f"\n{category}:")
        for tool in tools:
            print(f"  • {tool}")
    
    print("\nПримеры использования:")
    print("• Вася: git_commit('feat: add search API') - коммитит код")
    print("• Марина: execute_command('pytest tests/') - запускает тесты")
    print("• Петрович: web_search('FastAPI best practices') - ищет решения")
    
    return True

async def main():
    """Главная демонстрация"""
    print("🎭 ДЕМОНСТРАЦИЯ КОМАНДЫ РАЗРАБОТЧИКОВ PROMETHEUS")
    print("=" * 70)
    print("Интеллектуальная команда AI агентов для автономной разработки")
    
    demos = [
        ("Программирование Васи", demo_vasya_coding),
        ("Тестирование Марины", demo_marina_testing),
        ("Руководство Петровича", demo_petrovich_supervision),
        ("Workflow команды", demo_team_workflow),
        ("MCP возможности", demo_mcp_capabilities)
    ]
    
    success_count = 0
    
    for demo_name, demo_func in demos:
        try:
            result = await demo_func()
            if result:
                success_count += 1
        except Exception as e:
            print(f"❌ Ошибка в демо {demo_name}: {e}")
    
    print("\n" + "=" * 70)
    print("🎉 ЗАКЛЮЧЕНИЕ")
    print("=" * 70)
    
    if success_count == len(demos):
        print("✅ ВСЕ ДЕМОНСТРАЦИИ УСПЕШНЫ!")
        print("\n📋 Команда разработчиков готова:")
        print("   👨‍💼 Петрович - опытный руководитель (30 лет, GPT-4o)")
        print("   👨‍💻 Вася - энтузиаст программист (10 лет, Claude Sonnet)")
        print("   👩‍💼 Марина - дотошный QA (6 лет, GPT-4o)")
        print("\n🔌 MCP Integration:")
        print("   📁 Filesystem operations")
        print("   🔄 Git repository management")
        print("   ⚡ Terminal command execution")
        print("   🌐 Web access and search")
        print("\n🚀 Готовы к автономной разработке!")
        print("\n💡 Для начала работы:")
        print("   poetry run python prometheus.py telegram --entity petrovich")
        print("   (исправьте проблему с ChromaDB: rm -rf storage/)")
        
    else:
        print(f"⚠️ {success_count}/{len(demos)} демонстраций успешны")
    
    return success_count == len(demos)

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 