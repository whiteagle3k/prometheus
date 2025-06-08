#!/usr/bin/env python3
"""
Простой тест agent_communication MCP сервера в изоляции
"""

import asyncio
import subprocess
import sys
import json
from pathlib import Path

async def test_agent_comm_server():
    """Тест agent_communication сервера напрямую."""
    print("🧪 Тест agent_communication MCP сервера...")
    
    # Запуск сервера
    server_script = "core/mcp/servers/agent_communication_server.py"
    
    try:
        print(f"🚀 Запускаю {server_script}...")
        
        # Запуск через poetry чтобы использовать правильное окружение
        process = await asyncio.create_subprocess_exec(
            "poetry", "run", "python", server_script,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        print("✅ Сервер запущен, тестируем handshake...")
        
        # Отправим initialize message
        init_message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }
        
        message_str = json.dumps(init_message) + "\n"
        
        # Отправляем сообщение серверу
        process.stdin.write(message_str.encode())
        await process.stdin.drain()
        
        print("📤 Отправлено initialize сообщение...")
        
        # Ждем ответ с таймаутом
        try:
            stdout_data = await asyncio.wait_for(
                process.stdout.readline(), 
                timeout=5.0
            )
            
            if stdout_data:
                response = stdout_data.decode().strip()
                print(f"📥 Получен ответ: {response[:200]}...")
                
                # Попробуем распарсить JSON
                try:
                    response_data = json.loads(response)
                    if "result" in response_data:
                        print("✅ Handshake успешен!")
                        return True
                    else:
                        print(f"❌ Неожиданный ответ: {response_data}")
                except json.JSONDecodeError:
                    print(f"❌ Не JSON ответ: {response}")
            else:
                print("❌ Нет ответа от сервера")
                
        except asyncio.TimeoutError:
            print("❌ Timeout - сервер не отвечает")
            
        return False
        
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        return False
        
    finally:
        # Cleanup
        try:
            process.terminate()
            await process.wait()
        except:
            pass


async def main():
    """Основная функция."""
    success = await test_agent_comm_server()
    
    if success:
        print("\n🎉 Agent communication сервер работает корректно!")
    else:
        print("\n💔 Agent communication сервер имеет проблемы.")
        print("🔍 Рекомендации:")
        print("   1. Проверить зависимости (pip install mcp)")
        print("   2. Проверить синтаксис сервера")
        print("   3. Проверить порты и конфликты")


if __name__ == "__main__":
    asyncio.run(main()) 