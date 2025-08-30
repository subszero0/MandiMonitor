#!/usr/bin/env python3
"""
Debug script to see what query enhancement returns
"""

import sys
sys.path.insert(0, 'bot')

from bot.paapi_official import OfficialPaapiClient

client = OfficialPaapiClient()

# Test the problematic query
enhanced = client._enhance_search_query(
    keywords="gaming gaming monitor",
    title=None,
    brand=None,
    min_price=3500000,  # ₹35,000
    max_price=None,
    search_index="Electronics"
)

print("Original: 'gaming gaming monitor'")
print(f"Enhanced: '{enhanced}'")
print(f"Length: {len(enhanced) if enhanced else 0}")

if enhanced:
    gaming_count = enhanced.lower().count("gaming")
    print(f"Gaming count: {gaming_count}")

    # Show all terms
    terms = enhanced.split()
    print(f"Terms: {terms}")
    print(f"Unique terms: {len(set(term.lower() for term in terms))}")
