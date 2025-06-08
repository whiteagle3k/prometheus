#!/usr/bin/env python3
"""
Диагностический тест для выяснения проблем с роутингом и агентами.
"""

import asyncio
import requests
import time
import json


async def test_simple_request(entity: str, message: str = "Привет!"):
    """Тестирует простой запрос к агенту."""
    url = "http://localhost:8000/v1/chat"
    data = {"message": message, "user_id": "debug_test"}
    
    print(f"\n{'='*50}")
    print(f"ТЕСТ АГЕНТА: {entity}")
    print(f"{'='*50}")
    
    try:
        start_time = time.time()
        
        response = requests.post(
            url, json=data, 
            params={"entity": entity}, 
            timeout=60
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get("answer", "")
            route = result.get("route_used", "НЕ_ОПРЕДЕЛЕН")
            latency = result.get("latency_seconds", elapsed)
            
            print(f"✅ УСПЕХ за {elapsed:.1f}с")
            print(f"🎯 МАРШРУТ: '{route}'")
            print(f"⏱️ Латентность: {latency:.2f}с")
            print(f"📝 Ответ: {answer[:200]}...")
            
            # Debug info
            if hasattr(result, 'keys'):
                print(f"🔧 Все поля ответа: {list(result.keys())}")
            
            return True, route, answer
            
        else:
            print(f"❌ ОШИБКА {response.status_code}")
            print(f"📄 Ответ: {response.text[:500]}")
            return False, None, None
            
    except Exception as e:
        print(f"❌ ИСКЛЮЧЕНИЕ: {e}")
        return False, None, None


async def test_agent_identity_loading():
    """Тестирует загрузку identity агентов напрямую."""
    print(f"\n{'='*50}")
    print(f"ТЕСТ ЗАГРУЗКИ IDENTITY")
    print(f"{'='*50}")
    
    # Test loading entities directly
    entities = ["aletheia", "vasya", "marina"]
    
    for entity in entities:
        print(f"\n🧪 Тестирую загрузку {entity}...")
        try:
            # Try to load via API health check
            response = requests.get(f"http://localhost:8000/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                available = data.get("running_agents", [])
                
                if entity in available:
                    print(f"   ✅ {entity} доступен в API")
                else:
                    print(f"   ❌ {entity} НЕ НАЙДЕН в API")
                    print(f"   📋 Доступные: {available}")
        except Exception as e:
            print(f"   ❌ Ошибка проверки {entity}: {e}")


async def test_complex_routing_task():
    """Тестирует сложную задачу которая должна активировать внешний роутинг."""
    print(f"\n{'='*50}")
    print(f"ТЕСТ СЛОЖНОЙ ЗАДАЧИ ДЛЯ РОУТИНГА")
    print(f"{'='*50}")
    
    # Test each agent with a complex task
    complex_task = """Это СЛОЖНАЯ АРХИТЕКТУРНАЯ ЗАДАЧА требующая глубокого анализа и системного мышления:

Проанализируй и спроектируй модульную систему для интеграции нескольких AI провайдеров с динамическим роутингом на основе сложности задач, учитывая производительность, стоимость, доступность и специализацию каждого провайдера.

Требуется сложное техническое решение с многоуровневой архитектурой."""
    
    agents = ["aletheia", "vasya", "marina"]
    
    for agent in agents:
        success, route, answer = await test_simple_request(agent, complex_task)
        
        if success:
            if route == "external":
                print(f"   🌐 ✅ {agent}: ВНЕШНИЙ LLM активирован!")
            elif route == "unknown":
                print(f"   ❓ ⚠️ {agent}: маршрут неопределен")
            else:
                print(f"   🏠 ❌ {agent}: локальный маршрут ({route})")
        else:
            print(f"   💥 ❌ {agent}: запрос провалился")


async def test_api_response_structure():
    """Тестирует структуру ответа API."""
    print(f"\n{'='*50}")
    print(f"ТЕСТ СТРУКТУРЫ ОТВЕТА API")
    print(f"{'='*50}")
    
    try:
        response = requests.post(
            "http://localhost:8000/v1/chat",
            json={"message": "тест структуры", "user_id": "debug"},
            params={"entity": "aletheia"},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Структура ответа API:")
            
            # Pretty print the structure
            for key, value in result.items():
                value_type = type(value).__name__
                if isinstance(value, str):
                    value_preview = value[:50] + "..." if len(value) > 50 else value
                    print(f"   {key}: {value_type} = '{value_preview}'")
                else:
                    print(f"   {key}: {value_type} = {value}")
        else:
            print(f"❌ API ошибка: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Исключение при тесте API: {e}")


async def main():
    """Главная диагностическая функция."""
    print("🔍 ДИАГНОСТИКА ПРОБЛЕМ РОУТИНГА И АГЕНТОВ")
    print("=" * 60)
    
    # Check API availability
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ API сервер доступен")
            data = response.json()
            print(f"📋 Доступные агенты: {data.get('running_agents', [])}")
        else:
            print("❌ API сервер недоступен")
            return
    except:
        print("❌ API сервер недоступен")
        return
    
    # Run diagnostic tests
    await test_agent_identity_loading()
    await test_api_response_structure()
    
    # Test simple requests
    print(f"\n{'='*60}")
    print("ТЕСТ ПРОСТЫХ ЗАПРОСОВ")
    print(f"{'='*60}")
    
    agents = ["aletheia", "vasya", "marina"]
    simple_results = []
    
    for agent in agents:
        success, route, answer = await test_simple_request(agent, "Привет! Как дела?")
        simple_results.append((agent, success, route))
    
    # Test complex routing
    await test_complex_routing_task()
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 ИТОГИ ДИАГНОСТИКИ")
    print(f"{'='*60}")
    
    print("\n🔍 Результаты простых запросов:")
    for agent, success, route in simple_results:
        status = "✅" if success else "❌"
        route_status = f"(route: {route})" if route else "(нет маршрута)"
        print(f"   {agent}: {status} {route_status}")
    
    print("\n💡 РЕКОМЕНДАЦИИ:")
    failed_agents = [agent for agent, success, _ in simple_results if not success]
    unknown_routes = [agent for agent, success, route in simple_results if success and route == "unknown"]
    
    if failed_agents:
        print(f"❌ Починить агентов: {failed_agents}")
    if unknown_routes:
        print(f"🔧 Исправить роутинг для: {unknown_routes}")
    if not failed_agents and not unknown_routes:
        print("✅ Все агенты работают корректно!")


if __name__ == "__main__":
    asyncio.run(main()) 