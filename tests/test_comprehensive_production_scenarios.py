"""
COMPREHENSIVE PRODUCTION TESTING SUITE
======================================

This test suite is designed like a senior developer's final review before 
manager evaluation. It covers EVERY possible scenario that could fail in 
production and embarrass the team.

TESTING PHILOSOPHY:
- If it can break, it WILL break in production
- Users will try things we never thought of
- Systems will fail in the most inconvenient ways
- Murphy's Law: "Anything that can go wrong, will go wrong"
"""

import asyncio
import pytest
import time
import gc
import psutil
import os
from unittest.mock import patch, MagicMock, AsyncMock
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import random
import string

from bot.watch_flow import _finalize_watch, _cached_search_items_advanced, smart_product_selection_with_ai
from bot.cache_service import get_price, get_price_async
from bot.paapi_ai_bridge import search_products_with_ai_analysis
from bot.product_selection_models import smart_product_selection, get_selection_model
from bot.models import User, Watch, Cache
from sqlmodel import Session, select
from bot.cache_service import engine


class TestRealisticUserScenarios:
    """Test with REAL user queries that could break the system."""

    # Real user queries from different languages, weird formatting, edge cases
    REALISTIC_USER_QUERIES = [
        # Normal queries
        "gaming monitor under 50000",
        "coding monitor under ₹50000",
        "best monitor for programming",
        
        # Weird formatting that users actually use
        "monitor.under.50k",
        "monitor          under      50000",  # Multiple spaces
        "Monitor Under ₹50,000",  # Mixed case, comma in price
        "GAMING MONITOR UNDER RS.50000",  # All caps, Rs. format
        
        # Different price formats
        "monitor under 50k",
        "monitor under 50,000",
        "monitor under ₹ 50000",
        "monitor under rs 50000",
        "monitor under INR 50000",
        "monitor below 50 thousand",
        
        # Non-English characters and emojis
        "gaming monitor 🎮 under 50000",
        "monitor für gaming unter 50000",  # German
        "मॉनिटर अंडर 50000",  # Hindi
        "モニター under 50000",  # Japanese
        
        # Extreme cases
        "",  # Empty query
        " ",  # Just spaces
        "a",  # Single character
        "x" * 1000,  # Very long query
        "monitor under -1000",  # Negative price
        "monitor under 999999999999",  # Huge price
        "monitor under abc",  # Invalid price format
        
        # SQL injection attempts (users might try this)
        "monitor'; DROP TABLE watches;--",
        "monitor UNION SELECT * FROM users",
        
        # XSS attempts
        "monitor <script>alert('hack')</script>",
        "monitor javascript:alert(1)",
        
        # Special characters
        "monitor@#$%^&*()_+{}|:<>?",
        "monitor\n\t\r",  # Newlines and tabs
        "monitor\\\\\\///",  # Backslashes and slashes
        
        # Real typos users make
        "moniter under 50000",  # Common typo
        "gaming minitor",
        "4k monitro",
        "gamng monitor",
        
        # Complex technical queries
        "27 inch 144hz 1440p IPS gaming monitor under 50000 with G-Sync compatible FreeSync premium",
        "ultrawide curved 34 inch monitor with USB-C PD 90W for MacBook Pro programming work under 80000",
    ]

    @pytest.mark.asyncio
    async def test_all_realistic_user_queries(self):
        """Test EVERY realistic user query that could break the system."""
        
        mock_update = self._create_mock_update()
        mock_context = self._create_mock_context()
        
        # Test EVERY query - no mercy
        failed_queries = []
        successful_queries = []
        
        for query in self.REALISTIC_USER_QUERIES:
            try:
                watch_data = {
                    "asin": None,
                    "brand": None,
                    "max_price": 50000,
                    "min_discount": None,
                    "keywords": query,
                    "mode": "daily"
                }
                
                # Mock successful product search
                mock_products = self._create_mock_products(3)
                
                with patch('bot.watch_flow._cached_search_items_advanced', return_value=mock_products):
                    with patch('bot.cache_service.get_price', return_value=45000):
                        
                        await _finalize_watch(mock_update, mock_context, watch_data)
                        successful_queries.append(query)
                        
            except Exception as e:
                failed_queries.append((query, str(e)))
                print(f"❌ QUERY FAILED: '{query}' -> {e}")
        
        print(f"✅ SUCCESS: {len(successful_queries)}/{len(self.REALISTIC_USER_QUERIES)} queries handled")
        print(f"❌ FAILURES: {len(failed_queries)} queries failed")
        
        # If ANY query fails, we have a problem
        if failed_queries:
            failure_summary = "\n".join([f"'{q}': {e}" for q, e in failed_queries[:5]])  # Show first 5
            pytest.fail(f"CRITICAL: {len(failed_queries)} queries failed:\n{failure_summary}")

    def _create_mock_update(self):
        """Create a realistic mock update."""
        update = MagicMock()
        update.effective_user.id = random.randint(1000000, 9999999)
        update.effective_chat.send_message = AsyncMock()
        update.effective_chat.send_photo = AsyncMock()
        update.callback_query = None
        return update
    
    def _create_mock_context(self):
        """Create a realistic mock context."""
        context = MagicMock()
        context.user_data = {}
        return context
    
    def _create_mock_products(self, count: int):
        """Create realistic mock products."""
        return [
            {
                "asin": f"B{random.randint(10000000, 99999999)}",
                "title": f"Gaming Monitor {i+1} - 27 inch 144Hz",
                "price": random.randint(30000, 60000),
                "image": f"https://example.com/image{i}.jpg",
                "features": [f"Feature {j}" for j in range(3)]
            }
            for i in range(count)
        ]


