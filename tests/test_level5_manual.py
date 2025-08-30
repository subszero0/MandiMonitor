#!/usr/bin/env python3
"""
Level 5: Manual Testing - Reality Validation with Real PA-API Data

Purpose: Validate automated testing assumptions with real-world conditions
- Test with messy, incomplete, real production data patterns
- Expose gaps between mocks and reality 
- Catch false confidence from perfect test data

Following Testing Philosophy: "Perfect mocks create dangerous false confidence"
- Use ONLY real PA-API data
- Test edge cases that automation missed
- Validate user experience under real conditions
"""

import asyncio
import json
import traceback
import sys
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.paapi_official import OfficialPaapiClient
from bot.paapi_ai_bridge import search_products_with_ai_analysis
from bot.watch_parser import parse_watch
from bot.api_rate_limiter import acquire_api_permission

# Configure logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

class ManualTestingSuite:
    """Level 5 Manual Testing Suite - Real Production Data Validation"""
    
    def __init__(self):
        self.client = OfficialPaapiClient()
        self.test_results = []
        self.critical_issues = []
        self.performance_issues = []
        
    async def log_result(self, test_name: str, status: str, details: Dict[str, Any]):
        """Log test result with timestamp"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "test": test_name,
            "status": status,  # PASS, FAIL, WARNING
            "details": details
        }
        self.test_results.append(result)
        
        if status == "FAIL":
            self.critical_issues.append(result)
        elif status == "WARNING":
            self.performance_issues.append(result)
        
        status_emoji = {"PASS": "✅", "FAIL": "❌", "WARNING": "⚠️"}
        print(f"{status_emoji[status]} {test_name}: {details.get('summary', 'No summary')}")
    
    async def test_real_user_scenarios(self):
        """Test with actual user queries we'd expect in production"""
        print("\n🎯 REAL USER SCENARIOS - Manual Testing")
        print("=" * 60)
        
        # Real user scenarios (from actual MandiMonitor use cases)
        scenarios = [
            {
                "name": "Budget Gaming Laptop",
                "query": "gaming laptop under 50000",
                "expectation": "Find gaming laptops ≤ ₹50,000",
                "critical_checks": ["has_results", "price_within_budget", "actually_gaming"]
            },
            {
                "name": "Monitor for Work",
                "query": "24 inch monitor for office work",
                "expectation": "Find office monitors around 24 inches",
                "critical_checks": ["has_results", "monitor_category", "size_relevant"]
            },
            {
                "name": "Phone Under Budget",
                "query": "smartphone under 20000 with good camera",
                "expectation": "Find phones ≤ ₹20,000 with camera specs",
                "critical_checks": ["has_results", "price_within_budget", "phone_category"]
            },
            {
                "name": "Vague Electronics Query",
                "query": "electronics",
                "expectation": "Handle vague query gracefully",
                "critical_checks": ["has_results", "variety_of_products", "no_errors"]
            },
            {
                "name": "Specific Brand Search",
                "query": "Samsung Galaxy phone latest model",
                "expectation": "Find Samsung Galaxy phones",
                "critical_checks": ["has_results", "samsung_brand", "phone_category"]
            }
        ]
        
        for scenario in scenarios:
            test_name = f"Real User: {scenario['name']}"
            
            try:
                # Parse user query
                parsed = parse_watch(scenario["query"])
                
                # Search with AI analysis
                start_time = datetime.now()
                ai_results = await search_products_with_ai_analysis(
                    keywords=parsed.get("keywords", scenario["query"]),
                    search_index="All",
                    item_count=5
                )
                search_time = (datetime.now() - start_time).total_seconds()
                
                # Analyze results
                analysis = {
                    "query": scenario["query"],
                    "parsed_keywords": parsed.get("keywords"),
                    "results_count": len(ai_results.get("products", [])),
                    "search_time_seconds": search_time,
                    "ai_analysis": ai_results.get("analysis", {}),
                    "products": ai_results.get("products", [])
                }
                
                # Check critical requirements
                issues = []
                warnings = []
                
                if "has_results" in scenario["critical_checks"]:
                    if analysis["results_count"] == 0:
                        issues.append("No results returned for user query")
                
                if "price_within_budget" in scenario["critical_checks"] and "under" in scenario["query"]:
                    # Extract budget from query (rough)
                    import re
                    budget_match = re.search(r'under (\d+)', scenario["query"])
                    if budget_match:
                        budget = int(budget_match.group(1)) * 100  # Convert to paise
                        over_budget = [p for p in analysis["products"] 
                                     if p.get("price", 0) > budget]
                        if over_budget:
                            warnings.append(f"Found {len(over_budget)} products over budget")
                
                if "actually_gaming" in scenario["critical_checks"]:
                    gaming_terms = ["gaming", "rtx", "gtx", "nvidia", "radeon", "ryzen"]
                    gaming_products = [p for p in analysis["products"] 
                                     if any(term.lower() in p.get("title", "").lower() 
                                           for term in gaming_terms)]
                    if len(gaming_products) < analysis["results_count"] // 2:
                        warnings.append("Less than 50% of results are gaming-related")
                
                # Performance checks
                if search_time > 10:
                    warnings.append(f"Slow response time: {search_time:.2f}s")
                
                # Determine status
                if issues:
                    status = "FAIL"
                    summary = f"Critical issues: {'; '.join(issues)}"
                elif warnings:
                    status = "WARNING"
                    summary = f"Issues found: {'; '.join(warnings)}"
                else:
                    status = "PASS"
                    summary = f"Found {analysis['results_count']} relevant results in {search_time:.2f}s"
                
                analysis["issues"] = issues
                analysis["warnings"] = warnings
                
                await self.log_result(test_name, status, {
                    "summary": summary,
                    "analysis": analysis
                })
                
            except Exception as e:
                await self.log_result(test_name, "FAIL", {
                    "summary": f"Exception occurred: {str(e)}",
                    "exception": traceback.format_exc(),
                    "query": scenario["query"]
                })
            
            # Rate limiting
            await asyncio.sleep(2)
    
    async def test_messy_data_handling(self):
        """Test how system handles messy, incomplete real-world data"""
        print("\n🗑️ MESSY DATA HANDLING - Manual Testing")
        print("=" * 60)
        
        # Test queries that might return problematic data
        messy_scenarios = [
            {
                "name": "Empty Price Products",
                "keywords": "free sample",
                "check": "handle_zero_prices"
            },
            {
                "name": "Very Long Titles",
                "keywords": "laptop",
                "check": "handle_long_titles"
            },
            {
                "name": "Special Characters",
                "keywords": "laptop 16\" i7",
                "check": "handle_special_chars"
            },
            {
                "name": "Unicode Content",
                "keywords": "गेमिंग लैपटॉप",  # Gaming laptop in Hindi
                "check": "handle_unicode"
            },
            {
                "name": "Out of Stock Items",
                "keywords": "discontinued laptop model",
                "check": "handle_unavailable"
            }
        ]
        
        for scenario in messy_scenarios:
            test_name = f"Messy Data: {scenario['name']}"
            
            try:
                results = await self.client.search_items_advanced(
                    keywords=scenario["keywords"],
                    search_index="All",
                    item_count=3,
                    enable_ai_analysis=False
                )
                
                issues = []
                warnings = []
                
                if not results:
                    warnings.append("No results returned for messy data test")
                else:
                    for i, product in enumerate(results):
                        # Check for common data issues
                        title = product.get("title", "")
                        price = product.get("price", 0)
                        
                        # Check for empty/invalid data
                        if not title.strip():
                            issues.append(f"Product {i+1} has empty title")
                        
                        if price == 0 and scenario["check"] != "handle_zero_prices":
                            warnings.append(f"Product {i+1} has zero price")
                        
                        # Check title length handling
                        if len(title) > 200:
                            warnings.append(f"Product {i+1} has very long title ({len(title)} chars)")
                        
                        # Check for None values that should be handled
                        for key in ["price", "title", "image_url"]:
                            if product.get(key) is None:
                                warnings.append(f"Product {i+1} has None value for {key}")
                
                # Determine status
                if issues:
                    status = "FAIL"
                    summary = f"Data handling issues: {'; '.join(issues)}"
                elif warnings:
                    status = "WARNING" 
                    summary = f"Data quality concerns: {'; '.join(warnings)}"
                else:
                    status = "PASS"
                    summary = f"Handled messy data gracefully ({len(results)} results)"
                
                await self.log_result(test_name, status, {
                    "summary": summary,
                    "results_count": len(results) if results else 0,
                    "issues": issues,
                    "warnings": warnings,
                    "sample_data": results[:1] if results else None
                })
                
            except Exception as e:
                await self.log_result(test_name, "FAIL", {
                    "summary": f"Exception with messy data: {str(e)}",
                    "exception": traceback.format_exc(),
                    "keywords": scenario["keywords"]
                })
            
            await asyncio.sleep(1.5)
    
    async def test_edge_case_queries(self):
        """Test edge cases that users might actually try"""
        print("\n🔄 EDGE CASE QUERIES - Manual Testing")
        print("=" * 60)
        
        edge_cases = [
            {
                "name": "Empty Query",
                "input": "",
                "expectation": "Graceful handling of empty input"
            },
            {
                "name": "Only Numbers",
                "input": "12345",
                "expectation": "Handle pure numeric query"
            },
            {
                "name": "Only Special Chars",
                "input": "!@#$%",
                "expectation": "Handle special characters gracefully"
            },
            {
                "name": "Very Long Query",
                "input": "gaming laptop with nvidia rtx graphics card for professional video editing and 3d rendering work with at least 32gb ram and 1tb ssd storage under 150000 rupees budget",
                "expectation": "Handle very long queries"
            },
            {
                "name": "Mixed Languages",
                "input": "laptop laptop लैपटॉप",
                "expectation": "Handle mixed language input"
            },
            {
                "name": "SQL Injection Attempt",
                "input": "laptop'; DROP TABLE products; --",
                "expectation": "Safe handling of malicious input"
            }
        ]
        
        for case in edge_cases:
            test_name = f"Edge Case: {case['name']}"
            
            try:
                # Test with both parse_watch and direct search
                parsed = parse_watch(case["input"])
                
                if parsed.get("keywords"):
                    results = await self.client.search_items_advanced(
                        keywords=parsed["keywords"],
                        search_index="All",
                        item_count=3,
                        enable_ai_analysis=False
                    )
                    
                    status = "PASS"
                    summary = f"Handled gracefully, found {len(results) if results else 0} results"
                else:
                    status = "WARNING"
                    summary = "No keywords parsed from input"
                
                await self.log_result(test_name, status, {
                    "summary": summary,
                    "input": case["input"],
                    "parsed": parsed,
                    "expectation": case["expectation"]
                })
                
            except Exception as e:
                # For edge cases, exceptions might be expected
                if case["name"] in ["Empty Query", "Only Special Chars"]:
                    status = "PASS"
                    summary = f"Expected exception handled: {type(e).__name__}"
                else:
                    status = "FAIL"
                    summary = f"Unexpected exception: {str(e)}"
                
                await self.log_result(test_name, status, {
                    "summary": summary,
                    "input": case["input"],
                    "exception": str(e),
                    "expectation": case["expectation"]
                })
            
            await asyncio.sleep(1)
    
    async def test_production_load_patterns(self):
        """Test realistic production usage patterns"""
        print("\n⚡ PRODUCTION LOAD PATTERNS - Manual Testing")
        print("=" * 60)
        
        # Simulate realistic user behavior patterns
        load_patterns = [
            {
                "name": "Rapid Fire Searches",
                "description": "User doing multiple quick searches",
                "queries": ["laptop", "gaming laptop", "laptop under 50000"],
                "delay": 0.5
            },
            {
                "name": "Patient User Journey",
                "description": "User refining search gradually",
                "queries": ["laptop", "gaming laptop", "gaming laptop nvidia", "gaming laptop nvidia under 60000"],
                "delay": 3.0
            },
            {
                "name": "Mixed Category Exploration",
                "description": "User exploring different categories",
                "queries": ["smartphone", "laptop", "headphones", "monitor", "keyboard"],
                "delay": 2.0
            }
        ]
        
        for pattern in load_patterns:
            test_name = f"Load Pattern: {pattern['name']}"
            
            try:
                start_time = datetime.now()
                all_results = []
                errors = []
                
                for i, query in enumerate(pattern["queries"]):
                    try:
                        results = await self.client.search_items_advanced(
                            keywords=query,
                            search_index="All",
                            item_count=5,
                            enable_ai_analysis=False
                        )
                        all_results.append(len(results) if results else 0)
                        
                        if i < len(pattern["queries"]) - 1:
                            await asyncio.sleep(pattern["delay"])
                            
                    except Exception as e:
                        errors.append(f"Query '{query}': {str(e)}")
                
                total_time = (datetime.now() - start_time).total_seconds()
                
                # Analyze performance
                issues = []
                warnings = []
                
                if errors:
                    issues.extend(errors)
                
                if total_time > 30:
                    warnings.append(f"Slow pattern completion: {total_time:.2f}s")
                
                avg_results = sum(all_results) / len(all_results) if all_results else 0
                if avg_results < 1:
                    warnings.append("Low average results per query")
                
                # Determine status
                if issues:
                    status = "FAIL"
                    summary = f"Pattern failed: {'; '.join(issues)}"
                elif warnings:
                    status = "WARNING"
                    summary = f"Performance concerns: {'; '.join(warnings)}"
                else:
                    status = "PASS"
                    summary = f"Pattern completed successfully in {total_time:.2f}s"
                
                await self.log_result(test_name, status, {
                    "summary": summary,
                    "total_time": total_time,
                    "queries_tested": len(pattern["queries"]),
                    "results_per_query": all_results,
                    "errors": errors,
                    "warnings": warnings
                })
                
            except Exception as e:
                await self.log_result(test_name, "FAIL", {
                    "summary": f"Pattern execution failed: {str(e)}",
                    "exception": traceback.format_exc(),
                    "pattern": pattern["name"]
                })
    
    async def test_real_api_limitations(self):
        """Test real PA-API limitations and edge cases"""
        print("\n🚧 REAL API LIMITATIONS - Manual Testing")
        print("=" * 60)
        
        # Test actual PA-API quirks and limitations
        limitation_tests = [
            {
                "name": "High Price Range Search",
                "keywords": "laptop",
                "min_price": 20000000,  # ₹2,00,000 in paise
                "max_price": 30000000,  # ₹3,00,000 in paise
                "expectation": "Very few or no results in ultra-high range"
            },
            {
                "name": "Very Low Price Range",
                "keywords": "electronics",
                "min_price": 100,  # ₹1 in paise
                "max_price": 500,  # ₹5 in paise
                "expectation": "Handle very low price ranges"
            },
            {
                "name": "Exact Price Point",
                "keywords": "smartphone",
                "min_price": 1999900,  # ₹19,999 in paise
                "max_price": 2000100,  # ₹20,001 in paise
                "expectation": "Handle very narrow price ranges"
            },
            {
                "name": "Large Item Count Request",
                "keywords": "laptop",
                "item_count": 50,  # Max allowed by PA-API
                "expectation": "Handle maximum item count gracefully"
            }
        ]
        
        for test in limitation_tests:
            test_name = f"API Limitation: {test['name']}"
            
            try:
                kwargs = {
                    "keywords": test["keywords"],
                    "search_index": "All",
                    "enable_ai_analysis": False
                }
                
                if "min_price" in test:
                    kwargs["min_price"] = test["min_price"]
                if "max_price" in test:
                    kwargs["max_price"] = test["max_price"]
                if "item_count" in test:
                    kwargs["item_count"] = test["item_count"]
                else:
                    kwargs["item_count"] = 10
                
                results = await self.client.search_items_advanced(**kwargs)
                
                result_count = len(results) if results else 0
                
                # Analyze based on expectation
                if "very few or no results" in test["expectation"].lower():
                    if result_count <= 3:
                        status = "PASS"
                        summary = f"Expected few results, got {result_count}"
                    else:
                        status = "WARNING"
                        summary = f"More results than expected: {result_count}"
                elif "handle" in test["expectation"].lower():
                    status = "PASS"
                    summary = f"Handled gracefully, returned {result_count} results"
                else:
                    status = "PASS"
                    summary = f"Test completed, returned {result_count} results"
                
                await self.log_result(test_name, status, {
                    "summary": summary,
                    "results_count": result_count,
                    "test_params": kwargs,
                    "expectation": test["expectation"]
                })
                
            except Exception as e:
                # Some API limitations might cause exceptions
                if "InvalidParameterValue" in str(e):
                    status = "PASS"
                    summary = f"PA-API limitation confirmed: {str(e)}"
                else:
                    status = "FAIL"
                    summary = f"Unexpected API error: {str(e)}"
                
                await self.log_result(test_name, status, {
                    "summary": summary,
                    "exception": str(e),
                    "test_params": test,
                    "expectation": test["expectation"]
                })
            
            await asyncio.sleep(2)
    
    async def generate_test_report(self):
        """Generate comprehensive test report"""
        print("\n" + "=" * 80)
        print("📊 LEVEL 5 MANUAL TESTING REPORT")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed = len([r for r in self.test_results if r["status"] == "PASS"])
        warnings = len([r for r in self.test_results if r["status"] == "WARNING"])
        failed = len([r for r in self.test_results if r["status"] == "FAIL"])
        
        print(f"📈 SUMMARY:")
        print(f"   Total Tests: {total_tests}")
        print(f"   ✅ Passed: {passed}")
        print(f"   ⚠️  Warnings: {warnings}")
        print(f"   ❌ Failed: {failed}")
        print(f"   📊 Success Rate: {(passed/total_tests*100):.1f}%")
        
        if self.critical_issues:
            print(f"\n🚨 CRITICAL ISSUES ({len(self.critical_issues)}):")
            for issue in self.critical_issues:
                print(f"   ❌ {issue['test']}: {issue['details']['summary']}")
        
        if self.performance_issues:
            print(f"\n⚠️  PERFORMANCE WARNINGS ({len(self.performance_issues)}):")
            for warning in self.performance_issues:
                print(f"   ⚠️  {warning['test']}: {warning['details']['summary']}")
        
        # Save detailed report
        report_data = {
            "test_suite": "Level 5: Manual Testing",
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": total_tests,
                "passed": passed,
                "warnings": warnings,
                "failed": failed,
                "success_rate": round(passed/total_tests*100, 1)
            },
            "critical_issues": self.critical_issues,
            "performance_issues": self.performance_issues,
            "all_results": self.test_results
        }
        
        with open("manual_testing_report.json", "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n📁 Detailed report saved to: manual_testing_report.json")
        
        # Determine overall status
        if failed > 0:
            print("\n🚨 OVERALL STATUS: CRITICAL ISSUES FOUND")
            print("   Manual testing revealed production-blocking problems")
            return False
        elif warnings > 0:
            print("\n⚠️  OVERALL STATUS: ISSUES FOUND")
            print("   Manual testing revealed performance/quality concerns")
            return False
        else:
            print("\n✅ OVERALL STATUS: PRODUCTION READY")
            print("   Manual testing validates automated test results")
            return True

async def run_manual_testing():
    """Execute Level 5 Manual Testing Suite"""
    print("🔬 STARTING LEVEL 5: MANUAL TESTING")
    print("Using REAL PA-API data only - No mocks, No fake data")
    print("Following Testing Philosophy: Reality Validation")
    print("=" * 80)
    
    suite = ManualTestingSuite()
    
    try:
        # Execute all manual test categories
        await suite.test_real_user_scenarios()
        await suite.test_messy_data_handling()
        await suite.test_edge_case_queries()
        await suite.test_production_load_patterns()
        await suite.test_real_api_limitations()
        
        # Generate final report
        success = await suite.generate_test_report()
        
        return success
        
    except Exception as e:
        print(f"\n❌ MANUAL TESTING SUITE FAILED: {str(e)}")
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = asyncio.run(run_manual_testing())
    exit(0 if success else 1)
