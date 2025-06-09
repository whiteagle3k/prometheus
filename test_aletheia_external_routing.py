import asyncio
import os
from pathlib import Path
import unittest

from core.runtime.registry import AgentRegistry

class TestAletheiaExternalRouting(unittest.TestCase):
    async def asyncSetUp(self):
        self.registry = AgentRegistry()
        self.aletheia = await self.registry.get_agent('aletheia')
        await self.aletheia._ensure_mcp()
        self.tools = await self.aletheia.mcp_client.get_available_capabilities()
        self.aletheia._tools = self.tools

    async def asyncTearDown(self):
        await self.registry.shutdown_all()

    async def test_aletheia_external_routing(self):
        # USER -> Aletheia (точка входа)
        user_request = "Добавить timestamp на все выводы в консоль (обертка над print)"
        print(f"\n[TEST] USER -> Aletheia: {user_request}")
        aletheia_response = await self.aletheia.think(user_request)
        response_data = aletheia_response.get('result', aletheia_response)
        
        # Получаем информацию о маршруте
        execution_details = response_data.get('execution_details', {})
        route_used = execution_details.get('route_used', '')
        print(f"[TEST] Использованный маршрут: {route_used}")
        
        # Проверяем, что запрос был маршрутизирован на внешний LLM
        self.assertEqual(route_used, 'external', "Запрос должен был быть маршрутизирован на внешний LLM")
        print(f"[TEST] ✅ Проверка пройдена: запрос маршрутизирован на внешний LLM")

if __name__ == '__main__':
    async def run_tests():
        test_case = TestAletheiaExternalRouting()
        await test_case.asyncSetUp()
        try:
            await test_case.test_aletheia_external_routing()
            print("\n🎉 ТЕСТ ПРОЙДЕН! Aletheia корректно маршрутизирует задачи на разработку внешнему LLM 🎉")
        finally:
            await test_case.asyncTearDown()
    asyncio.run(run_tests()) 