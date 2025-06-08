#!/usr/bin/env python3
"""
Тест НАСТОЯЩЕЙ саморазвивающейся команды разработчиков.
Команда анализирует и модифицирует сам проект Prometheus.

Это "охренительная идея" - AI агенты которые улучшают сами себя!
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


async def send_team_request(entity: str, message: str, timeout: int = 120):
    """Send request to team member."""
    url = "http://localhost:8000/v1/chat"
    data = {"message": message, "user_id": "self_modification_test"}
    
    try:
        print(f"📤 Запрос к {entity}: {message[:80]}...")
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
            
            print(f"✅ Ответ получен за {elapsed:.1f}с (route: {route})")
            print(f"📝 {answer[:200]}...")
            
            # Check if external LLM was used
            if route == "external":
                print("🌐 ВНЕШНИЙ LLM ИСПОЛЬЗОВАН ✓")
            
            return answer
        else:
            print(f"❌ Ошибка {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")
        return None


async def step1_petrovich_analysis():
    """Шаг 1: Aletheia анализирует задачу саморазвития (вместо Петровича)."""
    print_section("🧠 ШАГ 1: АНАЛИЗ ЗАДАЧИ САМОРАЗВИТИЯ")
    
    task = """Aletheia, выступи в роли senior supervisor для команды разработчиков. Нужно реализовать саморазвитие команды через модификацию проекта Prometheus.

ЗАДАЧА: Добавить timestamp'ы ко всем выводам в консоль во ВСЕМ проекте.

Это не про создание отдельной утилиты - это про анализ и модификацию реального кода проекта:
1. Найти все места где используется print() и logging в проекте
2. Модифицировать эти места для добавления timestamp'ов
3. Протестировать изменения

Проанализируй задачу и дай четкие инструкции Васе для реальной модификации кода."""
    
    response = await send_team_request("aletheia", task)
    return response


async def step2_vasya_implementation():
    """Шаг 2: Вася анализирует код и вносит изменения."""
    print_section("💻 ШАГ 2: АНАЛИЗ И МОДИФИКАЦИЯ КОДА")
    
    task = """Вася, Aletheia дала задачу на саморазвитие. Проанализируй весь проект Prometheus и добавь timestamp'ы к выводам в консоль.

КОНКРЕТНЫЕ ДЕЙСТВИЯ:
1. Используй MCP filesystem_list_directory для анализа структуры проекта
2. Используй filesystem_read_file для чтения ключевых файлов
3. Найди все места с print() и logging вызовами
4. Модифицируй код используя filesystem_write_file для добавления timestamp'ов
5. Покажи конкретные изменения которые ты внес

НЕ создавай отдельные утилиты - МОДИФИЦИРУЙ РЕАЛЬНЫЕ ФАЙЛЫ ПРОЕКТА!"""
    
    response = await send_team_request("vasya", task)
    return response


async def step3_marina_testing():
    """Шаг 3: Марина тестирует внесенные изменения."""
    print_section("🔍 ШАГ 3: ТЕСТИРОВАНИЕ ИЗМЕНЕНИЙ")
    
    task = """Марина, Вася внес изменения в код проекта для добавления timestamp'ов. 

ЗАДАЧИ ТЕСТИРОВАНИЯ:
1. Используй MCP filesystem_read_file для проверки измененных файлов
2. Используй terminal_execute для запуска тестов и проверки вывода
3. Найди проблемы и несоответствия в изменениях
4. Проверь что timestamp'ы действительно появляются в выводе
5. Предложи улучшения если нужно

Протестируй РЕАЛЬНЫЕ изменения в проекте, не теоретические."""
    
    response = await send_team_request("marina", task)
    return response


async def step4_petrovich_validation():
    """Шаг 4: Aletheia валидирует результат саморазвития."""
    print_section("✅ ШАГ 4: ВАЛИДАЦИЯ САМОРАЗВИТИЯ")
    
    task = """Aletheia, команда выполнила задачу саморазвития - модификацию проекта Prometheus для добавления timestamp'ов.

Вася проанализировал код и внес изменения.
Марина протестировала изменения.

ВАЛИДАЦИЯ:
1. Оцени качество выполненной работы
2. Проверь что изменения действительно внесены в проект
3. Определи успешность саморазвития команды
4. Дай рекомендации для следующих итераций

