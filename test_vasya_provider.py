#!/usr/bin/env python3

import asyncio
import json
from pathlib import Path
from core.llm.router import LLMRouter, TaskContext

async def test():
    # Load Vasya's config directly
    config_path = Path("entities/vasya/identity/identity.json")
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    router = LLMRouter(identity_config=config)
    task = TaskContext(prompt="Create a simple function", max_tokens=500)
    
    result = await router.execute_task(task)
    metadata = result.get('consultation_metadata', {})
    
    provider = metadata.get('provider', 'unknown')
    print(f"Provider used: {provider}")
    print(f"Model: {metadata.get('model', 'unknown')}")
    
    if provider == "anthropic":
        print("✅ Вася использует Anthropic!")
    else:
        print(f"❌ Вася использует {provider} вместо Anthropic")

asyncio.run(test()) 