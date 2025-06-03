#!/usr/bin/env python3
"""
Integration test for Prometheus Framework refactoring.

Tests that entities.aletheia.AletheiaEntity().think("hello") works correctly
with the new core/entities separation.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


async def test_aletheia_entity():
    """Test that Aletheia entity can be imported and used."""
    
    print("🧪 Testing Aletheia entity integration...")
    
    try:
        # Test entity discovery
        print("1. Testing entity discovery...")
        from entities import discover_entities, get_entity_class
        
        entities = discover_entities()
        print(f"   Found entities: {list(entities.keys())}")
        
        if "aletheia" not in entities:
            print("   ❌ Aletheia entity not discovered")
            return False
        
        print("   ✅ Aletheia entity discovered")
        
        # Test entity class retrieval
        print("2. Testing entity class retrieval...")
        AletheiaEntity = get_entity_class("aletheia")
        print(f"   ✅ Got entity class: {AletheiaEntity}")
        
        # Test entity instantiation
        print("3. Testing entity instantiation...")
        entity = AletheiaEntity()
        print("   ✅ Entity instantiated successfully")
        
        # Test basic think operation
        print("4. Testing basic think operation...")
        response = await entity.think("hello")
        print(f"   Response: {response}")
        print("   ✅ Think operation completed")
        
        # Test status check
        print("5. Testing status check...")
        status = await entity.get_status()
        print(f"   Entity: {status['entity_name']}")
        print(f"   Session: {status['session_id']}")
        print(f"   Memory system: {status['memory_system']}")
        print("   ✅ Status check completed")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_core_components():
    """Test that core components can be imported."""
    
    print("\n🔧 Testing core component imports...")
    
    try:
        # Test core imports
        from core import BaseEntity, config
        print("   ✅ Core module imports work")
        
        # Test LLM imports
        from core.llm import LLMRouter, LocalLLM, FastLLM
        print("   ✅ LLM module imports work")
        
        # Test memory imports
        from core.memory import VectorStore, MemorySummariser
        print("   ✅ Memory module imports work")
        
        # Test context imports
        from core.context import ConversationContext
        print("   ✅ Context module imports work")
        
        # Test goals imports
        from core.goals import GoalManager
        print("   ✅ Goals module imports work")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Core component test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all integration tests."""
    
    print("🚀 Prometheus Framework Integration Test")
    print("=" * 50)
    
    # Test core components
    core_success = await test_core_components()
    
    # Test Aletheia entity
    entity_success = await test_aletheia_entity()
    
    print("\n" + "=" * 50)
    if core_success and entity_success:
        print("🎉 All integration tests passed!")
        print("✅ Framework refactoring successful")
        return 0
    else:
        print("❌ Some integration tests failed")
        print("🔧 Framework needs fixes")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main()) 