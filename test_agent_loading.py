#!/usr/bin/env python3
"""Тест загрузки всех агентов."""

import asyncio
from entities import available_entities
from core.runtime.registry import get_agent

async def test_agents():
    """Тестируем загрузку каждого агента."""
    print("🧪 Тестирование загрузки агентов...")
    print(f"📋 Доступные агенты: {list(available_entities.keys())}")
    
    for name in ['petrovich', 'vasya', 'marina', 'aletheia']:
        try:
            print(f'\n🔄 Тестирую {name}...')
            agent = await get_agent(name) 
            print(f'✅ {name} загружен успешно: {type(agent).__name__}')
        except Exception as e:
            print(f'❌ {name} не удалось загрузить: {e}')
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_agents()) 