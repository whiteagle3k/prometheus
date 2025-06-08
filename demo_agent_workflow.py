#!/usr/bin/env python3
"""
ДЕМОНСТРАЦИЯ WORKFLOW'А КОМАНДЫ РАЗРАБОТЧИКОВ

Показывает как Петрович (Supervisor) должен делегировать задачи
и координировать работу команды через Agent-to-Agent коммуникацию.

Workflow: User → Supervisor → Vasya ↔ Marina → Supervisor → User
"""

import asyncio
import requests
import time
import json
from typing import Dict, Any


class AgentWorkflowDemo:
    """Демонстрация workflow'а команды разработчиков."""
    
    def __init__(self):
        self.api_base = "http://localhost:8000"
        self.chat_endpoint = f"{self.api_base}/v1/chat"
        
    async def send_to_agent(self, agent: str, message: str, user_id: str = "workflow_demo") -> Dict[str, Any]:
        """Отправить сообщение агенту."""
        try:
            print(f"\n📤 ОТПРАВЛЯЮ {agent.upper()}:")
            print(f"   {message[:100]}...")
            
            response = requests.post(
                self.chat_endpoint,
                params={"entity": agent},
                json={"message": message, "user_id": user_id},
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get("answer", "")
                route = result.get("route", "unknown")
                latency = result.get("latency", 0)
                
                print(f"📥 ОТВЕТ {agent.upper()} ({route}, {latency:.1f}с):")
                print(f"   {answer[:200]}...")
                
                return {
                    "success": True,
                    "answer": answer,
                    "route": route,
                    "latency": latency
                }
            else:
                print(f"❌ Ошибка {response.status_code}: {response.text}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            print(f"❌ Ошибка коммуникации с {agent}: {e}")
            return {"success": False, "error": str(e)}
    
    async def demonstrate_workflow(self, task: str):
        """Демонстрация полного workflow'а команды."""
        print("=" * 80)
        print("🚀 ДЕМОНСТРАЦИЯ WORKFLOW'А КОМАНДЫ РАЗРАБОТЧИКОВ")
        print("=" * 80)
        print(f"📋 Задача: {task}")
        print(f"🎯 Workflow: User → Supervisor → Vasya ↔ Marina → Supervisor → User")
        
        # Шаг 1: Пользователь → Supervisor (Петрович)
        print(f"\n{'='*60}")
        print("ШАГ 1: ПОЛЬЗОВАТЕЛЬ → SUPERVISOR (ПЕТРОВИЧ)")
        print(f"{'='*60}")
        
        supervisor_message = f"""
ЗАДАЧА ОТ ПОЛЬЗОВАТЕЛЯ: {task}

Петрович, как руководитель команды разработки:
1. Проанализируй задачу
2. Разбей на подзадачи
3. Назначь Васе разработку
4. Назначь Марине тестирование
5. Координируй выполнение

⚠️ ВАЖНО: Ты должен координировать команду, а не делать сам!
"""
        
        supervisor_result = await self.send_to_agent("supervisor", supervisor_message)
        if not supervisor_result["success"]:
            print("❌ Supervisor недоступен")
            return
        
        # Шаг 2: Supervisor → Vasya (Делегирование разработки)
        print(f"\n{'='*60}")
        print("ШАГ 2: SUPERVISOR → VASYA (ДЕЛЕГИРОВАНИЕ РАЗРАБОТКИ)")
        print(f"{'='*60}")
        
        vasya_task = f"""
ДЕЛЕГИРОВАНИЕ ЗАДАЧИ ОТ ПЕТРОВИЧА:

Оригинальная задача: {task}

Вася, тебе поручается разработка:
1. Создай рабочий код для решения задачи
2. Используй MCP инструменты для реальной реализации
3. Создай файлы и протестируй базовую функциональность
4. После завершения сообщи результат

🔧 ОБЯЗАТЕЛЬНО: Используй filesystem_write_file и другие MCP инструменты!
⚡ Приступай к выполнению немедленно!
"""
        
        vasya_result = await self.send_to_agent("vasya", vasya_task)
        if not vasya_result["success"]:
            print("❌ Vasya недоступен")
            return
        
        # Шаг 3: Vasya → Marina (Передача на тестирование)
        print(f"\n{'='*60}")
        print("ШАГ 3: VASYA → MARINA (ПЕРЕДАЧА НА ТЕСТИРОВАНИЕ)")
        print(f"{'='*60}")
        
        marina_task = f"""
ПЕРЕДАЧА ОТ ВАСИ НА ТЕСТИРОВАНИЕ:

Исходная задача: {task}
Результат разработки: {vasya_result["answer"][:300]}...

Марина, Вася завершил разработку. Необходимо:
1. Проверить созданные файлы
2. Протестировать функциональность
3. Найти возможные баги или проблемы
4. Предоставить отчет о качестве
5. Дать рекомендации по улучшению

🔧 ИСПОЛЬЗУЙ: filesystem_read_file и terminal_execute для тестирования!
"""
        
        marina_result = await self.send_to_agent("marina", marina_task)
        if not marina_result["success"]:
            print("❌ Marina недоступна")
            return
        
        # Шаг 4: Marina → Supervisor (Отчет о тестировании)
        print(f"\n{'='*60}")
        print("ШАГ 4: MARINA → SUPERVISOR (ОТЧЕТ О ТЕСТИРОВАНИИ)")
        print(f"{'='*60}")
        
        final_report_message = f"""
ОТЧЕТ О ВЫПОЛНЕНИИ ЗАДАЧИ:

Исходная задача: {task}

РЕЗУЛЬТАТ РАЗРАБОТКИ (Вася):
{vasya_result["answer"][:400]}...

РЕЗУЛЬТАТ ТЕСТИРОВАНИЯ (Марина):
{marina_result["answer"][:400]}...

Петрович, команда завершила работу над задачей. Подготовь итоговый отчет для пользователя.
"""
        
        final_result = await self.send_to_agent("supervisor", final_report_message)
        
        # Итоги
        print(f"\n{'='*60}")
        print("📊 ИТОГИ WORKFLOW'А")
        print(f"{'='*60}")
        
        total_time = (
            supervisor_result.get("latency", 0) + 
            vasya_result.get("latency", 0) + 
            marina_result.get("latency", 0) + 
            final_result.get("latency", 0)
        )
        
        print(f"⏱️ Общее время: {total_time:.1f} секунд")
        print(f"🎯 Маршруты:")
        print(f"   Supervisor: {supervisor_result.get('route', 'unknown')}")
        print(f"   Vasya: {vasya_result.get('route', 'unknown')}")
        print(f"   Marina: {marina_result.get('route', 'unknown')}")
        print(f"   Final: {final_result.get('route', 'unknown')}")
        
        print(f"\n📋 ИТОГОВЫЙ РЕЗУЛЬТАТ:")
        print(f"{final_result.get('answer', 'Нет ответа')[:600]}...")
        
        print(f"\n{'='*60}")
        print("💡 ЗНАЧЕНИЕ ДЕМОНСТРАЦИИ")
        print(f"{'='*60}")
        print("🌟 Показан принцип саморазвивающейся команды:")
        print("   • Supervisor координирует и делегирует")
        print("   • Vasya выполняет разработку") 
        print("   • Marina проводит тестирование")
        print("   • Команда работает автономно")
        print("🚀 Следующий шаг: автоматизация через MCP инструменты")


async def main():
    """Запуск демонстрации."""
    demo = AgentWorkflowDemo()
    
    # Проверка доступности API
    try:
        response = requests.get(f"{demo.api_base}/health", timeout=5)
        if response.status_code != 200:
            print("❌ API сервер недоступен")
            return
    except:
        print("❌ API сервер недоступен") 
        return
    
    # Демонстрация с реальной задачей
    task = "Создать Python файл timestamp_utils.py с функцией get_current_timestamp() которая возвращает текущее время в формате ISO"
    
    await demo.demonstrate_workflow(task)


if __name__ == "__main__":
    asyncio.run(main()) 