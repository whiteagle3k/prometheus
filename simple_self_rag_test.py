#!/usr/bin/env python3
"""
Simple Self-RAG Test

Quick validation that Self-RAG components are working.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from entities.aletheia_enhanced import EnhancedAletheiaEntity


async def test_enhanced_aletheia():
    """Test the enhanced Aletheia entity."""
    print("🧪 Testing Enhanced Aletheia with Self-RAG")
    print("=" * 50)
    
    # Initialize enhanced entity
    print("🔧 Initializing Enhanced Aletheia...")
    entity = EnhancedAletheiaEntity()
    print("✅ Enhanced Aletheia initialized")
    
    # Test queries
    test_queries = [
        "Hello, how are you?",
        "What is machine learning?",
        "Как работает искусственный интеллект?"
    ]
    
    for i, query in enumerate(test_queries):
        print(f"\n--- Test {i+1}: {query} ---")
        
        try:
            # Test with enhanced processing
            result = await entity.process_query(query)
            
            response = result.get("response", "")
            quality = result.get("quality_assessment", {})
            stats = result.get("enhancement_stats", {})
            
            print(f"✅ Response: {response[:100]}{'...' if len(response) > 100 else ''}")
            print(f"📊 Quality Score: {quality.get('overall_score', 'N/A')}")
            print(f"🔧 Enhancements: {stats}")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
    
    # Test enhancement report
    print(f"\n--- Enhancement Report ---")
    try:
        report = await entity.get_enhancement_report()
        print(f"📈 Enhancement Report:")
        print(f"   Components: {report['components_status']}")
        print(f"   Stats: {report['enhancement_stats']}")
    except Exception as e:
        print(f"❌ Report failed: {e}")
    
    print("\n✅ Enhanced Aletheia test complete!")


async def main():
    """Run the simple test."""
    await test_enhanced_aletheia()


if __name__ == "__main__":
    asyncio.run(main()) 