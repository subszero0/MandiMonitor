#!/usr/bin/env python3
"""
Phase 4 Deployment Testing Script

This script performs comprehensive testing for the PA-API migration Phase 4.
It tests both legacy and official SDK implementations and provides detailed
comparison reports.

Usage:
    python scripts/phase4_deployment_test.py
"""

import asyncio
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.config import settings
from bot.paapi_factory import get_paapi_client
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

# Test ASINs known to work in India marketplace
TEST_ASINS = [
    "B08N5WRWNW",  # Echo Dot
    "B09VP7HLYN",  # One Plus Nord CE 2
    "B07DL6L8QX",  # Samsung Galaxy M12
    "B08GXTK6XV",  # Redmi 9 Prime
    "B0CS5Z3T4M"   # iPhone 15
]

TEST_SEARCHES = [
    {"keywords": "gaming laptop", "search_index": "Electronics"},
    {"keywords": "smartphone", "search_index": "Electronics"}, 
    {"keywords": "headphones wireless", "search_index": "Electronics"},
    {"keywords": "books python programming", "search_index": "Books"},
    {"keywords": "coffee machine", "search_index": "Kitchen"}
]


class DeploymentTester:
    """Comprehensive deployment testing for PA-API migration."""
    
    def __init__(self):
        """Initialize the deployment tester."""
        self.results = {
            "legacy": {"get_items": [], "search_items": [], "browse_nodes": []},
            "official": {"get_items": [], "search_items": [], "browse_nodes": []},
            "errors": {"legacy": [], "official": []},
            "performance": {"legacy": [], "official": []}
        }
        
    async def test_get_items(self, implementation: str, client) -> Dict:
        """Test GetItems functionality."""
        log.info(f"Testing GetItems with {implementation} implementation...")
        
        for asin in TEST_ASINS[:3]:  # Test first 3 ASINs
            try:
                start_time = time.time()
                result = await client.get_item_detailed(asin)
                end_time = time.time()
                
                response_data = {
                    "asin": asin,
                    "success": result is not None,
                    "has_title": bool(result and result.get("title")),
                    "has_price": bool(result and result.get("price_value")),
                    "has_image": bool(result and result.get("image_url")),
                    "response_time": round(end_time - start_time, 3),
                    "timestamp": datetime.now().isoformat()
                }
                
                self.results[implementation]["get_items"].append(response_data)
                log.info(f"GetItems {asin}: SUCCESS (impl={implementation}, time={response_data['response_time']}s)")
                
                # Add small delay to respect rate limits
                await asyncio.sleep(1.1)
                
            except Exception as e:
                error_data = {
                    "operation": "get_items",
                    "asin": asin,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
                self.results["errors"][implementation].append(error_data)
                log.error(f"GetItems {asin} FAILED (impl={implementation}): {e}")
                
    async def test_search_items(self, implementation: str, client) -> Dict:
        """Test SearchItems functionality."""
        log.info(f"Testing SearchItems with {implementation} implementation...")
        
        for search in TEST_SEARCHES[:3]:  # Test first 3 searches
            try:
                start_time = time.time()
                result = await client.search_items_advanced(
                    keywords=search["keywords"],
                    search_index=search["search_index"],
                    item_count=5
                )
                end_time = time.time()
                
                response_data = {
                    "keywords": search["keywords"],
                    "search_index": search["search_index"],
                    "success": result is not None and len(result) > 0,
                    "item_count": len(result) if result else 0,
                    "response_time": round(end_time - start_time, 3),
                    "timestamp": datetime.now().isoformat()
                }
                
                self.results[implementation]["search_items"].append(response_data)
                log.info(f"SearchItems '{search['keywords']}': SUCCESS (impl={implementation}, items={response_data['item_count']}, time={response_data['response_time']}s)")
                
                # Add delay to respect rate limits
                await asyncio.sleep(1.1)
                
            except Exception as e:
                error_data = {
                    "operation": "search_items",
                    "keywords": search["keywords"],
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
                self.results["errors"][implementation].append(error_data)
                log.error(f"SearchItems '{search['keywords']}' FAILED (impl={implementation}): {e}")
                
    async def test_browse_nodes(self, implementation: str, client) -> Dict:
        """Test Browse Nodes functionality."""
        log.info(f"Testing Browse Nodes with {implementation} implementation...")
        
        # Test common India browse node IDs
        test_browse_nodes = [1805560031, 976419031, 1389401031]  # Electronics, Computers, Mobiles
        
        for browse_node_id in test_browse_nodes:
            try:
                start_time = time.time()
                result = await client.get_browse_nodes_hierarchy(browse_node_id)
                end_time = time.time()
                
                response_data = {
                    "browse_node_id": browse_node_id,
                    "success": result is not None,
                    "has_children": bool(result and result.get("children")),
                    "response_time": round(end_time - start_time, 3),
                    "timestamp": datetime.now().isoformat()
                }
                
                self.results[implementation]["browse_nodes"].append(response_data)
                log.info(f"BrowseNode {browse_node_id}: SUCCESS (impl={implementation}, time={response_data['response_time']}s)")
                
                # Add delay to respect rate limits
                await asyncio.sleep(1.1)
                
            except Exception as e:
                error_data = {
                    "operation": "browse_nodes",
                    "browse_node_id": browse_node_id,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
                self.results["errors"][implementation].append(error_data)
                log.error(f"BrowseNode {browse_node_id} FAILED (impl={implementation}): {e}")
    
    async def run_comprehensive_test(self) -> Dict:
        """Run comprehensive tests for both implementations."""
        log.info("="*60)
        log.info("🚀 STARTING PHASE 4 DEPLOYMENT TESTING")
        log.info("="*60)
        
        # Test 1: Legacy Implementation (current state)
        log.info("\n📊 Phase 1: Testing Legacy Implementation (amazon-paapi)")
        log.info("-" * 50)
        
        original_flag = settings.USE_NEW_PAAPI_SDK
        settings.USE_NEW_PAAPI_SDK = False
        
        try:
            legacy_client = get_paapi_client()
            await self.test_get_items("legacy", legacy_client)
            await self.test_search_items("legacy", legacy_client)
            await self.test_browse_nodes("legacy", legacy_client)
        except Exception as e:
            log.error(f"Legacy implementation testing failed: {e}")
            self.results["errors"]["legacy"].append({
                "operation": "initialization",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
        
        # Wait between tests
        log.info("\n⏱️ Waiting 5 seconds between implementations...")
        await asyncio.sleep(5)
        
        # Test 2: Official SDK Implementation  
        log.info("\n📊 Phase 2: Testing Official SDK Implementation (paapi5-python-sdk)")
        log.info("-" * 50)
        
        settings.USE_NEW_PAAPI_SDK = True
        
        try:
            official_client = get_paapi_client()
            await self.test_get_items("official", official_client)
            await self.test_search_items("official", official_client)
            await self.test_browse_nodes("official", official_client)
        except Exception as e:
            log.error(f"Official SDK testing failed: {e}")
            self.results["errors"]["official"].append({
                "operation": "initialization", 
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
        finally:
            # Restore original flag
            settings.USE_NEW_PAAPI_SDK = original_flag
            
        return self.results
    
    def generate_report(self) -> str:
        """Generate comprehensive test report."""
        report = []
        report.append("="*80)
        report.append("🔍 PHASE 4 DEPLOYMENT TEST REPORT")
        report.append("="*80)
        report.append(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Summary statistics
        legacy_success = self._calculate_success_rate("legacy")
        official_success = self._calculate_success_rate("official")
        
        report.append("📊 SUMMARY STATISTICS")
        report.append("-" * 40)
        report.append(f"Legacy Implementation Success Rate:  {legacy_success:.1f}%")
        report.append(f"Official SDK Success Rate:          {official_success:.1f}%")
        report.append("")
        
        # Detailed results by operation
        for operation in ["get_items", "search_items", "browse_nodes"]:
            report.append(f"🔧 {operation.upper().replace('_', ' ')} RESULTS")
            report.append("-" * 40)
            
            for impl in ["legacy", "official"]:
                results = self.results[impl][operation]
                if results:
                    success_count = sum(1 for r in results if r.get("success", False))
                    total_count = len(results)
                    avg_time = sum(r.get("response_time", 0) for r in results) / total_count
                    
                    report.append(f"{impl.capitalize():>12}: {success_count}/{total_count} success, avg {avg_time:.2f}s")
                else:
                    report.append(f"{impl.capitalize():>12}: No tests run")
            report.append("")
        
        # Error analysis
        if any(self.results["errors"].values()):
            report.append("❌ ERROR ANALYSIS")
            report.append("-" * 40)
            
            for impl in ["legacy", "official"]:
                errors = self.results["errors"][impl]
                if errors:
                    report.append(f"{impl.capitalize()} Errors ({len(errors)}):")
                    for error in errors:
                        report.append(f"  • {error['operation']}: {error['error']}")
                    report.append("")
        
        # Recommendations
        report.append("💡 RECOMMENDATIONS")
        report.append("-" * 40)
        
        if official_success > legacy_success:
            report.append("✅ Official SDK shows better performance - READY FOR MIGRATION")
        elif official_success == legacy_success and official_success > 70:
            report.append("✅ Both implementations working well - MIGRATION SAFE")
        elif legacy_success > official_success:
            report.append("⚠️  Legacy implementation performing better - INVESTIGATE ISSUES")
        else:
            report.append("❌ Both implementations showing issues - DO NOT MIGRATE")
            
        if official_success >= 80:
            report.append("✅ Official SDK reliability acceptable for production")
        else:
            report.append("⚠️  Official SDK needs improvement before production")
            
        report.append("")
        report.append("="*80)
        
        return "\n".join(report)
    
    def _calculate_success_rate(self, implementation: str) -> float:
        """Calculate overall success rate for an implementation."""
        total_tests = 0
        successful_tests = 0
        
        for operation in ["get_items", "search_items", "browse_nodes"]:
            results = self.results[implementation][operation]
            total_tests += len(results)
            successful_tests += sum(1 for r in results if r.get("success", False))
            
        return (successful_tests / total_tests * 100) if total_tests > 0 else 0.0


async def main():
    """Main testing function."""
    # Verify we have proper credentials
    if not all([settings.PAAPI_ACCESS_KEY, settings.PAAPI_SECRET_KEY, settings.PAAPI_TAG]):
        print("❌ ERROR: PA-API credentials not configured properly!")
        print("Please check your .env file has:")
        print("- PAAPI_ACCESS_KEY")
        print("- PAAPI_SECRET_KEY") 
        print("- PAAPI_TAG")
        return
    
    print(f"🔧 Starting Phase 4 Deployment Tests")
    print(f"📍 Current feature flag: USE_NEW_PAAPI_SDK={settings.USE_NEW_PAAPI_SDK}")
    print(f"🌏 Testing marketplace: {settings.PAAPI_MARKETPLACE}")
    print("")
    
    tester = DeploymentTester()
    
    try:
        results = await tester.run_comprehensive_test()
        
        # Generate and display report
        report = tester.generate_report()
        print(report)
        
        # Save report to file
        report_file = f"phase4_deployment_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
            
        print(f"\n📄 Full report saved to: {report_file}")
        
        # Determine next steps
        official_success = tester._calculate_success_rate("official")
        if official_success >= 80:
            print("\n✅ READY FOR NEXT PHASE: Enable feature flag for limited production testing")
        else:
            print("\n⚠️  NEEDS INVESTIGATION: Official SDK success rate below 80%")
            
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        log.exception("Test execution failed")


if __name__ == "__main__":
    asyncio.run(main())
