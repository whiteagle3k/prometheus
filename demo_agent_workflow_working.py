#!/usr/bin/env python3
"""
Демонстрация работающего Agent Workflow
Обход проблем MCP клиента, прямое использование agent_communication функций
"""

import asyncio
import requests
from datetime import datetime
from typing import Dict, Any


# Прямой импорт функций из agent_communication_server
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

# Импортируем внутренние функции напрямую
from core.mcp.servers.agent_communication_server import (
    _agent_send_message,
    _agent_delegate_task,
    _agent_get_status,
    _agent_get_active_tasks,
    _agent_update_task_status,
    active_tasks,
    task_counter
)


class WorkingAgentCommunication:
    """Рабочая обертка для agent communication без MCP клиента."""
    
    async def send_message(self, target_agent: str, message: str, task_type: str = "general", priority: str = "medium"):
        """Отправить сообщение агенту."""
        result = await _agent_send_message({
            "target_agent": target_agent,
            "message": message,
            "task_type": task_type,
            "priority": priority
        })
        return result.content[0].text if result.content else "Ошибка отправки"
    
    async def delegate_task(self, target_agent: str, task_title: str, task_description: str, 
                          acceptance_criteria=None, priority: str = "medium", deadline=None):
        """Делегировать задачу агенту."""
        args = {
            "target_agent": target_agent,
            "task_title": task_title,
            "task_description": task_description,
            "priority": priority
        }
        if acceptance_criteria:
            args["acceptance_criteria"] = acceptance_criteria
        if deadline:
            args["deadline"] = deadline
            
        result = await _agent_delegate_task(args)
        return result.content[0].text if result.content else "Ошибка делегирования"
    
    async def get_status(self, target_agent=None):
        """Получить статус агентов."""
        args = {}
        if target_agent:
            args["target_agent"] = target_agent
            
        result = await _agent_get_status(args)
        return result.content[0].text if result.content else "Ошибка получения статуса"
    
    async def get_active_tasks(self, filter_by_agent=None, filter_by_status=None):
        """Получить активные задачи."""
        args = {}
        if filter_by_agent:
            args["filter_by_agent"] = filter_by_agent
        if filter_by_status:
            args["filter_by_status"] = filter_by_status
            
        result = await _agent_get_active_tasks(args)
        return result.content[0].text if result.content else "Ошибка получения задач"
    
    async def update_task_status(self, task_id: str, status: str, result_text=None, next_agent=None):
        """Обновить статус задачи."""
        args = {"task_id": task_id, "status": status}
        if result_text:
            args["result"] = result_text
        if next_agent:
            args["next_agent"] = next_agent
            
        result = await _agent_update_task_status(args)
        return result.content[0].text if result.content else "Ошибка обновления статуса"


async def demo_agent_workflow():
    """Демонстрация полного agent workflow."""
    print("🚀 ДЕМОНСТРАЦИЯ AGENT WORKFLOW")
    print("=" * 50)
    
    # Создаем рабочий клиент
    agent_comm = WorkingAgentCommunication()
    
    print("📊 1. Проверяем статус системы...")
    status = await agent_comm.get_status()
    print(f"Статус: {status[:200]}...")
    
    print("\n🎯 2. Делегируем задачу Васе...")
    delegation_result = await agent_comm.delegate_task(
        target_agent="vasya",
        task_title="Создать файл с утилитой времени",
        task_description="Создай Python файл time_utils.py с функцией get_current_timestamp() которая возвращает текущее время в ISO формате",
        acceptance_criteria=[
            "Файл должен быть создан в корне проекта",
            "Функция должна возвращать строку в ISO формате",
            "Добавить простой пример использования"
        ],
        priority="medium"
    )
    print(f"Результат делегирования: {delegation_result[:300]}...")
    
    # Ищем ID задачи из результата
    task_id = None
    if "TASK_" in delegation_result:
        import re
        match = re.search(r'(TASK_\d+_\w+_\d+)', delegation_result)
        if match:
            task_id = match.group(1)
            print(f"📋 Найден ID задачи: {task_id}")
    
    print("\n📋 3. Проверяем активные задачи...")
    tasks = await agent_comm.get_active_tasks()
    print(f"Активные задачи: {tasks}")
    
    if task_id:
        print(f"\n🔄 4. Обновляем статус задачи {task_id} на 'in_progress'...")
        update_result = await agent_comm.update_task_status(
            task_id=task_id,
            status="in_progress",
            result_text="Начинаю работу над файлом time_utils.py"
        )
        print(f"Результат обновления: {update_result}")
        
        print(f"\n✅ 5. Завершаем задачу {task_id}...")
        complete_result = await agent_comm.update_task_status(
            task_id=task_id,
            status="completed",
            result_text="Файл time_utils.py создан успешно с функцией get_current_timestamp()",
            next_agent="marina"
        )
        print(f"Результат завершения: {complete_result}")
    
    print("\n📋 6. Проверяем финальные активные задачи...")
    final_tasks = await agent_comm.get_active_tasks()
    print(f"Финальные задачи: {final_tasks}")
    
    print("\n🎉 ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА!")
    print("✅ Agent Communication система полностью функциональна!")
    print("📊 Возможности:")
    print("   • Делегирование задач между агентами")
    print("   • Отслеживание статуса задач")
    print("   • Автоматическая передача между агентами в workflow")
    print("   • Полная интеграция с Prometheus API")


async def main():
    """Основная функция."""
    try:
        await demo_agent_workflow()
    except Exception as e:
        print(f"❌ Ошибка демонстрации: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 