class TestConcurrentUserLoad:
    """Test system under realistic concurrent load."""

    @pytest.mark.asyncio
    async def test_concurrent_users_same_query(self):
        """Test multiple users searching the same thing simultaneously."""
        
        api_call_count = 0
        
        def mock_search(*args, **kwargs):
            nonlocal api_call_count
            api_call_count += 1
            # Simulate API delay
            time.sleep(0.1)
            return [{"asin": "TEST123", "title": "Test Product", "price": 50000}]
        
        async def simulate_user(user_id: int):
            """Simulate a user performing a search."""
            try:
                with patch('bot.paapi_factory.search_items_advanced', side_effect=mock_search):
                    result = await _cached_search_items_advanced("gaming monitor")
                    return f"User {user_id}: Success"
            except Exception as e:
                return f"User {user_id}: FAILED - {e}"
        
        # Simulate 50 concurrent users (realistic load)
        start_time = time.time()
        
        tasks = [simulate_user(i) for i in range(50)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Check results
        failures = [r for r in results if isinstance(r, Exception) or "FAILED" in str(r)]
        successes = [r for r in results if r not in failures]
        
        print(f"⏱️ PERFORMANCE: {total_time:.2f}s for 50 concurrent users")
        print(f"✅ SUCCESS: {len(successes)}/50 users handled successfully")
        print(f"❌ FAILURES: {len(failures)} users failed")
        print(f"🔧 API CALLS: {api_call_count} (should be minimal due to caching)")
        
        # Performance assertions
        assert total_time < 30, f"Took {total_time:.2f}s, should be under 30s"
        assert len(failures) == 0, f"Had {len(failures)} failures in concurrent load"
        assert api_call_count <= 5, f"Made {api_call_count} API calls, caching not working properly"

    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self):
        """Test for memory leaks under sustained load."""
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        async def memory_intensive_operation():
            """Simulate memory-intensive user operations."""
            # Create large product datasets
            large_products = [
                {
                    "asin": f"TEST{i}",
                    "title": "Large Product Title " * 50,  # Large strings
                    "price": i * 1000,
                    "features": [f"Feature {j}" * 20 for j in range(100)],  # Many large features
                    "technical_details": {f"spec_{k}": f"value_{k}" * 10 for k in range(50)}
                }
                for i in range(1000)  # 1000 large products
            ]
            
            # Process with AI enhancement
            from bot.watch_flow import _filter_products_by_criteria
            watch_data = {"max_price": 50000, "brand": None, "min_discount": None}
            
            filtered = _filter_products_by_criteria(large_products, watch_data)
            return len(filtered)
        
        # Run memory-intensive operations multiple times
        for i in range(10):
            result = await memory_intensive_operation()
            gc.collect()  # Force garbage collection
            
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = current_memory - initial_memory
            
            print(f"🧠 MEMORY CHECK {i+1}: {current_memory:.1f}MB (+{memory_increase:.1f}MB)")
            
            # Memory leak detection
            if memory_increase > 500:  # More than 500MB increase
                pytest.fail(f"MEMORY LEAK DETECTED: Memory increased by {memory_increase:.1f}MB")
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        total_increase = final_memory - initial_memory
        
        print(f"🎯 FINAL MEMORY: {final_memory:.1f}MB (total increase: {total_increase:.1f}MB)")
        assert total_increase < 200, f"Memory leak: increased by {total_increase:.1f}MB"


