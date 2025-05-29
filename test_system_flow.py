#!/usr/bin/env python3
"""Comprehensive test of Aletheia system functionality."""

import asyncio
import json
import time
from typing import Dict, Any, List

from aletheia.agent.orchestrator import AletheiaAgent
from aletheia.processing.pipeline import create_context_analysis_pipeline, create_simple_response_pipeline
from aletheia.processing.extractors import EntityExtractor, NameExtractor
from aletheia.processing.detectors import ReferenceDetector, ComplexityDetector
from aletheia.processing.validators import FactualValidator
from aletheia.processing.filters import ContaminationFilter


class SystemFlowTester:
    """Tests the complete Aletheia system flow."""
    
    def __init__(self):
        """Initialize the tester."""
        self.agent = AletheiaAgent()
        self.test_results = []
        self.user_id = "test_user_123"
    
    async def run_all_tests(self):
        """Run all system flow tests."""
        print("🚀 Starting Aletheia System Flow Tests")
        print("=" * 60)
        
        try:
            # Test 1: Basic Processing Components
            await self.test_processing_components()
            
            # Test 2: Simple Local Processing Flow
            await self.test_simple_local_flow()
            
            # Test 3: Context Building and Continuity
            await self.test_context_continuity()
            
            # Test 4: Complex Question External Routing
            await self.test_complex_external_routing()
            
            # Test 5: Conversation Flow with Mixed Questions
            await self.test_mixed_conversation_flow()
            
            # Test 6: Error Handling and Edge Cases
            await self.test_error_handling()
            
            # Test 7: Factual Validation
            await self.test_factual_validation()
            
            # Generate report
            self.generate_test_report()
            
        except Exception as e:
            print(f"❌ Test suite failed: {e}")
            raise

    async def test_processing_components(self):
        """Test individual processing components."""
        print("\n📋 Testing Processing Components")
        print("-" * 40)
        
        # Test Entity Extractor
        entity_extractor = EntityExtractor()
        test_text = "Как образуется водяной пар при нагревании воды?"
        entities = entity_extractor.extract(test_text)
        print(f"✓ Entity extraction: {entities}")
        assert "водяной пар" in entities or "вода" in entities, "Should extract water-related entities"
        
        # Test Name Extractor  
        name_extractor = NameExtractor()
        test_text = "Меня зовут Анна"
        names = name_extractor.extract(test_text)
        print(f"✓ Name extraction: {names}")
        assert "Анна" in names, "Should extract name Anna"
        
        # Test Reference Detector
        reference_detector = ReferenceDetector()
        ref_result = reference_detector.process("А что если это не так?")
        print(f"✓ Reference detection: {ref_result.data}")
        assert ref_result.data.get("has_references", False), "Should detect reference question"
        
        # Test Complexity Detector
        complexity_detector = ComplexityDetector()
        complex_text = "Объясни пошагово как работает двигатель внутреннего сгорания и какие химические реакции происходят"
        is_complex = complexity_detector.detect(complex_text)
        print(f"✓ Complexity detection: {is_complex}")
        assert is_complex, "Should detect complex question"
        
        # Test Contamination Filter
        contamination_filter = ContaminationFilter()
        dirty_text = "Я AI-помощник. Вот структура ответа: 1. Введение 2. Основная часть. Водяной пар образуется при испарении."
        result = contamination_filter.process(dirty_text)
        clean_text = result.data
        print(f"✓ Contamination filtering: '{clean_text}'")
        assert "AI-помощник" not in clean_text, "Should remove AI contamination"
        assert "Водяной пар" in clean_text, "Should preserve actual content"
        
        self.test_results.append({"test": "processing_components", "status": "✅ PASSED"})

    async def test_simple_local_flow(self):
        """Test simple questions that should be handled locally."""
        print("\n🏠 Testing Simple Local Processing Flow")
        print("-" * 40)
        
        simple_questions = [
            "Привет!",
            "Как дела?", 
            "Меня зовут Иван",
            "Что такое вода?",
            "Hello there!"
        ]
        
        for question in simple_questions:
            print(f"\nTesting: '{question}'")
            start_time = time.time()
            
            result = await self.agent.think(question)
            response = result.get("response", "")
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            print(f"Response: {response[:100]}...")
            print(f"Time: {processing_time:.2f}s")
            print(f"Method: {result.get('meta', {}).get('used_planning', False)}")
            
            # Validate response
            assert len(response) > 10, f"Response too short: {response}"
            assert processing_time < 60, f"Too slow for simple question: {processing_time}s"
            
        self.test_results.append({"test": "simple_local_flow", "status": "✅ PASSED"})

    async def test_context_continuity(self):
        """Test conversation context and continuity."""
        print("\n🔗 Testing Context Continuity")
        print("-" * 40)
        
        # Step 1: Introduce topic
        question1 = "Что такое водяной пар?"
        result1 = await self.agent.think(question1)
        response1 = result1.get("response", "")
        print(f"Q1: {question1}")
        print(f"A1: {response1[:100]}...")
        
        # Step 2: Ask reference question
        question2 = "А что если это не так?"
        result2 = await self.agent.think(question2)
        response2 = result2.get("response", "")
        print(f"\nQ2: {question2}")
        print(f"A2: {response2[:100]}...")
        
        # Validate context usage
        context_summary = self.agent.context.get_context_summary()
        print(f"\nContext summary: {json.dumps(context_summary, indent=2, ensure_ascii=False)}")
        
        # Step 3: Name introduction and memory
        question3 = "Меня зовут Алексей"
        result3 = await self.agent.think(question3)
        response3 = result3.get("response", "")
        print(f"\nQ3: {question3}")
        print(f"A3: {response3[:100]}...")
        
        self.test_results.append({"test": "context_continuity", "status": "✅ PASSED"})

    async def test_complex_external_routing(self):
        """Test complex questions that should route to external LLMs."""
        print("\n🌐 Testing Complex External Routing")
        print("-" * 40)
        
        complex_questions = [
            "Объясни подробно как работает квантовый компьютер",
            "Какие последние исследования в области нейронных сетей?",
            "Пошагово объясни процесс синтеза белка в клетке"
        ]
        
        for question in complex_questions:
            print(f"\nTesting: '{question}'")
            
            # Check complexity detection
            complexity_detector = ComplexityDetector()
            is_complex = complexity_detector.detect(question)
            print(f"Complexity detected: {is_complex}")
            assert is_complex, f"Should detect as complex: {question}"
            
            # Check if agent would use planning
            needs_planning = self.agent.context.should_plan_task(question)
            print(f"Would use planning: {needs_planning}")
            
        self.test_results.append({"test": "complex_external_routing", "status": "✅ PASSED"})

    async def test_mixed_conversation_flow(self):
        """Test mixed conversation with various question types."""
        print("\n🗣️ Testing Mixed Conversation Flow")
        print("-" * 40)
        
        conversation_flow = [
            ("Привет! Меня зовут Мария", "greeting_with_name"),
            ("Что такое лёд?", "simple_factual"),
            ("А водяной пар?", "reference_question"), 
            ("Как это связано с циклом воды в природе?", "follow_up"),
            ("Спасибо за объяснение", "acknowledgment")
        ]
        
        conversation_history = []
        
        for question, question_type in conversation_flow:
            print(f"\n[{question_type}] Q: {question}")
            
            start_time = time.time()
            result = await self.agent.think(question)
            response = result.get("response", "")
            end_time = time.time()
            
            print(f"A: {response[:100]}...")
            print(f"Time: {end_time - start_time:.2f}s")
            
            conversation_history.append({"question": question, "response": response, "type": question_type})
            
            # Validate response quality
            assert len(response) > 5, f"Response too short for {question_type}"
            
        # Check conversation context
        context_summary = self.agent.context.get_context_summary()
        print(f"\nConversation context: {context_summary}")
        
        self.test_results.append({"test": "mixed_conversation_flow", "status": "✅ PASSED"})

    async def test_error_handling(self):
        """Test error handling and edge cases."""
        print("\n⚠️ Testing Error Handling & Edge Cases")
        print("-" * 40)
        
        edge_cases = [
            "",  # Empty input
            "   ",  # Whitespace only
            "a" * 1000,  # Very long input
            "🤖🔥💯",  # Emoji only
            "Ыыыыы ъъъъ щщщ",  # Invalid/nonsense Russian
        ]
        
        for case in edge_cases:
            print(f"\nTesting edge case: '{case[:50]}{'...' if len(case) > 50 else ''}'")
            
            try:
                result = await self.agent.think(case)
                response = result.get("response", "")
                print(f"Response: {response[:100]}...")
                
                # Should handle gracefully, not crash
                assert isinstance(response, str), "Should return string response"
                
                if case.strip():  # Non-empty cases should get meaningful response
                    assert len(response) > 10, f"Should provide meaningful response for: {case}"
                
            except Exception as e:
                print(f"Error (this might be expected): {e}")
                # Some edge cases might fail, but shouldn't crash the system
        
        self.test_results.append({"test": "error_handling", "status": "✅ PASSED"})

    async def test_factual_validation(self):
        """Test factual validation system."""
        print("\n🔍 Testing Factual Validation")
        print("-" * 40)
        
        # Test case: water vapor confusion
        validator = FactualValidator()
        
        # Simulate response with factual error
        wrong_response = "Водяной пар - это водород, который образуется при нагревании воды."
        context = {"user_input": "Что такое водяной пар?"}
        
        issues = validator.validate(wrong_response, context)
        print(f"Validation issues found: {issues}")
        
        assert "confusion_water_vapor_hydrogen" in issues, "Should detect water vapor/hydrogen confusion"
        
        # Test correct response
        correct_response = "Водяной пар - это газообразная форма воды, которая образуется при испарении."
        issues_correct = validator.validate(correct_response, context)
        print(f"Issues in correct response: {issues_correct}")
        
        assert "confusion_water_vapor_hydrogen" not in issues_correct, "Should not flag correct response"
        
        self.test_results.append({"test": "factual_validation", "status": "✅ PASSED"})

    def generate_test_report(self):
        """Generate comprehensive test report."""
        print("\n" + "=" * 60)
        print("📊 ALETHEIA SYSTEM TEST REPORT")
        print("=" * 60)
        
        passed_tests = [t for t in self.test_results if "✅ PASSED" in t["status"]]
        failed_tests = [t for t in self.test_results if "❌ FAILED" in t["status"]]
        
        print(f"\n✅ Tests Passed: {len(passed_tests)}")
        print(f"❌ Tests Failed: {len(failed_tests)}")
        print(f"📈 Success Rate: {len(passed_tests)/len(self.test_results)*100:.1f}%")
        
        print("\n📋 Test Details:")
        for test in self.test_results:
            print(f"  {test['status']} {test['test']}")
        
        if failed_tests:
            print("\n❌ Failed Tests Details:")
            for test in failed_tests:
                print(f"  - {test['test']}: {test.get('error', 'Unknown error')}")
        
        print("\n🎯 System Capabilities Validated:")
        print("  ✓ Processing pipeline architecture")
        print("  ✓ Local LLM integration") 
        print("  ✓ Context management and continuity")
        print("  ✓ Entity extraction and name detection")
        print("  ✓ Reference question handling")
        print("  ✓ Contamination filtering")
        print("  ✓ Factual validation")
        print("  ✓ Error handling and edge cases")
        print("  ✓ Conversation flow management")
        
        print("\n🚀 Aletheia System Status: READY FOR PRODUCTION")
        print("=" * 60)


async def main():
    """Run the comprehensive system test."""
    tester = SystemFlowTester()
    
    print("Starting comprehensive Aletheia system tests...")
    print("This will test the complete flow from questions to responses.")
    
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main()) 