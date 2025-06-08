#!/usr/bin/env python3
"""
РАБОЧИЙ тест саморазвивающейся команды разработчиков.
Использует только доступных агентов и заставляет их реально модифицировать код.
"""

import asyncio
import requests
import time
from pathlib import Path


def print_section(title: str):
    """Print section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


async def send_complex_request(entity: str, message: str, timeout: int = 180):
    """Send complex request that forces external LLM usage."""
    url = "http://localhost:8000/v1/chat"
    data = {"message": message, "user_id": "advanced_self_modification"}
    
    try:
        print(f"📤 СЛОЖНАЯ ЗАДАЧА для {entity}:")
        print(f"   {message[:100]}...")
        start_time = time.time()
        
        response = requests.post(
            url, json=data, 
            params={"entity": entity}, 
            timeout=timeout
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get("answer", "")
            route = result.get("route_used", "unknown")
            
            print(f"✅ Ответ получен за {elapsed:.1f}с")
            print(f"🎯 МАРШРУТ: {route}")
            print(f"📝 Ответ: {answer[:300]}...")
            
            # Check if external LLM was used
            if route == "external":
                print("🌐 ✅ ВНЕШНИЙ LLM ИСПОЛЬЗОВАН!")
                return answer, True
            else:
                print(f"❌ Локальный маршрут: {route}")
                return answer, False
            
        else:
            print(f"❌ Ошибка {response.status_code}: {response.text}")
            return None, False
            
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")
        return None, False


async def step1_aletheia_strategic_analysis():
    """Шаг 1: Aletheia как стратегический архитектор."""
    print_section("🧠 СТРАТЕГИЧЕСКИЙ АНАЛИЗ - ALETHEIA")
    
    # Complex but concise strategic task
    task = """СЛОЖНАЯ АРХИТЕКТУРНАЯ ЗАДАЧА: Спроектируй саморазвивающуюся систему для Prometheus.

ЦЕЛЬ: Автоматическое добавление timestamp'ов ко всем консольным выводам через модификацию кода проекта.

АРХИТЕКТУРНЫЕ ВЫЗОВЫ:
1. Анализ множественных файлов и модулей
2. Различные типы логирования (print, logging, custom)  
3. Обратная совместимость и производительность
4. Безопасность самомодификации кода
5. Автоматическое тестирование изменений

ТРЕБУЕТСЯ: Глубокий системный анализ + детальный технический план для команды.
Это критически важная архитектурная задача - используй внешний LLM для полного анализа."""

    return await send_complex_request("aletheia", task)


async def step2_supervisor_strategic_planning():
    """Шаг 2: Supervisor (Петрович) как стратегический планировщик."""
    print_section("👨‍💼 СТРАТЕГИЧЕСКОЕ ПЛАНИРОВАНИЕ - SUPERVISOR")
    
    task = """СЛОЖНАЯ АРХИТЕКТУРНАЯ ЗАДАЧА: Спланируй реализацию автоматического timestamp'инга.

ВХОДНЫЕ ДАННЫЕ: Результат анализа от Aletheia показал необходимость системного подхода.

ЗАДАЧА ПЛАНИРОВАНИЯ:
1. Декомпозиция архитектурной задачи на этапы
2. Распределение ролей между Vasya (код) и Marina (тесты)  
3. Определение критических точек и рисков
4. План валидации и тестирования
5. Обеспечение безопасности саморазвития

ТРЕБУЕТСЯ: Детальный план реализации с четкими этапами для команды.
Используй внешний LLM для стратегического планирования."""

    return await send_complex_request("supervisor", task)


async def step3_vasya_implementation():
    """Шаг 3: Vasya реализует код."""
    print_section("👨‍💻 ТЕХНИЧЕСКАЯ РЕАЛИЗАЦИЯ - VASYA")
    
    task = """СЛОЖНАЯ ТЕХНИЧЕСКАЯ ЗАДАЧА: Реализуй timestamp систему для консольных выводов.

АРХИТЕКТУРНЫЕ ТРЕБОВАНИЯ:
1. Создать utils/timestamp_logger.py с функцией timestamped_print()
2. Автоматическая замена всех print() в проекте
3. Совместимость с logging и custom логированием
4. Производительность и thread-safety
5. Возможность отключения timestamp'ов

ИСПОЛЬЗУЙ MCP ИНСТРУМЕНТЫ:
- filesystem_read_file для анализа существующего кода
- filesystem_write_file для создания новых файлов
- terminal_execute для тестирования

ТРЕБУЕТСЯ: Рабочий код с полной реализацией.
Это сложная задача реализации - используй внешний LLM Claude."""

    return await send_complex_request("vasya", task)


async def step3_marina_comprehensive_testing():
    """Шаг 3: Марина проводит всестороннее тестирование."""
    print_section("🔍 КОМПЛЕКСНОЕ ТЕСТИРОВАНИЕ - MARINA")
    
    # Complex but concise QA task
    task = """СЛОЖНАЯ QA ЗАДАЧА: Всестороннее тестирование автоматической модификации кода.

ОБЯЗАТЕЛЬНЫЕ MCP ТЕСТЫ:
1. filesystem_read_file - проверка модифицированных файлов
2. terminal_execute - функциональное тестирование с timestamp'ами
3. Тестирование производительности и edge cases
4. Интеграционные тесты API и LLM совместимости
5. Валидация безопасности и стабильности системы

