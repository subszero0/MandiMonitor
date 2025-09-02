#!/usr/bin/env python3
"""Test enhanced value scoring algorithm"""

import sys
sys.path.append('.')

from bot.ai.matching_engine import FeatureMatchingEngine

def test_enhanced_value_scoring():
    """Test the enhanced value scoring with different product scenarios"""

    engine = FeatureMatchingEngine()

    print("=== ENHANCED VALUE SCORING TEST ===\n")

    # Test scenarios with different price/performance combinations
    test_cases = [
        {
            "name": "Budget Champion (₹15k with excellent specs)",
            "features": {
                "price": 1500000,  # ₹15,000
                "refresh_rate": 144,
                "response_time": 1,
                "resolution": "1440p",
                "panel_type": "ips",
                "brightness": 350,
                "color_accuracy": 95,
                "hdr_support": "hdr10"
            }
        },
        {
            "name": "Mid-range Good Value (₹25k with solid specs)",
            "features": {
                "price": 2500000,  # ₹25,000
                "refresh_rate": 144,
                "response_time": 4,
                "resolution": "1440p",
                "panel_type": "ips",
                "brightness": 300,
                "color_accuracy": 85
            }
        },
        {
            "name": "Premium Overpriced (₹45k with mediocre specs)",
            "features": {
                "price": 4500000,  # ₹45,000
                "refresh_rate": 75,
                "response_time": 8,
                "resolution": "1080p",
                "panel_type": "tn",
                "brightness": 250
            }
        },
        {
            "name": "Ultra-premium Justified (₹55k with top specs)",
            "features": {
                "price": 5500000,  # ₹55,000
                "refresh_rate": 240,
                "response_time": 1,
                "resolution": "4k",
                "panel_type": "ips",
                "brightness": 400,
                "color_accuracy": 99,
                "hdr_support": "hdr10",
                "connectivity": "hdmi2.1 displayport1.4 usb-c"
            }
        }
    ]

    user_features = {
        'max_price': 6000000,  # ₹60,000 budget
        'usage_context': 'gaming'
    }

    for i, test_case in enumerate(test_cases, 1):
        print(f"{i}. {test_case['name']}")
        print(f"   Price: ₹{test_case['features']['price']/100:,.0f}")

        # Calculate technical performance
        tech_perf = engine._calculate_technical_performance(test_case['features'])
        print(".3f")

        # Calculate value score
        value_score = engine._calculate_value_ratio_score(test_case['features'], user_features)
        print(".3f")

        # Calculate overall hybrid score
        hybrid_score, breakdown = engine.calculate_hybrid_score(user_features, test_case['features'])
        print(".3f")
        print(".3f")
        print()

if __name__ == "__main__":
    test_enhanced_value_scoring()
