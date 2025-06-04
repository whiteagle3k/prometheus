#!/usr/bin/env python3
"""
Comprehensive Self-RAG Enhancement Tests

Tests the new Self-RAG capabilities:
- Memory Critic functionality
- Enhanced Reflection system
- Context Retrieval Optimization
- Response Quality Assessment
"""

import asyncio
import time
import json
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.memory.memory_critic import MemoryCritic, MemoryQualityScore
from core.reflection.self_rag_reflection import SelfRAGReflection, ResponseQualityAssessment
from core.context.retrieval_optimizer import RetrievalOptimizer, ContextItem, RetrievalStrategy
from core.memory.vector_store import VectorStore


class SelfRAGTestSuite:
    """Comprehensive test suite for Self-RAG enhancements."""
    
    def __init__(self):
        """Initialize test suite."""
        self.test_results = {
            "memory_critic_tests": [],
            "reflection_tests": [],
            "context_optimization_tests": [],
            "integration_tests": [],
            "performance_metrics": {}
        }
        
        # Test identity configuration
        self.test_identity = {
            "name": "Test Agent",
            "personality": {"summary": "Test agent for Self-RAG validation"},
            "utility_model": {
                "model_path": "models/qwen2.5-3b-instruct-q8_0.gguf",
                "n_gpu_layers": 12,
                "n_ctx": 8192,
                "temperature": 0.3
            }
        }
    
    async def run_all_tests(self):
        """Run all Self-RAG enhancement tests."""
        print("🧪 Starting Self-RAG Enhancement Test Suite")
        print("=" * 60)
        
        start_time = time.time()
        
        # Test 1: Memory Critic Tests
        print("\n📋 Testing Memory Critic...")
        await self.test_memory_critic()
        
        # Test 2: Enhanced Reflection Tests
        print("\n🪞 Testing Enhanced Reflection...")
        await self.test_enhanced_reflection()
        
        # Test 3: Context Optimization Tests
        print("\n🔍 Testing Context Retrieval Optimization...")
        await self.test_context_optimization()
        
        # Test 4: Integration Tests
        print("\n🔗 Testing Integration...")
        await self.test_integration()
        
        # Test 5: Performance Benchmarks
        print("\n⚡ Running Performance Benchmarks...")
        await self.run_performance_benchmarks()
        
        total_time = time.time() - start_time
        self.test_results["performance_metrics"]["total_test_time"] = total_time
        
        # Generate report
        await self.generate_test_report()
        
        print(f"\n✅ Test Suite Complete in {total_time:.2f}s")
    
    async def test_memory_critic(self):
        """Test Memory Critic functionality."""
        try:
            memory_critic = MemoryCritic(identity_config=self.test_identity)
            
            # Test 1: Evaluate individual memory quality
            print("  Testing memory quality evaluation...")
            
            test_memories = [
                {
                    "content": "User asked about quantum mechanics. Explained wave-particle duality and provided examples.",
                    "metadata": {"type": "experience", "timestamp": "2024-01-01T10:00:00Z"}
                },
                {
                    "content": "short unclear note",
                    "metadata": {"type": "note", "timestamp": "2024-01-01T11:00:00Z"}
                },
                {
                    "content": "Comprehensive analysis of machine learning algorithms including detailed comparison of supervised vs unsupervised learning, practical applications in industry, and performance metrics evaluation.",
                    "metadata": {"type": "analysis", "timestamp": "2024-01-01T12:00:00Z"}
                }
            ]
            
            quality_scores = []
            for memory in test_memories:
                score = await memory_critic.evaluate_memory_quality(memory)
                quality_scores.append(score)
                print(f"    Memory quality: {score.overall:.2f} (relevance: {score.relevance:.2f})")
            
            # Test 2: Critique memory set
            print("  Testing memory set critique...")
            critiques = await memory_critic.critique_memory_set(test_memories)
            
            # Validate results
            high_quality_count = sum(1 for c in critiques if c.quality_score.overall >= 0.7)
            low_quality_count = sum(1 for c in critiques if c.quality_score.overall < 0.3)
            
            self.test_results["memory_critic_tests"].append({
                "test": "memory_quality_evaluation",
                "passed": len(quality_scores) == len(test_memories),
                "high_quality_count": high_quality_count,
                "low_quality_count": low_quality_count,
                "average_quality": sum(c.quality_score.overall for c in critiques) / len(critiques)
            })
            
            print(f"    ✅ Memory Critic: {len(critiques)} memories evaluated")
            print(f"    📊 Quality distribution: {high_quality_count} high, {low_quality_count} low")
            
        except Exception as e:
            print(f"    ❌ Memory Critic test failed: {e}")
            self.test_results["memory_critic_tests"].append({
                "test": "memory_quality_evaluation",
                "passed": False,
                "error": str(e)
            })
    
    async def test_enhanced_reflection(self):
        """Test Enhanced Reflection functionality."""
        try:
            enhanced_reflection = SelfRAGReflection(identity_config=self.test_identity)
            
            # Test 1: Response quality assessment
            print("  Testing response quality assessment...")
            
            test_scenarios = [
                {
                    "task": "Explain quantum computing",
                    "response": "Quantum computing leverages quantum mechanical phenomena like superposition and entanglement to process information in ways classical computers cannot. Qubits can exist in multiple states simultaneously, enabling parallel computation.",
                    "context": {"conversation_context": "User asked about quantum computing basics"}
                },
                {
                    "task": "What's the weather like?", 
                    "response": "I don't have access to current weather data.",
                    "context": {"conversation_context": "User asked about weather"}
                },
                {
                    "task": "Analyze market trends",
                    "response": "Market analysis requires comprehensive data on multiple indicators including trading volumes, price movements, economic factors, and sentiment analysis. Without specific market data, I cannot provide detailed analysis.",
                    "context": {"conversation_context": "User requested market analysis"}
                }
            ]
            
            reflection_results = []
            for scenario in test_scenarios:
                reflection = await enhanced_reflection.reflect_on_task(
                    scenario["task"], 
                    scenario["response"], 
                    scenario["context"]
                )
                reflection_results.append(reflection)
                
                if reflection:
                    quality = reflection.get("response_quality")
                    print(f"    Response quality: {quality.overall:.2f} (confidence: {quality.confidence})")
            
            # Test 2: Reflection triggering
            print("  Testing reflection triggering...")
            should_reflect_low = await enhanced_reflection.should_reflect(0.2)
            should_reflect_high = await enhanced_reflection.should_reflect(0.8)
            
            self.test_results["reflection_tests"].append({
                "test": "enhanced_reflection",
                "passed": len(reflection_results) == len(test_scenarios),
                "avg_quality": sum(r["response_quality"].overall for r in reflection_results if r) / len([r for r in reflection_results if r]),
                "reflection_triggers": {
                    "low_complexity": should_reflect_low,
                    "high_complexity": should_reflect_high
                }
            })
            
            print(f"    ✅ Enhanced Reflection: {len(reflection_results)} assessments completed")
            
        except Exception as e:
            print(f"    ❌ Enhanced Reflection test failed: {e}")
            self.test_results["reflection_tests"].append({
                "test": "enhanced_reflection",
                "passed": False,
                "error": str(e)
            })
    
    async def test_context_optimization(self):
        """Test Context Retrieval Optimization."""
        try:
            retrieval_optimizer = RetrievalOptimizer(identity_config=self.test_identity)
            
            # Test 1: Context relevance assessment
            print("  Testing context relevance assessment...")
            
            query = "How does machine learning work?"
            raw_contexts = [
                {
                    "content": "Machine learning is a subset of AI that uses algorithms to learn patterns from data",
                    "source": "memory",
                    "metadata": {"type": "definition"}
                },
                {
                    "content": "Today is a sunny day and I went for a walk",
                    "source": "conversation", 
                    "metadata": {"type": "personal"}
                },
                {
                    "content": "Neural networks are a popular machine learning technique inspired by biological neural networks",
                    "source": "memory",
                    "metadata": {"type": "technical"}
                },
                {
                    "content": "I like pizza and ice cream",
                    "source": "conversation",
                    "metadata": {"type": "preference"}
                }
            ]
            
            # Test optimization with default strategy
            optimized_contexts = await retrieval_optimizer.optimize_context_retrieval(
                query, raw_contexts
            )
            
            # Test with custom strategy
            custom_strategy = RetrievalStrategy(
                max_items=3,
                relevance_threshold=0.4,
                importance_threshold=0.3,
                diversity_bonus=0.2
            )
            
            optimized_custom = await retrieval_optimizer.optimize_context_retrieval(
                query, raw_contexts, custom_strategy
            )
            
            # Test smart context selection
            print("  Testing smart context selection...")
            conversation_history = [
                "User: I'm interested in AI",
                "Assistant: AI is a fascinating field with many applications",
                "User: How does machine learning work?",
            ]
            
            memory_items = [
                {"content": "Machine learning fundamentals", "metadata": {"timestamp": "2024-01-01T10:00:00Z"}},
                {"content": "Deep learning architectures", "metadata": {"timestamp": "2024-01-01T11:00:00Z"}}
            ]
            
            smart_selection = await retrieval_optimizer.smart_context_selection(
                query, conversation_history, memory_items, max_context_length=1000
            )
            
            self.test_results["context_optimization_tests"].append({
                "test": "context_optimization",
                "passed": True,
                "default_strategy_items": len(optimized_contexts),
                "custom_strategy_items": len(optimized_custom),
                "smart_selection_length": smart_selection["context_length"],
                "optimization_stats": retrieval_optimizer.get_optimization_stats()
            })
            
            print(f"    ✅ Context Optimization: {len(raw_contexts)} → {len(optimized_contexts)} items")
            print(f"    📊 Smart selection: {smart_selection['context_length']} chars, {smart_selection['context_items_used']} items")
            
        except Exception as e:
            print(f"    ❌ Context Optimization test failed: {e}")
            self.test_results["context_optimization_tests"].append({
                "test": "context_optimization", 
                "passed": False,
                "error": str(e)
            })
    
    async def test_integration(self):
        """Test integration of all Self-RAG components."""
        try:
            print("  Testing component integration...")
            
            # Initialize all components
            memory_critic = MemoryCritic(identity_config=self.test_identity)
            enhanced_reflection = SelfRAGReflection(identity_config=self.test_identity) 
            retrieval_optimizer = RetrievalOptimizer(identity_config=self.test_identity)
            
            # Simulate an end-to-end workflow
            query = "Explain the relationship between AI and machine learning"
            
            # Step 1: Optimize context
            raw_contexts = [
                {"content": "AI is the broader field encompassing machine learning", "source": "memory"},
                {"content": "Machine learning is a subset of artificial intelligence", "source": "memory"},
                {"content": "Random unrelated content about cooking", "source": "conversation"}
            ]
            
            optimized_contexts = await retrieval_optimizer.optimize_context_retrieval(query, raw_contexts)
            
            # Step 2: Generate response (simulated)
            response = "AI (Artificial Intelligence) is the broader field that encompasses machine learning. Machine learning is a specific subset of AI that focuses on algorithms that can learn from data."
            
            # Step 3: Assess quality with enhanced reflection
            context = {"conversation_context": "User asked about AI vs ML"}
            reflection_result = await enhanced_reflection.reflect_on_task(query, response, context)
            
            # Step 4: Create test memories and critique them
            test_memories = [
                {"content": f"Query: {query}", "metadata": {"type": "interaction"}},
                {"content": f"Response: {response}", "metadata": {"type": "response"}}
            ]
            
            memory_critiques = await memory_critic.critique_memory_set(test_memories)
            
            # Validate integration
            integration_success = (
                len(optimized_contexts) > 0 and
                reflection_result is not None and
                len(memory_critiques) == len(test_memories)
            )
            
            self.test_results["integration_tests"].append({
                "test": "end_to_end_integration",
                "passed": integration_success,
                "optimized_context_count": len(optimized_contexts),
                "reflection_quality": reflection_result["response_quality"].overall if reflection_result else 0,
                "memory_critique_count": len(memory_critiques)
            })
            
            print(f"    ✅ Integration test: {len(optimized_contexts)} contexts, quality {reflection_result['response_quality'].overall:.2f}")
            
        except Exception as e:
            print(f"    ❌ Integration test failed: {e}")
            self.test_results["integration_tests"].append({
                "test": "end_to_end_integration",
                "passed": False,
                "error": str(e)
            })
    
    async def run_performance_benchmarks(self):
        """Run performance benchmarks for Self-RAG components."""
        try:
            print("  Running performance benchmarks...")
            
            # Initialize components
            memory_critic = MemoryCritic(identity_config=self.test_identity)
            enhanced_reflection = SelfRAGReflection(identity_config=self.test_identity)
            retrieval_optimizer = RetrievalOptimizer(identity_config=self.test_identity)
            
            # Benchmark 1: Memory evaluation speed
            start_time = time.time()
            test_memory = {
                "content": "Test memory for performance evaluation",
                "metadata": {"type": "test"}
            }
            
            for _ in range(5):
                await memory_critic.evaluate_memory_quality(test_memory)
            
            memory_eval_time = (time.time() - start_time) / 5
            
            # Benchmark 2: Reflection speed
            start_time = time.time()
            
            for _ in range(5):
                await enhanced_reflection.reflect_on_task(
                    "Test task", 
                    "Test response", 
                    {"context": "test"}
                )
            
            reflection_time = (time.time() - start_time) / 5
            
            # Benchmark 3: Context optimization speed
            start_time = time.time()
            
            test_contexts = [
                {"content": f"Test context {i}", "source": "test"} 
                for i in range(10)
            ]
            
            for _ in range(3):
                await retrieval_optimizer.optimize_context_retrieval("test query", test_contexts)
            
            optimization_time = (time.time() - start_time) / 3
            
            self.test_results["performance_metrics"].update({
                "memory_evaluation_time": memory_eval_time,
                "reflection_time": reflection_time,
                "context_optimization_time": optimization_time,
                "total_component_time": memory_eval_time + reflection_time + optimization_time
            })
            
            print(f"    ⚡ Memory evaluation: {memory_eval_time:.2f}s avg")
            print(f"    ⚡ Reflection: {reflection_time:.2f}s avg")
            print(f"    ⚡ Context optimization: {optimization_time:.2f}s avg")
            
        except Exception as e:
            print(f"    ❌ Performance benchmark failed: {e}")
            self.test_results["performance_metrics"]["error"] = str(e)
    
    async def generate_test_report(self):
        """Generate comprehensive test report."""
        print("\n📊 Self-RAG Enhancement Test Report")
        print("=" * 60)
        
        # Calculate overall statistics
        total_tests = 0
        passed_tests = 0
        
        for category, tests in self.test_results.items():
            if category != "performance_metrics" and isinstance(tests, list):
                total_tests += len(tests)
                passed_tests += sum(1 for test in tests if test.get("passed", False))
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"Overall Success Rate: {success_rate:.1f}% ({passed_tests}/{total_tests})")
        print(f"Total Test Time: {self.test_results['performance_metrics'].get('total_test_time', 0):.2f}s")
        
        # Detailed results
        print("\n📋 Memory Critic Tests:")
        for test in self.test_results["memory_critic_tests"]:
            status = "✅" if test.get("passed") else "❌"
            print(f"  {status} {test.get('test', 'Unknown test')}")
            if test.get("average_quality"):
                print(f"      Average Quality: {test['average_quality']:.2f}")
        
        print("\n🪞 Enhanced Reflection Tests:")
        for test in self.test_results["reflection_tests"]:
            status = "✅" if test.get("passed") else "❌"
            print(f"  {status} {test.get('test', 'Unknown test')}")
            if test.get("avg_quality"):
                print(f"      Average Quality: {test['avg_quality']:.2f}")
        
        print("\n🔍 Context Optimization Tests:")
        for test in self.test_results["context_optimization_tests"]:
            status = "✅" if test.get("passed") else "❌"
            print(f"  {status} {test.get('test', 'Unknown test')}")
            if test.get("optimization_stats"):
                stats = test["optimization_stats"]
                print(f"      Contexts Evaluated: {stats.get('contexts_evaluated', 0)}")
                print(f"      Contexts Filtered: {stats.get('contexts_filtered', 0)}")
        
        print("\n🔗 Integration Tests:")
        for test in self.test_results["integration_tests"]:
            status = "✅" if test.get("passed") else "❌"
            print(f"  {status} {test.get('test', 'Unknown test')}")
        
        print("\n⚡ Performance Metrics:")
        metrics = self.test_results["performance_metrics"]
        for metric, value in metrics.items():
            if isinstance(value, (int, float)):
                print(f"  {metric}: {value:.3f}s")
        
        # Save detailed results to file
        output_file = Path("test_results_self_rag.json")
        with open(output_file, 'w') as f:
            json.dump(self.test_results, f, indent=2, default=str)
        
        print(f"\n💾 Detailed results saved to: {output_file}")
        
        # Recommendations
        print("\n💡 Recommendations:")
        if success_rate >= 90:
            print("  🎉 Excellent! Self-RAG enhancements are working well.")
        elif success_rate >= 70:
            print("  👍 Good performance with room for improvement.")
        else:
            print("  ⚠️ Several issues detected. Review failed tests.")
        
        # Performance recommendations
        total_time = metrics.get("total_component_time", 0)
        if total_time > 10:
            print("  ⚡ Consider optimizing component performance for production use.")
        elif total_time < 3:
            print("  ⚡ Excellent performance! Components are well optimized.")


async def main():
    """Run the Self-RAG enhancement test suite."""
    test_suite = SelfRAGTestSuite()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main()) 