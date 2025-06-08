#!/usr/bin/env python3
"""
Тест MCP agent communication с обходом проблем инициализации
"""

import asyncio
import sys
import json
from pathlib import Path

# Add core to path
sys.path.insert(0, str(Path(__file__).parent))

from core.mcp.client.mcp_client import MCPClient


async def test_agent_communication_simple():
    """Упрощенный тест agent_communication без полной инициализации."""
    print("🧪 Тестирую agent_communication напрямую...")
    
    # Попробуем создать только один сервер
    client = MCPClient()
    
    try:
        print("🔌 Запускаю только agent_communication сервер...")
        await client._start_server("agent_communication", "core/mcp/servers/agent_communication_server.py")
        
        if "agent_communication" in client.sessions:
            print("✅ Agent communication сервер запущен!")
            
            # Попробуем получить список инструментов
            session = client.sessions["agent_communication"]
            tools_result = await session.list_tools()
            
            print(f"📋 Найдено {len(tools_result.tools)} инструментов:")
            for tool in tools_result.tools:
                print(f"   • {tool.name}: {tool.description}")
            
            # Попробуем вызвать agent_get_status
            print("\n🧪 Тестирую agent_get_status...")
            status_result = await session.call_tool("agent_get_status", {})
            
            if status_result.content:
                print(f"📊 Результат: {status_result.content[0].text[:200]}...")
            
            return True
        else:
            print("❌ Agent communication сервер не запустился")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        try:
            await client.shutdown()
            print("🔌 MCP клиент закрыт")
        except:
            pass


if __name__ == "__main__":
    success = asyncio.run(test_agent_communication_simple())
    if success:
        print("\n🎉 Agent communication работает!")
    else:
        print("\n💔 Проблемы с agent communication.") 