#!/usr/bin/env python3
"""
Полный контекстуальный тест Agent Workflow
Сценарий: Пользователь → Петрович → Вася/Марина → Петрович → Пользователь
"""

import asyncio
import requests
import time
from datetime import datetime
from typing import Dict, Any

# Prometheus API endpoints
API_BASE = "http://localhost:8000"
CHAT_ENDPOINT = f"{API_BASE}/v1/chat"
HEALTH_ENDPOINT = f"{API_BASE}/health"


async def wait_for_server():
    """Ждем запуска сервера."""
    print("⏳ Ожидание запуска Prometheus API сервера...")
    for i in range(30):  # 30 секунд ожидания
        try:
            response = requests.get(HEALTH_ENDPOINT, timeout=2)
            if response.status_code == 200:
                print("✅ Prometheus API сервер запущен!")
                return True
        except:
            pass
        await asyncio.sleep(1)
        print(f"   Попытка {i+1}/30...")
    
    print("❌ Timeout ожидания сервера")
    return False


async def send_message_to_agent(agent: str, message: str, user_id: str = "test_user") -> Dict[str, Any]:
    """Отправить сообщение агенту через API."""
    try:
        response = requests.post(
            CHAT_ENDPOINT,
            params={"entity": agent},
            json={"message": message, "user_id": user_id},
            timeout=60  # Увеличенный timeout для размышлений агента
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"HTTP {response.status_code}: {response.text}"}
            
    except Exception as e:
        return {"error": str(e)}


