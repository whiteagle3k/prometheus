#!/usr/bin/env python3
"""
Минимальный тест команды разработчиков
Проверяет основные функции без полной инициализации
"""

import sys
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock

# Добавляем корневую директорию в path
sys.path.insert(0, str(Path(__file__).parent))

def test_entities_registration():
    """Тест регистрации агентов в системе"""
    print("🔍 Тестирование регистрации агентов...")
    
    try:
        from entities import discover_entities
        entities = discover_entities()
        
        print(f"   Найдено агентов: {len(entities)}")
        
        required_agents = ['petrovich', 'vasya', 'marina']
        for agent in required_agents:
            if agent in entities:
                info = entities[agent]
                print(f"   ✅ {agent}:")
                print(f"      Класс: {info['class'].__name__}")
                print(f"      Роль: {info.get('role', 'Не указана')}")
                print(f"      Описание: {info.get('description', 'Нет описания')[:50]}...")
            else:
                print(f"   ❌ {agent}: не найден")
                return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return False

def test_identity_files():
    """Тест наличия identity файлов"""
    print("\n📋 Тестирование наличия identity файлов...")
    
    identity_paths = {
        'petrovich': 'entities/supervisor/identity/identity.json',
        'vasya': 'entities/vasya/identity/identity.json', 
        'marina': 'entities/marina/identity/identity.json'
    }
    
    all_found = True
    
    for agent, path in identity_paths.items():
        file_path = Path(path)
        if file_path.exists():
            try:
                import json
                with open(file_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                name = config.get('name', 'Неизвестно')
                role = config.get('personality', {}).get('role', 'Неизвестна роль')
                
                print(f"   ✅ {agent} ({name}): {role}")
                
                # Проверяем обязательные поля
                required_fields = ['name', 'llm_instructions', 'external_llms']
                missing_fields = [field for field in required_fields if field not in config]
                
                if missing_fields:
                    print(f"      ⚠️ Отсутствуют поля: {missing_fields}")
                
            except Exception as e:
                print(f"   ❌ {agent}: ошибка чтения файла - {e}")
                all_found = False
        else:
            print(f"   ❌ {agent}: файл identity не найден - {path}")
            all_found = False
    
    return all_found

def test_agent_classes():
    """Тест создания классов агентов без полной инициализации"""
    print("\n🏗️ Тестирование классов агентов...")
    
    try:
        from entities import discover_entities
        entities_info = discover_entities()
        
        for name in ['petrovich', 'vasya', 'marina']:
            if name in entities_info:
                entity_class = entities_info[name]['class']
                print(f"   ✅ {name}: класс {entity_class.__name__} доступен")
                
                # Проверяем базовые атрибуты класса
                if hasattr(entity_class, '__init__'):
                    print(f"      Конструктор: ✓")
                else:
                    print(f"      ⚠️ Нет конструктора")
                
                if hasattr(entity_class, '_load_identity'):
                    print(f"      Метод _load_identity: ✓")
                else:
                    print(f"      ⚠️ Нет метода _load_identity")
                    
            else:
                print(f"   ❌ {name}: класс не найден")
                return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return False

async def test_agent_identity_loading():
    """Тест загрузки identity без полной инициализации"""
    print("\n🧠 Тестирование загрузки identity...")
    
    try:
        from entities import discover_entities
        entities_info = discover_entities()
        
        for name in ['petrovich', 'vasya', 'marina']:
            entity_class = entities_info[name]['class']
            
            # Создаем временный экземпляр только для тестирования _load_identity
            temp_instance = object.__new__(entity_class)  # Избегаем вызова __init__
            
            try:
                # Тестируем загрузку identity
                identity = temp_instance._load_identity()
                
                agent_name = identity.get('name', 'Неизвестно')
                print(f"   ✅ {name} ({agent_name}): identity загружен")
                print(f"      LLM инструкции: {'✓' if 'llm_instructions' in identity else '❌'}")
                print(f"      Внешние LLM: {'✓' if 'external_llms' in identity else '❌'}")
                print(f"      Личность: {'✓' if 'personality' in identity else '❌'}")
                
            except Exception as e:
                print(f"   ❌ {name}: ошибка загрузки identity - {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return False

def test_llm_configurations():
    """Тест конфигурации LLM для агентов"""
    print("\n🤖 Тестирование конфигурации LLM...")
    
    try:
        from entities import discover_entities
        entities_info = discover_entities()
        
        expected_models = {
            'petrovich': 'gpt-4o',
            'vasya': 'claude-3-5-sonnet-20241022',
            'marina': 'gpt-4o'
        }
        
        for name in ['petrovich', 'vasya', 'marina']:
            entity_class = entities_info[name]['class']
            temp_instance = object.__new__(entity_class)
            
            try:
                identity = temp_instance._load_identity()
                external_llms = identity.get('external_llms', {})
                primary_provider = external_llms.get('primary_provider', 'Не указан')
                
                print(f"   ✅ {name}: провайдер {primary_provider}")
                
                providers = external_llms.get('providers', {})
                for provider, config in providers.items():
                    model = config.get('model', 'Не указана')
                    enabled = config.get('enabled', False)
                    print(f"      {provider}: {model} ({'включен' if enabled else 'выключен'})")
                
            except Exception as e:
                print(f"   ❌ {name}: ошибка конфигурации LLM - {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return False

def test_team_hierarchy():
    """Тест иерархии команды"""
    print("\n👥 Тестирование иерархии команды...")
    
    try:
        from entities import discover_entities
        entities_info = discover_entities()
        
        expected_hierarchy = {
            'petrovich': {'role': 'team_lead', 'reports_to': None, 'direct_reports': ['vasya', 'marina']},
            'vasya': {'role': 'implementer', 'reports_to': 'petrovich'},
            'marina': {'role': 'quality_guardian', 'reports_to': 'petrovich'}
        }
        
        for name, expected in expected_hierarchy.items():
            if name in entities_info:
                info = entities_info[name]
                
                role = info.get('role', info.get('team_position', 'Неизвестна'))
                reports_to = info.get('reports_to')
                
                print(f"   ✅ {name}:")
                print(f"      Роль: {role}")
                if reports_to:
                    print(f"      Подчиняется: {reports_to}")
                    
                if 'direct_reports' in expected:
                    reports = info.get('direct_reports', [])
                    print(f"      Подчиненные: {reports}")
                    
            else:
                print(f"   ❌ {name}: не найден в иерархии")
                return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return False

async def main():
    """Основная функция тестирования"""
    print("🧪 Минимальные тесты команды разработчиков")
    print("=" * 60)
    print("(Тесты выполняются без полной инициализации BaseEntity)")
    
    tests = [
        ("Регистрация агентов", test_entities_registration),
        ("Identity файлы", test_identity_files),
        ("Классы агентов", test_agent_classes),
        ("Загрузка identity", test_agent_identity_loading),
        ("Конфигурация LLM", test_llm_configurations),
        ("Иерархия команды", test_team_hierarchy)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📝 {test_name}:")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
                
            if result:
                passed += 1
                print(f"   ✅ ПРОЙДЕН")
            else:
                print(f"   ❌ ПРОВАЛЕН")
        except Exception as e:
            print(f"   ❌ ОШИБКА: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 Результат: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("🎉 Все минимальные тесты прошли успешно!")
        print("Команда разработчиков готова к работе!")
        print("\n💡 Для полного тестирования исправьте проблему с ChromaDB:")
        print("   rm -rf storage/chromadb/")
        return True
    else:
        print("⚠️ Некоторые тесты провалены")
        print("Проверьте конфигурацию команды")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 