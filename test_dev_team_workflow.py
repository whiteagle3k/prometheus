#!/usr/bin/env python3
"""
Синтетические тесты для команды разработчиков
Проверяет взаимодействие между Петровичем, Васей и Мариной
"""

import asyncio
import pytest
import sys
import traceback
from typing import Dict, Any
from pathlib import Path

# Добавляем корневую директорию в path для импортов
sys.path.insert(0, str(Path(__file__).parent))

try:
    from entities import discover_entities
    from entities.supervisor import SupervisorEntity
    from entities.vasya import VasyaEntity
    from entities.marina import MarinaEntity
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("Убедитесь, что все модули команды установлены")
    sys.exit(1)


class TestDevTeamWorkflow:
    """Тесты для проверки workflow команды разработчиков"""
    
    @pytest.fixture
    def entities(self):
        """Инициализация всех агентов команды"""
        try:
            discovered = discover_entities()
            entities = {}
            
            # Создаем экземпляры агентов
            for name, info in discovered.items():
                if name in ['petrovich', 'vasya', 'marina']:
                    entity_class = info['class']
                    entities[name] = entity_class()
                    print(f"✅ Создан агент: {name}")
            
            return entities
        except Exception as e:
            print(f"❌ Ошибка создания агентов: {e}")
            traceback.print_exc()
            return {}
    
    def test_team_discovery(self):
        """Тест 1: Проверка обнаружения всех агентов команды"""
        print("\n🔍 Тест 1: Обнаружение агентов команды")
        
        discovered = discover_entities()
        required_agents = ['petrovich', 'vasya', 'marina']
        
        for agent in required_agents:
            assert agent in discovered, f"Агент {agent} не найден"
            print(f"✅ Найден агент: {agent}")
        
        print("✅ Все агенты команды обнаружены")
    
    def test_agent_initialization(self, entities):
        """Тест 2: Проверка инициализации агентов"""
        print("\n🚀 Тест 2: Инициализация агентов")
        
        required_agents = ['petrovich', 'vasya', 'marina']
        
        for agent_name in required_agents:
            assert agent_name in entities, f"Агент {agent_name} не создан"
            agent = entities[agent_name]
            
            # Проверяем наличие identity
            assert hasattr(agent, 'identity'), f"У агента {agent_name} нет identity"
            assert agent.identity is not None, f"Identity агента {agent_name} пуст"
            
            # Проверяем основные поля identity
            assert 'name' in agent.identity, f"У агента {agent_name} нет имени"
            assert 'llm_instructions' in agent.identity, f"У агента {agent_name} нет LLM инструкций"
            
            print(f"✅ Агент {agent_name} ({agent.identity['name']}) инициализирован")
        
        print("✅ Все агенты успешно инициализированы")
    
    def test_agent_capabilities(self, entities):
        """Тест 3: Проверка возможностей агентов"""
        print("\n⚡ Тест 3: Проверка возможностей агентов")
        
        # Проверяем MCP capabilities
        for agent_name, agent in entities.items():
            assert hasattr(agent, 'mcp_client'), f"У агента {agent_name} нет MCP клиента"
            
            # Проверяем MCP методы
            mcp_methods = [
                'read_file', 'write_file', 'list_directory',  # filesystem
                'git_status', 'git_add', 'git_commit',        # git
                'execute_command', 'run_script',              # terminal
                'web_search', 'http_get'                      # web
            ]
            
            for method in mcp_methods:
                assert hasattr(agent, method), f"У агента {agent_name} нет метода {method}"
            
            print(f"✅ Агент {agent_name} имеет все MCP возможности ({len(mcp_methods)} методов)")
        
        print("✅ Все агенты имеют необходимые возможности")
    
    @pytest.mark.asyncio
    async def test_vasya_coding_task(self, entities):
        """Тест 4: Вася может кодить"""
        print("\n👨‍💻 Тест 4: Вася выполняет задачу кодирования")
        
        vasya = entities.get('vasya')
        assert vasya is not None, "Вася не найден"
        
        # Даем Васе простую задачу кодирования
        coding_task = """
        Создай простую Python функцию для вычисления факториала числа.
        Функция должна называться calculate_factorial и принимать один параметр n.
        Добавь docstring и проверку на отрицательные числа.
        """
        
        try:
            # Тестируем способность Васи к программированию
            response = await vasya.think(coding_task)
            
            assert response is not None, "Вася не дал ответ на задачу кодирования"
            assert len(response) > 50, "Ответ Васи слишком короткий"
            
            # Проверяем, что в ответе есть признаки кода
            code_indicators = ['def ', 'factorial', 'return', 'docstring', 'if']
            found_indicators = [indicator for indicator in code_indicators if indicator.lower() in response.lower()]
            
            assert len(found_indicators) >= 3, f"В ответе Васи недостаточно признаков кода. Найдено: {found_indicators}"
            
            print(f"✅ Вася успешно выполнил задачу кодирования")
            print(f"   Найдены индикаторы кода: {found_indicators}")
            print(f"   Длина ответа: {len(response)} символов")
            
        except Exception as e:
            print(f"❌ Ошибка при тестировании кодирования Васи: {e}")
            raise
    
    @pytest.mark.asyncio
    async def test_marina_testing_task(self, entities):
        """Тест 5: Марина может тестировать"""
        print("\n👩‍💼 Тест 5: Марина выполняет задачу тестирования")
        
        marina = entities.get('marina')
        assert marina is not None, "Марина не найдена"
        
        # Даем Марине задачу тестирования
        testing_task = """
        Протестируй эту функцию Python:
        
        def calculate_factorial(n):
            '''Вычисляет факториал числа n'''
            if n < 0:
                return None
            if n == 0 or n == 1:
                return 1
            return n * calculate_factorial(n - 1)
        
        Найди возможные проблемы, создай тест-кейсы, проверь edge cases.
        """
        
        try:
            response = await marina.think(testing_task)
            
            assert response is not None, "Марина не дала ответ на задачу тестирования"
            assert len(response) > 100, "Ответ Марины слишком короткий"
            
            # Проверяем, что в ответе есть признаки тестирования
            test_indicators = ['тест', 'test', 'edge case', 'проблем', 'issue', 'assert', 'проверк']
            found_indicators = [indicator for indicator in test_indicators if indicator.lower() in response.lower()]
            
            assert len(found_indicators) >= 3, f"В ответе Марины недостаточно признаков тестирования. Найдено: {found_indicators}"
            
            print(f"✅ Марина успешно выполнила задачу тестирования")
            print(f"   Найдены индикаторы тестирования: {found_indicators}")
            print(f"   Длина ответа: {len(response)} символов")
            
        except Exception as e:
            print(f"❌ Ошибка при тестировании навыков Марины: {e}")
            raise
    
    @pytest.mark.asyncio
    async def test_petrovich_supervision_task(self, entities):
        """Тест 6: Петрович может руководить"""
        print("\n👨‍💼 Тест 6: Петрович выполняет задачу руководства")
        
        petrovich = entities.get('petrovich')
        assert petrovich is not None, "Петрович не найден"
        
        # Даем Петровичу задачу руководства
        supervision_task = """
        Пользователь хочет добавить в проект систему аутентификации.
        Проанализируй задачу, разбей на подзадачи для Васи и Марины.
        Определи последовательность работ и критерии приемки.
        """
        
        try:
            response = await petrovich.think(supervision_task)
            
            assert response is not None, "Петрович не дал ответ на задачу руководства"
            assert len(response) > 150, "Ответ Петровича слишком короткий"
            
            # Проверяем, что в ответе есть признаки планирования
            planning_indicators = ['задач', 'этап', 'plan', 'step', 'критери', 'criteria', 'приемк', 'acceptance']
            found_indicators = [indicator for indicator in planning_indicators if indicator.lower() in response.lower()]
            
            assert len(found_indicators) >= 3, f"В ответе Петровича недостаточно признаков планирования. Найдено: {found_indicators}"
            
            print(f"✅ Петрович успешно выполнил задачу руководства")
            print(f"   Найдены индикаторы планирования: {found_indicators}")
            print(f"   Длина ответа: {len(response)} символов")
            
        except Exception as e:
            print(f"❌ Ошибка при тестировании навыков Петровича: {e}")
            raise
    
    @pytest.mark.asyncio
    async def test_team_communication_workflow(self, entities):
        """Тест 7: Тестирование коммуникации между агентами"""
        print("\n💬 Тест 7: Коммуникация между агентами")
        
        # Симулируем workflow: Петрович → Вася → Марина
        
        # 1. Петрович создает задачу
        petrovich = entities.get('petrovich')
        task_brief = "Создай функцию для валидации email адресов"
        
        petrovich_response = await petrovich.think(f"Проанализируй и разбей задачу: {task_brief}")
        assert petrovich_response is not None, "Петрович не создал план задачи"
        print("✅ Петрович создал план задачи")
        
        # 2. Вася получает задачу от Петровича
        vasya = entities.get('vasya')
        vasya_task = f"Петрович дал задачу: {task_brief}. Реализуй эту функцию."
        
        vasya_response = await vasya.think(vasya_task)
        assert vasya_response is not None, "Вася не выполнил задачу"
        print("✅ Вася выполнил задачу")
        
        # 3. Марина тестирует работу Васи
        marina = entities.get('marina')
        marina_task = f"Вася создал код для валидации email. Протестируй его: {vasya_response[:200]}..."
        
        marina_response = await marina.think(marina_task)
        assert marina_response is not None, "Марина не протестировала код"
        print("✅ Марина протестировала код")
        
        # 4. Проверяем, что все этапы workflow выполнены
        workflow_steps = [
            (petrovich_response, "Петрович"),
            (vasya_response, "Вася"),
            (marina_response, "Марина")
        ]
        
        for response, agent in workflow_steps:
            assert len(response) > 50, f"Ответ агента {agent} слишком короткий"
        
        print("✅ Полный workflow команды протестирован успешно")
    
    def test_mcp_integration(self, entities):
        """Тест 8: Проверка MCP интеграции"""
        print("\n🔌 Тест 8: MCP интеграция")
        
        for agent_name, agent in entities.items():
            # Проверяем наличие MCP клиента
            assert hasattr(agent, 'mcp_client'), f"У агента {agent_name} нет MCP клиента"
            
            # Проверяем, что MCP клиент инициализирован
            mcp_client = agent.mcp_client
            assert mcp_client is not None, f"MCP клиент агента {agent_name} не инициализирован"
            
            # Проверяем количество серверов
            if hasattr(mcp_client, 'servers'):
                print(f"   Агент {agent_name}: {len(mcp_client.servers)} MCP серверов")
            
            print(f"✅ Агент {agent_name} имеет MCP интеграцию")
        
        print("✅ MCP интеграция всех агентов проверена")


def run_synthetic_tests():
    """Запуск синтетических тестов"""
    print("🚀 Запуск синтетических тестов команды разработчиков")
    print("=" * 60)
    
    try:
        # Запускаем pytest с подробным выводом
        import subprocess
        result = subprocess.run([
            'python', '-m', 'pytest', 
            __file__, 
            '-v', 
            '--tb=short',
            '--disable-warnings'
        ], capture_output=True, text=True)
        
        print("STDOUT:")
        print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("\n🎉 Все синтетические тесты прошли успешно!")
        else:
            print(f"\n❌ Тесты завершились с кодом {result.returncode}")
            
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Ошибка запуска тестов: {e}")
        return False


if __name__ == "__main__":
    # Запуск тестов напрямую
    success = run_synthetic_tests()
    sys.exit(0 if success else 1) 