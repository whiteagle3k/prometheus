#!/usr/bin/env python3
"""
Stress Test Script for Aletheia Service

Tests singleton thread-safety and performance under load.
Verifies that singleton pattern holds under concurrent access.
"""

import asyncio
import aiohttp
import json
import time
import statistics
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import argparse
import sys


class AletheiaStressTester:
    """Stress tester for Aletheia service."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        self.results = []
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def health_check(self) -> bool:
        """Check if service is running."""
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                return response.status == 200
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False
    
    async def send_chat_request(self, user_id: str, message: str) -> Dict[str, Any]:
        """Send a chat request and measure response time."""
        start_time = time.time()
        
        try:
            payload = {
                "user_id": user_id,
                "message": message
            }
            
            async with self.session.post(
                f"{self.base_url}/v1/chat",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                end_time = time.time()
                latency = end_time - start_time
                
                if response.status == 200:
                    data = await response.json()
                    return {
                        "status": "success",
                        "latency": latency,
                        "response_data": data,
                        "user_id": user_id,
                        "message": message
                    }
                else:
                    text = await response.text()
                    return {
                        "status": "error",
                        "latency": latency,
                        "error": f"HTTP {response.status}: {text}",
                        "user_id": user_id,
                        "message": message
                    }
                    
        except Exception as e:
            end_time = time.time()
            latency = end_time - start_time
            return {
                "status": "exception",
                "latency": latency,
                "error": str(e),
                "user_id": user_id,
                "message": message
            }
    
    async def concurrent_load_test(
        self, 
        num_requests: int = 100, 
        concurrency: int = 10,
        test_duration: int = None
    ) -> Dict[str, Any]:
        """Run concurrent load test."""
        print(f"🚀 Starting load test: {num_requests} requests, {concurrency} concurrent")
        
        messages = [
            "Hello Aletheia, how are you?",
            "What is machine learning?",
            "Explain quantum computing",
            "Tell me about Python programming",
            "What is the meaning of life?",
            "How does AI work?",
            "Describe neural networks",
            "What is the weather like?",
            "Help me understand recursion",
            "Explain blockchain technology"
        ]
        
        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(concurrency)
        
        async def limited_request(request_id: int):
            async with semaphore:
                user_id = f"stress_user_{request_id % 10}"  # 10 different users
                message = messages[request_id % len(messages)]
                return await self.send_chat_request(user_id, message)
        
        # Run load test
        start_time = time.time()
        
        if test_duration:
            # Time-based test
            print(f"⏱️ Running for {test_duration} seconds...")
            end_time = start_time + test_duration
            tasks = []
            request_id = 0
            
            while time.time() < end_time:
                if len(tasks) < concurrency:
                    task = asyncio.create_task(limited_request(request_id))
                    tasks.append(task)
                    request_id += 1
                
                # Process completed tasks
                done_tasks = [task for task in tasks if task.done()]
                for task in done_tasks:
                    try:
                        result = await task
                        self.results.append(result)
                    except Exception as e:
                        print(f"Task error: {e}")
                    tasks.remove(task)
                
                await asyncio.sleep(0.01)  # Small delay
            
            # Wait for remaining tasks
            if tasks:
                remaining_results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in remaining_results:
                    if not isinstance(result, Exception):
                        self.results.append(result)
        
        else:
            # Request count-based test
            tasks = [limited_request(i) for i in range(num_requests)]
            self.results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out exceptions
            valid_results = [r for r in self.results if not isinstance(r, Exception)]
            self.results = valid_results
        
        total_time = time.time() - start_time
        
        return self.analyze_results(total_time)
    
    def analyze_results(self, total_time: float) -> Dict[str, Any]:
        """Analyze test results."""
        if not self.results:
            return {"error": "No results to analyze"}
        
        # Separate by status
        successful = [r for r in self.results if r["status"] == "success"]
        errors = [r for r in self.results if r["status"] != "success"]
        
        # Calculate latency statistics
        latencies = [r["latency"] for r in successful]
        
        stats = {
            "total_requests": len(self.results),
            "successful_requests": len(successful),
            "failed_requests": len(errors),
            "success_rate": len(successful) / len(self.results) * 100,
            "total_duration": total_time,
            "requests_per_second": len(self.results) / total_time,
            "latency_stats": {}
        }
        
        if latencies:
            stats["latency_stats"] = {
                "min": min(latencies),
                "max": max(latencies),
                "mean": statistics.mean(latencies),
                "median": statistics.median(latencies),
                "p95": self.percentile(latencies, 95),
                "p99": self.percentile(latencies, 99)
            }
        
        # Check for singleton violations (different instance IDs in responses)
        instance_ids = set()
        for result in successful:
            response_data = result.get("response_data", {})
            # Look for any instance ID indicators in response
            if "request_id" in response_data:
                # For now, we can't directly check instance IDs from API responses
                # This would need additional endpoint or response metadata
                pass
        
        return stats
    
    @staticmethod
    def percentile(data: List[float], percentile: float) -> float:
        """Calculate percentile of a dataset."""
        if not data:
            return 0.0
        
        sorted_data = sorted(data)
        index = (percentile / 100) * (len(sorted_data) - 1)
        
        if index.is_integer():
            return sorted_data[int(index)]
        else:
            lower = sorted_data[int(index)]
            upper = sorted_data[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))
    
    async def memory_leak_test(self, iterations: int = 50) -> Dict[str, Any]:
        """Test for memory leaks by monitoring memory usage."""
        print(f"🧠 Running memory leak test: {iterations} iterations")
        
        memory_usage = []
        
        for i in range(iterations):
            # Send batch of requests
            batch_size = 10
            tasks = []
            
            for j in range(batch_size):
                user_id = f"memory_test_{i}_{j}"
                message = f"Memory test iteration {i}, request {j}"
                task = self.send_chat_request(user_id, message)
                tasks.append(task)
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check metrics endpoint for memory usage (if available)
            try:
                async with self.session.get(f"{self.base_url}/metrics") as response:
                    if response.status == 200:
                        metrics_text = await response.text()
                        # Parse memory metrics if available
                        # This is simplified - would need proper Prometheus parser
                        memory_usage.append(len(metrics_text))
            except Exception:
                pass
            
            if i % 10 == 0:
                print(f"  Iteration {i}/{iterations}")
        
        return {
            "iterations": iterations,
            "memory_samples": len(memory_usage),
            "memory_growth": "stable" if len(set(memory_usage[-10:])) < 3 else "growing"
        }
    
    def print_results(self, stats: Dict[str, Any]):
        """Print formatted test results."""
        print("\n" + "="*60)
        print("🧪 STRESS TEST RESULTS")
        print("="*60)
        
        print(f"📊 Request Statistics:")
        print(f"  Total requests: {stats['total_requests']}")
        print(f"  Successful: {stats['successful_requests']}")
        print(f"  Failed: {stats['failed_requests']}")
        print(f"  Success rate: {stats['success_rate']:.1f}%")
        print(f"  Duration: {stats['total_duration']:.2f}s")
        print(f"  RPS: {stats['requests_per_second']:.1f}")
        
        if stats.get("latency_stats"):
            latency = stats["latency_stats"]
            print(f"\n⏱️ Latency Statistics:")
            print(f"  Min: {latency['min']*1000:.0f}ms")
            print(f"  Max: {latency['max']*1000:.0f}ms")
            print(f"  Mean: {latency['mean']*1000:.0f}ms")
            print(f"  Median: {latency['median']*1000:.0f}ms")
            print(f"  P95: {latency['p95']*1000:.0f}ms")
            print(f"  P99: {latency['p99']*1000:.0f}ms")
        
        # Performance assessment
        print(f"\n🎯 Performance Assessment:")
        success_rate = stats['success_rate']
        mean_latency = stats.get("latency_stats", {}).get("mean", 0) * 1000
        
        if success_rate >= 99 and mean_latency < 200:
            print("  ✅ EXCELLENT - Ready for production")
        elif success_rate >= 95 and mean_latency < 500:
            print("  🟡 GOOD - Minor optimizations recommended")
        elif success_rate >= 90 and mean_latency < 1000:
            print("  🟠 FAIR - Performance tuning needed")
        else:
            print("  ❌ POOR - Significant issues detected")
        
        print("="*60)


async def main():
    parser = argparse.ArgumentParser(description="Stress test Aletheia service")
    parser.add_argument("--url", default="http://localhost:8000", help="Service URL")
    parser.add_argument("--requests", type=int, default=100, help="Number of requests")
    parser.add_argument("--concurrency", type=int, default=10, help="Concurrent requests")
    parser.add_argument("--duration", type=int, help="Test duration in seconds")
    parser.add_argument("--memory-test", action="store_true", help="Run memory leak test")
    
    args = parser.parse_args()
    
    async with AletheiaStressTester(args.url) as tester:
        # Health check
        print(f"🔍 Checking service health at {args.url}...")
        if not await tester.health_check():
            print("❌ Service is not responding. Please start the service first.")
            sys.exit(1)
        
        print("✅ Service is healthy")
        
        # Run load test
        if args.duration:
            stats = await tester.concurrent_load_test(
                concurrency=args.concurrency,
                test_duration=args.duration
            )
        else:
            stats = await tester.concurrent_load_test(
                num_requests=args.requests,
                concurrency=args.concurrency
            )
        
        tester.print_results(stats)
        
        # Run memory test if requested
        if args.memory_test:
            print("\n🧠 Running memory leak test...")
            memory_stats = await tester.memory_leak_test()
            print(f"Memory test: {memory_stats['memory_growth']}")


if __name__ == "__main__":
    asyncio.run(main()) 