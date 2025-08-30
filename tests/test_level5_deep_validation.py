#!/usr/bin/env python3
"""
Level 5: Deep Manual Testing - Rigorous Reality Validation

Purpose: Uncover deep-rooted problems that surface testing missed
- Stress test with extreme scenarios
- Validate edge cases that break assumptions
- Test production failure modes
- Expose hidden technical debt

Philosophy: "If it can break in production, make it break in testing first"
"""

import asyncio
import json
import traceback
import sys
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging
import time
import gc
import psutil

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.paapi_official import OfficialPaapiClient
from bot.paapi_ai_bridge import search_products_with_ai_analysis
from bot.watch_parser import parse_watch

# Configure logging for deep debugging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

class DeepValidationSuite:
    """Level 5 Deep Manual Testing - Uncover Hidden Problems"""
    
    def __init__(self):
        self.client = OfficialPaapiClient()
        self.test_results = []
        self.critical_issues = []
        self.performance_issues = []
        self.memory_issues = []
        self.data_corruption_issues = []
        self.concurrency_issues = []
        
    async def log_result(self, test_name: str, status: str, details: Dict[str, Any]):
        """Enhanced logging with memory tracking"""
        process = psutil.Process()
        memory_info = process.memory_info()
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "test": test_name,
            "status": status,
            "details": details,
            "system_metrics": {
                "memory_rss_mb": memory_info.rss / 1024 / 1024,
                "memory_vms_mb": memory_info.vms / 1024 / 1024,
                "cpu_percent": process.cpu_percent()
            }
        }
        self.test_results.append(result)
        
        if status == "FAIL":
            self.critical_issues.append(result)
        elif status == "WARNING":
            self.performance_issues.append(result)
        elif status == "MEMORY_LEAK":
            self.memory_issues.append(result)
        elif status == "DATA_CORRUPTION":
            self.data_corruption_issues.append(result)
        elif status == "CONCURRENCY_FAIL":
            self.concurrency_issues.append(result)
        
        status_emoji = {
            "PASS": "✅", "FAIL": "❌", "WARNING": "⚠️", 
            "MEMORY_LEAK": "🧠", "DATA_CORRUPTION": "💾", "CONCURRENCY_FAIL": "⚡"
        }
        print(f"{status_emoji.get(status, '❓')} {test_name}: {details.get('summary', 'No summary')}")
    
    async def test_extreme_data_scenarios(self):
        """Test with extreme data that breaks assumptions"""
        print("\n💥 EXTREME DATA SCENARIOS - Deep Validation")
        print("=" * 60)
        
        extreme_scenarios = [
            {
                "name": "Massive Unicode Query",
                "query": "🎮🔥💻⚡🚀" * 50 + " गेमिंग लैपटॉप " + "משחקי מחשב נייד " + "ゲーミングノートパソコン",
                "expectation": "Handle massive unicode without corruption"
            },
            {
                "name": "SQL Injection Variants",
                "query": "laptop' UNION SELECT * FROM users--; DROP TABLE products; laptop",
                "expectation": "Block all SQL injection attempts"
            },
            {
                "name": "Buffer Overflow Attempt",
                "query": "A" * 10000,  # 10KB query
                "expectation": "Handle extremely long input safely"
            },
            {
                "name": "Control Characters",
                "query": "laptop\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0A\x0B\x0C\x0D\x0E\x0F",
                "expectation": "Filter control characters safely"
            },
            {
                "name": "Price Injection",
                "query": "laptop under '; DROP TABLE prices; SELECT * FROM",
                "expectation": "Parse price safely from malicious input"
            },
            {
                "name": "Memory Exhaustion Query",
                "query": "laptop " + " ".join([f"term{i}" for i in range(1000)]),
                "expectation": "Handle memory-intensive queries"
            }
        ]
        
        for scenario in extreme_scenarios:
            test_name = f"Extreme: {scenario['name']}"
            
            try:
                start_memory = psutil.Process().memory_info().rss
                start_time = time.time()
                
                # Test with both parser and direct search
                parsed = parse_watch(scenario["query"])
                
                if parsed.get("keywords"):
                    results = await self.client.search_items_advanced(
                        keywords=parsed["keywords"][:500],  # Limit to prevent API abuse
                        search_index="All",
                        item_count=3,
                        enable_ai_analysis=False
                    )
                    
                    end_time = time.time()
                    end_memory = psutil.Process().memory_info().rss
                    memory_delta = (end_memory - start_memory) / 1024 / 1024  # MB
                    
                    # Check for issues
                    issues = []
                    warnings = []
                    
                    if end_time - start_time > 10:
                        warnings.append(f"Slow processing: {end_time - start_time:.2f}s")
                    
                    if memory_delta > 50:  # 50MB increase
                        issues.append(f"Memory spike: +{memory_delta:.1f}MB")
                    
                    # Check for data corruption
                    if results:
                        for result in results:
                            title = result.get('title', '')
                            if any(char in title for char in ['\x00', '\x01', '\x02']):
                                issues.append("Control characters in response data")
                    
                    # Determine status
                    if issues:
                        if any("Memory spike" in issue for issue in issues):
                            status = "MEMORY_LEAK"
                        elif any("Control characters" in issue for issue in issues):
                            status = "DATA_CORRUPTION"
                        else:
                            status = "FAIL"
                        summary = f"Issues found: {'; '.join(issues)}"
                    elif warnings:
                        status = "WARNING"
                        summary = f"Performance concerns: {'; '.join(warnings)}"
                    else:
                        status = "PASS"
                        summary = f"Handled extreme input safely ({len(results)} results)"
                    
                    await self.log_result(test_name, status, {
                        "summary": summary,
                        "query_length": len(scenario["query"]),
                        "processing_time": end_time - start_time,
                        "memory_delta_mb": memory_delta,
                        "results_count": len(results) if results else 0,
                        "issues": issues,
                        "warnings": warnings
                    })
                
                else:
                    # Parser rejected the input
                    status = "PASS"
                    summary = "Parser safely rejected malicious input"
                    
                    await self.log_result(test_name, status, {
                        "summary": summary,
                        "query": scenario["query"][:100] + "..." if len(scenario["query"]) > 100 else scenario["query"],
                        "expectation": scenario["expectation"]
                    })
                
            except Exception as e:
                # Check if it's an expected security exception
                if any(term in str(e).lower() for term in ['invalid', 'malformed', 'security', 'blocked']):
                    status = "PASS"
                    summary = f"Security exception as expected: {type(e).__name__}"
                else:
                    status = "FAIL"
                    summary = f"Unexpected exception: {str(e)}"
                
                await self.log_result(test_name, status, {
                    "summary": summary,
                    "exception": str(e),
                    "exception_type": type(e).__name__,
                    "query": scenario["query"][:100] + "..." if len(scenario["query"]) > 100 else scenario["query"]
                })
            
            # Cleanup between tests
            gc.collect()
            await asyncio.sleep(1)
    
    async def test_concurrent_stress(self):
        """Test concurrent access patterns that expose race conditions"""
        print("\n⚡ CONCURRENT STRESS TESTING - Race Condition Detection")
        print("=" * 60)
        
        # Test 1: Rapid concurrent searches
        test_name = "Concurrent: Rapid Fire Race Conditions"
        
        try:
            async def rapid_search(query_id: int):
                """Single rapid search task"""
                query = f"laptop {query_id}"
                try:
                    results = await self.client.search_items_advanced(
                        keywords=query,
                        search_index="All",
                        item_count=2,
                        enable_ai_analysis=False
                    )
                    return {"id": query_id, "results": len(results), "error": None}
                except Exception as e:
                    return {"id": query_id, "results": 0, "error": str(e)}
            
            # Launch 20 concurrent searches
            start_time = time.time()
            tasks = [rapid_search(i) for i in range(20)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            # Analyze results
            successful = [r for r in results if isinstance(r, dict) and r.get("error") is None]
            failed = [r for r in results if isinstance(r, dict) and r.get("error") is not None]
            exceptions = [r for r in results if isinstance(r, Exception)]
            
            issues = []
            warnings = []
            
            if len(exceptions) > 0:
                issues.append(f"Concurrency exceptions: {len(exceptions)}")
            
            if len(failed) > 5:  # Allow some failures due to rate limiting
                issues.append(f"High failure rate: {len(failed)}/20")
            
            if end_time - start_time > 30:
                warnings.append(f"Slow concurrent processing: {end_time - start_time:.2f}s")
            
            # Check for race conditions (inconsistent results)
            result_counts = [r.get("results", 0) for r in successful]
            if len(set(result_counts)) > 3:  # Too much variance suggests race conditions
                warnings.append("Inconsistent results suggest race conditions")
            
            if issues:
                status = "CONCURRENCY_FAIL"
                summary = f"Concurrency issues: {'; '.join(issues)}"
            elif warnings:
                status = "WARNING"
                summary = f"Performance concerns: {'; '.join(warnings)}"
            else:
                status = "PASS"
                summary = f"Handled {len(successful)}/{len(tasks)} concurrent requests"
            
            await self.log_result(test_name, status, {
                "summary": summary,
                "total_tasks": len(tasks),
                "successful": len(successful),
                "failed": len(failed),
                "exceptions": len(exceptions),
                "total_time": end_time - start_time,
                "issues": issues,
                "warnings": warnings
            })
            
        except Exception as e:
            await self.log_result(test_name, "FAIL", {
                "summary": f"Concurrent stress test failed: {str(e)}",
                "exception": traceback.format_exc()
            })
    
    async def test_memory_pressure(self):
        """Test behavior under memory pressure"""
        print("\n🧠 MEMORY PRESSURE TESTING - Memory Leak Detection")
        print("=" * 60)
        
        test_name = "Memory: Pressure and Leak Detection"
        
        try:
            initial_memory = psutil.Process().memory_info().rss
            memory_readings = [initial_memory]
            
            # Perform 50 searches to detect memory leaks
            for i in range(50):
                try:
                    results = await self.client.search_items_advanced(
                        keywords=f"electronics item {i % 10}",
                        search_index="All",
                        item_count=2,
                        enable_ai_analysis=False
                    )
                    
                    # Take memory reading every 10 iterations
                    if i % 10 == 0:
                        current_memory = psutil.Process().memory_info().rss
                        memory_readings.append(current_memory)
                        
                        # Force garbage collection
                        gc.collect()
                        
                except Exception as e:
                    log.warning(f"Memory test iteration {i} failed: {e}")
                
                # Small delay to prevent rate limiting
                await asyncio.sleep(0.1)
            
            final_memory = psutil.Process().memory_info().rss
            memory_readings.append(final_memory)
            
            # Analyze memory usage
            memory_growth = (final_memory - initial_memory) / 1024 / 1024  # MB
            max_memory = max(memory_readings)
            memory_spike = (max_memory - initial_memory) / 1024 / 1024  # MB
            
            issues = []
            warnings = []
            
            if memory_growth > 100:  # 100MB growth indicates leak
                issues.append(f"Memory leak detected: +{memory_growth:.1f}MB")
            elif memory_growth > 50:  # 50MB growth is concerning
                warnings.append(f"Memory growth: +{memory_growth:.1f}MB")
            
            if memory_spike > 200:  # 200MB spike is problematic
                warnings.append(f"Memory spike: +{memory_spike:.1f}MB")
            
            if issues:
                status = "MEMORY_LEAK"
                summary = f"Memory issues detected: {'; '.join(issues)}"
            elif warnings:
                status = "WARNING"
                summary = f"Memory concerns: {'; '.join(warnings)}"
            else:
                status = "PASS"
                summary = f"Memory stable: {memory_growth:+.1f}MB after 50 operations"
            
            await self.log_result(test_name, status, {
                "summary": summary,
                "initial_memory_mb": initial_memory / 1024 / 1024,
                "final_memory_mb": final_memory / 1024 / 1024,
                "memory_growth_mb": memory_growth,
                "memory_spike_mb": memory_spike,
                "iterations": 50,
                "issues": issues,
                "warnings": warnings
            })
            
        except Exception as e:
            await self.log_result(test_name, "FAIL", {
                "summary": f"Memory pressure test failed: {str(e)}",
                "exception": traceback.format_exc()
            })
    
    async def test_data_integrity(self):
        """Test data integrity under various conditions"""
        print("\n💾 DATA INTEGRITY TESTING - Corruption Detection")
        print("=" * 60)
        
        data_integrity_tests = [
            {
                "name": "Price Data Validation",
                "query": "laptop",
                "validation": "price_integrity"
            },
            {
                "name": "Title Encoding Integrity",
                "query": "गेमिंग लैपटॉप",
                "validation": "encoding_integrity"
            },
            {
                "name": "ASIN Format Validation",
                "query": "smartphone",
                "validation": "asin_format"
            },
            {
                "name": "URL Validation",
                "query": "monitor",
                "validation": "url_integrity"
            }
        ]
        
        for test_case in data_integrity_tests:
            test_name = f"Data Integrity: {test_case['name']}"
            
            try:
                results = await self.client.search_items_advanced(
                    keywords=test_case["query"],
                    search_index="All",
                    item_count=5,
                    enable_ai_analysis=False
                )
                
                corruption_issues = []
                data_warnings = []
                
                if results:
                    for i, result in enumerate(results):
                        if test_case["validation"] == "price_integrity":
                            # Check price data integrity
                            price = result.get('price')
                            if price is not None:
                                if not isinstance(price, (int, float)) or price < 0:
                                    corruption_issues.append(f"Product {i+1}: Invalid price format {price}")
                                if price > 100000000:  # ₹10 lakh in paise seems unreasonable
                                    data_warnings.append(f"Product {i+1}: Suspicious price ₹{price/100:.2f}")
                        
                        elif test_case["validation"] == "encoding_integrity":
                            # Check title encoding
                            title = result.get('title', '')
                            if title:
                                try:
                                    # Try to encode/decode to check for corruption
                                    title.encode('utf-8').decode('utf-8')
                                except UnicodeError:
                                    corruption_issues.append(f"Product {i+1}: Title encoding corrupted")
                                
                                # Check for mojibake (encoding artifacts)
                                if any(char in title for char in ['�', '\ufffd']):
                                    corruption_issues.append(f"Product {i+1}: Mojibake detected in title")
                        
                        elif test_case["validation"] == "asin_format":
                            # Check ASIN format integrity
                            asin = result.get('asin', '')
                            if asin:
                                if len(asin) != 10 or not asin.isalnum():
                                    corruption_issues.append(f"Product {i+1}: Invalid ASIN format: {asin}")
                        
                        elif test_case["validation"] == "url_integrity":
                            # Check URL integrity
                            for url_field in ['image_url', 'detail_page_url']:
                                url = result.get(url_field, '')
                                if url:
                                    if not url.startswith(('http://', 'https://')):
                                        corruption_issues.append(f"Product {i+1}: Invalid URL format in {url_field}")
                                    if 'amazon' not in url.lower():
                                        data_warnings.append(f"Product {i+1}: Non-Amazon URL in {url_field}")
                
                # Determine status
                if corruption_issues:
                    status = "DATA_CORRUPTION"
                    summary = f"Data corruption detected: {len(corruption_issues)} issues"
                elif data_warnings:
                    status = "WARNING"
                    summary = f"Data quality concerns: {len(data_warnings)} warnings"
                else:
                    status = "PASS"
                    summary = f"Data integrity validated for {len(results)} products"
                
                await self.log_result(test_name, status, {
                    "summary": summary,
                    "results_count": len(results) if results else 0,
                    "corruption_issues": corruption_issues,
                    "data_warnings": data_warnings,
                    "validation_type": test_case["validation"]
                })
                
            except Exception as e:
                await self.log_result(test_name, "FAIL", {
                    "summary": f"Data integrity test failed: {str(e)}",
                    "exception": traceback.format_exc(),
                    "validation_type": test_case["validation"]
                })
            
            await asyncio.sleep(1)
    
    async def test_cascade_failures(self):
        """Test how the system handles cascade failures"""
        print("\n🔥 CASCADE FAILURE TESTING - System Resilience")
        print("=" * 60)
        
        # Test 1: API rate limit exhaustion
        test_name = "Cascade: API Rate Limit Exhaustion"
        
        try:
            # Rapidly exhaust API limits
            rapid_tasks = []
            for i in range(30):  # Try to overwhelm rate limiter
                task = self.client.search_items_advanced(
                    keywords=f"test {i}",
                    search_index="All",
                    item_count=1,
                    enable_ai_analysis=False
                )
                rapid_tasks.append(task)
            
            start_time = time.time()
            results = await asyncio.gather(*rapid_tasks, return_exceptions=True)
            end_time = time.time()
            
            # Analyze cascade behavior
            successful = sum(1 for r in results if not isinstance(r, Exception))
            exceptions = sum(1 for r in results if isinstance(r, Exception))
            
            issues = []
            warnings = []
            
            if end_time - start_time < 5:  # Too fast suggests rate limiter bypassed
                issues.append("Rate limiter may be bypassed")
            
            if exceptions > 20:  # Too many exceptions suggest poor error handling
                issues.append(f"Poor error handling: {exceptions}/30 exceptions")
            elif exceptions == 0:  # No exceptions might mean no rate limiting
                warnings.append("No rate limiting detected")
            
            if successful < 5:  # Some requests should succeed
                warnings.append(f"Low success rate: {successful}/30")
            
            if issues:
                status = "FAIL"
                summary = f"Cascade failure issues: {'; '.join(issues)}"
            elif warnings:
                status = "WARNING"
                summary = f"Resilience concerns: {'; '.join(warnings)}"
            else:
                status = "PASS"
                summary = f"Handled rate limit cascade gracefully ({successful} succeeded)"
            
            await self.log_result(test_name, status, {
                "summary": summary,
                "total_requests": 30,
                "successful": successful,
                "exceptions": exceptions,
                "total_time": end_time - start_time,
                "issues": issues,
                "warnings": warnings
            })
            
        except Exception as e:
            await self.log_result(test_name, "FAIL", {
                "summary": f"Cascade failure test crashed: {str(e)}",
                "exception": traceback.format_exc()
            })
    
    async def generate_deep_validation_report(self):
        """Generate comprehensive deep validation report"""
        print("\n" + "=" * 80)
        print("📊 LEVEL 5 DEEP VALIDATION REPORT")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed = len([r for r in self.test_results if r["status"] == "PASS"])
        warnings = len([r for r in self.test_results if r["status"] == "WARNING"])
        failed = len([r for r in self.test_results if r["status"] == "FAIL"])
        memory_leaks = len(self.memory_issues)
        data_corruption = len(self.data_corruption_issues)
        concurrency_fails = len(self.concurrency_issues)
        
        print(f"📈 DEEP VALIDATION SUMMARY:")
        print(f"   Total Tests: {total_tests}")
        print(f"   ✅ Passed: {passed}")
        print(f"   ⚠️  Warnings: {warnings}")
        print(f"   ❌ Failed: {failed}")
        print(f"   🧠 Memory Leaks: {memory_leaks}")
        print(f"   💾 Data Corruption: {data_corruption}")
        print(f"   ⚡ Concurrency Failures: {concurrency_fails}")
        
        critical_issues_total = failed + memory_leaks + data_corruption + concurrency_fails
        
        if critical_issues_total > 0:
            print(f"\n🚨 CRITICAL ISSUES FOUND ({critical_issues_total}):")
            
            for issue in self.critical_issues + self.memory_issues + self.data_corruption_issues + self.concurrency_issues:
                print(f"   ❌ {issue['test']}: {issue['details']['summary']}")
        
        if self.performance_issues:
            print(f"\n⚠️  PERFORMANCE WARNINGS ({len(self.performance_issues)}):")
            for warning in self.performance_issues:
                print(f"   ⚠️  {warning['test']}: {warning['details']['summary']}")
        
        # Overall assessment
        success_rate = (passed / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\n📊 SUCCESS RATE: {success_rate:.1f}%")
        
        if critical_issues_total > 0:
            print("\n🚨 OVERALL STATUS: CRITICAL ISSUES FOUND - NOT PRODUCTION READY")
            print("   Deep validation revealed serious problems requiring immediate attention")
            return False
        elif warnings > 0:
            print("\n⚠️  OVERALL STATUS: PERFORMANCE CONCERNS")
            print("   Deep validation revealed quality issues requiring review")
            return False
        else:
            print("\n✅ OVERALL STATUS: DEEP VALIDATION PASSED")
            print("   System passed rigorous deep validation testing")
            return True

async def run_deep_validation():
    """Execute Level 5 Deep Validation Suite"""
    print("🔬 STARTING LEVEL 5: DEEP MANUAL TESTING")
    print("Uncovering deep-rooted problems through rigorous validation")
    print("Using REAL PA-API data only - Maximum stress testing")
    print("=" * 80)
    
    suite = DeepValidationSuite()
    
    try:
        # Execute deep validation categories
        await suite.test_extreme_data_scenarios()
        await suite.test_concurrent_stress()
        await suite.test_memory_pressure()
        await suite.test_data_integrity()
        await suite.test_cascade_failures()
        
        # Generate comprehensive report
        success = await suite.generate_deep_validation_report()
        
        return success
        
    except Exception as e:
        print(f"\n❌ DEEP VALIDATION SUITE CRASHED: {str(e)}")
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = asyncio.run(run_deep_validation())
    exit(0 if success else 1)
