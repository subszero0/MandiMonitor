#!/usr/bin/env python3
"""
Level 5: Focused Deep Testing - Targeted Issue Discovery

Focused approach to uncover specific deep-rooted problems
"""

import asyncio
import sys
import os
from datetime import datetime
import traceback
import logging

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.paapi_official import OfficialPaapiClient
from bot.paapi_ai_bridge import search_products_with_ai_analysis
from bot.watch_parser import parse_watch

logging.basicConfig(level=logging.WARNING)  # Reduce noise
log = logging.getLogger(__name__)

class FocusedDeepTesting:
    """Focused deep testing to find specific issues"""
    
    def __init__(self):
        self.client = OfficialPaapiClient()
        self.issues_found = []
    
    def log_issue(self, severity: str, category: str, description: str, details: dict = None):
        """Log discovered issues"""
        issue = {
            "timestamp": datetime.now().isoformat(),
            "severity": severity,  # CRITICAL, HIGH, MEDIUM, LOW
            "category": category,
            "description": description,
            "details": details or {}
        }
        self.issues_found.append(issue)
        
        emoji = {"CRITICAL": "🚨", "HIGH": "❌", "MEDIUM": "⚠️", "LOW": "ℹ️"}
        print(f"{emoji[severity]} {severity} [{category}]: {description}")
        
        if details:
            for key, value in details.items():
                print(f"    {key}: {value}")
    
    async def test_1_ai_bridge_consistency(self):
        """Test 1: AI Bridge result consistency under load"""
        print("\n🔍 TEST 1: AI Bridge Consistency Analysis")
        print("-" * 50)
        
        try:
            # Test same query multiple times to check for inconsistency
            query = "gaming laptop under 50000"
            results_batch = []
            
            for i in range(5):
                print(f"  Running iteration {i+1}/5...")
                result = await search_products_with_ai_analysis(
                    keywords=query,
                    search_index="All", 
                    item_count=3
                )
                results_batch.append({
                    "iteration": i+1,
                    "count": len(result.get("products", [])),
                    "analysis_present": bool(result.get("analysis")),
                    "first_product": result.get("products", [{}])[0].get("title", "No product") if result.get("products") else "No products"
                })
                await asyncio.sleep(1)  # Rate limiting
            
            # Analyze consistency
            counts = [r["count"] for r in results_batch]
            unique_counts = set(counts)
            
            if len(unique_counts) > 2:  # More than 2 different counts suggests inconsistency
                self.log_issue("HIGH", "AI_CONSISTENCY", 
                             f"Inconsistent result counts: {counts}",
                             {"query": query, "results": results_batch})
            
            # Check if AI analysis is consistently present/absent
            ai_present = [r["analysis_present"] for r in results_batch]
            if not all(ai_present) and any(ai_present):
                self.log_issue("MEDIUM", "AI_CONSISTENCY",
                             f"Inconsistent AI analysis presence: {ai_present}",
                             {"query": query, "results": results_batch})
            
            print(f"  ✅ AI Bridge consistency test completed. Issues found: {len([i for i in self.issues_found if i['category'] == 'AI_CONSISTENCY'])}")
            
        except Exception as e:
            self.log_issue("CRITICAL", "AI_BRIDGE_CRASH", 
                         f"AI Bridge test crashed: {str(e)}", 
                         {"exception": traceback.format_exc()})
    
    async def test_2_price_filter_edge_cases(self):
        """Test 2: Price filter edge cases that might break"""
        print("\n💰 TEST 2: Price Filter Edge Cases")
        print("-" * 50)
        
        edge_cases = [
            {"name": "Zero Price Range", "min": 0, "max": 0},
            {"name": "Negative Prices", "min": -1000, "max": -1},
            {"name": "Extremely High Range", "min": 99999999, "max": 100000000},
            {"name": "Inverted Range", "min": 50000, "max": 10000},  # min > max
            {"name": "Single Paisa Range", "min": 1, "max": 1},
        ]
        
        for case in edge_cases:
            try:
                print(f"  Testing: {case['name']}")
                
                result = await self.client.search_items_advanced(
                    keywords="laptop",
                    search_index="All",
                    min_price=case["min"],
                    max_price=case["max"],
                    item_count=3,
                    enable_ai_analysis=False
                )
                
                # Analyze result for issues
                if case["name"] == "Inverted Range" and result and len(result) > 0:
                    self.log_issue("HIGH", "PRICE_FILTER_LOGIC",
                                 "Inverted price range returned results",
                                 {"case": case, "result_count": len(result)})
                
                if case["name"] == "Negative Prices" and result and len(result) > 0:
                    self.log_issue("MEDIUM", "PRICE_FILTER_VALIDATION",
                                 "Negative prices accepted and returned results",
                                 {"case": case, "result_count": len(result)})
                
                await asyncio.sleep(0.5)
                
            except Exception as e:
                # Some exceptions are expected for invalid ranges
                if "InvalidParameterValue" in str(e):
                    print(f"    Expected validation error for {case['name']}")
                else:
                    self.log_issue("HIGH", "PRICE_FILTER_ERROR",
                                 f"Unexpected error for {case['name']}: {str(e)}",
                                 {"case": case, "exception": str(e)})
        
        print(f"  ✅ Price filter edge cases completed. Issues found: {len([i for i in self.issues_found if i['category'].startswith('PRICE_FILTER')])}")
    
    async def test_3_memory_behavior(self):
        """Test 3: Memory behavior under repeated operations"""
        print("\n🧠 TEST 3: Memory Behavior Analysis")
        print("-" * 50)
        
        try:
            import psutil
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            print(f"  Initial memory: {initial_memory:.1f} MB")
            
            # Perform 20 search operations
            for i in range(20):
                if i % 5 == 0:
                    current_memory = process.memory_info().rss / 1024 / 1024
                    print(f"  Iteration {i}: {current_memory:.1f} MB")
                
                await self.client.search_items_advanced(
                    keywords=f"test query {i % 3}",  # Rotate queries
                    search_index="All",
                    item_count=2,
                    enable_ai_analysis=False
                )
                await asyncio.sleep(0.2)
            
            final_memory = process.memory_info().rss / 1024 / 1024
            memory_growth = final_memory - initial_memory
            
            print(f"  Final memory: {final_memory:.1f} MB")
            print(f"  Memory growth: {memory_growth:+.1f} MB")
            
            if memory_growth > 30:  # 30MB growth is concerning
                self.log_issue("HIGH", "MEMORY_LEAK",
                             f"Significant memory growth: {memory_growth:.1f} MB",
                             {"initial_mb": initial_memory, "final_mb": final_memory})
            elif memory_growth > 15:
                self.log_issue("MEDIUM", "MEMORY_GROWTH", 
                             f"Moderate memory growth: {memory_growth:.1f} MB",
                             {"initial_mb": initial_memory, "final_mb": final_memory})
            
            print(f"  ✅ Memory behavior test completed. Issues found: {len([i for i in self.issues_found if i['category'].startswith('MEMORY')])}")
            
        except ImportError:
            self.log_issue("LOW", "DEPENDENCY", "psutil not available for memory testing")
        except Exception as e:
            self.log_issue("HIGH", "MEMORY_TEST_ERROR", 
                         f"Memory test failed: {str(e)}",
                         {"exception": traceback.format_exc()})
    
    async def test_4_data_quality_validation(self):
        """Test 4: Data quality issues in real responses"""
        print("\n💾 TEST 4: Data Quality Validation")
        print("-" * 50)
        
        try:
            # Get real data and check for quality issues
            result = await self.client.search_items_advanced(
                keywords="smartphone",
                search_index="All",
                item_count=10,
                enable_ai_analysis=False
            )
            
            if not result:
                self.log_issue("HIGH", "DATA_AVAILABILITY", "No results returned for basic query")
                return
            
            print(f"  Analyzing {len(result)} products for data quality...")
            
            issues_per_product = []
            for i, product in enumerate(result):
                product_issues = []
                
                # Check required fields
                if not product.get("title"):
                    product_issues.append("missing_title")
                if not product.get("asin"):
                    product_issues.append("missing_asin")
                
                # Check price data quality
                price = product.get("price")
                if price is None:
                    product_issues.append("null_price")
                elif price == 0:
                    product_issues.append("zero_price")
                elif not isinstance(price, (int, float)):
                    product_issues.append("invalid_price_type")
                elif price < 0:
                    product_issues.append("negative_price")
                
                # Check ASIN format
                asin = product.get("asin", "")
                if asin and (len(asin) != 10 or not asin.isalnum()):
                    product_issues.append("invalid_asin_format")
                
                # Check URLs
                image_url = product.get("image_url", "")
                if image_url and not image_url.startswith(("http://", "https://")):
                    product_issues.append("invalid_image_url")
                
                if product_issues:
                    issues_per_product.append({"product_index": i, "issues": product_issues})
            
            # Report data quality issues
            total_issues = sum(len(p["issues"]) for p in issues_per_product)
            issue_rate = (len(issues_per_product) / len(result)) * 100
            
            if issue_rate > 50:
                self.log_issue("CRITICAL", "DATA_QUALITY",
                             f"High data quality issue rate: {issue_rate:.1f}% of products affected",
                             {"total_products": len(result), "affected_products": len(issues_per_product), "total_issues": total_issues})
            elif issue_rate > 20:
                self.log_issue("HIGH", "DATA_QUALITY",
                             f"Moderate data quality issues: {issue_rate:.1f}% of products affected",
                             {"total_products": len(result), "affected_products": len(issues_per_product)})
            elif total_issues > 0:
                self.log_issue("MEDIUM", "DATA_QUALITY",
                             f"Minor data quality issues found: {total_issues} issues across {len(issues_per_product)} products")
            
            # Check for specific patterns
            null_prices = sum(1 for p in result if p.get("price") is None)
            if null_prices > len(result) * 0.3:  # >30% null prices
                self.log_issue("HIGH", "PRICE_DATA",
                             f"High null price rate: {null_prices}/{len(result)} products",
                             {"null_price_percentage": (null_prices/len(result))*100})
            
            print(f"  ✅ Data quality validation completed. Issues found: {len([i for i in self.issues_found if i['category'] in ['DATA_QUALITY', 'PRICE_DATA']])}")
            
        except Exception as e:
            self.log_issue("CRITICAL", "DATA_VALIDATION_CRASH",
                         f"Data quality test crashed: {str(e)}",
                         {"exception": traceback.format_exc()})
    
    async def test_5_parser_vulnerabilities(self):
        """Test 5: Watch parser security and edge cases"""
        print("\n🔒 TEST 5: Parser Security & Edge Cases")
        print("-" * 50)
        
        malicious_inputs = [
            # SQL Injection variants
            "laptop'; DROP TABLE users; --",
            "laptop' UNION SELECT password FROM users--",
            
            # Script injection
            "<script>alert('xss')</script> laptop",
            "javascript:alert(1) laptop",
            
            # Path traversal
            "../../../etc/passwd laptop",
            "..\\..\\..\\windows\\system32\\config\\sam laptop",
            
            # Command injection
            "laptop; rm -rf /",
            "laptop && del C:\\Windows\\System32",
            
            # Buffer overflow attempts
            "A" * 1000,
            
            # Unicode attacks
            "\u0000\u0001\u0002 laptop",
            "laptop \uFEFF price",  # Zero-width no-break space
        ]
        
        for i, malicious_input in enumerate(malicious_inputs):
            try:
                print(f"  Testing malicious input {i+1}/{len(malicious_inputs)}")
                
                # Test parser
                parsed = parse_watch(malicious_input)
                
                # Check if malicious content leaked through
                keywords = parsed.get("keywords", "")
                
                # Look for dangerous patterns in parsed output
                dangerous_patterns = [
                    "DROP TABLE", "SELECT", "UNION", "<script>", "javascript:",
                    "../", "..\\", "; rm", "&& del", "\u0000"
                ]
                
                for pattern in dangerous_patterns:
                    if pattern.lower() in keywords.lower():
                        self.log_issue("CRITICAL", "PARSER_SECURITY",
                                     f"Malicious pattern leaked through parser: {pattern}",
                                     {"input": malicious_input[:100], "parsed_keywords": keywords[:100]})
                
                # Test if extremely long input is handled
                if len(malicious_input) > 500 and len(keywords) > 500:
                    self.log_issue("MEDIUM", "PARSER_LIMITS",
                                 "Parser doesn't limit extremely long input",
                                 {"input_length": len(malicious_input), "output_length": len(keywords)})
                
            except Exception as e:
                # Some exceptions are expected for malicious input
                if any(term in str(e).lower() for term in ["invalid", "malformed", "error"]):
                    print(f"    Expected security exception for input {i+1}")
                else:
                    self.log_issue("HIGH", "PARSER_ERROR",
                                 f"Unexpected parser error: {str(e)}",
                                 {"input": malicious_input[:100], "exception": str(e)})
        
        print(f"  ✅ Parser security test completed. Issues found: {len([i for i in self.issues_found if i['category'].startswith('PARSER')])}")
    
    async def generate_focused_report(self):
        """Generate focused deep testing report"""
        print("\n" + "=" * 80)
        print("📊 LEVEL 5 FOCUSED DEEP TESTING REPORT")
        print("=" * 80)
        
        # Categorize issues by severity
        critical_issues = [i for i in self.issues_found if i["severity"] == "CRITICAL"]
        high_issues = [i for i in self.issues_found if i["severity"] == "HIGH"]
        medium_issues = [i for i in self.issues_found if i["severity"] == "MEDIUM"]
        low_issues = [i for i in self.issues_found if i["severity"] == "LOW"]
        
        total_issues = len(self.issues_found)
        
        print(f"📈 ISSUE SUMMARY:")
        print(f"   🚨 Critical Issues: {len(critical_issues)}")
        print(f"   ❌ High Issues: {len(high_issues)}")
        print(f"   ⚠️  Medium Issues: {len(medium_issues)}")
        print(f"   ℹ️  Low Issues: {len(low_issues)}")
        print(f"   📊 Total Issues: {total_issues}")
        
        if critical_issues:
            print(f"\n🚨 CRITICAL ISSUES REQUIRING IMMEDIATE ATTENTION:")
            for issue in critical_issues:
                print(f"   • [{issue['category']}] {issue['description']}")
        
        if high_issues:
            print(f"\n❌ HIGH PRIORITY ISSUES:")
            for issue in high_issues:
                print(f"   • [{issue['category']}] {issue['description']}")
        
        if medium_issues:
            print(f"\n⚠️  MEDIUM PRIORITY ISSUES:")
            for issue in medium_issues:
                print(f"   • [{issue['category']}] {issue['description']}")
        
        # Overall assessment
        if critical_issues:
            print("\n🚨 OVERALL STATUS: CRITICAL ISSUES FOUND - SYSTEM NOT PRODUCTION READY")
            print("   Deep testing revealed critical problems that must be fixed immediately")
            return False
        elif high_issues:
            print("\n❌ OVERALL STATUS: HIGH PRIORITY ISSUES FOUND")
            print("   Deep testing revealed serious problems requiring attention before production")
            return False
        elif medium_issues:
            print("\n⚠️  OVERALL STATUS: MEDIUM PRIORITY ISSUES FOUND")
            print("   Deep testing revealed quality issues that should be addressed")
            return False
        else:
            print("\n✅ OVERALL STATUS: NO SIGNIFICANT ISSUES FOUND")
            print("   Focused deep testing passed - system appears stable")
            return True

async def run_focused_deep_testing():
    """Run focused deep testing to uncover specific issues"""
    print("🔬 LEVEL 5: FOCUSED DEEP TESTING")
    print("Systematically uncovering deep-rooted problems")
    print("=" * 80)
    
    tester = FocusedDeepTesting()
    
    try:
        # Run focused tests
        await tester.test_1_ai_bridge_consistency()
        await tester.test_2_price_filter_edge_cases()
        await tester.test_3_memory_behavior()
        await tester.test_4_data_quality_validation()
        await tester.test_5_parser_vulnerabilities()
        
        # Generate report
        success = await tester.generate_focused_report()
        return success
        
    except Exception as e:
        print(f"\n❌ FOCUSED DEEP TESTING CRASHED: {str(e)}")
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = asyncio.run(run_focused_deep_testing())
    exit(0 if success else 1)
