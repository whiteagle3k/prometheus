#!/usr/bin/env python3
"""
🧪 ПРОСТОЙ ТЕСТ ОДНОГО АГЕНТА
"""

import requests
import time
import json

def test_single_agent():
    """Тестируем одного агента."""
    
    print("🧪 ПРОСТОЙ ТЕСТ АГЕНТА SUPERVISOR")
    print("=" * 50)
    
    # Проверяем сервер
    try:
        health_response = requests.get("http://localhost:8000/health", timeout=5)
        if health_response.status_code != 200:
            print("❌ Сервер недоступен")
            return
        print("✅ Сервер доступен")
    except:
        print("❌ Сервер недоступен")
        return
    
    # Простой запрос
    message = "Привет! Что ты умеешь?"
    
    print(f"📤 Отправляю: {message}")
    
    try:
        start_time = time.time()
        response = requests.post(
            "http://localhost:8000/v1/chat",
            params={"entity": "supervisor"},
            json={"message": message, "user_id": "simple_test"},
            timeout=30
        )
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get('answer', 'Нет ответа')
            route = result.get('route', 'unknown')
            latency = result.get('latency', elapsed)
            
            print(f"✅ УСПЕХ!")
            print(f"   ⏱️  Время: {latency:.1f}с")
            print(f"   🛤️  Маршрут: {route}")
            print(f"   💬 Ответ: {answer[:200]}{'...' if len(answer) > 200 else ''}")
            
            if route == "external":
                print("   ✅ Используется внешний LLM - правильно!")
            else:
                print("   ⚠️ Используется локальная модель")
        else:
            print(f"❌ Ошибка: HTTP {response.status_code}")
            print(f"   {response.text}")
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    test_single_agent() 