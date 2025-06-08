#!/usr/bin/env python3
"""
Базовые тесты команды разработчиков
Быстрая проверка работоспособности агентов
"""

import sys
from pathlib import Path

# Добавляем корневую директорию в path
sys.path.insert(0, str(Path(__file__).parent))

def test_entities_discovery():
    """Тест обнаружения агентов"""
    print("🔍 Тестирование обнаружения агентов...")
    
    try:
        from entities import discover_entities
        entities = discover_entities()
        
        print(f"   Найдено агентов: {len(entities)}")
        
        required_agents = ['petrovich', 'vasya', 'marina']
        for agent in required_agents:
            if agent in entities:
                info = entities[agent]
                print(f"   ✅ {agent}: {info.get('description', 'Без описания')}")
            else:
                print(f"   ❌ {agent}: не найден")
                return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return False

def test_entities_creation():
    """Тест создания экземпляров агентов"""
    print("\n🚀 Тестирование создания агентов...")
    
    try:
        from entities import discover_entities
        entities_info = discover_entities()
        
        agents = {}
        
        for name in ['petrovich', 'vasya', 'marina']:
            if name in entities_info:
                entity_class = entities_info[name]['class']
                agent = entity_class()
                agents[name] = agent
                print(f"   ✅ {name}: создан успешно")
            else:
                print(f"   ❌ {name}: не найден в реестре")
                return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка создания: {e}")
        return False

def test_identities_loading():
    """Тест загрузки identity файлов"""
    print("\n📋 Тестирование загрузки identity...")
    
    try:
        from entities import discover_entities
        entities_info = discover_entities()
        
        for name in ['petrovich', 'vasya', 'marina']:
            entity_class = entities_info[name]['class']
            agent = entity_class()
            
            # Проверяем identity
            if hasattr(agent, 'identity') and agent.identity:
                identity = agent.identity
                agent_name = identity.get('name', 'Неизвестно')
                role = identity.get('personality', {}).get('role', 'Неизвестна роль')
                print(f"   ✅ {name} ({agent_name}): {role}")
            else:
                print(f"   ❌ {name}: identity не загружен")
                return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка загрузки identity: {e}")
        return False

def test_mcp_availability():
    """Тест доступности MCP интеграции"""
    print("\n🔌 Тестирование MCP интеграции...")
    
    try:
        from entities import discover_entities
        entities_info = discover_entities()
        
        for name in ['petrovich', 'vasya', 'marina']:
            entity_class = entities_info[name]['class']
            agent = entity_class()
            
            # Проверяем MCP методы
            mcp_methods = ['read_file', 'write_file', 'git_status', 'execute_command', 'web_search']
            available_methods = 0
            
            for method in mcp_methods:
                if hasattr(agent, method):
                    available_methods += 1
            
            if available_methods >= 3:
                print(f"   ✅ {name}: {available_methods}/{len(mcp_methods)} MCP методов доступно")
            else:
                print(f"   ⚠️ {name}: только {available_methods}/{len(mcp_methods)} MCP методов")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка MCP: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("🧪 Базовые тесты команды разработчиков")
    print("=" * 50)
    
    tests = [
        ("Обнаружение агентов", test_entities_discovery),
        ("Создание агентов", test_entities_creation),
        ("Загрузка identity", test_identities_loading),
        ("MCP интеграция", test_mcp_availability)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"📝 {test_name}:")
        try:
            if test_func():
                passed += 1
                print(f"   ✅ ПРОЙДЕН")
            else:
                print(f"   ❌ ПРОВАЛЕН")
        except Exception as e:
            print(f"   ❌ ОШИБКА: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Результат: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("🎉 Все базовые тесты прошли успешно!")
        print("Команда разработчиков готова к работе!")
        return True
    else:
        print("⚠️ Некоторые тесты провалены")
        print("Проверьте конфигурацию команды")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 