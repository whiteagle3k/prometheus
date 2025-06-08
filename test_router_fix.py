#!/usr/bin/env python3
"""
Тест исправления роутера для правильной маршрутизации внешних LLM.
"""

import asyncio
import json
from pathlib import Path
from core.llm.router import LLMRouter, TaskContext


def print_section(title: str):
    """Print section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def load_agent_config(agent_name: str) -> dict:
    """Load agent configuration from identity file."""
    config_path = Path(f"entities/{agent_name}/identity/identity.json")
    
    if not config_path.exists():
        print(f"❌ Конфигурация не найдена: {config_path}")
        return {}
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print(f"✅ Загружена конфигурация {agent_name}")
        return config
    except Exception as e:
        print(f"❌ Ошибка чтения конфигурации {agent_name}: {e}")
        return {}


async def test_router_with_config(agent_name: str, config: dict):
    """Test router with specific agent configuration."""
    print(f"\n🧪 Тестирование роутера для {agent_name}...")
    
    # Create router with agent config
    router = LLMRouter(identity_config=config)
    
    # Test task context
    task = TaskContext(
        prompt="Создай функцию для вывода timestamp",
        max_tokens=500,
        temperature=0.7
    )
    
    try:
        # Check routing preferences
        operational_guidelines = config.get("operational_guidelines", {})
        routing_policy = operational_guidelines.get("routing_policy", {})
        prefer_external = routing_policy.get("prefer_external", False)
        
        print(f"📋 Конфигурация:")
        print(f"   prefer_external: {prefer_external}")
        print(f"   routing_policy: {routing_policy}")
        
        # Test routing decision
        decision = await router.route_task(task)
        print(f"🎯 Решение маршрутизации: {decision.value}")
        
        if prefer_external and decision.value == "external":
            print("✅ Правильная маршрутизация - используется внешний LLM")
            return True
        elif prefer_external and decision.value != "external":
            print("❌ Неправильная маршрутизация - должен использоваться внешний LLM")
            return False
        else:
            print("ℹ️  Маршрутизация соответствует конфигурации")
            return True
            
    except Exception as e:
        print(f"❌ Ошибка тестирования роутера: {e}")
        return False


async def main():
    """Main test function."""
    print_section("🔧 ТЕСТ ИСПРАВЛЕНИЯ РОУТЕРА")
    
    # Test all dev team agents
    agents = ["supervisor", "vasya", "marina"]
    results = {}
    
    for agent in agents:
        print_section(f"Тестирование {agent.upper()}")
        
        # Load agent config
        config = load_agent_config(agent)
        if not config:
            results[agent] = False
            continue
        
        # Test router
        success = await test_router_with_config(agent, config)
        results[agent] = success
    
    # Summary
    print_section("📊 РЕЗУЛЬТАТЫ ТЕСТОВ")
    
    all_passed = True
    for agent, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{agent}: {status}")
        if not success:
            all_passed = False
    
    print(f"\n🎯 Общий результат: {'✅ ВСЕ ТЕСТЫ ПРОШЛИ' if all_passed else '❌ ЕСТЬ ОШИБКИ'}")
    
    if all_passed:
        print("\n💡 Исправления роутера работают правильно!")
        print("   Агенты будут использовать внешние LLM (GPT-4o, Claude)")
    else:
        print("\n⚠️ Требуются дополнительные исправления")


if __name__ == "__main__":
    asyncio.run(main()) 