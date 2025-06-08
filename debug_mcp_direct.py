#!/usr/bin/env python3
"""
Прямой тест MCP клиента для диагностики agent_communication проблемы
"""

import asyncio
import sys
from pathlib import Path

# Add core to path
sys.path.insert(0, str(Path(__file__).parent))

from core.mcp.client.mcp_client import MCPClient

async def debug_mcp():
    """Прямая диагностика MCP клиента."""
    print("🔍 ДИАГНОСТИКА MCP КЛИЕНТА")
    print("=" * 50)
    
    client = MCPClient()
    
    try:
        print("🔌 Инициализирую MCP клиент...")
        await client.initialize()
        
        print(f"\n📊 РЕЗУЛЬТАТЫ:")
        print(f"   Серверов: {len(client.sessions)}")
        print(f"   Capabilities: {len(client.capabilities)}")
        
        print(f"\n🚀 АКТИВНЫЕ СЕРВЕРЫ:")
        for name in client.sessions.keys():
            print(f"   ✅ {name}")
            
        print(f"\n❌ НЕДОСТАЮЩИЕ СЕРВЕРЫ:")
        expected = ["filesystem", "git", "terminal", "web", "agent_communication"]
        missing = [name for name in expected if name not in client.sessions]
        for name in missing:
            print(f"   ❌ {name}")
            
        print(f"\n📋 CAPABILITIES:")
        for name in sorted(client.capabilities.keys()):
            cap = client.capabilities[name]
            print(f"   • {name} ({cap.server_name})")
            
        # Тест agent_communication capabilities
        agent_caps = [name for name in client.capabilities.keys() if "agent_communication" in name]
        print(f"\n🎯 AGENT COMMUNICATION CAPABILITIES: {len(agent_caps)}")
        for cap in agent_caps:
            print(f"   • {cap}")
            
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        try:
            await client.shutdown()
        except:
            pass

if __name__ == "__main__":
    asyncio.run(debug_mcp()) 