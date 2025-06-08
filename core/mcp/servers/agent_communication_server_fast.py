#!/usr/bin/env python3
"""
Agent Communication MCP Server (FastMCP version)

Позволяет агентам общаться друг с другом через упрощенный FastMCP API.
"""

import requests
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP("Agent Communication")

# Prometheus API endpoints
API_BASE = "http://localhost:8000"
CHAT_ENDPOINT = f"{API_BASE}/v1/chat"
HEALTH_ENDPOINT = f"{API_BASE}/health"

# Task delegation storage
active_tasks: Dict[str, Dict[str, Any]] = {}
task_counter = 0


@mcp.tool()
def agent_send_message(
    target_agent: str, 
    message: str, 
    task_type: str = "general", 
    priority: str = "medium"
) -> str:
    """Send a message to another agent"""
    
    # Format message with context
    formatted_message = f"""
МЕЖАГЕНТНОЕ СООБЩЕНИЕ от агента команды разработки:

Тип: {task_type}
Приоритет: {priority}
Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Сообщение: {message}

⚠️ ВАЖНО: Это сообщение от коллеги по команде разработки. Если это делегирование задачи - выполни её и используй MCP инструменты для результата.
"""
    
    try:
        # Send message via Prometheus API
        response = requests.post(
            CHAT_ENDPOINT,
            params={"entity": target_agent},
            json={
                "message": formatted_message,
                "user_id": "agent_communication"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            agent_response = result.get("answer", "No response")
            route = result.get("route", "unknown")
            latency = result.get("latency", 0)
            
            return f"""✅ Сообщение отправлено агенту {target_agent}

📤 Отправлено: {message[:100]}...
📥 Ответ агента: {agent_response[:200]}...
🎯 Маршрут: {route}
⏱️ Время ответа: {latency:.1f}с

💡 Агент получил и обработал сообщение."""
        else:
            return f"❌ Ошибка отправки сообщения агенту {target_agent}: {response.status_code} - {response.text}"
            
    except Exception as e:
        return f"❌ Ошибка коммуникации с агентом {target_agent}: {str(e)}"


@mcp.tool()
def agent_delegate_task(
    target_agent: str,
    task_title: str,
    task_description: str,
    acceptance_criteria: Optional[List[str]] = None,
    priority: str = "medium",
    deadline: Optional[str] = None
) -> str:
    """Delegate a specific task to another agent with tracking"""
    global task_counter
    task_counter += 1
    
    # Generate task ID
    task_id = f"TASK_{task_counter:04d}_{target_agent}_{datetime.now().strftime('%m%d_%H%M')}"
    
    # Store task for tracking
    task_data = {
        "id": task_id,
        "title": task_title,
        "description": task_description,
        "target_agent": target_agent,
        "acceptance_criteria": acceptance_criteria or [],
        "priority": priority,
        "deadline": deadline,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "assigned_by": "supervisor"
    }
    active_tasks[task_id] = task_data
    
    # Format delegation message
    criteria_text = "\n".join([f"  ✓ {criteria}" for criteria in acceptance_criteria]) if acceptance_criteria else "  ✓ Выполнить задачу полностью"
    
    delegation_message = f"""
🎯 ДЕЛЕГИРОВАНИЕ ЗАДАЧИ #{task_id}

Название: {task_title}
Приоритет: {priority}
{'Дедлайн: ' + deadline if deadline else ''}

ОПИСАНИЕ ЗАДАЧИ:
{task_description}

КРИТЕРИИ ПРИЕМКИ:
{criteria_text}

🔧 ОБЯЗАТЕЛЬНО: Используй MCP инструменты для выполнения задачи!
📝 По завершении используй agent_update_task_status для отчета о результате.

⚡ Приступай к выполнению немедленно!
"""
    
    # Send delegation via agent communication
    send_result = agent_send_message(target_agent, delegation_message, "delegation", priority)
    
    return f"""✅ Задача делегирована агенту {target_agent}

🆔 ID задачи: {task_id}
📋 Название: {task_title}
👤 Исполнитель: {target_agent}
⚡ Статус: pending → отправлена агенту

{send_result}

💡 Задача добавлена в систему отслеживания."""


@mcp.tool()
def agent_get_status(target_agent: Optional[str] = None) -> str:
    """Get status and availability of other agents"""
    
    try:
        # Check Prometheus API health
        health_response = requests.get(HEALTH_ENDPOINT, timeout=5)
        
        if health_response.status_code == 200:
            health_data = health_response.json()
            running_agents = health_data.get("running_agents", [])
            
            if target_agent:
                # Check specific agent
                if target_agent in running_agents:
                    # Test agent responsiveness
                    test_response = requests.post(
                        CHAT_ENDPOINT,
                        params={"entity": target_agent},
                        json={"message": "Status check", "user_id": "status_check"},
                        timeout=10
                    )
                    
                    if test_response.status_code == 200:
                        result = test_response.json()
                        latency = result.get("latency", 0)
                        route = result.get("route", "unknown")
                        
                        return f"""
✅ Агент {target_agent} - АКТИВЕН

📊 Статус: Online и отвечает
⏱️ Время ответа: {latency:.1f}с  
🎯 Роутинг: {route}
🔄 Последняя проверка: {datetime.now().strftime('%H:%M:%S')}
"""
                    else:
                        return f"⚠️ Агент {target_agent} зарегистрирован но не отвечает"
                else:
                    return f"❌ Агент {target_agent} не найден в системе"
            else:
                # Check all agents
                return f"""
📊 СТАТУС ВСЕХ АГЕНТОВ:

✅ Активные агенты: {', '.join(running_agents)}
📈 Всего агентов: {len(running_agents)}
🔄 Проверено: {datetime.now().strftime('%H:%M:%S')}

💡 Для детальной проверки укажите конкретного агента.
"""
        else:
            return "❌ Ошибка подключения к Prometheus API"
            
    except Exception as e:
        return f"❌ Ошибка проверки статуса: {str(e)}"


@mcp.tool()
def agent_get_active_tasks(
    filter_by_agent: Optional[str] = None, 
    filter_by_status: Optional[str] = None
) -> str:
    """Get list of active tasks in the system"""
    
    filtered_tasks = active_tasks.copy()
    
    # Apply filters
    if filter_by_agent:
        filtered_tasks = {k: v for k, v in filtered_tasks.items() if v["target_agent"] == filter_by_agent}
    if filter_by_status:
        filtered_tasks = {k: v for k, v in filtered_tasks.items() if v["status"] == filter_by_status}
    
    if not filtered_tasks:
        return "📭 Нет активных задач соответствующих фильтрам."
    
    # Format task list
    task_list = []
    for task_id, task in filtered_tasks.items():
        status_emoji = {
            "pending": "⏳",
            "in_progress": "🔄", 
            "completed": "✅",
            "failed": "❌",
            "needs_review": "🔍"
        }.get(task["status"], "❓")
        
        task_info = f"""{status_emoji} {task_id}
   📋 {task["title"]}
   👤 {task["target_agent"]} | 🎯 {task["priority"]}
   📅 {task["created_at"][:16]}"""
        task_list.append(task_info)
    
    return f"""
📋 АКТИВНЫЕ ЗАДАЧИ ({len(filtered_tasks)})

{chr(10).join(task_list)}

💡 Для обновления статуса задачи используйте agent_update_task_status
"""


@mcp.tool()
def agent_update_task_status(
    task_id: str,
    status: str,
    result: Optional[str] = None,
    next_agent: Optional[str] = None
) -> str:
    """Update status of a delegated task"""
    
    if task_id not in active_tasks:
        return f"❌ Задача {task_id} не найдена в системе"
    
    # Update task
    task = active_tasks[task_id]
    old_status = task["status"]
    task["status"] = status
    task["updated_at"] = datetime.now().isoformat()
    if result:
        task["result"] = result
    
    status_emoji = {
        "in_progress": "🔄",
        "completed": "✅", 
        "failed": "❌",
        "needs_review": "🔍"
    }.get(status, "❓")
    
    update_info = f"""
{status_emoji} Статус задачи обновлен

🆔 Задача: {task_id}
📋 {task["title"]}
📊 {old_status} → {status}
⏰ {datetime.now().strftime('%H:%M:%S')}
"""
    
    if result:
        update_info += f"\n📝 Результат: {result[:200]}..."
    
    # Handle workflow transitions
    if next_agent and status == "completed":
        # Auto-delegate to next agent in workflow
        next_task_title = f"Review: {task['title']}"
        next_task_description = f"""
Получен результат выполнения задачи от {task['target_agent']}:

ОРИГИНАЛЬНАЯ ЗАДАЧА: {task['title']}
РЕЗУЛЬТАТ: {result}

Необходимо проверить результат и предоставить фидбек.
"""
        
        delegation_result = agent_delegate_task(
            target_agent=next_agent,
            task_title=next_task_title,
            task_description=next_task_description,
            priority=task["priority"]
        )
        
        update_info += f"\n\n🔄 Автоматически делегировано агенту {next_agent} для review"
    
    return update_info


if __name__ == "__main__":
    mcp.run()  # ✅ stdio-transport (default) 