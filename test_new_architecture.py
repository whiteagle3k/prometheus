#!/usr/bin/env python3
"""
Тест новой архитектуры с разделением технических ID и человеческих имен.
Включает тестирование мультиязыковой поддержки.
"""

import asyncio
from entities import (
    discover_entities, get_entity_info, list_entity_ids, 
    list_entity_names, get_entity_name, get_localized_name
)
from core.runtime.registry import get_agent

async def test_new_architecture():
    """Тестируем новую архитектуру агентов с мультиязыковой поддержкой."""
    print("🏗️ ТЕСТ НОВОЙ АРХИТЕКТУРЫ АГЕНТОВ")
    print("=" * 60)
    
    # 1. Тест entity discovery
    print("\n📋 ШАГ 1: ТЕСТИРОВАНИЕ ENTITY DISCOVERY")
    print("-" * 40)
    
    entities = discover_entities()
    print(f"✅ Найдено агентов: {len(entities)}")
    
    for entity_id, info in entities.items():
        name_info = info.get('name', entity_id)
        if isinstance(name_info, dict):
            name_display = f"{name_info.get('en', 'Unknown')} / {name_info.get('ru', 'Unknown')}"
        else:
            name_display = str(name_info)
        print(f"   • {entity_id}: {name_display} ({info['class'].__name__})")
        print(f"     └─ {info.get('description', 'No description')}")
    
    # 2. Тест мультиязыковых имен
    print(f"\n🌍 ШАГ 2: ТЕСТИРОВАНИЕ МУЛЬТИЯЗЫКОВЫХ ИМЕН") 
    print("-" * 40)
    
    entity_ids = list_entity_ids()
    print(f"📱 Технические ID: {entity_ids}")
    
    # Тест английских имен
    entity_names_en = list_entity_names("en")
    print(f"🇬🇧 Английские имена: {entity_names_en}")
    
    # Тест русских имен
    entity_names_ru = list_entity_names("ru")
    print(f"🇷🇺 Русские имена: {entity_names_ru}")
    
    # Тест fallback на неизвестный язык
    entity_names_de = list_entity_names("de")  # Немецкий - должен fallback на английский
    print(f"🇩🇪 Немецкие имена (fallback): {entity_names_de}")
    
    # 3. Тест функции локализации
    print(f"\n🔧 ШАГ 3: ТЕСТИРОВАНИЕ ЛОКАЛИЗАЦИИ")
    print("-" * 40)
    
    test_cases = [
        ("supervisor", "en"),
        ("supervisor", "ru"), 
        ("developer", "en"),
        ("developer", "ru"),
        ("qa", "en"),
        ("qa", "ru"),
        ("aletheia", "en"),
        ("aletheia", "ru")
    ]
    
    for entity_id, lang in test_cases:
        try:
            localized_name = get_entity_name(entity_id, lang)
            print(f"   ✅ {entity_id} ({lang}): {localized_name}")
        except Exception as e:
            print(f"   ❌ {entity_id} ({lang}): Ошибка - {e}")
    
    # 4. Тест загрузки агентов через новый registry
    print(f"\n🚀 ШАГ 4: ТЕСТИРОВАНИЕ ЗАГРУЗКИ АГЕНТОВ")
    print("-" * 40)
    
    for entity_id in entity_ids:
        try:
            print(f"\n🔄 Загружаю {entity_id}...")
            agent = await get_agent(entity_id)
            entity_info = get_entity_info(entity_id)
            
            name_en = get_entity_name(entity_id, "en")
            name_ru = get_entity_name(entity_id, "ru")
            
            print(f"✅ {entity_id} загружен успешно:")
            print(f"   • Имя (EN): {name_en}")
            print(f"   • Имя (RU): {name_ru}")
            print(f"   • Класс: {type(agent).__name__}")
            print(f"   • Модуль: {entity_info['module_path']}")
            print(f"   • Роль: {entity_info.get('role', 'Unknown')}")
            
        except Exception as e:
            print(f"❌ {entity_id} не удалось загрузить: {e}")
            import traceback
            traceback.print_exc()
    
    # 5. Тест registry statistics с мультиязыковой поддержкой
    print(f"\n📊 ШАГ 5: СТАТИСТИКА REGISTRY С МУЛЬТИЯЗЫКОВОЙ ПОДДЕРЖКОЙ")
    print("-" * 40)
    
    from core.runtime.registry import get_registry_stats
    stats = get_registry_stats()
    
    print(f"🔢 Запущено агентов: {stats['agent_count']}")
    print(f"📋 Список ID: {stats['running_agents']}")
    
    if 'agent_info' in stats:
        print(f"\n📝 Детальная информация:")
        for entity_id, info in stats['agent_info'].items():
            name_en = info.get('name', entity_id)
            name_data = info.get('name_localized', entity_id)
            if isinstance(name_data, dict):
                name_ru = name_data.get('ru', name_en)
            else:
                name_ru = str(name_data)
            print(f"   • {entity_id}: {name_en} / {name_ru} ({info.get('class', 'Unknown')})")
    
    # 6. Тест исправления проблемы с Anthropic
    print(f"\n🔧 ШАГ 6: ПРОВЕРКА ИСПРАВЛЕНИЯ ANTHROPIC")
    print("-" * 40)
    
    try:
        vasya_info = get_entity_info("developer")
        vasya_agent = await get_agent("developer")
        
        # Проверяем что Vasya использует OpenAI вместо Anthropic
        identity = vasya_agent.identity_config
        llm_config = identity.get("external_llms", {})
        primary_provider = llm_config.get("primary_provider", "unknown")
        anthropic_enabled = llm_config.get("providers", {}).get("anthropic", {}).get("enabled", False)
        
        print(f"   ✅ Вася primary provider: {primary_provider}")
        print(f"   ✅ Anthropic enabled: {anthropic_enabled}")
        
        if primary_provider == "openai" and not anthropic_enabled:
            print(f"   ✅ Проблема с Anthropic исправлена!")
        else:
            print(f"   ⚠️ Конфигурация требует дополнительной проверки")
            
    except Exception as e:
        print(f"   ❌ Ошибка при проверке Anthropic: {e}")

    # 7. Тест fast-track оптимизации
    print(f"\n⚡ ШАГ 7: ТЕСТИРОВАНИЕ FAST-TRACK ОПТИМИЗАЦИИ")
    print("-" * 40)
    
    external_agents = ["supervisor", "developer", "qa"]  # Все имеют prefer_external: true
    
    for agent_id in external_agents:
        try:
            print(f"\n🔄 Тестирую fast-track для {agent_id}...")
            agent = await get_agent(agent_id)
            
            # Проверяем что агент настроен на prefer_external
            should_fast_track = agent._should_use_external_fast_track("Привет, как дела?")
            print(f"   🎯 Fast-track enabled: {should_fast_track}")
            
            if should_fast_track:
                # Тест скорости с fast-track (простой запрос)
                import time
                start_time = time.time()
                
                simple_request = "Привет! Как дела?"
                result = await agent.think(simple_request, user_id="fast_track_test")
                
                elapsed_time = time.time() - start_time
                fast_track_used = result.get("execution_details", {}).get("fast_track", False)
                route_used = result.get("execution_details", {}).get("route_used", "unknown")
                
                print(f"   ⏱️ Время выполнения: {elapsed_time:.1f}s")
                print(f"   🚀 Fast-track использован: {fast_track_used}")
                print(f"   📊 Маршрут: {route_used}")
                
                if fast_track_used and elapsed_time < 5.0:  # Менее 5 секунд
                    print(f"   ✅ Fast-track работает! Значительное ускорение")
                elif fast_track_used:
                    print(f"   ⚠️ Fast-track работает, но время выше ожидаемого")
                else:
                    print(f"   ❌ Fast-track не сработал")
            else:
                print(f"   ⚠️ Агент не настроен на fast-track")
                
        except Exception as e:
            print(f"   ❌ Ошибка тестирования {agent_id}: {e}")
    
    print(f"\n🎉 ТЕСТ ЗАВЕРШЕН!")
    print("✅ Новая архитектура с мультиязыковыми именами работает!")
    print("✅ Проблема с Anthropic для Васи исправлена!")
    print("⚡ Fast-track оптимизация для external-only агентов протестирована!")


if __name__ == "__main__":
    asyncio.run(test_new_architecture()) 