#!/usr/bin/env python3
"""
РЕАЛЬНЫЙ WORKFLOW ТЕСТ С ПРАВИЛЬНОЙ АРХИТЕКТУРОЙ
Демонстрация полного цикла: User → Supervisor → Developer/QA → Real Files → Results
Использует технические ID: supervisor, developer, qa
"""

import asyncio
import requests
import time
import json
from datetime import datetime
from pathlib import Path

# API endpoints
API_BASE = "http://localhost:8000"
CHAT_ENDPOINT = f"{API_BASE}/v1/chat"
HEALTH_ENDPOINT = f"{API_BASE}/health"

class RealWorkflowDemo:
    """Реальная демонстрация workflow с созданием файлов."""
    
    def __init__(self):
        self.start_time = time.time()
        self.session_log = []
    
    async def wait_for_server(self, timeout=30) -> bool:
        """Ждем запуска сервера."""
        print("⏳ Ожидание запуска Prometheus API сервера...")
        for i in range(timeout):
            try:
                response = requests.get(HEALTH_ENDPOINT, timeout=2)
                if response.status_code == 200:
                    print("✅ Prometheus API сервер запущен!")
                    return True
            except:
                pass
            await asyncio.sleep(1)
            if i % 5 == 0:
                print(f"   Попытка {i+1}/{timeout}...")
        return False
    
    async def send_to_agent(self, agent_id: str, message: str, user_id: str = "workflow_test") -> dict:
        """Отправить сообщение агенту и получить ответ."""
        print(f"\n📤 → {agent_id.upper()}: {message[:100]}...")
        
        try:
            response = requests.post(
                CHAT_ENDPOINT,
                params={"entity": agent_id},
                json={"message": message, "user_id": user_id},
                timeout=120  # 2 минуты на выполнение
            )
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get('answer', 'Нет ответа')
                route = result.get('route', 'unknown')
                latency = result.get('latency', 0)
                
                print(f"📥 ← {agent_id.upper()} ({latency:.1f}s, {route}): {answer[:200]}...")
                
                # Логируем для отчета
                self.session_log.append({
                    "timestamp": datetime.now().isoformat(),
                    "agent": agent_id,
                    "request": message[:100],
                    "response": answer,
                    "route": route,
                    "latency": latency,
                    "success": True
                })
                
                return {"success": True, "answer": answer, "route": route, "latency": latency}
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                print(f"❌ Ошибка: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Ошибка соединения: {error_msg}")
            return {"success": False, "error": error_msg}
    
    def check_created_files(self) -> dict:
        """Проверяем какие файлы были созданы."""
        created_files = {}
        
        # Проверяем несколько возможных локаций
        possible_paths = [
            Path("."),
            Path("output"),
            Path("generated"),
            Path("work"),
            Path("tmp")
        ]
        
        for base_path in possible_paths:
            if base_path.exists():
                for file_path in base_path.rglob("*.py"):
                    if file_path.stat().st_mtime > self.start_time:
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            created_files[str(file_path)] = {
                                "size": len(content),
                                "lines": len(content.split('\n')),
                                "content_preview": content[:300] + "..." if len(content) > 300 else content
                            }
                        except:
                            created_files[str(file_path)] = {"error": "Could not read file"}
        
        return created_files
    
    async def run_real_workflow(self):
        """Запуск реального workflow."""
        print("🚀 РЕАЛЬНЫЙ WORKFLOW С ПРАВИЛЬНОЙ АРХИТЕКТУРОЙ")
        print("=" * 70)
        
        # Проверяем сервер
        if not await self.wait_for_server():
            print("💔 Сервер недоступен")
            return False
        
        # === ЗАДАЧА ОТ ПОЛЬЗОВАТЕЛЯ ===
        user_task = """
Петрович, мне нужно создать утилиту для работы с файлами в Python проекте.

ТРЕБОВАНИЯ:
- Создать модуль file_operations.py
- Функция read_text_file(filepath) - читает текстовый файл
- Функция write_text_file(filepath, content) - записывает в файл
- Функция get_file_info(filepath) - возвращает размер, дату изменения
- Функция backup_file(filepath) - создает backup с timestamp
- Обработка ошибок для всех операций
- Unit тесты для проверки функций
- Документация с примерами

Это для production системы, качество критично.
Координируй команду и убедись что все сделано правильно.
"""
        
        print("🎯 ПОЛЬЗОВАТЕЛЬСКАЯ ЗАДАЧА:")
        print(user_task.strip())
        
        # === ШАГ 1: ПОЛЬЗОВАТЕЛЬ → SUPERVISOR ===
        print(f"\n{'='*70}")
        print("ШАГ 1: ПОЛЬЗОВАТЕЛЬ → SUPERVISOR (ПЕТРОВИЧ)")
        print("="*70)
        
        supervisor_response = await self.send_to_agent("supervisor", user_task)
        
        if not supervisor_response["success"]:
            print("❌ Супервизор недоступен!")
            return False
        
        print(f"\n✅ Петрович получил задачу и отвечает:")
        print(f"📊 Маршрут: {supervisor_response['route']}")
        print(f"⏱️  Время: {supervisor_response['latency']:.1f}с")
        print(f"💬 Ответ: {supervisor_response['answer']}")
        
        # === ШАГ 2: SUPERVISOR ДЕЛЕГИРУЕТ ЗАДАЧИ ===
        print(f"\n{'='*70}")
        print("ШАГ 2: SUPERVISOR ДЕЛЕГИРУЕТ РАЗРАБОТКУ DEVELOPER")
        print("="*70)
        
        # Даем время супервизору на осмысление
        await asyncio.sleep(3)
        
        developer_task = f"""
Петрович поручает тебе разработку модуля file_operations.py.

ЗАДАЧА ОТ СУПЕРВИЗОРА:
{user_task}

ТВОЯ ЧАСТЬ:
- Создай файл file_operations.py в текущей директории
- Реализуй все 4 функции с обработкой ошибок  
- Добавь докстринги с примерами использования
- Убедись что код готов к production

Используй MCP инструменты для создания файла.
Отчитайся о результате.
"""
        
        developer_response = await self.send_to_agent("developer", developer_task)
        
        if developer_response["success"]:
            print(f"✅ Вася принял задачу от Петровича")
            print(f"📊 Маршрут: {developer_response['route']}")
            print(f"⏱️  Время: {developer_response['latency']:.1f}с")
            print(f"💬 Ответ: {developer_response['answer']}")
        
        # === ШАГ 3: SUPERVISOR ДЕЛЕГИРУЕТ ТЕСТИРОВАНИЕ QA ===
        print(f"\n{'='*70}")
        print("ШАГ 3: SUPERVISOR ДЕЛЕГИРУЕТ ТЕСТИРОВАНИЕ QA")
        print("="*70)
        
        qa_task = f"""
Петрович поручает тебе тестирование модуля file_operations.py.

ЗАДАЧА ОТ СУПЕРВИЗОРА:
После того как разработчик создаст file_operations.py, тебе нужно:

- Создать test_file_operations.py
- Unit тесты для всех 4 функций
- Тестирование граничных случаев и ошибок
- Проверить что backup функция работает корректно
- Удостовериться что все тесты проходят

Используй MCP инструменты для создания тестов.
Отчитайся о результате тестирования.
"""
        
        qa_response = await self.send_to_agent("qa", qa_task)
        
        if qa_response["success"]:
            print(f"✅ Марина приняла задачу от Петровича")
            print(f"📊 Маршрут: {qa_response['route']}")
            print(f"⏱️  Время: {qa_response['latency']:.1f}с")
            print(f"💬 Ответ: {qa_response['answer']}")
        
        # === ШАГ 4: ОЖИДАНИЕ ВЫПОЛНЕНИЯ ===
        print(f"\n{'='*70}")
        print("ШАГ 4: ОЖИДАНИЕ ВЫПОЛНЕНИЯ АГЕНТАМИ (30 сек)")
        print("="*70)
        
        print("⏳ Даем агентам время на выполнение задач...")
        for i in range(6):
            await asyncio.sleep(5)
            print(f"   ⌛ {(i+1)*5}/30 секунд...")
            
            # Проверяем появились ли файлы
            created_files = self.check_created_files()
            if created_files:
                print(f"   📁 Найдены созданные файлы: {list(created_files.keys())}")
        
        # === ШАГ 5: ПРОВЕРКА РЕЗУЛЬТАТОВ ===
        print(f"\n{'='*70}")
        print("ШАГ 5: ПРОВЕРКА РЕЗУЛЬТАТОВ ВЫПОЛНЕНИЯ")
        print("="*70)
        
        created_files = self.check_created_files()
        
        if created_files:
            print(f"✅ СОЗДАНЫ ФАЙЛЫ ({len(created_files)} шт):")
            for file_path, info in created_files.items():
                print(f"   📄 {file_path}")
                print(f"      - Размер: {info.get('size', 0)} символов")
                print(f"      - Строк: {info.get('lines', 0)}")
                if 'content_preview' in info:
                    print(f"      - Превью: {info['content_preview'][:100]}...")
        else:
            print("❌ Файлы не найдены. Проверим работу агентов...")
        
        # === ШАГ 6: ОТЧЕТ SUPERVISOR ===
        print(f"\n{'='*70}")
        print("ШАГ 6: ФИНАЛЬНЫЙ ОТЧЕТ SUPERVISOR")
        print("="*70)
        
        report_request = f"""
Петрович, какой статус выполнения задачи по созданию file_operations.py?

Что сделал разработчик? Что проверил QA специалист? 
Все ли готово для production?
Какие файлы созданы? Можно ли считать задачу завершенной?

Проанализируй результаты и дай финальную оценку.
"""
        
        final_report = await self.send_to_agent("supervisor", report_request)
        
        if final_report["success"]:
            print(f"📊 ФИНАЛЬНЫЙ ОТЧЕТ ПЕТРОВИЧА:")
            print(f"   Маршрут: {final_report['route']}")
            print(f"   Время: {final_report['latency']:.1f}с")
            print(f"   Отчет: {final_report['answer']}")
        
        # === ИТОГОВАЯ СТАТИСТИКА ===
        print(f"\n{'='*70}")
        print("ИТОГОВАЯ СТАТИСТИКА WORKFLOW")
        print("="*70)
        
        total_time = time.time() - self.start_time
        successful_calls = len([log for log in self.session_log if log['success']])
        total_latency = sum(log.get('latency', 0) for log in self.session_log)
        
        print(f"⏱️  Общее время: {total_time:.1f} секунд")
        print(f"🔄 Успешных вызовов: {successful_calls}")
        print(f"🧠 Общее время LLM: {total_latency:.1f} секунд")
        print(f"📁 Создано файлов: {len(created_files)}")
        print(f"👥 Задействованных агентов: 3 (Supervisor, Developer, QA)")
        
        print(f"\n🎯 УЧАСТНИКИ WORKFLOW:")
        print(f"   • supervisor: Петрович - супервизор и координатор")
        print(f"   • developer: Вася - разработчик")
        print(f"   • qa: Марина - тестировщик")
        
        agents_used = set(log['agent'] for log in self.session_log)
        routes_used = set(log['route'] for log in self.session_log)
        
        print(f"\n📊 ИСПОЛЬЗОВАННЫЕ АГЕНТЫ: {sorted(agents_used)}")
        print(f"🛤️  ИСПОЛЬЗОВАННЫЕ МАРШРУТЫ: {sorted(routes_used)}")
        
        # Показываем созданные файлы
        if created_files:
            print(f"\n📄 СОЗДАННЫЕ ФАЙЛЫ:")
            for file_path, info in created_files.items():
                print(f"   {file_path} ({info.get('size', 0)} chars, {info.get('lines', 0)} lines)")
        
        return len(created_files) > 0 and successful_calls >= 3


async def main():
    """Основная функция."""
    demo = RealWorkflowDemo()
    
    print("🎬 ЗАПУСК РЕАЛЬНОГО WORKFLOW ТЕСТА С ПРАВИЛЬНОЙ АРХИТЕКТУРОЙ")
    print("Демонстрация: User → Supervisor → Developer/QA → Real Results")
    print("Используем технические ID: supervisor, developer, qa")
    print()
    
    try:
        success = await demo.run_real_workflow()
        
        if success:
            print(f"\n🎉 РЕАЛЬНЫЙ WORKFLOW УСПЕШНО ЗАВЕРШЕН!")
            print(f"✅ Supervisor координировал команду")
            print(f"✅ Developer выполнил разработку") 
            print(f"✅ QA провел тестирование")
            print(f"✅ Созданы реальные файлы")
            print(f"✅ Архитектура с разделением ID/имен РАБОТАЕТ!")
        else:
            print(f"\n💔 Workflow завершился неуспешно")
            print(f"❌ Не все задачи выполнены или файлы не созданы")
    
    except KeyboardInterrupt:
        print(f"\n⏹️  Workflow прерван пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 