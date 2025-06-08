#!/usr/bin/env python3

import asyncio
from core.llm.providers.anthropic_provider import AnthropicProvider
from core.llm.providers.base import GenerationRequest

async def test():
    provider = AnthropicProvider({'model': 'claude-3-5-sonnet-20241022'})
    
    try:
        await provider._setup_client()
        print('Setup OK')
        
        is_healthy = await provider._health_check()
        print('Health:', is_healthy)
        
        if is_healthy:
            request = GenerationRequest(prompt='Hello', max_tokens=20, temperature=0.1)
            response = await provider._generate_text(request)
            print('Response:', response.text)
    except Exception as e:
        print('Error:', str(e))

asyncio.run(test()) 