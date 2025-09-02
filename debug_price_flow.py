#!/usr/bin/env python3
"""Debug the complete price data flow from PA-API to AI scoring"""

import sys
sys.path.append('.')

from bot.paapi_ai_bridge import extract_price, transform_paapi_to_ai_format
from bot.ai.product_analyzer import ProductFeatureAnalyzer
from bot.ai.matching_engine import FeatureMatchingEngine

# Mock PA-API response structure
class MockPrice:
    def __init__(self, amount):
        self.amount = amount

class MockListing:
    def __init__(self, price):
        self.price = price

class MockOffers:
    def __init__(self, listings):
        self.listings = listings

class MockItem:
    def __init__(self, offers, asin="B0123456789", title="Test Gaming Monitor 32\""):
        self.offers = offers
        self.asin = asin
        self.title = title

# Test the complete data flow
async def test_price_flow():
    print("=== TESTING PRICE DATA FLOW ===\n")

    # 1. Create mock PA-API item with price
    mock_item = MockItem(
        MockOffers([MockListing(MockPrice('25990'))]),
        asin="B0123456789",
        title="Samsung UR59C 32\" 4K UHD Monitor"
    )

    # 2. Test price extraction
    price = extract_price(mock_item)
    print(f"1. PA-API Price Extraction: {price} paise (₹{price/100 if price else 0:.2f})")

    # 3. Test transformation to AI format
    ai_product = await transform_paapi_to_ai_format(mock_item)
    print(f"2. AI Format Price: {ai_product.get('price')} paise (₹{ai_product.get('price', 0)/100:.2f})")

    # 4. Test feature extraction
    analyzer = ProductFeatureAnalyzer()
    features = await analyzer.analyze_product_features(ai_product)
    print(f"3. Extracted Features: {len(features)} features")
    print(f"   Price in features: {features.get('price', 'NOT FOUND')}")

    # For scoring, we need simple values, not dict structures
    simple_features = {}
    for key, value in features.items():
        if isinstance(value, dict) and 'value' in value:
            simple_features[key] = value['value']
        else:
            simple_features[key] = value

    print(f"   Simple price for scoring: {simple_features.get('price', 'NOT FOUND')}")

    # 5. Test scoring
    engine = FeatureMatchingEngine()
    user_features = {
        'category_detected': 'gaming_monitor',
        'size': '32',
        'usage_context': 'gaming',
        'max_price': 6000000,  # ₹60,000 in paise
        'original_query': '32 inch gaming monitor under INR 60,000'
    }

    score, breakdown = engine.calculate_hybrid_score(user_features, simple_features)
    print(f"4. Hybrid Score: {score:.3f}")
    print(f"   Value Score: {breakdown['value_score']:.3f}")
    print(f"   Budget Score: {breakdown['budget_score']:.3f}")
    print(f"   Price used in scoring: ₹{simple_features.get('price', 0):,.0f}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_price_flow())