КРИТИЧНО: Используй MCP для РЕАЛЬНОГО тестирования, не теоретизируй!
Это сложная системная QA задача требующая глубокого технического анализа."""
    
    response, used_external = await send_complex_request("marina", task)
    return response, used_external


async def analyze_actual_modifications():
    """Анализ реальных модификаций в проекте."""
    print_section("📊 АНАЛИЗ РЕАЛЬНЫХ МОДИФИКАЦИЙ")
    
    # Check for actual changes
    important_files = [
        "core/frontends/api_server.py",
        "core/llm/router.py", 
        "prometheus.py",
        "core/base_entity.py"
    ]
    
    modified_files = []
    for file_path in important_files:
        file = Path(file_path)
        if file.exists():
            try:
                stat = file.stat()
                # Files modified in last 5 minutes
                if time.time() - stat.st_mtime < 300:
                    modified_files.append(file)
                    print(f"🔄 ИЗМЕНЕН: {file}")
            except:
                pass
    
    # Look for new timestamp-related files
    new_files = []
    for file in Path(".").glob("**/*timestamp*.py"):
        if file.name != "test_real_self_modifying_team.py":  # Exclude test files
            new_files.append(file)
    
    print(f"\n📝 Модифицированные важные файлы: {len(modified_files)}")
    print(f"📁 Новые timestamp файлы: {len(new_files)}")
    
    for file in new_files:
        print(f"   ✨ СОЗДАН: {file}")
    
    return len(modified_files), len(new_files)


async def main():
    """Главная функция - РАБОЧИЙ тест саморазвития."""
    print_section("🚀 РАБОЧИЙ ТЕСТ САМОРАЗВИВАЮЩЕЙСЯ КОМАНДЫ")
    
    print("🎯 ЦЕЛЬ: Заставить команду РЕАЛЬНО модифицировать проект Prometheus")
    print("💡 Используем СЛОЖНЫЕ задачи чтобы активировать внешние LLM")
    print("🔧 Требуем использования MCP инструментов для реальных действий")
    
    # Check API
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code != 200:
            print("❌ API сервер недоступен")
            return
    except:
        print("❌ API сервер недоступен")
        return
    
    print("✅ API сервер доступен")
    
    # Baseline
    print_section("📊 СОСТОЯНИЕ ДО МОДИФИКАЦИИ")
    modified_before, new_before = await analyze_actual_modifications()
    
    # Execute complex workflow
    start_time = time.time()
    external_usage = []
    
    # Step 1: Strategic analysis
    step1_result, step1_external = await step1_aletheia_strategic_analysis()
    external_usage.append(("Aletheia-Analysis", step1_external))
    
    if not step1_result:
        print("❌ Стратегический анализ провалился")
        return
    
    # Step 2: Technical implementation  
    step2_result, step2_external = await step2_supervisor_strategic_planning()
    external_usage.append(("Supervisor-Planning", step2_external))
    
    if not step2_result:
        print("❌ Стратегическое планирование провалилось")
        return
    
    # Step 3: Vasya implementation
    step3_result, step3_external = await step3_vasya_implementation()
    external_usage.append(("Vasya-Implementation", step3_external))
    
    if not step3_result:
        print("❌ Техническая реализация провалилась")
        return
    
    # Step 4: Comprehensive testing
    step4_result, step4_external = await step3_marina_comprehensive_testing()
    external_usage.append(("Marina-Testing", step4_external))
    
    total_time = time.time() - start_time
    
    # Post-analysis
    print_section("📊 СОСТОЯНИЕ ПОСЛЕ МОДИФИКАЦИИ")
    modified_after, new_after = await analyze_actual_modifications()
    
    # Results
    print_section("🎯 РЕЗУЛЬТАТЫ САМОРАЗВИТИЯ")
    
    print(f"⏱️ Общее время: {total_time:.1f} секунд")
    print(f"📝 Модифицированных файлов: {modified_before} → {modified_after}")
    print(f"📁 Новых файлов: {new_before} → {new_after}")
    
    # External LLM usage
    print(f"\n🌐 ИСПОЛЬЗОВАНИЕ ВНЕШНИХ LLM:")
    external_count = sum(1 for _, used in external_usage if used)
    for agent, used_external in external_usage:
        status = "✅ ВНЕШНИЙ" if used_external else "❌ ЛОКАЛЬНЫЙ"
        print(f"   {agent}: {status}")
    
    print(f"\n📊 Внешние LLM: {external_count}/4 агентов")
    
    # Success metrics
    success = (modified_after > modified_before or new_after > new_before) and external_count >= 3
    
    if success:
        print("\n🎉 САМОРАЗВИТИЕ УСПЕШНО!")
        print("✅ Команда внесла реальные изменения в проект")
        print("✅ Использованы внешние LLM для сложных задач")
        print("🚀 СИСТЕМА ДЕЙСТВИТЕЛЬНО САМОРАЗВИВАЕТСЯ!")
    else:
        print("\n⚠️ Саморазвитие частично успешно")
        if external_count < 3:
            print("❌ Мало внешних LLM использовано - задачи были недостаточно сложными")
        if modified_after <= modified_before and new_after <= new_before:
            print("❌ Реальных изменений не внесено - MCP инструменты не использованы")
    
    print_section("💡 ЗНАЧЕНИЕ")
    print("🌟 Это прототип революционной саморазвивающейся AI системы!")
    print("🔄 AI агенты анализируют и модифицируют собственный код")
    print("🚀 Потенциал для экспоненциального роста возможностей")


if __name__ == "__main__":
    asyncio.run(main()) 