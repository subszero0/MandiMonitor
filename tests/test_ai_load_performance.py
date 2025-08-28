"""
Phase R6: Load Testing and Performance Validation for AI Intelligence Model.

This module provides load testing scenarios to validate:
- System stability under concurrent load
- Performance degradation analysis  
- Memory usage patterns
- Response time distribution under stress
"""

import asyncio
import time
import statistics
import psutil
import pytest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from typing import List, Dict, Any

from bot.product_selection_models import smart_product_selection
from bot.ai.multi_card_selector import MultiCardSelector
from bot.ai_performance_monitor import get_ai_monitor


class TestAILoadPerformance:
    """Load testing and performance validation for AI system."""

    @pytest.fixture
    def load_test_products(self):
        """Extended product dataset for load testing."""
        products = []
        for i in range(20):  # 20 products for more realistic load
            products.append({
                "asin": f"B{i:08d}TEST",
                "title": f"Gaming Monitor {i+1} - 27 inch {144+i*10}Hz Display",
                "price": 25000 + (i * 1000),
                "image": f"https://m.media-amazon.com/images/I/{i}test.jpg",
                "features": [
                    f"{27+i%5} inch display",
                    f"{144+i*10}Hz refresh rate",
                    "1ms response time",
                    "IPS panel" if i % 2 == 0 else "VA panel",
                    "Gaming focused"
                ],
                "technical_details": {
                    "Display Type": "IPS" if i % 2 == 0 else "VA",
                    "Refresh Rate": f"{144+i*10} Hz",
                    "Resolution": "2560 x 1440" if i % 3 == 0 else "1920 x 1080",
                    "Response Time": "1 ms"
                }
            })
        return products

    @pytest.fixture 
    def stress_test_queries(self):
        """Diverse query set for stress testing."""
        return [
            "gaming monitor 144hz 4k",
            "programming monitor IPS 1440p", 
            "curved gaming monitor 240hz",
            "budget monitor under 25000",
            "professional monitor color accuracy",
            "ultrawide monitor 34 inch",
            "4k monitor HDR gaming",
            "monitor dual setup programming",
            "esports monitor 1ms latency",
            "content creation monitor 32 inch"
        ]

    @pytest.mark.asyncio
    async def test_concurrent_ai_selections(self, load_test_products, stress_test_queries):
        """
        Test AI system under concurrent load.
        Target: Handle 50+ concurrent requests without degradation.
        """
        concurrent_requests = 50
        queries = stress_test_queries * (concurrent_requests // len(stress_test_queries) + 1)
        
        async def single_request(query: str, request_id: int):
            """Single AI selection request with timing."""
            start_time = time.time()
            try:
                result = await smart_product_selection(load_test_products, query)
                processing_time = (time.time() - start_time) * 1000
                return {
                    "request_id": request_id,
                    "query": query,
                    "success": result is not None,
                    "processing_time_ms": processing_time,
                    "has_ai_metadata": "_ai_metadata" in (result or {}),
                    "error": None
                }
            except Exception as e:
                processing_time = (time.time() - start_time) * 1000
                return {
                    "request_id": request_id,
                    "query": query,
                    "success": False,
                    "processing_time_ms": processing_time,
                    "has_ai_metadata": False,
                    "error": str(e)
                }
        
        # Execute concurrent requests
        start_total = time.time()
        tasks = [
            single_request(queries[i % len(queries)], i)
            for i in range(concurrent_requests)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = (time.time() - start_total) * 1000
        
        # Analyze results
        successful_results = [r for r in results if isinstance(r, dict) and r["success"]]
        failed_results = [r for r in results if isinstance(r, dict) and not r["success"]]
        
        # Performance assertions
        success_rate = len(successful_results) / concurrent_requests
        assert success_rate >= 0.9  # At least 90% success rate
        
        if successful_results:
            processing_times = [r["processing_time_ms"] for r in successful_results]
            avg_time = statistics.mean(processing_times)
            p95_time = statistics.quantiles(processing_times, n=20)[18]  # 95th percentile
            
            # Performance benchmarks
            assert avg_time < 1000  # Average under 1 second
            assert p95_time < 2000   # 95th percentile under 2 seconds
            assert total_time < 10000  # Total execution under 10 seconds
        
        # Check AI usage distribution
        ai_used_count = len([r for r in successful_results if r["has_ai_metadata"]])
        ai_usage_rate = ai_used_count / len(successful_results) if successful_results else 0
        
        # Log performance metrics
        print(f"\n=== CONCURRENT LOAD TEST RESULTS ===")
        print(f"Concurrent Requests: {concurrent_requests}")
        print(f"Success Rate: {success_rate:.1%}")
        print(f"AI Usage Rate: {ai_usage_rate:.1%}")
        if successful_results:
            print(f"Average Time: {avg_time:.1f}ms")
            print(f"95th Percentile: {p95_time:.1f}ms")
        print(f"Total Time: {total_time:.1f}ms")
        if failed_results:
            print(f"Failures: {len(failed_results)}")
            for failure in failed_results[:3]:  # Show first 3 failures
                print(f"  - {failure['error']}")

    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, load_test_products):
        """
        Test memory usage patterns under sustained load.
        Target: No significant memory leaks, stable usage.
        """
        import gc
        
        # Baseline memory usage
        gc.collect()
        process = psutil.Process()
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Sustained load test
        iterations = 100
        memory_samples = []
        
        for i in range(iterations):
            # Perform AI selection
            query = f"gaming monitor test iteration {i}"
            result = await smart_product_selection(load_test_products, query)
            
            # Sample memory every 10 iterations
            if i % 10 == 0:
                gc.collect()  # Force garbage collection
                current_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_samples.append(current_memory)
        
        # Analyze memory usage
        final_memory = memory_samples[-1]
        memory_growth = final_memory - baseline_memory
        max_memory = max(memory_samples)
        
        # Memory usage assertions
        assert memory_growth < 50  # Less than 50MB growth
        assert max_memory < baseline_memory + 100  # Peak under 100MB above baseline
        
        print(f"\n=== MEMORY USAGE TEST RESULTS ===")
        print(f"Baseline Memory: {baseline_memory:.1f}MB")
        print(f"Final Memory: {final_memory:.1f}MB") 
        print(f"Memory Growth: {memory_growth:.1f}MB")
        print(f"Peak Memory: {max_memory:.1f}MB")

    @pytest.mark.asyncio
    async def test_multi_card_performance_under_load(self, load_test_products):
        """
        Test multi-card selector performance under load.
        Target: <300ms for multi-card generation, stable under concurrent load.
        """
        from bot.watch_flow import smart_product_selection_with_ai
        concurrent_multi_card_requests = 20
        
        async def multi_card_request(request_id: int):
            """Single multi-card selection request."""
            query = f"gaming monitor comparison test {request_id}"
            start_time = time.time()
            
            try:
                result = await smart_product_selection_with_ai(
                    products=load_test_products[:8],  # Limit for performance
                    user_query=query,
                    user_preferences={"budget_flexible": True},
                    enable_multi_card=True
                )
                processing_time = (time.time() - start_time) * 1000
                
                return {
                    "request_id": request_id,
                    "success": result is not None,
                    "processing_time_ms": processing_time,
                    "is_multi_card": result.get("presentation_mode") == "multi_card" if result else False,
                    "product_count": len(result.get("products", [])) if result else 0
                }
            except Exception as e:
                processing_time = (time.time() - start_time) * 1000
                return {
                    "request_id": request_id,
                    "success": False,
                    "processing_time_ms": processing_time,
                    "error": str(e)
                }
        
        # Execute concurrent multi-card requests
        tasks = [multi_card_request(i) for i in range(concurrent_multi_card_requests)]
        results = await asyncio.gather(*tasks)
        
        # Analyze multi-card performance
        successful_results = [r for r in results if r["success"]]
        multi_card_results = [r for r in successful_results if r.get("is_multi_card")]
        
        success_rate = len(successful_results) / concurrent_multi_card_requests
        assert success_rate >= 0.85  # At least 85% success rate for complex operations
        
        if successful_results:
            processing_times = [r["processing_time_ms"] for r in successful_results]
            avg_time = statistics.mean(processing_times)
            max_time = max(processing_times)
            
            # Multi-card performance benchmarks
            assert avg_time < 500  # Average under 500ms
            assert max_time < 1000  # Maximum under 1 second
        
        print(f"\n=== MULTI-CARD LOAD TEST RESULTS ===")
        print(f"Concurrent Requests: {concurrent_multi_card_requests}")
        print(f"Success Rate: {success_rate:.1%}")
        print(f"Multi-card Results: {len(multi_card_results)}")
        if successful_results:
            print(f"Average Time: {avg_time:.1f}ms")
            print(f"Max Time: {max_time:.1f}ms")

    def test_sequential_performance_baseline(self, load_test_products, stress_test_queries):
        """
        Establish sequential performance baseline for comparison.
        Target: Understand single-threaded performance characteristics.
        """
        import asyncio
        
        async def run_sequential_test():
            results = []
            
            for i, query in enumerate(stress_test_queries[:10]):  # Test first 10 queries
                start_time = time.time()
                result = await smart_product_selection(load_test_products, query)
                processing_time = (time.time() - start_time) * 1000
                
                results.append({
                    "iteration": i,
                    "query": query,
                    "processing_time_ms": processing_time,
                    "success": result is not None,
                    "has_ai": "_ai_metadata" in (result or {})
                })
            
            return results
        
        # Run sequential test
        results = asyncio.run(run_sequential_test())
        
        # Analyze sequential performance
        successful_results = [r for r in results if r["success"]]
        processing_times = [r["processing_time_ms"] for r in successful_results]
        
        if processing_times:
            avg_time = statistics.mean(processing_times)
            min_time = min(processing_times)
            max_time = max(processing_times)
            
            # Sequential performance assertions
            assert avg_time < 300  # Average under 300ms sequential
            assert max_time < 1000  # Max under 1 second sequential
        
        ai_usage = len([r for r in successful_results if r["has_ai"]])
        ai_rate = ai_usage / len(successful_results) if successful_results else 0
        
        print(f"\n=== SEQUENTIAL BASELINE RESULTS ===")
        print(f"Test Queries: {len(stress_test_queries[:10])}")
        print(f"Successful: {len(successful_results)}")
        print(f"AI Usage Rate: {ai_rate:.1%}")
        if processing_times:
            print(f"Avg Time: {avg_time:.1f}ms")
            print(f"Min Time: {min_time:.1f}ms") 
            print(f"Max Time: {max_time:.1f}ms")

    @pytest.mark.asyncio
    async def test_stress_test_extended_duration(self, load_test_products):
        """
        Extended duration stress test.
        Target: System stability over extended periods.
        """
        duration_minutes = 2  # 2-minute stress test
        requests_per_minute = 30
        total_requests = duration_minutes * requests_per_minute
        
        start_time = time.time()
        successful_count = 0
        failed_count = 0
        processing_times = []
        
        for i in range(total_requests):
            query = f"stress test query {i} gaming monitor"
            
            request_start = time.time()
            try:
                result = await smart_product_selection(load_test_products, query)
                request_time = (time.time() - request_start) * 1000
                processing_times.append(request_time)
                
                if result:
                    successful_count += 1
                else:
                    failed_count += 1
                    
            except Exception:
                failed_count += 1
                request_time = (time.time() - request_start) * 1000
                processing_times.append(request_time)
            
            # Brief pause to simulate realistic request patterns
            await asyncio.sleep(0.1)
        
        total_duration = time.time() - start_time
        
        # Stress test assertions
        success_rate = successful_count / total_requests
        assert success_rate >= 0.85  # 85% success rate over extended duration
        
        if processing_times:
            avg_time = statistics.mean(processing_times)
            assert avg_time < 800  # Average under 800ms during stress
        
        throughput = total_requests / (total_duration / 60)  # Requests per minute
        
        print(f"\n=== EXTENDED STRESS TEST RESULTS ===")
        print(f"Duration: {total_duration:.1f} seconds")
        print(f"Total Requests: {total_requests}")
        print(f"Successful: {successful_count}")
        print(f"Failed: {failed_count}")
        print(f"Success Rate: {success_rate:.1%}")
        print(f"Throughput: {throughput:.1f} requests/minute")
        if processing_times:
            print(f"Average Response Time: {avg_time:.1f}ms")
