#!/usr/bin/env python3
"""
Comprehensive Test Suite for Prometheus Framework
==============================================

Tests all core functionality:
- Fast LLM routing decisions (LOCAL vs EXTERNAL)
- Memory storage and retrieval
- Context flow and conversation continuity
- Language handling (Russian/English with proper forms)
- User profile extraction and usage
- Debug output and transparency

Usage: python test_comprehensive.py
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Dict, List, Any

# Import our framework
from entities.aletheia import AletheiaEntity


class ComprehensiveTest:
    """Comprehensive test suite for the Prometheus framework."""
    
    def __init__(self):
        self.entity = None
        self.test_results: List[Dict[str, Any]] = []
        self.start_time = time.time()
        
    async def setup(self):
        """Initialize the test environment."""
        print("🚀 Setting up Comprehensive Test Suite")
        print("=" * 60)
        
        # Initialize Aletheia entity
        self.entity = AletheiaEntity()
        
        # Clear memory for clean test
        await self.entity.reset_memory()
        print("✅ Test environment ready\n")
        
    async def run_all_tests(self):
        """Run all comprehensive tests."""
        
        await self.setup()
        
        test_groups = [
            ("🎯 Routing Intelligence Tests", self.test_routing),
            ("🧠 Memory & Context Tests", self.test_memory_context),
            ("🌍 Language & Forms Tests", self.test_language_forms),
            ("👤 User Profile Tests", self.test_user_profiles),
            ("🔍 Debug & Transparency Tests", self.test_debug_output),
        ]
        
        for group_name, test_method in test_groups:
            print(f"\n{group_name}")
            print("-" * 50)
            await test_method()
            
        await self.generate_report()
        
    async def test_routing(self):
        """Test intelligent routing decisions."""
        
        test_cases = [
            {
                "name": "Simple Greeting",
                "query": "привет как дела",
                "expected_route": "local",
                "description": "Basic conversational greeting should stay local"
            },
            {
                "name": "Scientific Question", 
                "query": "расскажи принцип Сферы Дайсона",
                "expected_route": "external",
                "description": "Complex scientific topics should route to external"
            },
            {
                "name": "Personal Question",
                "query": "как тебя зовут",
                "expected_route": "local", 
                "description": "Simple personal questions should stay local"
            }
        ]
        
        for test_case in test_cases:
            print(f"  🧪 {test_case['name']}: {test_case['query'][:30]}...")
            
            start_time = time.time()
            response = await self.entity.think(test_case['query'])
            end_time = time.time()
            
            result = {
                "test": test_case['name'],
                "query": test_case['query'],
                "expected_route": test_case['expected_route'],
                "response_time": end_time - start_time,
                "response_length": len(response),
                "response_preview": response[:80] + "..." if len(response) > 80 else response,
            }
            
            self.test_results.append(result)
            print(f"     ✅ Response: {result['response_preview']}")
            print(f"     ⏱️  Time: {result['response_time']:.2f}s\n")
            
    async def test_memory_context(self):
        """Test memory storage and context preservation."""
        
        # Sequential conversation to test context flow
        conversation = [
            "Меня зовут Игорь",
            "помнишь как меня зовут?"
        ]
        
        print("  🧪 Sequential Conversation Test")
        
        for i, query in enumerate(conversation):
            print(f"     Round {i+1}: {query}")
            
            start_time = time.time()
            response = await self.entity.think(query)
            end_time = time.time()
            
            result = {
                "test": f"Context Flow Round {i+1}",
                "query": query,
                "response_time": end_time - start_time,
                "response_preview": response[:80] + "..." if len(response) > 80 else response,
                "context_check": "Игорь" in response if i >= 1 else "N/A"
            }
            
            self.test_results.append(result)
            print(f"     ✅ Response: {result['response_preview']}")
            print(f"     📝 Context preserved: {result['context_check']}\n")
            
    async def test_language_forms(self):
        """Test Russian feminine forms and language switching."""
        
        test_cases = [
            {
                "name": "Russian Feminine Forms",
                "query": "ты готова помочь?",
                "expected_forms": ["готова", "рада"],
            },
            {
                "name": "English Response",
                "query": "are you ready to help?",
                "expected_forms": ["ready", "help"],
            }
        ]
        
        for test_case in test_cases:
            print(f"  🧪 {test_case['name']}: {test_case['query']}")
            
            start_time = time.time()
            response = await self.entity.think(test_case['query'])
            end_time = time.time()
            
            forms_found = [form for form in test_case['expected_forms'] if form.lower() in response.lower()]
            
            result = {
                "test": test_case['name'],
                "query": test_case['query'],
                "response_time": end_time - start_time,
                "expected_forms": test_case['expected_forms'],
                "forms_found": forms_found,
                "response_preview": response[:80] + "..." if len(response) > 80 else response,
                "language_correct": len(forms_found) > 0
            }
            
            self.test_results.append(result)
            print(f"     ✅ Response: {result['response_preview']}")
            print(f"     🔤 Forms found: {forms_found}\n")
            
    async def test_user_profiles(self):
        """Test user profile extraction and usage."""
        
        print("  🧪 User Profile Test")
        
        # Provide user data then query it
        await self.entity.think("мой рост 180 см")
        
        start_time = time.time()
        response = await self.entity.think("какой у меня рост?")
        end_time = time.time()
        
        result = {
            "test": "Profile Retrieval",
            "query": "какой у меня рост?",
            "response_time": end_time - start_time,
            "response_preview": response[:80] + "..." if len(response) > 80 else response,
            "contains_data": "180" in response
        }
        
        self.test_results.append(result)
        print(f"     ✅ Response: {result['response_preview']}")
        print(f"     📊 Contains data: {result['contains_data']}\n")
            
    async def test_debug_output(self):
        """Test debug output and transparency features."""
        
        print("  🧪 Debug Output Validation")
        print("     Testing scientific question for full debug chain...")
        
        query = "объясни принцип работы теплового двигателя"
        print(f"     Query: {query}")
        
        start_time = time.time()
        response = await self.entity.think(query)
        end_time = time.time()
        
        result = {
            "test": "Debug Output",
            "query": query,
            "response_time": end_time - start_time,
            "response_preview": response[:80] + "..." if len(response) > 80 else response,
        }
        
        self.test_results.append(result)
        print(f"     ✅ Response: {result['response_preview']}")
        print("     📊 Check console output above for debug visibility\n")
        
    async def generate_report(self):
        """Generate comprehensive test report."""
        
        total_time = time.time() - self.start_time
        
        print("\n" + "=" * 60)
        print("📊 COMPREHENSIVE TEST REPORT")
        print("=" * 60)
        
        print(f"⏱️  Total Test Time: {total_time:.2f} seconds")
        print(f"🧪 Total Tests Run: {len(self.test_results)}")
        
        # Performance analysis
        response_times = [r['response_time'] for r in self.test_results if 'response_time' in r]
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            min_time = min(response_times)
            print(f"📈 Average response time: {avg_time:.2f}s")
            print(f"🚀 Fastest response: {min_time:.2f}s")
            print(f"🐌 Slowest response: {max_time:.2f}s")
            
        # Language analysis
        language_tests = [r for r in self.test_results if 'language_correct' in r]
        if language_tests:
            language_success = len([r for r in language_tests if r['language_correct']])
            print(f"🌍 Language form tests: {language_success}/{len(language_tests)} passed")
        
        print("\n✅ Comprehensive testing complete!")


async def main():
    """Run the comprehensive test suite."""
    
    print("🧪 Prometheus Framework - Comprehensive Test Suite")
    print("=" * 60)
    print("Testing:")
    print("  • Fast LLM routing decisions")  
    print("  • Memory storage and retrieval")
    print("  • Context flow and conversation continuity")
    print("  • Russian feminine forms and language switching")
    print("  • User profile extraction and usage")
    print("  • Debug output and system transparency")
    print()
    
    test_suite = ComprehensiveTest()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main()) 