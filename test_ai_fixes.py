#!/usr/bin/env python3
"""
Test script to validate AI fixes for the bot - FORCED AI MODE.

This script tests:
1. Feature extraction for technical queries
2. FORCED AI model selection (no PopularityModel)
3. Multi-card eligibility
4. Enhanced carousel feature flags

CRITICAL CHANGE: technical_query_required is now ALWAYS TRUE
This forces AI usage and prevents PopularityModel from being used.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bot.product_selection_models import has_technical_features, FeatureMatchModel, get_selection_model
from bot.watch_flow import _is_technical_query
from bot.feature_rollout import is_ai_feature_enabled
from bot.ai.feature_extractor import FeatureExtractor


async def test_forced_ai_model_selection():
    """Test that PopularityModel is never selected."""
    print("=== Testing FORCED AI Model Selection (No PopularityModel) ===")

    test_cases = [
        ("32 inch gaming monitor", 10),
        ("simple phone", 5),
        ("laptop", 3),
        ("headphones", 2),
        ("random query", 1)
    ]

    user_id = "test_user"
    all_passed = True

    for query, product_count in test_cases:
        print(f"\nTesting: '{query}' with {product_count} products")

        # Test which model would be selected
        model = get_selection_model(query, product_count, user_id)
        model_name = model.__class__.__name__

        print(f"  Selected model: {model_name}")

        # Check if PopularityModel is avoided
        if model_name == "PopularityModel":
            print("  ❌ FAILED: PopularityModel selected - this should never happen!")
            all_passed = False
        elif model_name in ["FeatureMatchModel", "RandomSelectionModel"]:
            print("  ✅ PASSED: AI or Random model selected")
        else:
            print(f"  ⚠️  UNKNOWN: Unexpected model {model_name}")

    print(f"\nFORCED AI TEST RESULT: {'PASSED' if all_passed else 'FAILED'}")
    return all_passed


async def test_feature_extraction():
    """Test feature extraction improvements."""
    print("\n=== Testing Feature Extraction ===")

    query = "32 inch gaming monitor between INR 40000 and INR 50000"
    print(f"Query: {query}")

    # Test global function
    is_tech_global = has_technical_features(query)
    print(f"Global has_technical_features: {is_tech_global}")

    # Test watch_flow helper
    is_tech_watch = _is_technical_query(query)
    print(f"Watch flow _is_technical_query: {is_tech_watch}")

    # Test FeatureExtractor
    extractor = FeatureExtractor()
    features = extractor.extract_features(query)

    print("FeatureExtractor results:")
    for key, value in features.items():
        print(f"  {key}: {value}")

    # Check if features would pass AI thresholds
    confidence = features.get('confidence', 0)
    technical_density = features.get('technical_density', 0)

    print("\nThreshold checks:")
    print(f"  Confidence >= 0.2: {confidence >= 0.2}")
    print(f"  Technical density >= 0.25: {technical_density >= 0.25}")

    return features


async def test_feature_flags():
    """Test feature flag logic with forced technical queries."""
    print("\n=== Testing Feature Flags (FORCED Technical) ===")

    user_id = "test_user"

    # Test enhanced carousel flag (should always pass now due to forced technical)
    enhanced_carousel = is_ai_feature_enabled(
        "ai_enhanced_carousel",
        user_id,
        multi_card_enabled=True,
        product_count=10,
        has_technical_features=True  # This should now be ignored due to forced technical
    )
    print(f"Enhanced carousel enabled: {enhanced_carousel}")

    # Test AI feature matching flag
    ai_matching = is_ai_feature_enabled(
        "ai_feature_matching",
        user_id,
        has_technical_features=True,
        product_count=10
    )
    print(f"AI feature matching enabled: {ai_matching}")

    return enhanced_carousel, ai_matching


async def test_multi_card_logic():
    """Test multi-card selection logic."""
    print("\n=== Testing Multi-Card Logic ===")

    from bot.ai.enhanced_product_selection import EnhancedFeatureMatchModel

    query = "32 inch gaming monitor between INR 40000 and INR 50000"

    # Create sample products
    products = [
        {"asin": f"TEST{i}", "title": f"Test Monitor {i}"} for i in range(10)
    ]

    extractor = FeatureExtractor()
    features = extractor.extract_features(query)

    model = EnhancedFeatureMatchModel()
    should_use_multi = model._should_use_multi_card(features, products)

    print(f"Should use multi-card: {should_use_multi}")
    print(f"Products count: {len(products)}")
    print(f"Features extracted: {len([k for k in features.keys() if k not in ['confidence', 'processing_time_ms']])}")
    print(f"Technical density: {features.get('technical_density', 0):.3f}")
    print(f"Confidence: {features.get('confidence', 0):.3f}")

    return should_use_multi


async def main():
    """Run all tests."""
    print("🔧 Testing AI Bot Fixes - FORCED AI MODE")
    print("🚫 PopularityModel DISABLED - AI Only")
    print("=" * 60)

    try:
        # Test 0: FORCED AI model selection (most important)
        forced_ai_passed = await test_forced_ai_model_selection()

        # Test 1: Feature extraction
        features = await test_feature_extraction()

        # Test 2: Feature flags with forced technical
        enhanced_carousel, ai_matching = await test_feature_flags()

        # Test 3: Multi-card logic
        should_use_multi = await test_multi_card_logic()

        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY - FORCED AI MODE")
        print("=" * 60)

        success_count = 0
        total_tests = 7

        # Check FORCED AI (most critical)
        if forced_ai_passed:
            print("✅ FORCED AI: PopularityModel never selected")
            success_count += 1
        else:
            print("❌ FORCED AI: PopularityModel still being used")

        # Check feature extraction
        if features.get('confidence', 0) >= 0.2:
            print("✅ Feature extraction confidence >= 0.2")
            success_count += 1
        else:
            print("❌ Feature extraction confidence < 0.2")

        # Check technical detection
        if has_technical_features("32 inch gaming monitor between INR 40000 and INR 50000"):
            print("✅ Global technical detection working")
            success_count += 1
        else:
            print("❌ Global technical detection failed")

        # Check feature flags
        if enhanced_carousel:
            print("✅ Enhanced carousel enabled (forced technical)")
            success_count += 1
        else:
            print("❌ Enhanced carousel disabled")

        # Check AI matching
        if ai_matching:
            print("✅ AI feature matching enabled")
            success_count += 1
        else:
            print("❌ AI feature matching disabled")

        # Check multi-card
        if should_use_multi:
            print("✅ Multi-card selection enabled")
            success_count += 1
        else:
            print("❌ Multi-card selection disabled")

        print(f"\n🎯 Overall: {success_count}/{total_tests} tests passed")

        if success_count == total_tests:
            print("🎉 ALL FIXES WORKING - FORCED AI MODE ACTIVE!")
            print("🚫 PopularityModel is DISABLED - Only AI selection")
        elif forced_ai_passed and success_count >= 5:
            print("✅ FORCED AI working, some secondary features may need tuning")
        else:
            print("⚠️  Critical issues remain - check the failed tests above")

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
