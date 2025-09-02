#!/usr/bin/env python3
"""Test search query enhancement for max-price-only searches"""

import sys
sys.path.append('.')

from bot.paapi_official import OfficialPaapiClient

def test_search_enhancement():
    """Test that search queries are enhanced correctly for max-price searches"""
    paapi = OfficialPaapiClient()

    # Test case: "32 inch gaming monitor under INR 60,000"
    # This should trigger premium/gaming enhancements
    keywords = "32 inch gaming monitor under INR 60,000"
    min_price = None  # No minimum price
    max_price = 6000000  # ₹60,000 in paise
    search_index = "All"

    enhanced = paapi._enhance_search_query(
        keywords=keywords,
        title=None,
        brand=None,
        min_price=min_price,
        max_price=max_price,
        search_index=search_index
    )

    print("=== SEARCH ENHANCEMENT TEST ===")
    print(f"Original keywords: '{keywords}'")
    print(f"Min price: {min_price} (₹{(min_price/100) if min_price else 0:.2f})")
    print(f"Max price: {max_price} (₹{max_price/100:.2f})")
    print(f"Search index: {search_index}")
    print(f"Enhanced keywords: '{enhanced}'")

    # Check if premium terms were added
    premium_terms = ["premium", "high-performance", "advanced", "gaming", "144hz", "ips"]
    found_terms = [term for term in premium_terms if term in enhanced.lower()]

    print(f"\nPremium terms found: {found_terms}")
    print(f"Enhancement successful: {len(found_terms) > 0}")

    # Test with lower max price
    print("\n=== TESTING LOWER BUDGET ===")
    low_max_price = 2000000  # ₹20,000
    enhanced_low = paapi._enhance_search_query(
        keywords="32 inch monitor",
        title=None,
        brand=None,
        min_price=None,
        max_price=low_max_price,
        search_index="All"
    )

    print(f"Low budget enhanced: '{enhanced_low}'")

if __name__ == "__main__":
    test_search_enhancement()
