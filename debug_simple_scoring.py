#!/usr/bin/env python3
"""Simple test of enhanced scoring"""

import sys
sys.path.append('.')

from bot.ai.matching_engine import FeatureMatchingEngine

def test_enhanced_scoring():
    engine = FeatureMatchingEngine()

    # Test case: High-end gaming monitor specs
    test_features = {
        'refresh_rate': 144,
        'response_time': 1,
        'resolution': '1440p',
        'panel_type': 'ips',
        'brightness': 350,
        'color_accuracy': 95,
        'hdr_support': 'hdr10',
        'size': 32,
        'price': 2500000  # ₹25,000
    }

    user_features = {'max_price': 6000000}

    print("=== ENHANCED SCORING TEST ===")
    print(f"Product: ₹{test_features['price']/100:,.0f} gaming monitor")
    print(f"Specs: {test_features['refresh_rate']}Hz, {test_features['response_time']}ms, {test_features['resolution']}, {test_features['panel_type'].upper()}")
    print()

    # Calculate components
    tech_perf = engine._calculate_technical_performance(test_features)
    value_score = engine._calculate_value_ratio_score(test_features, user_features)
    budget_score = engine._calculate_budget_adherence_score(test_features, user_features)

    print(".3f")
    print(".3f")
    print(".3f")

    # Calculate hybrid score
    hybrid_score, breakdown = engine.calculate_hybrid_score(user_features, test_features)
    print(".3f")
    print("Weights: Tech 45%, Value 30%, Budget 20%, Excellence 5%")

    print("\n=== ANALYSIS ===")
    if value_score > 0.7:
        print("✅ Excellent value for money")
    elif value_score > 0.5:
        print("👍 Good value proposition")
    else:
        print("⚠️  Price may not justify performance")

if __name__ == "__main__":
    test_enhanced_scoring()
