#!/usr/bin/env python3
"""
📁 ЧИСТЫЙ ТЕСТ СОЗДАНИЯ ФАЙЛА АГЕНТОМ
"""

import requests
import time
import json
from pathlib import Path

def clean_test_file_creation():
    """Чистый тест создания файла Developer агентом."""
    
    print("📁 ТЕСТ СОЗДАНИЯ ФАЙЛА АГЕНТОМ DEVELOPER (ВАСЯ)")
    print("=" * 60)
    
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
    
    # Задача для Developer (Васи)
    task = """Вася, создай файл hello_world.py с простой функцией:

def hello_world(name):
    return f"Привет, {name}!"

if __name__ == "__main__":
    print(hello_world("Мир"))

Используй MCP инструменты для создания файла в текущей директории."""
    
    print("📋 ЗАДАЧА ДЛЯ ВАСИ (developer):")
    print(f"   {task}")
    print()
    
    # Проверяем что файл не существует
    test_file = Path("hello_world.py")
    if test_file.exists():
        test_file.unlink()
        print("🗑️ Удалил существующий файл для чистого теста")
    
    print("📤 Отправляю задачу Васе (developer)...")
    
    try:
        start_time = time.time()
        response = requests.post(
            "http://localhost:8000/v1/chat",
            params={"entity": "developer"},  # Используем правильный технический ID
            json={"message": task, "user_id": "file_creation_test"},
            timeout=60
        )
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get('answer', 'Нет ответа')
            route = result.get('route', 'unknown')
            latency = result.get('latency', elapsed)
            
            print(f"✅ ВАСЯ (DEVELOPER) ОТВЕТИЛ:")
            print(f"   ⏱️  Время: {latency:.1f}с")
            print(f"   🛤️  Маршрут: {route}")
            print(f"   💬 Ответ Васи:")
            
            # Красиво форматируем ответ
            lines = answer.split('\n')
            for line in lines:
                if line.strip():
                    print(f"      {line}")
            
            print()
            
            # Проверяем создался ли файл
            if test_file.exists():
                print("🎉 ФАЙЛ СОЗДАН УСПЕШНО!")
                
                # Читаем содержимое
                try:
                    with open(test_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    print("📄 СОДЕРЖИМОЕ ФАЙЛА:")
                    content_lines = content.split('\n')
                    for i, line in enumerate(content_lines, 1):
                        print(f"      {i:2d}: {line}")
                    
                    # Проверяем работает ли код
                    print("\n🧪 ТЕСТИРУЕМ КОД:")
                    try:
                        exec(content)
                        print("   ✅ Код выполняется без ошибок!")
                    except Exception as e:
                        print(f"   ❌ Ошибка выполнения: {e}")
                
                except Exception as e:
                    print(f"❌ Ошибка чтения файла: {e}")
            else:
                print("❌ Файл не был создан")
                print("   Возможно Вася не использовал MCP tools")
            
        else:
            print(f"❌ Ошибка от Васи: HTTP {response.status_code}")
            print(f"   {response.text}")
    
    except Exception as e:
        print(f"❌ Ошибка соединения: {e}")

if __name__ == "__main__":
    clean_test_file_creation() 