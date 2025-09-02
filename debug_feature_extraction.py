#!/usr/bin/env python3
"""Test enhanced feature extraction for monitor specifications"""

import sys
sys.path.append('.')

from bot.ai.product_analyzer import ProductFeatureAnalyzer

def test_enhanced_feature_extraction():
    """Test that enhanced feature extraction captures more monitor specifications"""

    # Create test product data with detailed monitor specs
    test_product = {
        "asin": "B0123456789",
        "title": "Samsung UR59C 32\" 4K UHD Monitor, 144Hz, IPS Panel, HDR10, 1ms Response Time, HDMI 2.1, DisplayPort 1.4",
        "features": [
            "32-inch 4K UHD (3840x2160) resolution",
            "144Hz refresh rate with 1ms response time",
            "IPS panel technology for vibrant colors",
            "HDR10 support for enhanced contrast",
            "HDMI 2.1 and DisplayPort 1.4 connectivity",
            "99% sRGB color gamut coverage",
            "400 nits brightness for bright visuals",
            "16:9 aspect ratio with ultra-thin bezels"
        ],
        "technical_details": {
            "Brand": "Samsung",
            "Screen Size": "32 Inches",
            "Resolution": "4K UHD (3840 x 2160)",
            "Refresh Rate": "144 Hz",
            "Response Time": "1 ms",
            "Panel Type": "IPS",
            "Brightness": "400 cd/m²",
            "Color Accuracy": "99% sRGB",
            "HDR Support": "HDR10",
            "Connectivity": "HDMI 2.1, DisplayPort 1.4, USB-C"
        },
        "price": 4500000  # ₹45,000 in paise
    }

    print("=== ENHANCED FEATURE EXTRACTION TEST ===\n")
    print(f"Product: {test_product['title']}")
    print(f"Expected Price: ₹{test_product['price']/100:,.0f}")
    print()

    # Test feature extraction
    analyzer = ProductFeatureAnalyzer()

    import asyncio
    extracted_features = asyncio.run(analyzer.analyze_product_features(test_product))

    print("EXTRACTED FEATURES:")
    for feature_name, feature_data in extracted_features.items():
        if isinstance(feature_data, dict):
            value = feature_data.get('value', feature_data)
            confidence = feature_data.get('confidence', 'N/A')
            source = feature_data.get('source', 'N/A')
            print(f"  {feature_name}: {value} (confidence: {confidence}, source: {source})")
        else:
            print(f"  {feature_name}: {feature_data}")

    print(f"\nTotal features extracted: {len(extracted_features)}")

    # Check for key monitor specifications
    expected_features = [
        'refresh_rate', 'response_time', 'size', 'resolution',
        'panel_type', 'brightness', 'color_accuracy', 'hdr_support',
        'connectivity', 'price', 'brand', 'category'
    ]

    found_features = [f for f in expected_features if f in extracted_features]
    missing_features = [f for f in expected_features if f not in extracted_features]

    print(f"\nExpected features found: {len(found_features)}/{len(expected_features)}")
    print(f"Found: {found_features}")
    if missing_features:
        print(f"Missing: {missing_features}")

    # Verify price extraction specifically
    price_value = None
    if 'price' in extracted_features:
        price_data = extracted_features['price']
        if isinstance(price_data, dict):
            price_value = price_data.get('value')
        else:
            price_value = price_data

    print(f"\nPrice extraction verification:")
    print(f"  Expected: ₹45,000")
    print(f"  Extracted: ₹{price_value:,.0f}" if price_value else "  Extracted: None")
    print(f"  Status: {'✅ PASS' if price_value == 45000.0 else '❌ FAIL'}")

if __name__ == "__main__":
    test_enhanced_feature_extraction()
