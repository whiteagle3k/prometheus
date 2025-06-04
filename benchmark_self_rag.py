#!/usr/bin/env python3
"""
Self-RAG Enhancement Benchmark

Compares the original Aletheia with the Self-RAG enhanced version
across multiple dimensions: response quality, memory efficiency, 
context optimization, and performance.
"""

import asyncio
import time
import json
from pathlib import Path
import sys
from typing import Dict, List, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from entities.aletheia import AletheiaEntity
from entities.aletheia_enhanced import EnhancedAletheiaEntity


class SelfRAGBenchmark:
    """Benchmark suite for comparing original vs enhanced Aletheia."""
    
    def __init__(self):
        """Initialize benchmark suite."""
        self.benchmark_queries = [
            {
                "query": "Как работает квантовая физика?",
                "complexity": 0.8,
                "category": "scientific",
                "expected_language": "ru"
            },
            {
                "query": "What are the key differences between machine learning and deep learning?",
                "complexity": 0.6,
                "category": "technical",
                "expected_language": "en"
            },
            {
                "query": "Объясни принципы работы нейронных сетей простым языком",
                "complexity": 0.7,
                "category": "educational",
                "expected_language": "ru"
            },
            {
                "query": "How can we improve renewable energy efficiency?",
                "complexity": 0.5,
                "category": "environmental",
                "expected_language": "en"
            },
            {
                "query": "Что такое искусственный интеллект и как он влияет на общество?",
                "complexity": 0.9,
                "category": "social",
                "expected_language": "ru"
            }
        ]
        
        self.results = {
            "original_aletheia": [],
            "enhanced_aletheia": [],
            "comparison_metrics": {},
            "performance_comparison": {}
        }
    
    async def run_benchmark(self):
        """Run comprehensive benchmark comparison."""
        print("🏁 Starting Self-RAG Enhancement Benchmark")
        print("=" * 60)
        
        # Initialize entities
        print("🔧 Initializing entities...")
        original_aletheia = AletheiaEntity()
        enhanced_aletheia = EnhancedAletheiaEntity()
        
        print("✅ Entities initialized")
        
        # Run benchmark queries on both entities
        print("\n📊 Running benchmark queries...")
        
        for i, query_data in enumerate(self.benchmark_queries):
            print(f"\n--- Query {i+1}/{len(self.benchmark_queries)}: {query_data['category']} ---")
            print(f"Query: {query_data['query'][:50]}{'...' if len(query_data['query']) > 50 else ''}")
            
            # Test original Aletheia
            print("  Testing original Aletheia...")
            original_result = await self._test_entity(original_aletheia, query_data, "original")
            self.results["original_aletheia"].append(original_result)
            
            # Test enhanced Aletheia
            print("  Testing enhanced Aletheia...")
            enhanced_result = await self._test_entity(enhanced_aletheia, query_data, "enhanced")
            self.results["enhanced_aletheia"].append(enhanced_result)
            
            # Compare results
            await self._compare_query_results(original_result, enhanced_result, query_data)
        
        # Generate comprehensive comparison
        await self._generate_comparison_report()
        
        print("\n🏆 Benchmark Complete!")
    
    async def _test_entity(self, entity, query_data: Dict[str, Any], entity_type: str) -> Dict[str, Any]:
        """Test a single entity with a query."""
        query = query_data["query"]
        start_time = time.time()
        
        try:
            # Process query
            if entity_type == "enhanced":
                # Enhanced entity has process_query method
                context = {
                    "conversation_context": "Benchmark test query",
                    "enable_optimization": True
                }
                response_data = await entity.process_query(query, context)
                response = response_data.get("response", "")
                
                # Extract additional metrics from enhanced entity
                result = {
                    "query": query,
                    "response": response,
                    "processing_time": time.time() - start_time,
                    "response_length": len(response),
                    "entity_type": entity_type,
                    "query_metadata": query_data,
                    "llm_used": "unknown",  # Would need to extract from response_data
                    "route_decision": "unknown",
                    "performance_metrics": {},
                    "routing_stats": {},
                    "success": True,
                    "quality_assessment": response_data.get("quality_assessment", {}),
                    "enhancement_stats": response_data.get("enhancement_stats", {}),
                    "optimization_metadata": context.get("optimization_metadata", {})
                }
            else:
                # Original entity uses think method
                response = await entity.think(query)
                
                result = {
                    "query": query,
                    "response": response,
                    "processing_time": time.time() - start_time,
                    "response_length": len(response),
                    "entity_type": entity_type,
                    "query_metadata": query_data,
                    "llm_used": "unknown",  # Would need to extract from entity state
                    "route_decision": "unknown",
                    "performance_metrics": {},
                    "routing_stats": {},
                    "success": True
                }
            
            # Validate response quality for both
            result["response_quality"] = await self._assess_response_quality(query, response, query_data)
            
            print(f"    ✅ {entity_type}: {result['processing_time']:.2f}s, {len(response)} chars")
            
            return result
            
        except Exception as e:
            print(f"    ❌ {entity_type} failed: {e}")
            return {
                "query": query,
                "response": "",
                "processing_time": 0,
                "entity_type": entity_type,
                "query_metadata": query_data,
                "success": False,
                "error": str(e)
            }
    
    async def _assess_response_quality(self, query: str, response: str, query_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess response quality using multiple criteria."""
        quality_metrics = {
            "completeness": 0.5,
            "relevance": 0.5,
            "language_correctness": 0.5,
            "technical_accuracy": 0.5,
            "overall": 0.5
        }
        
        # Basic quality checks
        if not response or len(response) < 50:
            quality_metrics["completeness"] = 0.2
        elif len(response) > 200:
            quality_metrics["completeness"] = 0.8
        
        # Language check
        expected_language = query_data.get("expected_language", "en")
        if expected_language == "ru":
            # Check for Cyrillic characters
            has_cyrillic = any('\u0400' <= char <= '\u04FF' for char in response)
            quality_metrics["language_correctness"] = 0.8 if has_cyrillic else 0.3
        else:
            # Check for English
            has_latin = any('a' <= char <= 'z' or 'A' <= char <= 'Z' for char in response)
            quality_metrics["language_correctness"] = 0.8 if has_latin else 0.3
        
        # Relevance check (basic keyword matching)
        query_words = set(query.lower().split())
        response_words = set(response.lower().split())
        overlap = len(query_words & response_words) / len(query_words) if query_words else 0
        quality_metrics["relevance"] = min(overlap * 2, 1.0)  # Scale up overlap
        
        # Technical accuracy (category-specific)
        category = query_data.get("category", "general")
        if category in ["scientific", "technical"]:
            # Look for technical terms
            technical_terms = ["algorithm", "data", "model", "system", "process", "theory", 
                             "analysis", "method", "principle", "technology", "алгоритм", 
                             "данные", "модель", "система", "процесс", "теория", "анализ"]
            
            response_lower = response.lower()
            found_terms = sum(1 for term in technical_terms if term in response_lower)
            quality_metrics["technical_accuracy"] = min(found_terms * 0.2, 1.0)
        else:
            quality_metrics["technical_accuracy"] = 0.7  # Neutral for non-technical
        
        # Calculate overall quality
        quality_metrics["overall"] = sum(quality_metrics.values()) / len(quality_metrics)
        
        return quality_metrics
    
    async def _compare_query_results(self, original_result: Dict[str, Any], 
                                   enhanced_result: Dict[str, Any], 
                                   query_data: Dict[str, Any]):
        """Compare results from original vs enhanced entity for a single query."""
        if not original_result.get("success") or not enhanced_result.get("success"):
            return
        
        # Performance comparison
        time_diff = enhanced_result["processing_time"] - original_result["processing_time"]
        time_improvement = -time_diff / original_result["processing_time"] * 100 if original_result["processing_time"] > 0 else 0
        
        # Quality comparison
        original_quality = original_result["response_quality"]["overall"]
        enhanced_quality = enhanced_result["response_quality"]["overall"]
        quality_improvement = (enhanced_quality - original_quality) / original_quality * 100 if original_quality > 0 else 0
        
        # Length comparison
        length_diff = enhanced_result["response_length"] - original_result["response_length"]
        
        comparison = {
            "query_category": query_data["category"],
            "performance": {
                "time_difference": time_diff,
                "time_improvement_percent": time_improvement,
                "original_time": original_result["processing_time"],
                "enhanced_time": enhanced_result["processing_time"]
            },
            "quality": {
                "original_quality": original_quality,
                "enhanced_quality": enhanced_quality,
                "quality_improvement_percent": quality_improvement
            },
            "response_metrics": {
                "original_length": original_result["response_length"],
                "enhanced_length": enhanced_result["response_length"],
                "length_difference": length_diff
            }
        }
        
        # Enhanced-specific improvements
        if enhanced_result.get("enhancement_stats"):
            comparison["enhancements"] = {
                "context_optimization": enhanced_result["enhancement_stats"].get("context_optimizations", 0) > 0,
                "quality_assessment": enhanced_result["enhancement_stats"].get("quality_assessments", 0) > 0,
                "enhanced_reflection": enhanced_result["enhancement_stats"].get("enhanced_reflections", 0) > 0
            }
        
        print(f"    📈 Quality: {quality_improvement:+.1f}%, Time: {time_improvement:+.1f}%")
        
        # Store comparison
        if "query_comparisons" not in self.results["comparison_metrics"]:
            self.results["comparison_metrics"]["query_comparisons"] = []
        
        self.results["comparison_metrics"]["query_comparisons"].append(comparison)
    
    async def _generate_comparison_report(self):
        """Generate comprehensive comparison report."""
        print("\n📊 Self-RAG Enhancement Comparison Report")
        print("=" * 60)
        
        # Calculate aggregate metrics
        comparisons = self.results["comparison_metrics"].get("query_comparisons", [])
        
        if not comparisons:
            print("❌ No valid comparisons to analyze")
            return
        
        # Performance metrics
        avg_time_improvement = sum(c["performance"]["time_improvement_percent"] for c in comparisons) / len(comparisons)
        avg_quality_improvement = sum(c["quality"]["quality_improvement_percent"] for c in comparisons) / len(comparisons)
        
        # Success rates
        original_successes = sum(1 for r in self.results["original_aletheia"] if r.get("success"))
        enhanced_successes = sum(1 for r in self.results["enhanced_aletheia"] if r.get("success"))
        total_queries = len(self.benchmark_queries)
        
        original_success_rate = original_successes / total_queries * 100
        enhanced_success_rate = enhanced_successes / total_queries * 100
        
        # Quality analysis
        original_qualities = [r["response_quality"]["overall"] for r in self.results["original_aletheia"] if r.get("success")]
        enhanced_qualities = [r["response_quality"]["overall"] for r in self.results["enhanced_aletheia"] if r.get("success")]
        
        original_avg_quality = sum(original_qualities) / len(original_qualities) if original_qualities else 0
        enhanced_avg_quality = sum(enhanced_qualities) / len(enhanced_qualities) if enhanced_qualities else 0
        
        # Performance analysis
        original_times = [r["processing_time"] for r in self.results["original_aletheia"] if r.get("success")]
        enhanced_times = [r["processing_time"] for r in self.results["enhanced_aletheia"] if r.get("success")]
        
        original_avg_time = sum(original_times) / len(original_times) if original_times else 0
        enhanced_avg_time = sum(enhanced_times) / len(enhanced_times) if enhanced_times else 0
        
        # Generate report
        print(f"📈 Overall Performance Summary:")
        print(f"  Success Rate: Original {original_success_rate:.1f}% → Enhanced {enhanced_success_rate:.1f}%")
        print(f"  Average Quality: {original_avg_quality:.3f} → {enhanced_avg_quality:.3f} ({avg_quality_improvement:+.1f}%)")
        print(f"  Average Time: {original_avg_time:.2f}s → {enhanced_avg_time:.2f}s ({avg_time_improvement:+.1f}%)")
        
        print(f"\n🔍 Detailed Analysis:")
        
        # Quality breakdown
        quality_improvements = [c["quality"]["quality_improvement_percent"] for c in comparisons]
        quality_wins = sum(1 for q in quality_improvements if q > 0)
        print(f"  Quality Improvements: {quality_wins}/{len(comparisons)} queries improved")
        
        # Performance breakdown
        time_improvements = [c["performance"]["time_improvement_percent"] for c in comparisons]
        time_wins = sum(1 for t in time_improvements if t > 0)
        print(f"  Performance Improvements: {time_wins}/{len(comparisons)} queries faster")
        
        # Category analysis
        categories = {}
        for comparison in comparisons:
            category = comparison["query_category"]
            if category not in categories:
                categories[category] = {"quality_improvements": [], "time_improvements": []}
            
            categories[category]["quality_improvements"].append(comparison["quality"]["quality_improvement_percent"])
            categories[category]["time_improvements"].append(comparison["performance"]["time_improvement_percent"])
        
        print(f"\n📋 Category Breakdown:")
        for category, metrics in categories.items():
            avg_quality_imp = sum(metrics["quality_improvements"]) / len(metrics["quality_improvements"])
            avg_time_imp = sum(metrics["time_improvements"]) / len(metrics["time_improvements"])
            print(f"  {category.title()}: Quality {avg_quality_imp:+.1f}%, Time {avg_time_imp:+.1f}%")
        
        # Enhancement features analysis
        print(f"\n🧠 Self-RAG Feature Utilization:")
        enhanced_results = [r for r in self.results["enhanced_aletheia"] if r.get("success")]
        
        context_optimizations = sum(r.get("enhancement_stats", {}).get("context_optimizations", 0) for r in enhanced_results)
        quality_assessments = sum(r.get("enhancement_stats", {}).get("quality_assessments", 0) for r in enhanced_results)
        enhanced_reflections = sum(r.get("enhancement_stats", {}).get("enhanced_reflections", 0) for r in enhanced_results)
        
        print(f"  Context Optimizations: {context_optimizations}")
        print(f"  Quality Assessments: {quality_assessments}")
        print(f"  Enhanced Reflections: {enhanced_reflections}")
        
        # LLM routing analysis
        print(f"\n🎯 LLM Routing Analysis:")
        
        original_routes = {}
        enhanced_routes = {}
        
        for result in self.results["original_aletheia"]:
            if result.get("success"):
                route = result.get("llm_used", "unknown")
                original_routes[route] = original_routes.get(route, 0) + 1
        
        for result in self.results["enhanced_aletheia"]:
            if result.get("success"):
                route = result.get("llm_used", "unknown")
                enhanced_routes[route] = enhanced_routes.get(route, 0) + 1
        
        print(f"  Original routing: {original_routes}")
        print(f"  Enhanced routing: {enhanced_routes}")
        
        # Overall assessment
        print(f"\n🎯 Overall Assessment:")
        
        if enhanced_avg_quality > original_avg_quality and enhanced_success_rate >= original_success_rate:
            if enhanced_avg_time <= original_avg_time * 1.2:  # Allow 20% time increase for quality gains
                print("  🎉 EXCELLENT: Enhanced version shows significant improvements!")
            else:
                print("  👍 GOOD: Enhanced version improves quality but at time cost")
        elif enhanced_avg_quality > original_avg_quality * 0.95:  # Within 5% quality
            if enhanced_avg_time < original_avg_time:
                print("  👍 GOOD: Enhanced version maintains quality with better performance")
            else:
                print("  ⚖️ MIXED: Trade-offs between quality and performance")
        else:
            print("  ⚠️ NEEDS WORK: Enhanced version may need optimization")
        
        # Recommendations
        print(f"\n💡 Recommendations:")
        
        if avg_quality_improvement > 10:
            print("  ✅ Quality improvements are significant - Self-RAG enhancements are effective")
        elif avg_quality_improvement > 0:
            print("  📈 Modest quality improvements - consider tuning Self-RAG parameters")
        else:
            print("  🔧 Quality regression detected - review Self-RAG implementation")
        
        if avg_time_improvement > 10:
            print("  ⚠️ Performance regression - optimize Self-RAG components")
        elif abs(avg_time_improvement) < 5:
            print("  ⚖️ Performance impact minimal - good balance")
        else:
            print("  ⚡ Performance improvement achieved")
        
        # Save detailed results
        output_file = Path("benchmark_results_self_rag.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n💾 Detailed results saved to: {output_file}")


async def main():
    """Run the Self-RAG enhancement benchmark."""
    benchmark = SelfRAGBenchmark()
    await benchmark.run_benchmark()


if __name__ == "__main__":
    asyncio.run(main()) 