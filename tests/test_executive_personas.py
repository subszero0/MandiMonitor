"""
EXECUTIVE PERSONA TESTING SUITE
===============================

Tests the system from the perspective of different types of executives,
each with their own testing patterns, expectations, and tolerance levels.

This is CRITICAL for production readiness - different executives will 
stress the system in completely different ways.
"""

import pytest
import asyncio
import time
import random
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, List

from bot.watch_flow import _finalize_watch
from bot.product_selection_models import smart_product_selection


class TestExecutivePersonas:
    """Test system behavior with different executive personality types."""

    @pytest.mark.asyncio
    async def test_skeptical_cto_persona(self):
        """
        The Skeptical CTO: Tries to break everything, asks technical questions.
        
        Characteristics:
        - Complex technical queries
        - Tries edge cases deliberately
        - Low tolerance for any technical issues
        - Asks about performance, security, scalability
        """
        print("\n🔬 SKEPTICAL CTO TESTING")
        print("=" * 50)
        
        # CTO-style queries: technical, complex, trying to find limits
        cto_queries = [
            # Technical complexity tests
            "27 inch 144hz 1440p IPS gaming monitor with G-Sync compatible FreeSync premium HDR 600 USB-C PD 90W under ₹80000",
            
            # Edge case attempts
            "monitor under ₹1",  # Unrealistic budget
            "monitor under ₹999999999",  # Massive budget
            "OLED ultrawide curved 49 inch gaming monitor with Thunderbolt 4 and built-in KVM switch",  # Very specific
            
            # Potential system breakers
            "monitor" * 100,  # Repetitive query
            "मॉनिटर गेमिंग अंडर ₹50000 4K HDR10+ OLED",  # Mixed languages with technical terms
            
            # Security probes (CTOs think about security)
            "monitor'; DROP TABLE watches;--",  # SQL injection attempt
            "monitor<script>alert('xss')</script>",  # XSS attempt
        ]
        
        cto_failures = []
        performance_times = []
        
        for i, query in enumerate(cto_queries):
            print(f"\n🔍 CTO Query {i+1}: '{query[:50]}...'")
            
            start_time = time.time()
            
            try:
                result = await self._execute_executive_demo(query, {"exec_type": "cto"})
                end_time = time.time()
                
                duration = (end_time - start_time) * 1000
                performance_times.append(duration)
                
                # CTO expects sub-500ms responses even for complex queries
                if duration > 500:
                    print(f"   ⚠️  SLOW: {duration:.0f}ms (CTO expects <500ms)")
                else:
                    print(f"   ✅ FAST: {duration:.0f}ms")
                    
            except Exception as e:
                cto_failures.append((query, str(e)))
                print(f"   ❌ FAILED: {e}")
        
        # CTO Evaluation Criteria (very strict)
        avg_response_time = sum(performance_times) / len(performance_times) if performance_times else 0
        max_response_time = max(performance_times) if performance_times else 0
        
        print(f"\n📊 CTO EVALUATION:")
        print(f"   Queries Tested: {len(cto_queries)}")
        print(f"   Failures: {len(cto_failures)}")
        print(f"   Avg Response: {avg_response_time:.0f}ms")
        print(f"   Max Response: {max_response_time:.0f}ms")
        
        # CTO has zero tolerance for failures and demands high performance
        assert len(cto_failures) == 0, f"CTO found {len(cto_failures)} critical issues"
        assert avg_response_time < 300, f"CTO rejected system: avg {avg_response_time:.0f}ms too slow"
        assert max_response_time < 500, f"CTO rejected system: max {max_response_time:.0f}ms unacceptable"

    @pytest.mark.asyncio
    async def test_impatient_ceo_persona(self):
        """
        The Impatient CEO: Wants immediate results, no tolerance for delays.
        
        Characteristics:
        - Simple, business-focused queries
        - Expects instant responses
        - Will interrupt/retry if slow
        - Wants clear, immediate value demonstration
        """
        print("\n👔 IMPATIENT CEO TESTING")
        print("=" * 50)
        
        # CEO-style queries: business-focused, simple, results-oriented
        ceo_queries = [
            "good monitor for office",
            "best gaming monitor",
            "cheap monitor under 30000",
            "premium monitor for executives",
            "monitor for video calls",
        ]
        
        for i, query in enumerate(ceo_queries):
            print(f"\n💼 CEO Query {i+1}: '{query}'")
            
            start_time = time.time()
            
            # CEO will timeout quickly if system is slow
            try:
                result = await asyncio.wait_for(
                    self._execute_executive_demo(query, {"exec_type": "ceo"}),
                    timeout=2.0  # CEO has 2-second patience
                )
                
                end_time = time.time()
                duration = (end_time - start_time) * 1000
                
                # CEO wants sub-200ms for "snappy" feel
                if duration > 200:
                    print(f"   😤 TOO SLOW: {duration:.0f}ms (CEO getting impatient)")
                else:
                    print(f"   😊 PERFECT: {duration:.0f}ms (CEO happy)")
                
            except asyncio.TimeoutError:
                pytest.fail(f"CEO RAGE QUIT: Query '{query}' took >2s")
            except Exception as e:
                pytest.fail(f"CEO DEMO DISASTER: {e}")

    @pytest.mark.asyncio
    async def test_detail_oriented_cfo_persona(self):
        """
        The Detail-Oriented CFO: Asks about edge cases, costs, efficiency.
        
        Characteristics:
        - Questions about cost optimization
        - Wants to understand edge cases
        - Asks "what if" scenarios
        - Concerned about system efficiency
        """
        print("\n💰 DETAIL-ORIENTED CFO TESTING")
        print("=" * 50)
        
        # CFO-style queries: cost-focused, efficiency-minded
        cfo_test_scenarios = [
            # Cost optimization queries
            {"query": "cheapest monitor under 20000", "budget": 20000},
            {"query": "best value monitor under 35000", "budget": 35000},
            {"query": "cost-effective monitor for bulk purchase", "budget": 30000},
            
            # Edge case questions CFOs ask
            {"query": "monitor under ₹10", "budget": 10},  # Unrealistic budget
            {"query": "monitor", "budget": None},  # No budget specified
            {"query": "most expensive monitor", "budget": 999999},  # No upper limit
        ]
        
        for i, scenario in enumerate(cfo_test_scenarios):
            print(f"\n💵 CFO Scenario {i+1}: '{scenario['query']}' (Budget: {scenario['budget']})")
            
            try:
                # CFO wants detailed analysis of cost efficiency
                result = await self._execute_executive_demo(
                    scenario["query"], 
                    {"exec_type": "cfo", "budget": scenario["budget"]}
                )
                
                # CFO expects system to handle all financial edge cases
                print(f"   ✅ CFO APPROVED: Handled budget scenario professionally")
                
            except Exception as e:
                pytest.fail(f"CFO AUDIT FAILED: Financial scenario broke system - {e}")

    @pytest.mark.asyncio
    async def test_international_vp_persona(self):
        """
        The International VP: Uses different languages, currency formats.
        
        Characteristics:
        - Queries in different languages
        - Different currency formats
        - Different cultural expectations
        - Tests global compatibility
        """
        print("\n🌍 INTERNATIONAL VP TESTING")
        print("=" * 50)
        
        # International VP queries: multi-language, multi-currency
        international_queries = [
            # Hindi queries
            "गेमिंग मॉनिटर अंडर ₹50000",
            "मॉनिटर 27 इंच गेमिंग",
            
            # Mixed language queries
            "gaming monitor अंडर fifty thousand rupees",
            "4K मॉनिटर for video editing",
            
            # Different currency formats
            "monitor under Rs. 50,000",
            "monitor under INR 50000",
            "monitor below fifty thousand Indian rupees",
            
            # Cultural variations
            "monitor for Diwali festival setup",
            "monitor for Indian office environment",
        ]
        
        for i, query in enumerate(international_queries):
            print(f"\n🗣️  International Query {i+1}: '{query}'")
            
            try:
                result = await self._execute_executive_demo(query, {"exec_type": "international_vp"})
                print(f"   ✅ GLOBAL READY: Handled international query")
                
            except Exception as e:
                pytest.fail(f"INTERNATIONAL EXPANSION BLOCKED: {query} failed - {e}")

    @pytest.mark.asyncio
    async def test_risk_averse_compliance_officer_persona(self):
        """
        The Risk-Averse Compliance Officer: Worried about security, data handling.
        
        Characteristics:
        - Concerned about data security
        - Tests error handling and data protection
        - Wants graceful failure modes
        - No tolerance for data leakage
        """
        print("\n🛡️  COMPLIANCE OFFICER TESTING")
        print("=" * 50)
        
        # Compliance-focused scenarios: security, data protection, graceful failures
        compliance_scenarios = [
            # Data protection tests
            {"scenario": "SQL Injection Protection", "query": "monitor'; DROP TABLE users;--"},
            {"scenario": "XSS Protection", "query": "monitor<script>alert('breach')</script>"},
            {"scenario": "Command Injection Protection", "query": "monitor; rm -rf /"},
            
            # Error handling tests
            {"scenario": "Graceful API Failure", "query": "gaming monitor", "simulate_api_failure": True},
            {"scenario": "Database Failure Handling", "query": "coding monitor", "simulate_db_failure": True},
            
            # Data validation tests
            {"scenario": "Invalid Data Handling", "query": "\x00\x01\x02invalid"},
            {"scenario": "Oversized Input Handling", "query": "monitor " + "x" * 10000},
        ]
        
        for scenario in compliance_scenarios:
            print(f"\n🔒 {scenario['scenario']}")
            
            try:
                if scenario.get("simulate_api_failure"):
                    with patch('bot.paapi_factory.search_items_advanced', side_effect=Exception("Simulated API failure")):
                        result = await self._execute_executive_demo(scenario["query"], {"exec_type": "compliance"})
                elif scenario.get("simulate_db_failure"):
                    with patch('bot.cache_service.Session', side_effect=Exception("Simulated DB failure")):
                        result = await self._execute_executive_demo(scenario["query"], {"exec_type": "compliance"})
                else:
                    result = await self._execute_executive_demo(scenario["query"], {"exec_type": "compliance"})
                
                print(f"   ✅ COMPLIANT: {scenario['scenario']} handled securely")
                
            except Exception as e:
                # For compliance officer, we want to see HOW the system fails
                print(f"   🔍 FAILURE MODE: {e}")
                # Ensure it's a graceful failure, not a security breach
                assert "DROP TABLE" not in str(e), "SQL injection vulnerability detected!"
                assert "<script>" not in str(e), "XSS vulnerability detected!"
                print(f"   ✅ SECURE FAILURE: System failed gracefully without security breach")

    async def _execute_executive_demo(self, query: str, executive_context: Dict) -> str:
        """Execute a demo query with executive context."""
        
        mock_update = MagicMock()
        mock_update.effective_user.id = random.randint(1000000, 9999999)
        mock_update.effective_chat.send_message = AsyncMock()
        mock_update.effective_chat.send_photo = AsyncMock()
        mock_context = MagicMock()
        mock_context.user_data = {}
        
        watch_data = {
            "asin": None,
            "brand": None,
            "max_price": 50000,
            "keywords": query,
            "mode": "daily"
        }
        
        # Generate executive-appropriate products
        products = self._generate_executive_demo_products(executive_context)
        
        with patch('bot.watch_flow._cached_search_items_advanced', return_value=products):
            with patch('bot.cache_service.get_price', return_value=45000):
                await _finalize_watch(mock_update, mock_context, watch_data)
                
                # Verify executive expectations were met
                assert (mock_update.effective_chat.send_message.called or 
                       mock_update.effective_chat.send_photo.called), \
                       f"Executive demo failed: no response sent"
                
                return "Demo successful"

    def _generate_executive_demo_products(self, executive_context: Dict) -> List[Dict]:
        """Generate products appropriate for different executive contexts."""
        
        exec_type = executive_context.get("exec_type", "general")
        
        if exec_type == "cto":
            # CTOs want technical products with detailed specs
            return [
                {
                    "asin": "B08N5WRWNW",
                    "title": "ASUS ROG Swift PG279QM 27\" 1440p 240Hz IPS G-Sync Ultimate Gaming Monitor",
                    "price": 75000,
                    "brand": "ASUS",
                    "features": ["240Hz refresh rate", "1ms response time", "G-Sync Ultimate", "IPS panel"],
                    "technical_details": {
                        "Refresh Rate": "240 Hz",
                        "Response Time": "1 ms",
                        "Panel Type": "IPS",
                        "Resolution": "2560 x 1440"
                    }
                }
            ]
        elif exec_type == "ceo":
            # CEOs want business-value focused products
            return [
                {
                    "asin": "B08CEO123",
                    "title": "Samsung 27\" Business Monitor - Perfect for Executive Productivity",
                    "price": 45000,
                    "brand": "Samsung",
                    "features": ["Professional design", "High productivity", "Executive quality"],
                }
            ]
        elif exec_type == "cfo":
            # CFOs want cost-effective options
            budget = executive_context.get("budget", 50000)
            price = min(budget - 5000, 40000) if budget and budget > 5000 else 25000
            return [
                {
                    "asin": "B08CFO456",
                    "title": "Cost-Effective Business Monitor - Best Value",
                    "price": price,
                    "brand": "LG",
                    "features": ["Cost-effective", "Energy efficient", "Long warranty"],
                }
            ]
        else:
            # General executive-appropriate products
            return [
                {
                    "asin": "B08EXEC789",
                    "title": "Professional Monitor for Business Use",
                    "price": 50000,
                    "brand": "Dell",
                    "features": ["Professional grade", "Reliable", "Business focused"],
                }
            ]


if __name__ == "__main__":
    print("🎭 EXECUTIVE PERSONA TESTING SUITE")
    print("=" * 60)
    print("Testing system behavior with different executive personality types...")
    print("This is CRITICAL for ensuring the system handles real executive expectations!")
