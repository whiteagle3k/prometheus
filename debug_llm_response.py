#!/usr/bin/env python3
"""Debug local LLM responses for scientific questions."""

import asyncio
from aletheia.llm.router import LLMRouter
from aletheia.processing.filters import ContaminationFilter

async def debug_llm_responses():
    print("🔍 Debugging Local LLM Self-Assessment")
    
    router = LLMRouter()
    
    test_question = "расскажи тогда про квантовую запутанность"
    print(f"Question: {test_question}")
    
    # Get raw response first
    raw_response = await router.local_llm.generate(
        prompt=router.local_llm._format_structured_prompt(test_question),
        max_tokens=256,
        temperature=0.3
    )
    
    print("\n🔍 Raw Response (before filtering):")
    print(raw_response)
    
    # Test contamination filter
    contamination_filter = ContaminationFilter()
    filter_result = contamination_filter.process(raw_response)
    filtered_response = filter_result.data if filter_result.success else raw_response.strip()
    
    print("\n🧹 After Contamination Filter:")
    print(filtered_response)
    
    # Test full structured parsing
    result = await router.local_llm.generate_structured(
        prompt=test_question,
        max_tokens=256,
        temperature=0.3
    )
    
    print("\n📝 Final Structured Result:")
    print(f"Answer: {result.get('answer', 'None')}")
    print(f"Confidence: {result.get('confidence', 'None')}")
    print(f"External needed: {result.get('external_needed', 'None')}")
    print(f"Reasoning: {result.get('reasoning', 'None')}")

if __name__ == "__main__":
    asyncio.run(debug_llm_responses()) 