class TestDatabaseStressAndIntegrity:
    """Test database under stress and failure conditions."""

    @pytest.mark.asyncio
    async def test_concurrent_database_operations(self):
        """Test database integrity under concurrent operations."""
        
        async def create_watch_for_user(user_id: int):
            """Create a watch for a user concurrently."""
            try:
                with Session(engine) as session:
                    # Check if user exists
                    user_statement = select(User).where(User.tg_user_id == user_id)
                    user = session.exec(user_statement).first()
                    
                    if not user:
                        user = User(tg_user_id=user_id)
                        session.add(user)
                        session.commit()
                        session.refresh(user)
                    
                    # Create watch
                    watch = Watch(
                        user_id=user.id,
                        asin=f"TEST{user_id}",
                        keywords=f"test query {user_id}",
                        max_price=50000,
                        mode="daily"
                    )
                    
                    session.add(watch)
                    session.commit()
                    session.refresh(watch)
                    
                    return f"User {user_id}: Watch {watch.id} created"
                    
            except Exception as e:
                return f"User {user_id}: FAILED - {e}"
        
        # Create watches for 100 users concurrently
        tasks = [create_watch_for_user(i) for i in range(1000, 1100)]  # Unique user IDs
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check results
        failures = [r for r in results if isinstance(r, Exception) or "FAILED" in str(r)]
        successes = [r for r in results if r not in failures]
        
        print(f"✅ DATABASE SUCCESS: {len(successes)}/100 concurrent operations")
        print(f"❌ DATABASE FAILURES: {len(failures)} operations failed")
        
        # Database integrity check
        with Session(engine) as session:
            user_count = len(session.exec(select(User)).all())
            watch_count = len(session.exec(select(Watch)).all())
            
            print(f"📊 DATABASE STATE: {user_count} users, {watch_count} watches")
        
        assert len(failures) == 0, f"Database integrity compromised: {len(failures)} failures"

    @pytest.mark.asyncio
    async def test_database_corruption_scenarios(self):
        """Test handling of database corruption and constraint violations."""
        
        corruption_scenarios = [
            # Invalid data types
            {"asin": None, "keywords": "test", "max_price": 50000},
            {"asin": "", "keywords": None, "max_price": 50000},
            {"asin": "TEST", "keywords": "test", "max_price": None},
            
            # Extreme values
            {"asin": "A" * 1000, "keywords": "test", "max_price": 50000},  # Very long ASIN
            {"asin": "TEST", "keywords": "x" * 10000, "max_price": 50000},  # Very long keywords
            {"asin": "TEST", "keywords": "test", "max_price": -1},  # Negative price
            {"asin": "TEST", "keywords": "test", "max_price": 999999999999},  # Huge price
            
            # Special characters
            {"asin": "TEST'; DROP TABLE users;--", "keywords": "test", "max_price": 50000},
            {"asin": "TEST\x00\x01\x02", "keywords": "test\n\r\t", "max_price": 50000},
        ]
        
        for i, scenario in enumerate(corruption_scenarios):
            try:
                with Session(engine) as session:
                    # Create a test user
                    user = User(tg_user_id=9999990 + i)
                    session.add(user)
                    session.commit()
                    session.refresh(user)
                    
                    # Try to create watch with corrupted data
                    watch = Watch(
                        user_id=user.id,
                        asin=scenario["asin"],
                        keywords=scenario["keywords"],
                        max_price=scenario["max_price"],
                        mode="daily"
                    )
                    
                    session.add(watch)
                    session.commit()
                    
                    print(f"⚠️ SCENARIO {i+1}: Accepted corrupted data (might be OK)")
                    
            except Exception as e:
                print(f"✅ SCENARIO {i+1}: Properly rejected corrupted data - {e}")
                # This is actually good - the database should reject bad data


