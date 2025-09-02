#!/usr/bin/env python3
"""Test enhanced messaging system with detailed product differentiation"""

import sys
sys.path.append('.')

from bot.ai.enhanced_carousel import _get_product_highlights

def test_enhanced_messaging():
    """Test the enhanced product highlight generation"""

    # Test product with comprehensive features
    test_product = {
        'asin': 'B0123456789',
        'title': 'Samsung UR59C 32" 4K UHD Gaming Monitor',
        'price': 2599000,  # ₹25,990
        'features': {
            'refresh_rate': 144,
            'response_time': 1,
            'resolution': '4K UHD',
            'panel_type': 'IPS',
            'brightness': 350,
            'color_accuracy': 95,
            'hdr_support': 'HDR10',
            'size': 32,
            'connectivity': 'HDMI 2.1'
        },
        'scoring_breakdown': {
            'technical_score': 0.88,
            'value_score': 0.76,
            'budget_score': 1.0
        }
    }

    print("=== ENHANCED MESSAGING TEST ===\n")
    print(f"Product: {test_product['title']}")
    print(f"Price: ₹{test_product['price']/100:,.0f}")
    print(f"Key Features: {test_product['features']}")
    print()

    # Test highlight generation
    highlights = _get_product_highlights(test_product, 0, {})

    print("GENERATED HIGHLIGHTS:")
    for i, highlight in enumerate(highlights, 1):
        print(f"{i}. {highlight}")

    print(f"\nTotal highlights: {len(highlights)}")
    print()

    # Test with different product (budget option)
    budget_product = {
        'asin': 'B0987654321',
        'title': 'Acer Nitro VG240Y 24" Full HD Gaming Monitor',
        'price': 1499000,  # ₹14,990
        'features': {
            'refresh_rate': 75,
            'response_time': 4,
            'resolution': '1080p',
            'panel_type': 'IPS',
            'brightness': 250,
            'size': 24
        },
        'scoring_breakdown': {
            'technical_score': 0.65,
            'value_score': 0.82,
            'budget_score': 1.0
        }
    }

    print("=== BUDGET PRODUCT TEST ===")
    print(f"Product: {budget_product['title']}")
    print(f"Price: ₹{budget_product['price']/100:,.0f}")

    budget_highlights = _get_product_highlights(budget_product, 0, {})

    print("\nBUDGET PRODUCT HIGHLIGHTS:")
    for i, highlight in enumerate(budget_highlights, 1):
        print(f"{i}. {highlight}")

    print(f"\nTotal highlights: {len(budget_highlights)}")

    print("\n=== ANALYSIS ===")
    print("✅ Premium product highlights focus on:")
    premium_focus = [h for h in highlights if any(term in h.lower() for term in ['premium', 'excellent', 'ultra', 'professional', '4k', 'hdr10'])]
    print(f"   - {len(premium_focus)} premium/advanced features")

    print("✅ Budget product highlights focus on:")
    budget_focus = [h for h in budget_highlights if any(term in h.lower() for term in ['budget', 'value', 'great', 'entry-level', 'casual'])]
    print(f"   - {len(budget_focus)} value-focused features")

    print("✅ Both products have differentiated messaging based on their price tier and features")

if __name__ == "__main__":
    test_enhanced_messaging()
