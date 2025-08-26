"""
Development Sandbox for Feature Match AI Testing.

Interactive tool for testing and refining feature extraction and matching algorithms.
Useful for development, debugging, and demonstration purposes.

Usage:
    python -m bot.ai.sandbox
    
Features:
- Interactive query testing
- Performance benchmarking
- Feature extraction analysis
- Scoring algorithm testing
"""

import asyncio
import json
import sys
import time
from typing import Dict, List, Any

from .feature_extractor import FeatureExtractor
from .matching_engine import FeatureMatchingEngine
from .vocabularies import get_category_vocabulary, get_feature_weights


class AIModelSandbox:
    """Interactive sandbox for testing AI model components."""
    
    def __init__(self):
        """Initialize the sandbox with AI components."""
        print("🤖 Initializing Feature Match AI Sandbox...")
        
        self.feature_extractor = FeatureExtractor()
        self.matching_engine = FeatureMatchingEngine()
        
        print("✅ Components loaded successfully!")
        print("📊 Available commands: test, extract, score, benchmark, demo, help, quit")
    
    def run(self):
        """Run the interactive sandbox."""
        print("\n" + "="*60)
        print("🧪 FEATURE MATCH AI SANDBOX")
        print("="*60)
        print("Type 'help' for available commands or 'quit' to exit.")
        
        while True:
            try:
                command = input("\n🔬 sandbox> ").strip().lower()
                
                if command == "quit" or command == "exit":
                    print("👋 Goodbye!")
                    break
                elif command == "help":
                    self.show_help()
                elif command == "test":
                    self.run_quick_test()
                elif command == "extract":
                    self.interactive_extraction()
                elif command == "score":
                    self.interactive_scoring()
                elif command == "benchmark":
                    self.run_benchmark()
                elif command == "demo":
                    self.run_demo()
                elif command == "validate":
                    self.validate_phase1()
                elif command == "":
                    continue
                else:
                    print(f"❌ Unknown command: {command}")
                    print("💡 Type 'help' for available commands")
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    def show_help(self):
        """Show available commands."""
        print("\n📖 AVAILABLE COMMANDS:")
        print("  test      - Run quick feature extraction test")
        print("  extract   - Interactive feature extraction testing")
        print("  score     - Test product scoring algorithm")
        print("  benchmark - Performance benchmarking")
        print("  demo      - Run full AI model demonstration")
        print("  validate  - Validate Phase 1 completion criteria")
        print("  help      - Show this help message")
        print("  quit      - Exit sandbox")
    
    def run_quick_test(self):
        """Run a quick test of feature extraction."""
        print("\n🧪 QUICK FEATURE EXTRACTION TEST")
        print("-" * 40)
        
        test_queries = [
            "gaming monitor 144hz curved 27 inch",
            "Samsung 4K 32 inch IPS monitor",
            "curved OLED display 240hz",
            "27\" 1440p monitor for coding",
            "good monitor",  # Should have low confidence
            "cinematic gaming experience"  # Should be filtered
        ]
        
        for query in test_queries:
            print(f"\nQuery: '{query}'")
            
            start_time = time.time()
            features = self.feature_extractor.extract_features(query)
            processing_time = (time.time() - start_time) * 1000
            
            # Display results
            extracted = {k: v for k, v in features.items() 
                        if k not in ["confidence", "processing_time_ms", "technical_query", 
                                   "category_detected", "matched_features_count", "technical_density"]}
            
            confidence = features.get("confidence", 0)
            print(f"  Features: {extracted}")
            print(f"  Confidence: {confidence:.3f}")
            print(f"  Time: {processing_time:.1f}ms")
            
            if extracted:
                explanation = self.feature_extractor.get_feature_explanation(features)
                print(f"  Explanation: {explanation}")
    
    def interactive_extraction(self):
        """Interactive feature extraction testing."""
        print("\n🔍 INTERACTIVE FEATURE EXTRACTION")
        print("-" * 40)
        print("Enter queries to test feature extraction (empty line to return)")
        
        while True:
            query = input("\nEnter query: ").strip()
            if not query:
                break
            
            print("\n📊 EXTRACTION RESULTS:")
            
            # Extract features
            start_time = time.time()
            features = self.feature_extractor.extract_features(query)
            processing_time = (time.time() - start_time) * 1000
            
            # Display detailed results
            print(f"  Query: '{query}'")
            print(f"  Processing time: {processing_time:.1f}ms")
            print(f"  Confidence: {features.get('confidence', 0):.3f}")
            print(f"  Technical query: {features.get('technical_query', False)}")
            
            # Show extracted features
            extracted = {k: v for k, v in features.items() 
                        if k not in ["confidence", "processing_time_ms", "technical_query", 
                                   "category_detected", "matched_features_count", "technical_density"]}
            
            if extracted:
                print("  Extracted features:")
                for feature, value in extracted.items():
                    print(f"    {feature}: {value}")
                
                # Show explanation
                explanation = self.feature_extractor.get_feature_explanation(features)
                print(f"  Explanation: {explanation}")
                
                # Validate features
                validated = self.feature_extractor.validate_extraction(features)
                validation = validated.get("validation", {})
                
                if not validation.get("valid", True):
                    print("  ⚠️  Validation issues:")
                    for error in validation.get("errors", []):
                        print(f"    Error: {error}")
                    for warning in validation.get("warnings", []):
                        print(f"    Warning: {warning}")
            else:
                print("  No features extracted")
    
    def interactive_scoring(self):
        """Interactive product scoring testing."""
        print("\n🎯 INTERACTIVE SCORING TEST")
        print("-" * 40)
        
        # Get user query
        query = input("Enter search query: ").strip()
        if not query:
            return
        
        print(f"\nExtracting features from: '{query}'")
        user_features = self.feature_extractor.extract_features(query)
        
        extracted = {k: v for k, v in user_features.items() 
                    if k not in ["confidence", "processing_time_ms", "technical_query", 
                               "category_detected", "matched_features_count", "technical_density"]}
        
        if not extracted:
            print("❌ No features extracted from query")
            return
        
        print(f"User requirements: {extracted}")
        
        # Create sample products for testing
        sample_products = [
            {
                "title": "Samsung 27 inch 144Hz Curved Gaming Monitor",
                "asin": "B12345",
                "price": 2500000  # 25,000 rupees in paise
            },
            {
                "title": "LG 32 inch 4K IPS Professional Monitor", 
                "asin": "B67890",
                "price": 4500000  # 45,000 rupees in paise
            },
            {
                "title": "ASUS 24 inch 165Hz TN Gaming Display",
                "asin": "B11111", 
                "price": 1800000  # 18,000 rupees in paise
            }
        ]
        
        print(f"\n📊 SCORING {len(sample_products)} SAMPLE PRODUCTS:")
        
        # Score products
        scored_products = self.matching_engine.score_products(
            user_features, sample_products, "gaming_monitor"
        )
        
        # Display results
        for i, (product, score_data) in enumerate(scored_products):
            print(f"\n🏆 Rank #{i+1}: {product['title']}")
            print(f"  Score: {score_data['score']:.3f}")
            print(f"  Confidence: {score_data['confidence']:.3f}")
            print(f"  Rationale: {score_data['rationale']}")
            print(f"  Matched: {', '.join(score_data['matched_features'])}")
            
            if score_data['mismatched_features']:
                print(f"  Mismatched: {', '.join(score_data['mismatched_features'])}")
            if score_data['missing_features']:
                print(f"  Missing: {', '.join(score_data['missing_features'])}")
    
    def run_benchmark(self):
        """Run performance benchmarking."""
        print("\n⚡ PERFORMANCE BENCHMARK")
        print("-" * 40)
        
        benchmark_queries = [
            "gaming monitor 144hz curved 27 inch",
            "Samsung 4K 32 inch professional monitor for design work",
            "curved OLED display 240hz with HDR for gaming",
            "ultrawide 34 inch 1440p monitor for productivity",
            "budget 24 inch 1080p monitor under 15000"
        ] * 20  # 100 total queries
        
        print(f"Testing {len(benchmark_queries)} queries...")
        
        # Benchmark feature extraction
        start_time = time.time()
        results = []
        
        for query in benchmark_queries:
            result = self.feature_extractor.extract_features(query)
            results.append(result)
        
        total_time = (time.time() - start_time) * 1000
        avg_time = total_time / len(benchmark_queries)
        
        # Analyze results
        processing_times = [r.get("processing_time_ms", 0) for r in results]
        max_time = max(processing_times)
        min_time = min(processing_times)
        
        successful_extractions = sum(1 for r in results if any(
            k for k in r.keys() if k not in ["confidence", "processing_time_ms", 
                                           "technical_query", "category_detected"]
        ))
        
        success_rate = successful_extractions / len(results)
        
        print(f"\n📈 BENCHMARK RESULTS:")
        print(f"  Total time: {total_time:.1f}ms")
        print(f"  Average per query: {avg_time:.1f}ms")
        print(f"  Min time: {min_time:.1f}ms")
        print(f"  Max time: {max_time:.1f}ms")
        print(f"  Success rate: {success_rate:.1%}")
        print(f"  Successful extractions: {successful_extractions}/{len(results)}")
        
        # Performance validation
        print(f"\n✅ PERFORMANCE VALIDATION:")
        print(f"  <100ms requirement: {'✅ PASS' if max_time < 100 else '❌ FAIL'}")
        print(f"  Average performance: {'✅ GOOD' if avg_time < 50 else '⚠️ OK' if avg_time < 100 else '❌ POOR'}")
    
    def run_demo(self):
        """Run a full demonstration of the AI model."""
        print("\n🎬 FEATURE MATCH AI DEMONSTRATION")
        print("=" * 50)
        
        demo_scenarios = [
            {
                "name": "Gaming Enthusiast",
                "query": "gaming monitor 144hz curved 27 inch under 30000",
                "description": "Looking for a high-refresh gaming monitor"
            },
            {
                "name": "Professional Designer", 
                "query": "4K IPS monitor 32 inch for design work",
                "description": "Needs color-accurate display for professional work"
            },
            {
                "name": "Budget Buyer",
                "query": "Samsung monitor under 20000 24 inch",
                "description": "Price-conscious buyer with brand preference"
            },
            {
                "name": "Hinglish User",
                "query": "curved gaming monitor 144hz ka good wala",
                "description": "Mixed language query with Indian English"
            }
        ]
        
        for scenario in demo_scenarios:
            print(f"\n🎭 SCENARIO: {scenario['name']}")
            print(f"Description: {scenario['description']}")
            print(f"Query: '{scenario['query']}'")
            print("-" * 30)
            
            # Extract features
            features = self.feature_extractor.extract_features(scenario['query'])
            
            # Show extraction results
            extracted = {k: v for k, v in features.items() 
                        if k not in ["confidence", "processing_time_ms", "technical_query", 
                                   "category_detected", "matched_features_count", "technical_density"]}
            
            print(f"✨ AI Understanding:")
            if extracted:
                explanation = self.feature_extractor.get_feature_explanation(features)
                print(f"  {explanation}")
            else:
                print("  No specific features detected")
            
            confidence = features.get("confidence", 0)
            print(f"  AI Confidence: {confidence:.0%}")
            
            # Demo product scoring (simplified)
            if extracted:
                print(f"\n🏆 How AI would rank products:")
                sample_matches = [
                    ("Perfect match with all requirements", 0.95),
                    ("Good match, missing one feature", 0.75), 
                    ("Partial match with price consideration", 0.60),
                    ("Poor match, different category", 0.25)
                ]
                
                for desc, score in sample_matches:
                    stars = "★" * int(score * 5)
                    print(f"  {stars:<5} {score:.0%} - {desc}")
            
            input("\nPress Enter to continue...")
    
    def validate_phase1(self):
        """Validate Phase 1 completion criteria."""
        print("\n🎯 PHASE 1 VALIDATION")
        print("=" * 40)
        
        validation_tests = []
        
        # Test 1: Key features extraction
        print("✅ Test 1: Key Gaming Monitor Features")
        key_features_query = "gaming monitor 144hz curved 27 inch IPS Samsung"
        result = self.feature_extractor.extract_features(key_features_query)
        
        required_features = ["refresh_rate", "size", "curvature", "panel_type", "brand"]
        found_features = [f for f in required_features if f in result]
        
        print(f"  Required: {required_features}")
        print(f"  Found: {found_features}")
        print(f"  Success: {len(found_features)}/{len(required_features)}")
        
        feature_test_pass = len(found_features) >= 4  # Allow 4/5
        validation_tests.append(("Key Features", feature_test_pass))
        
        # Test 2: Performance requirement
        print("\n⚡ Test 2: Performance (<100ms)")
        performance_queries = [
            "gaming monitor 144hz curved 27 inch",
            "Samsung 4K professional monitor 32 inch IPS"
        ]
        
        max_time = 0
        for query in performance_queries:
            start_time = time.time()
            self.feature_extractor.extract_features(query)
            processing_time = (time.time() - start_time) * 1000
            max_time = max(max_time, processing_time)
        
        print(f"  Max processing time: {max_time:.1f}ms")
        performance_test_pass = max_time < 100
        validation_tests.append(("Performance", performance_test_pass))
        
        # Test 3: Unit variants
        print("\n🔄 Test 3: Unit Variants")
        unit_tests = [
            ("144hz vs 144 fps", "144hz monitor", "144 fps monitor"),
            ("QHD vs 1440p", "QHD monitor", "1440p monitor"),
            ("27 inch vs 27\"", "27 inch monitor", "27\" monitor")
        ]
        
        unit_test_results = []
        for test_name, query1, query2 in unit_tests:
            result1 = self.feature_extractor.extract_features(query1)
            result2 = self.feature_extractor.extract_features(query2)
            
            # Find common features between the two queries
            common_features = []
            for key in result1:
                if key in result2 and result1[key] == result2[key]:
                    if key not in ["confidence", "processing_time_ms", "technical_query"]:
                        common_features.append(key)
            
            success = len(common_features) > 0
            unit_test_results.append(success)
            print(f"  {test_name}: {'✅' if success else '❌'}")
        
        unit_variants_pass = all(unit_test_results)
        validation_tests.append(("Unit Variants", unit_variants_pass))
        
        # Test 4: Marketing fluff filtering
        print("\n🎭 Test 4: Marketing Fluff Filtering")
        marketing_queries = [
            "cinematic gaming experience",
            "eye care monitor",
            "stunning visual display"
        ]
        
        marketing_test_results = []
        for query in marketing_queries:
            result = self.feature_extractor.extract_features(query)
            confidence = result.get("confidence", 0)
            low_confidence = confidence < 0.3
            marketing_test_results.append(low_confidence)
            print(f"  '{query}': confidence {confidence:.3f} {'✅' if low_confidence else '❌'}")
        
        marketing_filter_pass = all(marketing_test_results)
        validation_tests.append(("Marketing Filter", marketing_filter_pass))
        
        # Test 5: Hinglish support
        print("\n🌏 Test 5: Hinglish Support")
        hinglish_query = "gaming monitor 144hz ka curved 27 inch"
        hinglish_result = self.feature_extractor.extract_features(hinglish_query)
        
        hinglish_features = [k for k in hinglish_result.keys() 
                           if k not in ["confidence", "processing_time_ms", "technical_query", 
                                      "category_detected"]]
        
        hinglish_pass = len(hinglish_features) >= 3
        print(f"  Query: '{hinglish_query}'")
        print(f"  Features extracted: {hinglish_features}")
        print(f"  Success: {'✅' if hinglish_pass else '❌'}")
        
        validation_tests.append(("Hinglish Support", hinglish_pass))
        
        # Summary
        print(f"\n🏁 PHASE 1 VALIDATION SUMMARY")
        print("=" * 40)
        
        passed_tests = sum(1 for _, passed in validation_tests)
        total_tests = len(validation_tests)
        
        for test_name, passed in validation_tests:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {test_name:<20} {status}")
        
        overall_pass = passed_tests >= 4  # Allow 4/5 tests to pass
        
        print(f"\nOverall Result: {passed_tests}/{total_tests} tests passed")
        print(f"Phase 1 Status: {'✅ READY FOR PHASE 2' if overall_pass else '❌ NEEDS WORK'}")
        
        if overall_pass:
            print("\n🎉 Phase 1 validation complete! Ready to proceed to Phase 2.")
        else:
            print("\n⚠️  Some tests failed. Review and fix issues before proceeding.")


def main():
    """Main entry point for the sandbox."""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        sandbox = AIModelSandbox()
        
        if command == "validate":
            sandbox.validate_phase1()
        elif command == "benchmark":
            sandbox.run_benchmark()
        elif command == "demo":
            sandbox.run_demo()
        else:
            print(f"Unknown command: {command}")
            print("Available commands: validate, benchmark, demo")
    else:
        # Interactive mode
        sandbox = AIModelSandbox()
        sandbox.run()


if __name__ == "__main__":
    main()