class TestAISystemUnderStress:
    """Test AI components under stress and edge cases."""

    @pytest.mark.asyncio
    async def test_ai_with_extreme_product_datasets(self):
        """Test AI system with extreme product datasets."""
        
        extreme_scenarios = [
            # No products
            [],
            
            # Single product
            [{"asin": "TEST1", "title": "Single Product", "price": 50000}],
            
            # Identical products (confusion test)
            [{"asin": f"TEST{i}", "title": "Identical Product", "price": 50000} for i in range(10)],
            
            # Extreme price ranges
            [
                {"asin": "CHEAP", "title": "Cheap Product", "price": 100},
                {"asin": "EXPENSIVE", "title": "Expensive Product", "price": 10000000}
            ],
            
            # Products with no useful data
            [
                {"asin": "NODATA1", "title": "", "price": None},
                {"asin": "NODATA2", "title": None, "price": "Invalid"},
                {"asin": "NODATA3", "features": None, "technical_details": {}}
            ],
            
            # Products with corrupted data
            [
                {"asin": "CORRUPT1", "title": "x" * 10000, "price": "not_a_number"},
                {"asin": "CORRUPT2", "title": "\x00\x01\x02", "price": -999999},
                {"asin": "CORRUPT3", "features": ["a" * 1000] * 100}  # Huge features
            ]
        ]
        
        for i, products in enumerate(extreme_scenarios):
            try:
                result = await smart_product_selection(products, "gaming monitor")
                
                if products and result is None:
                    print(f"⚠️ SCENARIO {i+1}: AI returned None for {len(products)} products")
                elif not products and result is not None:
                    print(f"❌ SCENARIO {i+1}: AI returned product for empty dataset")
                else:
                    print(f"✅ SCENARIO {i+1}: AI handled {len(products)} products correctly")
                    
            except Exception as e:
                print(f"❌ SCENARIO {i+1}: AI crashed with {len(products)} products - {e}")
                pytest.fail(f"AI system should handle extreme datasets gracefully: {e}")

    @pytest.mark.asyncio
    async def test_ai_performance_degradation(self):
        """Test AI performance doesn't degrade over time."""
        
        # Measure AI performance over multiple iterations
        performance_times = []
        
        for iteration in range(20):  # 20 iterations
            # Create realistic product dataset
            products = [
                {
                    "asin": f"PERF{i}",
                    "title": f"Gaming Monitor {i} - 27 inch 144Hz IPS",
                    "price": random.randint(30000, 80000),
                    "features": [
                        "27 inch display",
                        "144Hz refresh rate",
                        "1ms response time",
                        "AMD FreeSync",
                        "HDMI 2.1"
                    ],
                    "technical_details": {
                        "Display Type": "IPS",
                        "Refresh Rate": "144 Hz",
                        "Resolution": "2560 x 1440",
                        "Response Time": "1 ms"
                    }
                }
                for i in range(100)  # 100 products each time
            ]
            
            start_time = time.time()
            result = await smart_product_selection(products, "gaming monitor 144hz")
            end_time = time.time()
            
            processing_time = (end_time - start_time) * 1000  # ms
            performance_times.append(processing_time)
            
            print(f"🔄 ITERATION {iteration+1}: {processing_time:.1f}ms")
        
        # Analyze performance trends
        avg_time = sum(performance_times) / len(performance_times)
        max_time = max(performance_times)
        min_time = min(performance_times)
        
        # Check for performance degradation
        first_half_avg = sum(performance_times[:10]) / 10
        second_half_avg = sum(performance_times[10:]) / 10
        degradation = ((second_half_avg - first_half_avg) / first_half_avg) * 100
        
        print(f"📊 PERFORMANCE SUMMARY:")
        print(f"   Average: {avg_time:.1f}ms")
        print(f"   Range: {min_time:.1f}ms - {max_time:.1f}ms")
        print(f"   Degradation: {degradation:.1f}%")
        
        # Performance assertions
        assert avg_time < 1000, f"AI too slow: average {avg_time:.1f}ms"
        assert max_time < 2000, f"AI has spikes: max {max_time:.1f}ms"
        assert degradation < 50, f"AI degrading: {degradation:.1f}% slower over time"


