#!/usr/bin/env python3
"""
Agent Communication MCP Server

Позволяет агентам общаться друг с другом:
- Отправка сообщений между агентами
- Делегирование задач
- Получение статуса других агентов
- Workflow координация
"""

import asyncio
import json
import logging
import requests
from datetime import datetime
from typing import Any, Dict, List, Optional

# MCP SDK imports - reverted to 1.8.1
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import (
        CallToolRequest,
        CallToolResult,
        ListToolsRequest, 
        ListToolsResult,
        Tool,
        TextContent
    )
except ImportError as e:
    print(f"⚠️ MCP SDK not available: {e}")
    print("   Install with: pip install mcp")
    exit(1)

# Prometheus API endpoints
API_BASE = "http://localhost:8000"
CHAT_ENDPOINT = f"{API_BASE}/v1/chat"
HEALTH_ENDPOINT = f"{API_BASE}/health"

# Task delegation storage (Redis in production)
active_tasks: Dict[str, Dict[str, Any]] = {}
task_counter = 0

logger = logging.getLogger(__name__)

# Initialize MCP server
server = Server("agent-communication")

@server.list_tools()
async def list_tools() -> ListToolsResult:
    """List available agent communication tools."""
    tools = [
        Tool(
            name="agent_send_message",
            description="Send a message to another agent",
            inputSchema={
                "type": "object",
                "properties": {
                    "target_agent": {
                        "type": "string",
                        "description": "Target agent name (aletheia, vasya, marina, supervisor)",
                        "enum": ["aletheia", "vasya", "marina", "supervisor"]
                    },
                    "message": {
                        "type": "string",
                        "description": "Message to send to the agent"
                    },
                    "task_type": {
                        "type": "string", 
                        "description": "Type of task (delegation, collaboration, status_check)",
                        "enum": ["delegation", "collaboration", "status_check", "general"]
                    },
                    "priority": {
                        "type": "string",
                        "description": "Task priority level",
                        "enum": ["low", "medium", "high", "urgent"],
                        "default": "medium"
                    }
                },
                "required": ["target_agent", "message"]
            }
        ),
        Tool(
            name="agent_delegate_task",
            description="Delegate a specific task to another agent with tracking",
            inputSchema={
                "type": "object",
                "properties": {
                    "target_agent": {
                        "type": "string",
                        "description": "Agent to assign the task to",
                        "enum": ["vasya", "marina", "aletheia"]
                    },
                    "task_title": {
                        "type": "string",
                        "description": "Clear title for the task"
                    },
                    "task_description": {
                        "type": "string",
                        "description": "Detailed task description and requirements"
                    },
                    "acceptance_criteria": {
                        "type": "array",
                        "description": "List of acceptance criteria",
                        "items": {"type": "string"}
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "urgent"],
                        "default": "medium"
                    },
                    "deadline": {
                        "type": "string",
                        "description": "Task deadline (optional)"
                    }
                },
                "required": ["target_agent", "task_title", "task_description"]
            }
        ),
        Tool(
            name="agent_get_status",
            description="Get status and availability of other agents",
            inputSchema={
                "type": "object",
                "properties": {
                    "target_agent": {
                        "type": "string", 
                        "description": "Agent to check status (optional, checks all if not specified)",
                        "enum": ["aletheia", "vasya", "marina", "supervisor"]
                    }
                }
            }
        ),
        Tool(
            name="agent_get_active_tasks",
            description="Get list of active tasks in the system",
            inputSchema={
                "type": "object",
                "properties": {
                    "filter_by_agent": {
                        "type": "string",
                        "description": "Filter tasks by assigned agent (optional)"
                    },
                    "filter_by_status": {
                        "type": "string",
                        "description": "Filter tasks by status (optional)",
                        "enum": ["pending", "in_progress", "completed", "failed"]
                    }
                }
            }
        ),
        Tool(
            name="agent_update_task_status", 
            description="Update status of a delegated task",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "ID of the task to update"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["in_progress", "completed", "failed", "needs_review"],
                        "description": "New task status"
                    },
                    "result": {
                        "type": "string",
                        "description": "Task result or progress update"
                    },
                    "next_agent": {
                        "type": "string",
                        "description": "Next agent to hand off to (optional)",
                        "enum": ["aletheia", "vasya", "marina", "supervisor"]
                    }
                },
                "required": ["task_id", "status"]
            }
        )
    ]
    
    return ListToolsResult(tools=tools)

