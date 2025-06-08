#!/usr/bin/env python3
"""
Простой тест загрузки агента для диагностики проблем.
"""

import asyncio
import json
from pathlib import Path


def print_section(title: str):
    """Print section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def test_identity_loading():
    """Test loading identity directly."""
    print_section("📋 ТЕСТ ЗАГРУЗКИ IDENTITY ФАЙЛОВ")
    
    agents = ["supervisor", "vasya", "marina"]
    
    for agent in agents:
        print(f"\n🧪 Тестирование {agent}...")
        
        identity_path = Path(f"entities/{agent}/identity/identity.json")
        
        if not identity_path.exists():
            print(f"❌ Identity файл не найден: {identity_path}")
            continue
        
        try:
            with open(identity_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Check key fields
            name = config.get('name', 'Неизвестно')
            print(f"✅ {agent} ({name}): identity загружен")
            
            # Check routing policy
            routing_policy = config.get('operational_guidelines', {}).get('routing_policy', {})
            prefer_external = routing_policy.get('prefer_external', False)
            print(f"   🎯 prefer_external: {prefer_external}")
            
            # Check personality structure
            personality = config.get('personality', {})
            if 'summary' in personality:
                print(f"   👤 personality.summary: ✓")
            else:
                print(f"   👤 personality.summary: ❌ ОТСУТСТВУЕТ")
            
            if 'traits' in personality:
                print(f"   🎭 personality.traits: ✓ ({len(personality['traits'])} items)")
            else:
                print(f"   🎭 personality.traits: ❌ ОТСУТСТВУЕТ")
            
        except Exception as e:
            print(f"❌ Ошибка загрузки identity: {e}")


async def test_agent_creation():
    """Test creating agent instances."""
    print_section("🤖 ТЕСТ СОЗДАНИЯ АГЕНТОВ")
    
    try:
        from entities import discover_entities
        entities_info = discover_entities()
        
        for name in ['supervisor', 'vasya', 'marina']:
            print(f"\n🧪 Создание агента {name}...")
            
            try:
                entity_class = entities_info[name]['class']
                print(f"   ✅ Класс найден: {entity_class.__name__}")
                
                # Try to create instance
                agent = entity_class()
                print(f"   ✅ Агент создан успешно")
                
                # Check identity loading
                if hasattr(agent, 'identity_config'):
                    agent_name = agent.identity_config.get('name', 'Неизвестно')
                    print(f"   ✅ Identity загружен: {agent_name}")
                    
                    # Check personality in identity
                    personality = agent.identity_config.get('personality', {})
                    if 'summary' in personality:
                        print(f"   ✅ personality.summary: {personality['summary'][:50]}...")
                    else:
                        print(f"   ❌ personality.summary отсутствует")
                        print(f"   📋 Доступные поля personality: {list(personality.keys())}")
                        
                else:
                    print(f"   ❌ identity_config не найден")
                    
            except Exception as e:
                print(f"   ❌ Ошибка создания агента: {e}")
                import traceback
                traceback.print_exc()
        
    except Exception as e:
        print(f"❌ Ошибка обнаружения агентов: {e}")


async def test_router_creation():
    """Test creating router with agent config."""
    print_section("🔄 ТЕСТ СОЗДАНИЯ РОУТЕРА")
    
    try:
        # Load vasya config
        vasya_path = Path("entities/vasya/identity/identity.json")
        with open(vasya_path, 'r', encoding='utf-8') as f:
            vasya_config = json.load(f)
        
        print("✅ Конфигурация Васи загружена")
        
        # Try to create router
        from core.llm.router import LLMRouter
        router = LLMRouter(identity_config=vasya_config)
        print("✅ Роутер создан успешно")
        
        # Check routing preferences
        operational_guidelines = vasya_config.get("operational_guidelines", {})
        routing_policy = operational_guidelines.get("routing_policy", {})
        prefer_external = routing_policy.get("prefer_external", False)
        print(f"🎯 prefer_external: {prefer_external}")
        
    except Exception as e:
        print(f"❌ Ошибка создания роутера: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Main test function."""
    print_section("🔍 ДИАГНОСТИКА ПРОБЛЕМ АГЕНТОВ")
    
    # Test 1: Identity loading
    test_identity_loading()
    
    # Test 2: Agent creation
    await test_agent_creation()
    
    # Test 3: Router creation
    await test_router_creation()
    
    print_section("🎯 ЗАКЛЮЧЕНИЕ")
    print("Если все тесты прошли успешно, проблема может быть в:")
    print("   • API ключах для внешних LLM")
    print("   • Интеграции с API сервером")
    print("   • Обработке ошибок в runtime")


if __name__ == "__main__":
    asyncio.run(main()) 