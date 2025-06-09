import asyncio
import os
from pathlib import Path
import unittest

from core.runtime.registry import AgentRegistry

class TestAletheiaSupervisorWorkflow(unittest.TestCase):
    async def asyncSetUp(self):
        self.registry = AgentRegistry()
        self.output_file = Path("utils/timestamp_print.py")
        if self.output_file.exists():
            os.remove(self.output_file)
        self.aletheia = await self.registry.get_agent('aletheia')
        self.supervisor = await self.registry.get_agent('supervisor')
        self.developer = await self.registry.get_agent('developer')
        self.qa = await self.registry.get_agent('qa')
        await self.aletheia._ensure_mcp()
        self.tools = await self.aletheia.mcp_client.get_available_capabilities()
        self.aletheia._tools = self.tools
        self.supervisor._tools = self.tools
        self.developer._tools = self.tools
        self.qa._tools = self.tools

    async def asyncTearDown(self):
        await self.registry.shutdown_all()
        if self.output_file.exists():
            os.remove(self.output_file)

    async def test_aletheia_supervisor_flow(self):
        # USER -> Aletheia (точка входа)
        user_request = "Добавить timestamp на все выводы в консоль (обертка над print)"
        print(f"\n[TEST] USER -> Aletheia: {user_request}")
        aletheia_response = await self.aletheia.think(user_request)
        print(f"[TEST] Aletheia (финальный ответ): {aletheia_response.get('result', aletheia_response)}")

        # Проверка создания файла
        self.assertTrue(self.output_file.exists(), "Файл 'utils/timestamp_print.py' не был создан через workflow Aletheia/Supervisor")
        print(f"[TEST] ✅ Файл создан: {self.output_file}")
        file_content = self.output_file.read_text()
        print(f"[TEST] Содержимое файла:\n{file_content}")

if __name__ == '__main__':
    async def run_tests():
        test_case = TestAletheiaSupervisorWorkflow()
        await test_case.asyncSetUp()
        try:
            await test_case.test_aletheia_supervisor_flow()
            print("\n🎉 ВЕСЬ ЦИКЛ ПРОЙДЕН! (через Aletheia → Supervisor → команда) 🎉")
        finally:
            await test_case.asyncTearDown()
    asyncio.run(run_tests())