#!/usr/bin/env python3
"""
Тест реальной работы команды разработчиков с внешними LLM.
Проверяет что агенты используют GPT-4o и Claude вместо локальных моделей.
"""

import asyncio
import json
import time
from pathlib import Path
import requests


def print_section(title: str):
    """Print section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def check_anthropic_console():
    """Provide instructions for checking Anthropic console."""
    print("🔍 Для проверки вызовов Anthropic:")
    print("   1. Откройте https://console.anthropic.com/")
    print("   2. Перейдите в Usage -> Activity")
    print("   3. Обновите страницу после тестов")
    print("   4. Должны появиться новые API вызовы")


def check_openai_console():
    """Provide instructions for checking OpenAI console."""
    print("🔍 Для проверки вызовов OpenAI:")
    print("   1. Откройте https://platform.openai.com/usage")
    print("   2. Проверьте Activity в реальном времени")
    print("   3. Должны появиться новые API вызовы")


async def test_agent_external_llm(agent_name: str, entity_name: str, test_message: str):
    """Test single agent with external LLM."""
    print(f"\n🧪 Тестирование {agent_name} ({entity_name})...")
    
    # API endpoint
    url = "http://localhost:8000/v1/chat"
    
    # Request data
    data = {
        "message": test_message,
        "user_id": "test_external_routing"
    }
    
    # Headers
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        print(f"📤 Отправка запроса к {agent_name}...")
        print(f"   Сообщение: {test_message}")
        
        start_time = time.time()
        
        # Make request with entity parameter
        response = requests.post(
            url,
            json=data,
            headers=headers,
            params={"entity": entity_name},
            timeout=60
        )
        
        elapsed_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get("answer", "")
            route_used = result.get("route_used", "unknown")
            
            print(f"✅ Ответ получен за {elapsed_time:.1f} сек")
            print(f"🎯 Маршрут: {route_used}")
            print(f"📝 Ответ: {answer[:100]}..." if len(answer) > 100 else f"📝 Ответ: {answer}")
            
            # Check if external route was used
            if route_used == "external":
                print("✅ ВНЕШНИЙ LLM ИСПОЛЬЗОВАН! 🎉")
                return True
            else:
                print(f"❌ Локальный маршрут использован: {route_used}")
                return False
                
        else:
            print(f"❌ HTTP ошибка: {response.status_code}")
            print(f"   Текст: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Таймаут запроса (60 сек)")
        return False
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")
        return False


async def main():
    """Main test function."""
    print_section("🚀 ТЕСТ ВНЕШНИХ LLM В КОМАНДЕ РАЗРАБОТЧИКОВ")
    
    print("🎯 Цель: Убедиться что агенты используют GPT-4o/Claude вместо локальных моделей")
    
    # Check if API server is running
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code != 200:
            print("❌ API сервер не доступен. Запустите: poetry run python prometheus.py api")
            return
    except:
        print("❌ API сервер не доступен. Запустите: poetry run python prometheus.py api")
        return
    
    print("✅ API сервер доступен")
    
    # Test cases for each agent
    test_cases = [
        {
            "agent_name": "Петрович (Supervisor)",
            "entity_name": "petrovich", 
            "message": "Нужно создать функцию для подсчета файлов в директории. Проанализируй задачу.",
            "expected_llm": "GPT-4o"
        },
        {
            "agent_name": "Вася (Developer)",
            "entity_name": "vasya",
            "message": "Создай функцию count_files(directory) которая возвращает количество файлов в папке.",
            "expected_llm": "Claude Sonnet"
        },
        {
            "agent_name": "Марина (QA)",
            "entity_name": "marina", 
            "message": "Протестируй функцию count_files и найди возможные проблемы.",
            "expected_llm": "GPT-4o"
        }
    ]
    
    # Show console checking instructions
    print_section("📋 ИНСТРУКЦИИ ПО ПРОВЕРКЕ")
    check_anthropic_console()
    print()
    check_openai_console()
    
    # Run tests
    results = {}
    
    for test_case in test_cases:
        print_section(f"🧪 {test_case['agent_name']}")
        print(f"🎯 Ожидаемая модель: {test_case['expected_llm']}")
        
        success = await test_agent_external_llm(
            test_case["agent_name"],
            test_case["entity_name"], 
            test_case["message"]
        )
        
        results[test_case["agent_name"]] = success
        
        # Pause between requests
        if success:
            print("⏳ Пауза 3 сек перед следующим тестом...")
            await asyncio.sleep(3)
    
    # Summary
    print_section("📊 РЕЗУЛЬТАТЫ ТЕСТОВ")
    
    all_passed = True
    for agent, success in results.items():
        status = "✅ ВНЕШНИЙ LLM" if success else "❌ ЛОКАЛЬНЫЙ"
        print(f"{agent}: {status}")
        if not success:
            all_passed = False
    
    print_section("🎯 ЗАКЛЮЧЕНИЕ")
    
    if all_passed:
        print("🎉 ВСЕ АГЕНТЫ ИСПОЛЬЗУЮТ ВНЕШНИЕ LLM!")
        print("✅ Проблема маршрутизации решена")
        print("🔧 Исправления работают корректно")
        print("\n📊 Проверьте консоли:")
        print("   • Anthropic Console: новые вызовы Claude") 
        print("   • OpenAI Console: новые вызовы GPT-4o")
    else:
        print("❌ НЕКОТОРЫЕ АГЕНТЫ ВСЕ ЕЩЕ ИСПОЛЬЗУЮТ ЛОКАЛЬНЫЕ МОДЕЛИ")
        print("⚠️ Требуются дополнительные исправления")
        print("\n🔧 Возможные причины:")
        print("   • API ключи не настроены")
        print("   • Внешние LLM недоступны")
        print("   • Конфигурация все еще неправильная")


if __name__ == "__main__":
    asyncio.run(main()) 