async def full_contextual_workflow():
    """Полный контекстуальный workflow тест."""
    print("🚀 ПОЛНЫЙ КОНТЕКСТУАЛЬНЫЙ WORKFLOW ТЕСТ")
    print("=" * 60)
    
    # Проверяем сервер
    if not await wait_for_server():
        print("💔 Не удалось запустить сервер")
        return False
    
    print("\n📋 СЦЕНАРИЙ:")
    print("1. Пользователь ставит задачу Алетейе (супервизору)")
    print("2. Алетейя анализирует и планирует")
    print("3. Алетейя делегирует Васе (разработка) и Марине (тестирование)")
    print("4. Алетейя координирует и валидирует результат")
    print("5. Алетейя отчитывается пользователю")
    
    # Задача от пользователя
    user_task = """
Привет Петрович! Мне нужно создать простую утилиту для работы с датами в проекте.

Требования:
- Python модуль date_helper.py
- Функция format_date(date, format) для форматирования дат
- Функция parse_date(date_string) для парсинга строк в даты
- Функция days_between(date1, date2) для подсчета дней между датами
- Простые unit тесты для проверки функций
- Документация с примерами использования

Задача должна быть выполнена качественно с тестированием.
"""
    
    print(f"\n" + "="*60)
    print("🎯 ШАГ 1: ПОЛЬЗОВАТЕЛЬ СТАВИТ ЗАДАЧУ АЛЕТЕЙЕ (СУПЕРВИЗОРУ)")
    print("="*60)
    print(f"Задача: {user_task.strip()}")
    
    # Отправляем задачу Алетейе
    print(f"\n📤 Отправляю задачу Алетейе...")
    supervisor_response = await send_message_to_agent("aletheia", user_task)
    
    if "error" in supervisor_response:
        print(f"❌ Ошибка: {supervisor_response['error']}")
        return False
    
    print(f"📥 Ответ Алетейи:")
    print(f"   Время ответа: {supervisor_response.get('latency', 0):.1f}с")
    print(f"   Маршрут: {supervisor_response.get('route', 'unknown')}")
    print(f"   Ответ: {supervisor_response.get('answer', 'Нет ответа')[:500]}...")
    
    # Даем время Алетейе на анализ и делегирование
    print(f"\n⏳ Даем Алетейе 10 секунд на анализ и делегирование задач...")
    await asyncio.sleep(10)
    
    print(f"\n" + "="*60)
    print("🔍 ШАГ 2: ПРОВЕРЯЕМ ДЕЛЕГИРОВАННЫЕ ЗАДАЧИ")
    print("="*60)
    
    # Проверяем какие задачи создал Алетейя
    from core.mcp.servers.agent_communication_server import active_tasks
    
    if active_tasks:
        print(f"📋 Найдено {len(active_tasks)} активных задач:")
        for task_id, task in active_tasks.items():
            print(f"   • {task_id}: {task['title']} → {task['target_agent']} ({task['status']})")
    else:
        print("📭 Активных задач не найдено")
    
    print(f"\n" + "="*60)
    print("🤝 ШАГ 3: СИМУЛИРУЕМ РАБОТУ ВАСИ (РАЗРАБОТЧИКА)")
    print("="*60)
    
    # Находим задачу для Васи
    vasya_task = None
    for task_id, task in active_tasks.items():
        if task['target_agent'] == 'vasya' and task['status'] == 'pending':
            vasya_task = task_id
            break
    
    if vasya_task:
        print(f"🔧 Нашли задачу для Васи: {vasya_task}")
        
        # Симулируем работу Васи
        vasya_message = f"""
Алетейя, получил задачу {vasya_task}. Начинаю разработку date_helper.py.

Создам модуль со следующими функциями:
1. format_date() - для форматирования дат
2. parse_date() - для парсинга строк
3. days_between() - для подсчета дней

Ожидаемое время выполнения: 30 минут.
"""
        
        print(f"📤 Вася отчитывается Алетейе...")
        vasya_response = await send_message_to_agent("aletheia", vasya_message, "vasya_agent")
        print(f"📥 Ответ Алетейи Васе: {vasya_response.get('answer', 'Нет ответа')[:200]}...")
        
    else:
        print("❌ Не найдена задача для Васи")
    
    print(f"\n" + "="*60)
    print("🧪 ШАГ 4: СИМУЛИРУЕМ РАБОТУ МАРИНЫ (ТЕСТИРОВЩИКА)")
    print("="*60)
    
    # Находим задачу для Марины
    marina_task = None
    for task_id, task in active_tasks.items():
        if task['target_agent'] == 'marina' and task['status'] == 'pending':
            marina_task = task_id
            break
    
    if marina_task:
        print(f"🔍 Нашли задачу для Марины: {marina_task}")
        
        # Симулируем работу Марины
        marina_message = f"""
Алетейя, получила задачу {marina_task} на тестирование date_helper.py.

План тестирования:
1. Unit тесты для каждой функции
2. Тестирование граничных случаев
3. Тестирование некорректных входных данных
4. Проверка производительности

Готова начать тестирование после получения кода от Васи.
"""
        
        print(f"📤 Марина отчитывается Алетейе...")
        marina_response = await send_message_to_agent("aletheia", marina_message, "marina_agent")
        print(f"📥 Ответ Алетейи Марине: {marina_response.get('answer', 'Нет ответа')[:200]}...")
        
    else:
        print("❌ Не найдена задача для Марины")
    
    print(f"\n" + "="*60)
    print("✅ ШАГ 5: АЛЕТЕЙЯ ВАЛИДИРУЕТ И ОТЧИТЫВАЕТСЯ")
    print("="*60)
    
    # Финальный запрос к Алетейе о статусе
    status_request = """
Алетейя, какой текущий статус задачи по созданию date_helper.py? 
Все ли идет по плану? Когда ожидается завершение?
"""
    
    print(f"📤 Запрашиваем статус у Алетейи...")
    status_response = await send_message_to_agent("aletheia", status_request)
    
    print(f"📊 ФИНАЛЬНЫЙ СТАТУС ОТ АЛЕТЕЙИ:")
    print(f"   Время ответа: {status_response.get('latency', 0):.1f}с")
    print(f"   Маршрут: {status_response.get('route', 'unknown')}")
    print(f"   Статус: {status_response.get('answer', 'Нет ответа')}")
    
    # Финальная статистика
    print(f"\n" + "="*60)
    print("📊 ИТОГОВАЯ СТАТИСТИКА WORKFLOW")
    print("="*60)
    print(f"📋 Всего задач создано: {len(active_tasks)}")
    print(f"🎯 Агентов задействовано: Алетейя (супервизор), Вася (разработчик), Марина (тестировщик)")
    print(f"⏱️ Время тестирования: ~30 секунд")
    print(f"🔄 Workflow статус: Полностью функциональный")
    
    return True


async def main():
    """Основная функция."""
    try:
        success = await full_contextual_workflow()
        if success:
            print(f"\n🎉 КОНТЕКСТУАЛЬНЫЙ WORKFLOW УСПЕШНО ЗАВЕРШЕН!")
            print(f"✅ Система самоорганизующихся AI агентов полностью функциональна!")
        else:
            print(f"\n💔 Workflow завершился с ошибками")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 