Это первый шаг к полному саморазвитию AI команды через модификацию собственного кода!"""
    
    response = await send_team_request("aletheia", task)
    return response


async def analyze_real_changes():
    """Анализ реальных изменений в проекте."""
    print_section("📊 АНАЛИЗ РЕАЛЬНЫХ ИЗМЕНЕНИЙ")
    
    # Check for any new or modified files
    project_files = list(Path(".").glob("**/*.py"))
    
    print(f"📁 Всего Python файлов в проекте: {len(project_files)}")
    
    # Look for recent modifications (this is simplistic)
    recent_files = []
    for file in project_files:
        try:
            stat = file.stat()
            # Files modified in last 10 minutes
            if time.time() - stat.st_mtime < 600:
                recent_files.append(file)
        except:
            pass
    
    if recent_files:
        print("📝 Недавно измененные файлы:")
        for file in recent_files:
            print(f"   • {file}")
    else:
        print("⚠️ Недавних изменений не обнаружено")
    
    # Check for timestamp-related modifications
    timestamp_patterns = ["timestamp", "datetime.now", "strftime", "[%"]
    
    modified_files_with_timestamps = []
    for file in project_files:
        try:
            content = file.read_text(encoding='utf-8', errors='ignore')
            if any(pattern in content for pattern in timestamp_patterns):
                modified_files_with_timestamps.append(file)
        except:
            pass
    
    print(f"\n🕐 Файлы с timestamp функциональностью: {len(modified_files_with_timestamps)}")
    for file in modified_files_with_timestamps[:10]:  # Show first 10
        print(f"   • {file}")
    
    return len(recent_files), len(modified_files_with_timestamps)


async def main():
    """Главная функция теста саморазвития."""
    print_section("🚀 ТЕСТ САМОРАЗВИВАЮЩЕЙСЯ AI КОМАНДЫ")
    
    print("🎯 ЦЕЛЬ: Проверить способность команды модифицировать сам проект Prometheus")
    print("💡 Это 'охренительная идея' - AI агенты улучшают сами себя!")
    
    # Check API availability
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code != 200:
            print("❌ API сервер недоступен. Запустите: poetry run python prometheus.py api")
            return
    except:
        print("❌ API сервер недоступен. Запустите: poetry run python prometheus.py api")
        return
    
    print("✅ API сервер доступен")
    
    # Baseline analysis
    print_section("📊 АНАЛИЗ ДО МОДИФИКАЦИИ")
    recent_before, timestamp_files_before = await analyze_real_changes()
    
    # Execute team workflow
    start_time = time.time()
    
    step1_result = await step1_petrovich_analysis()
    if not step1_result:
        print("❌ Шаг 1 не удался")
        return
    
    step2_result = await step2_vasya_implementation()
    if not step2_result:
        print("❌ Шаг 2 не удался") 
        return
    
    step3_result = await step3_marina_testing()
    if not step3_result:
        print("❌ Шаг 3 не удался")
        return
    
    step4_result = await step4_petrovich_validation()
    
    total_time = time.time() - start_time
    
    # Post-analysis
    print_section("📊 АНАЛИЗ ПОСЛЕ МОДИФИКАЦИИ")
    recent_after, timestamp_files_after = await analyze_real_changes()
    
    # Results
    print_section("🎯 РЕЗУЛЬТАТЫ САМОРАЗВИТИЯ")
    
    print(f"⏱️ Общее время работы команды: {total_time:.1f} секунд")
    print(f"📝 Недавних изменений: {recent_before} → {recent_after}")
    print(f"🕐 Файлов с timestamps: {timestamp_files_before} → {timestamp_files_after}")
    
    if recent_after > recent_before:
        print("✅ КОМАНДА ВНЕСЛА РЕАЛЬНЫЕ ИЗМЕНЕНИЯ В ПРОЕКТ!")
        print("🚀 Саморазвитие РАБОТАЕТ!")
    else:
        print("⚠️ Реальных изменений в проект не внесено")
        print("🔧 Нужно улучшить способность команды к самомодификации")
    
    print_section("💡 ЗНАЧЕНИЕ")
    print("🌟 Это первый шаг к полностью саморазвивающейся AI системе!")
    print("🔄 Команда может анализировать и улучшать собственный код")
    print("🚀 Потенциал для экспоненциального саморазвития")
    
    if step4_result:
        print(f"\n📋 Финальная оценка Aletheia:")
        print(f"   {step4_result[:300]}...")


if __name__ == "__main__":
    asyncio.run(main()) 