#!/usr/bin/env python3
"""
Простой тест MCP клиента с одним сервером
"""

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_single_server():
    """Тест одного MCP сервера."""
    print("🔧 Тест одного MCP сервера...")
    
    try:
        # Создаем параметры сервера
        server_params = StdioServerParameters(
            command=sys.executable,
            args=["-u", "core/mcp/servers/agent_communication_server.py"],
            env=None
        )
        
        print("🔌 Создаю подключение к agent_communication серверу...")
        
        # Создаем подключение
        async with stdio_client(server_params) as (read_stream, write_stream):
            print("✅ Потоки созданы, создаю сессию...")
            
            # Создаем сессию
            session = ClientSession(read_stream, write_stream)
            
            print("🤝 Инициализирую сессию с таймаутом 10 секунд...")
            
            # Инициализируем с большим таймаутом
            await asyncio.wait_for(session.initialize(), timeout=10)
            
            print("✅ Сессия инициализирована!")
            
            # Получаем список инструментов
            tools_result = await session.list_tools()
            print(f"📋 Найдено инструментов: {len(tools_result.tools)}")
            
            for tool in tools_result.tools:
                print(f"   • {tool.name}: {tool.description}")
            
            # Закрываем сессию
            await session.close()
            print("🔌 Сессия закрыта")
            
            return True
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_single_server())
    if success:
        print("\n🎉 Одиночный MCP сервер работает!")
    else:
        print("\n💔 Проблема с MCP сервером.") 