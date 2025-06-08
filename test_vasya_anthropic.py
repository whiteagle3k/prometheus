#!/usr/bin/env python3
"""
Тест проверки какой провайдер использует Вася и работает ли anthropic.
"""

import asyncio
import json
from pathlib import Path
from core.llm.router import LLMRouter, TaskContext
from core.llm.providers import ExternalLLMManager
from core.processing.configs.config_loader import load_agent_config


def print_section(title: str):
    """Print section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


async def test_anthropic_provider():
    """Test if anthropic provider is working."""
    print_section("🧪 ТЕСТ ANTHROPIC ПРОВАЙДЕРА")
    
    # Load Vasya's config
    config = load_agent_config('vasya')
    if not config:
        print("❌ Не удалось загрузить конфигурацию Васи")
        return False
    
    external_config = config.get('external_llms', {})
    print(f"📋 Конфигурация external_llms:")
    print(f"   primary_provider: {external_config.get('primary_provider')}")
    print(f"   routing_preferences: {external_config.get('routing_preferences')}")
    
    # Test external LLM manager
    external_manager = ExternalLLMManager(providers_config=external_config)
    
    # Check available providers
    available_providers = external_manager.list_available_providers()
    print(f"\n🔍 Доступные провайдеры: {available_providers}")
    
    # Test anthropic specifically
    try:
        anthropic_provider = external_manager.get_provider('anthropic')
        if anthropic_provider:
            print("✅ Anthropic провайдер найден")
            
            # Try to get best available
            best_provider = await external_manager.get_best_available()
            if best_provider:
                print(f"🎯 Лучший доступный провайдер: {best_provider.provider_type.value}")
                print(f"   Модель: {best_provider.get_model_info().get('model', 'unknown')}")
                
                # Test simple request
                try:
                    response = await best_provider.generate(
                        prompt="Hello, can you respond in 10 words or less?",
                        max_tokens=50,
                        temperature=0.1
                    )
                    print(f"✅ Тест запрос успешен: {response[:100]}...")
                    return True
                except Exception as e:
                    print(f"❌ Ошибка тест запроса: {e}")
                    return False
            else:
                print("❌ Не удалось получить лучший провайдер")
                return False
        else:
            print("❌ Anthropic провайдер не найден")
            return False
    except Exception as e:
        print(f"❌ Ошибка тестирования anthropic: {e}")
        return False


async def test_vasya_routing():
    """Test routing decision for Vasya."""
    print_section("🎯 ТЕСТ РОУТИНГА ВАСИ")
    
    # Load Vasya's config
    config = load_agent_config('vasya')
    if not config:
        print("❌ Не удалось загрузить конфигурацию Васи")
        return False
    
    # Create router with Vasya's config
    router = LLMRouter(identity_config=config)
    
    # Test routing for coding task
    task = TaskContext(
        prompt="Создай функцию для обработки данных",
        max_tokens=1000,
        temperature=0.1
    )
    
    try:
        # Test routing decision
        decision = await router.route_task(task)
        print(f"🎯 Решение роутера: {decision.value}")
        
        if decision.value == "external":
            # Test actual execution
            result = await router.execute_task(task)
            route_used = result.get('route_used', 'unknown')
            
            # Check consultation metadata for provider info
            metadata = result.get('consultation_metadata', {})
            provider = metadata.get('provider', 'unknown')
            model = metadata.get('model', 'unknown')
            
            print(f"📊 Результат выполнения:")
            print(f"   route_used: {route_used}")
            print(f"   provider: {provider}")
            print(f"   model: {model}")
            
            if provider == "anthropic":
                print("✅ Вася использует Anthropic (Claude) как ожидается")
                return True
            else:
                print(f"⚠️ Вася использует {provider} вместо Anthropic")
                return False
        else:
            print("⚠️ Роутер выбрал локальную модель вместо внешней")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка тестирования роутинга: {e}")
        return False


async def test_vasya_anthropic():
    config = load_agent_config('vasya')
    external_config = config.get('external_llms', {})
    
    print("Primary provider:", external_config.get('primary_provider'))
    print("Routing preferences:", external_config.get('routing_preferences'))
    
    router = LLMRouter(identity_config=config)
    task = TaskContext(prompt="Create a function", max_tokens=500)
    
    result = await router.execute_task(task)
    metadata = result.get('consultation_metadata', {})
    
    print("Provider used:", metadata.get('provider', 'unknown'))
    print("Model used:", metadata.get('model', 'unknown'))


async def main():
    """Main test function."""
    print_section("🔧 ДИАГНОСТИКА ANTHROPIC ПРОВАЙДЕРА ВАСИ")
    
    # Test 1: Check if anthropic provider works at all
    anthropic_works = await test_anthropic_provider()
    
    # Test 2: Check Vasya's routing
    vasya_routing_correct = await test_vasya_routing()
    
    # Test 3: Check Vasya's anthropic usage
    await test_vasya_anthropic()
    
    # Summary
    print_section("📊 ИТОГОВЫЙ РЕЗУЛЬТАТ")
    
    print(f"Anthropic провайдер работает: {'✅ ДА' if anthropic_works else '❌ НЕТ'}")
    print(f"Вася использует Anthropic: {'✅ ДА' if vasya_routing_correct else '❌ НЕТ'}")
    
    if anthropic_works and vasya_routing_correct:
        print("\n🎉 ВСЕ РАБОТАЕТ ПРАВИЛЬНО!")
        print("   Вася корректно использует Anthropic (Claude) для кодинга")
    elif anthropic_works and not vasya_routing_correct:
        print("\n⚠️ ПРОБЛЕМА С РОУТИНГОМ")
        print("   Anthropic работает, но Вася его не использует")
    elif not anthropic_works:
        print("\n❌ ПРОБЛЕМА С ANTHROPIC ПРОВАЙДЕРОМ")
        print("   Нужно проверить API ключи и конфигурацию")
    
    return anthropic_works and vasya_routing_correct


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1) 