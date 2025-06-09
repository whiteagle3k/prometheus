import asyncio
import os
from pathlib import Path
import unittest

# Импорты агентов и реестра
from core.runtime.registry import AgentRegistry

class TestFullDevTeamWorkflow(unittest.TestCase):
    async def asyncSetUp(self):
        self.registry = AgentRegistry()
        self.output_file = Path("utils/timestamp_print.py")
        if self.output_file.exists():
            os.remove(self.output_file)
        self.supervisor = await self.registry.get_agent('supervisor')
        self.developer = await self.registry.get_agent('developer')
        self.qa = await self.registry.get_agent('qa')
        # Инициализируем MCP клиент и получаем инструменты
        await self.developer._ensure_mcp()
        self.tools = await self.developer.mcp_client.get_available_capabilities()

    async def asyncTearDown(self):
        await self.registry.shutdown_all()
        if self.output_file.exists():
            os.remove(self.output_file)

    async def test_timestamp_feature_workflow(self):
        # Шаг 1: Пользователь -> Петрович
        user_request = "Добавить timestamp на все выводы в консоль (обертка над print)"
        print(f"\n[TEST] USER -> ПЕТРОВИЧ: {user_request}")
        supervisor_response = await self.supervisor.think(user_request)
        print(f"[TEST] ПЕТРОВИЧ: {supervisor_response.get('result', supervisor_response)}")

        # Шаг 2: Петрович -> Вася
        vasya_task = "Вася, создай функцию timestamped_print в файле utils/timestamp_print.py, которая добавляет временную метку к print()"
        print(f"\n[TEST] ПЕТРОВИЧ -> ВАСЯ: {vasya_task}")
        # Передаем инструменты через self._tools (BaseEntity будет их использовать)
        self.developer._tools = self.tools
        developer_response = await self.developer.think(vasya_task)
        print(f"[TEST] ВАСЯ: {developer_response.get('result', developer_response)}")

        # Проверка создания файла
        self.assertTrue(self.output_file.exists(), "Вася не создал файл 'utils/timestamp_print.py'")
        print(f"[TEST] ✅ Файл создан: {self.output_file}")
        file_content = self.output_file.read_text()
        print(f"[TEST] Содержимое файла:\n{file_content}")

if __name__ == '__main__':
    async def run_tests():
        test_case = TestFullDevTeamWorkflow()
        await test_case.asyncSetUp()
        try:
            await test_case.test_timestamp_feature_workflow()
            print("\n🎉 ВЕСЬ ЦИКЛ ПРОЙДЕН! 🎉")
        finally:
            await test_case.asyncTearDown()
    asyncio.run(run_tests()) 