class TestErrorRecoveryAndResilience:
    """Test system recovery from various failure modes."""

    @pytest.mark.asyncio
    async def test_cascade_failure_recovery(self):
        """Test recovery from cascading system failures."""
        
        failure_scenarios = [
            # API failures
            {"api_failure": True, "db_failure": False, "cache_failure": False},
            {"api_failure": False, "db_failure": True, "cache_failure": False},
            {"api_failure": False, "db_failure": False, "cache_failure": True},
            
            # Multiple failures
            {"api_failure": True, "db_failure": True, "cache_failure": False},
            {"api_failure": True, "db_failure": False, "cache_failure": True},
            {"api_failure": False, "db_failure": True, "cache_failure": True},
            
            # Complete system failure
            {"api_failure": True, "db_failure": True, "cache_failure": True},
        ]
        
        for i, scenario in enumerate(failure_scenarios):
            print(f"\n🔥 TESTING FAILURE SCENARIO {i+1}: {scenario}")
            
            # Setup failure conditions
            api_mock = Exception("API down") if scenario["api_failure"] else [{"asin": "TEST", "title": "Product"}]
            db_mock = Exception("Database down") if scenario["db_failure"] else None
            cache_mock = Exception("Cache down") if scenario["cache_failure"] else 45000
            
            try:
                mock_update = MagicMock()
                mock_update.effective_user.id = 12345
                mock_update.effective_chat.send_message = AsyncMock()
                mock_context = MagicMock()
                mock_context.user_data = {}
                
                watch_data = {
                    "asin": None,
                    "keywords": "test query",
                    "max_price": 50000,
                    "mode": "daily"
                }
                
                with patch('bot.paapi_factory.search_items_advanced', side_effect=api_mock if scenario["api_failure"] else lambda *args: api_mock):
                    with patch('bot.cache_service.get_price', side_effect=cache_mock if scenario["cache_failure"] else lambda *args: cache_mock):
                        
                        # This should NOT crash, even with multiple failures
                        await _finalize_watch(mock_update, mock_context, watch_data)
                        
                        # Should send SOME message to user
                        assert mock_update.effective_chat.send_message.called, \
                               f"Scenario {i+1}: No user communication during failures"
                        
                        print(f"✅ SCENARIO {i+1}: System survived cascading failures")
                        
            except Exception as e:
                pytest.fail(f"SCENARIO {i+1}: System crashed during failures - {e}")

    @pytest.mark.asyncio
    async def test_resource_exhaustion_recovery(self):
        """Test recovery from resource exhaustion."""
        
        # Simulate resource exhaustion scenarios
        def memory_exhaustion_mock(*args, **kwargs):
            raise MemoryError("Out of memory")
        
        def timeout_mock(*args, **kwargs):
            raise TimeoutError("Operation timed out")
        
        def file_system_full_mock(*args, **kwargs):
            raise OSError("No space left on device")
        
        exhaustion_scenarios = [
            ("Memory exhaustion", memory_exhaustion_mock),
            ("Timeout", timeout_mock),
            ("File system full", file_system_full_mock),
        ]
        
        for scenario_name, mock_function in exhaustion_scenarios:
            print(f"\n💥 TESTING {scenario_name.upper()}")
            
            try:
                with patch('bot.paapi_factory.search_items_advanced', side_effect=mock_function):
                    
                    mock_update = MagicMock()
                    mock_update.effective_user.id = 12345
                    mock_update.effective_chat.send_message = AsyncMock()
                    mock_context = MagicMock()
                    
                    watch_data = {
                        "keywords": "test query",
                        "max_price": 50000,
                        "mode": "daily"
                    }
                    
                    # Should handle resource exhaustion gracefully
                    await _finalize_watch(mock_update, mock_context, watch_data)
                    
                    print(f"✅ {scenario_name}: System recovered gracefully")
                    
            except Exception as e:
                pytest.fail(f"{scenario_name}: System should recover from resource exhaustion - {e}")


if __name__ == "__main__":
    # Quick smoke test
    print("🔥 COMPREHENSIVE PRODUCTION TEST SUITE")
    print("=" * 60)
    print("Testing scenarios that could break in production...")
    
    # You can run individual test classes here for debugging
    pass