@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
    """Handle tool calls for agent communication."""
    
    try:
        if name == "agent_send_message":
            return await _agent_send_message(arguments)
        elif name == "agent_delegate_task":
            return await _agent_delegate_task(arguments)
        elif name == "agent_get_status":
            return await _agent_get_status(arguments)
        elif name == "agent_get_active_tasks":
            return await _agent_get_active_tasks(arguments)
        elif name == "agent_update_task_status":
            return await _agent_update_task_status(arguments)
        else:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"❌ Unknown tool: {name}"
                )]
            )
            
    except Exception as e:
        logger.error(f"Tool call error: {e}")
        return CallToolResult(
            content=[TextContent(
                type="text", 
                text=f"❌ Error executing {name}: {str(e)}"
            )]
        )

async def _agent_send_message(args: Dict[str, Any]) -> CallToolResult:
    """Send message to another agent."""
    target_agent = args["target_agent"]
    message = args["message"]
    task_type = args.get("task_type", "general")
    priority = args.get("priority", "medium")
    
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
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"""✅ Сообщение отправлено агенту {target_agent}

📤 Отправлено: {message[:100]}...
📥 Ответ агента: {agent_response[:200]}...
🎯 Маршрут: {route}
⏱️ Время ответа: {latency:.1f}с

💡 Агент получил и обработал сообщение."""
                )]
            )
        else:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"❌ Ошибка отправки сообщения агенту {target_agent}: {response.status_code} - {response.text}"
                )]
            )
            
    except Exception as e:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"❌ Ошибка коммуникации с агентом {target_agent}: {str(e)}"
            )]
        )

async def _agent_delegate_task(args: Dict[str, Any]) -> CallToolResult:
    """Delegate a task to another agent with tracking."""
    global task_counter
    task_counter += 1
    
    target_agent = args["target_agent"]
    task_title = args["task_title"]
    task_description = args["task_description"]
    acceptance_criteria = args.get("acceptance_criteria", [])
    priority = args.get("priority", "medium")
    deadline = args.get("deadline")
    
    # Generate task ID
    task_id = f"TASK_{task_counter:04d}_{target_agent}_{datetime.now().strftime('%m%d_%H%M')}"
    
    # Store task for tracking
    task_data = {
        "id": task_id,
        "title": task_title,
        "description": task_description,
        "target_agent": target_agent,
        "acceptance_criteria": acceptance_criteria,
        "priority": priority,
        "deadline": deadline,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "assigned_by": "supervisor"  # Можно передавать от calling agent
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
    send_result = await _agent_send_message({
        "target_agent": target_agent,
        "message": delegation_message,
        "task_type": "delegation",
        "priority": priority
    })
    
    return CallToolResult(
        content=[TextContent(
            type="text",
            text=f"""✅ Задача делегирована агенту {target_agent}

🆔 ID задачи: {task_id}
📋 Название: {task_title}
👤 Исполнитель: {target_agent}
⚡ Статус: pending → отправлена агенту

{send_result.content[0].text if send_result.content else ''}

💡 Задача добавлена в систему отслеживания."""
        )]
    )

async def _agent_get_status(args: Dict[str, Any]) -> CallToolResult:
    """Get status of agents."""
    target_agent = args.get("target_agent")
    
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
                        
                        status_info = f"""
✅ Агент {target_agent} - АКТИВЕН

📊 Статус: Online и отвечает
⏱️ Время ответа: {latency:.1f}с  
🎯 Роутинг: {route}
🔄 Последняя проверка: {datetime.now().strftime('%H:%M:%S')}
"""
                    else:
                        status_info = f"⚠️ Агент {target_agent} зарегистрирован но не отвечает"
                else:
                    status_info = f"❌ Агент {target_agent} не найден в системе"
            else:
                # Check all agents
                status_info = f"""
📊 СТАТУС ВСЕХ АГЕНТОВ:

✅ Активные агенты: {', '.join(running_agents)}
📈 Всего агентов: {len(running_agents)}
🔄 Проверено: {datetime.now().strftime('%H:%M:%S')}

💡 Для детальной проверки укажите конкретного агента.
"""
                
            return CallToolResult(
                content=[TextContent(type="text", text=status_info)]
            )
        else:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text="❌ Ошибка подключения к Prometheus API"
                )]
            )
            
    except Exception as e:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"❌ Ошибка проверки статуса: {str(e)}"
            )]
        )

