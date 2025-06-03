#!/usr/bin/env python3
"""Test the improved LLM-based routing approach."""

import asyncio
from aletheia.llm.router import LLMRouter, TaskContext

async def test_llm_based_routing():
    """Test that physics questions are properly detected by local LLM self-assessment."""
    print("🧠 Testing LLM-Based Routing Approach")
    
    router = LLMRouter()
    
    # Test physics questions from the dialogue
    test_cases = [
        {
            "prompt": "расскажи тогда про квантовую запутанность",
            "description": "Quantum entanglement explanation"
        },
        {
            "prompt": "согласно ОТО, информация не может передаваться мгновенно, её максимальная скорость это скорость света, нет ?",
            "description": "Relativity theory question"
        },
        {
            "prompt": "как это работает ? откуда одна частица может знать состояние другой ?",
            "description": "Quantum mechanics mechanism"
        },
        {
            "prompt": "почему так происходит ? может, есть еще и другие исключения ?",
            "description": "Physics exceptions question"
        },
        {
            "prompt": "привет, как дела?",
            "description": "Simple greeting (should stay local)"
        }
    ]
    
    print("\n🧪 Testing Local LLM Self-Assessment:")
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n{i}. {case['description']}")
        print(f"   Query: \"{case['prompt'][:50]}...\"")
        
        try:
            # Test local LLM self-assessment directly
            task = TaskContext(
                prompt=case['prompt'],
                max_tokens=512,
                conversation_context=None
            )
            
            # Get structured response from local LLM for routing decision
            structured_result = await router.local_llm.generate_structured(
                prompt=case['prompt'],
                max_tokens=256,
                temperature=0.3
            )
            
            confidence = structured_result.get('confidence', 'unknown')
            external_needed = structured_result.get('external_needed', False)
            reasoning = structured_result.get('reasoning', 'No reasoning provided')
            raw_response = structured_result.get('raw_response', 'No raw response')
            
            print(f"   🤖 Local LLM Assessment:")
            print(f"      Confidence: {confidence}")
            print(f"      External needed: {external_needed}")
            print(f"      Reasoning: {reasoning}")
            print(f"      Raw response: {raw_response[:200]}...")  # Debug output
            
            # Test actual routing decision
            routing_decision = await router.route_task(task)
            print(f"   🎯 Routing Decision: {routing_decision.value}")
            
            # Evaluate correctness
            is_scientific = i <= 4  # First 4 are scientific
            should_be_external = is_scientific
            is_correct = (routing_decision.value == "external") == should_be_external
            
            status = "✅ CORRECT" if is_correct else "❌ INCORRECT"
            print(f"   {status} (Expected: {'external' if should_be_external else 'local'})")
            
        except Exception as e:
            print(f"   ❌ ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_llm_based_routing()) 