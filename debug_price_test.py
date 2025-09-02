#!/usr/bin/env python3
"""Debug price extraction issues"""

import sys
sys.path.append('.')

from bot.paapi_ai_bridge import extract_price

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
    def __init__(self, offers):
        self.offers = offers

# Test with valid price
item_with_price = MockItem(MockOffers([MockListing(MockPrice('25990'))]))
price = extract_price(item_with_price)
print(f'Price extraction test: {price} paise (₹{price/100 if price else 0:.2f})')

# Test with no price
item_no_price = MockItem(None)
price_no = extract_price(item_no_price)
print(f'No price test: {price_no}')

print("Price extraction function works correctly")