async def _agent_get_active_tasks(args: Dict[str, Any]) -> CallToolResult:
    """Get list of active tasks."""
    filter_agent = args.get("filter_by_agent")
    filter_status = args.get("filter_by_status")
    
    filtered_tasks = active_tasks.copy()
    
    # Apply filters
    if filter_agent:
        filtered_tasks = {k: v for k, v in filtered_tasks.items() if v["target_agent"] == filter_agent}
    if filter_status:
        filtered_tasks = {k: v for k, v in filtered_tasks.items() if v["status"] == filter_status}
    
    if not filtered_tasks:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text="📭 Нет активных задач соответствующих фильтрам."
            )]
        )
    
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
    
    result_text = f"""
📋 АКТИВНЫЕ ЗАДАЧИ ({len(filtered_tasks)})

{chr(10).join(task_list)}

💡 Для обновления статуса задачи используйте agent_update_task_status
"""
    
    return CallToolResult(
        content=[TextContent(type="text", text=result_text)]
    )

async def _agent_update_task_status(args: Dict[str, Any]) -> CallToolResult:
    """Update task status."""
    task_id = args["task_id"]
    new_status = args["status"]
    result = args.get("result", "")
    next_agent = args.get("next_agent")
    
    if task_id not in active_tasks:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"❌ Задача {task_id} не найдена в системе"
            )]
        )
    
    # Update task
    task = active_tasks[task_id]
    old_status = task["status"]
    task["status"] = new_status
    task["updated_at"] = datetime.now().isoformat()
    if result:
        task["result"] = result
    
    status_emoji = {
        "in_progress": "🔄",
        "completed": "✅", 
        "failed": "❌",
        "needs_review": "🔍"
    }.get(new_status, "❓")
    
    update_info = f"""
{status_emoji} Статус задачи обновлен

🆔 Задача: {task_id}
📋 {task["title"]}
📊 {old_status} → {new_status}
⏰ {datetime.now().strftime('%H:%M:%S')}
"""
    
    if result:
        update_info += f"\n📝 Результат: {result[:200]}..."
    
    # Handle workflow transitions
    if next_agent and new_status == "completed":
        # Auto-delegate to next agent in workflow
        next_task_title = f"Review: {task['title']}"
        next_task_description = f"""
Получен результат выполнения задачи от {task['target_agent']}:

ОРИГИНАЛЬНАЯ ЗАДАЧА: {task['title']}
РЕЗУЛЬТАТ: {result}

Необходимо проверить результат и предоставить фидбек.
"""
        
        delegation_result = await _agent_delegate_task({
            "target_agent": next_agent,
            "task_title": next_task_title,
            "task_description": next_task_description,
            "priority": task["priority"]
        })
        
        update_info += f"\n\n🔄 Автоматически делегировано агенту {next_agent} для review"
    
    return CallToolResult(
        content=[TextContent(type="text", text=update_info)]
    )

async def main():
    """Run the agent communication MCP server."""
    logger.info("🚀 Starting Agent Communication MCP Server...")
    logger.info("📡 Providing inter-agent communication capabilities")
    
    # New MCP 1.8.1 API
    async with stdio_server() as (read_stream, write_stream):
        logger.info("✅ Agent Communication MCP Server ready")
        await server.run(
            read_stream, 
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main()) 