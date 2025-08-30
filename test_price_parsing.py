#!/usr/bin/env python3
"""
Test script to verify price parsing fixes for INR currency support.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bot.watch_parser import parse_watch


def test_price_parsing():
    """Test price parsing with various formats including INR."""

    test_cases = [
        # Test case: Original failing query
        {
            "input": "32 inch gaming monitor between INR 40000 and INR 50000",
            "expected": {"min_price": 40000, "max_price": 50000}
        },
        # Test case: Mixed currency formats
        {
            "input": "laptop between INR 30000 and 50000",
            "expected": {"min_price": 30000, "max_price": 50000}
        },
        # Test case: Traditional format
        {
            "input": "phone between 20000 and 40000",
            "expected": {"min_price": 20000, "max_price": 40000}
        },
        # Test case: With K notation
        {
            "input": "monitor between INR 40k and INR 50k",
            "expected": {"min_price": 40000, "max_price": 50000}
        },
        # Test case: Under format with INR
        {
            "input": "laptop under INR 30000",
            "expected": {"max_price": 30000, "min_price": None}
        },
    ]

    print("🧪 Testing Price Parsing with INR Support")
    print("=" * 60)

    all_passed = True

    for i, test_case in enumerate(test_cases, 1):
        input_text = test_case["input"]
        expected = test_case["expected"]

        print(f"\nTest {i}: '{input_text}'")

        # Parse the watch data
        result = parse_watch(input_text)

        # Check results
        actual_min = result.get("min_price")
        actual_max = result.get("max_price")
        expected_min = expected.get("min_price")
        expected_max = expected.get("max_price")

        min_passed = actual_min == expected_min
        max_passed = actual_max == expected_max

        if min_passed and max_passed:
            print("  ✅ PASSED")
        else:
            print("  ❌ FAILED")
            all_passed = False
            print(f"     Expected: min_price={expected_min}, max_price={expected_max}")
            print(f"     Actual:   min_price={actual_min}, max_price={actual_max}")

        # Additional debug info
        print(f"     Parsed keywords: {result.get('keywords', '')[:50]}...")
        print(f"     Full result: {result}")

    print("\n" + "=" * 60)
    print("📊 FINAL RESULT")
    print("=" * 60)

    if all_passed:
        print("🎉 ALL TESTS PASSED! INR price parsing is working correctly.")
        print("✅ Price filters should now be applied to PA-API searches.")
    else:
        print("❌ SOME TESTS FAILED! Price parsing needs more work.")

    return all_passed


if __name__ == "__main__":
    test_price_parsing()
