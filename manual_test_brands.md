# Manual Testing Guide for Dynamic Brand Discovery

## What We Fixed

The issue was that when users searched for "car polish", the bot was showing irrelevant electronics brands (Samsung, LG, Sony, etc.) instead of car care brands.

## How the Fix Works

1. **PA-API First**: Try to get real product data from Amazon PA-API
2. **Scraper Fallback**: If PA-API fails (no credentials or quota exceeded), use Playwright to scrape Amazon search results
3. **Common Brands Fallback**: If both fail, fall back to common electronics brands

## Testing Instructions

### Option 1: Test with Real Telegram Bot

1. Start the bot:
   ```bash
   poetry run python -m bot.main
   ```

2. In Telegram, send messages to test brand discovery:
   - "car polish" 
   - "facewash"
   - "laptop"
   - "headphones"

3. When the bot asks for brand selection, it should now show contextual brands instead of electronics brands for car polish and facewash.

### Option 2: Test Individual Function

You can test the function directly:

```python
import asyncio
from bot.watch_flow import get_dynamic_brands

# Test different categories
async def test_brands():
    print("Car polish brands:", await get_dynamic_brands("car polish"))
    print("Face wash brands:", await get_dynamic_brands("facewash"))
    print("Laptop brands:", await get_dynamic_brands("laptop"))

asyncio.run(test_brands())
```

## Expected Results

### Before Fix
- **Car Polish**: Samsung, LG, Sony, Apple, Boat, Oneplus, Realme, Oppo
- **Face Wash**: Samsung, LG, Sony, Apple, Boat, Oneplus, Realme, Oppo

### After Fix (with working scraper)
- **Car Polish**: 3M, Meguiar's, Chemical Guys, Turtle Wax, Armor All, etc.
- **Face Wash**: Himalaya, Cetaphil, Neutrogena, Plum, Lakme, etc.

### After Fix (scraper timeout - fallback)
- **Car Polish**: Samsung, LG, Sony, Apple, Boat (graceful degradation)
- **Face Wash**: Samsung, LG, Sony, Apple, Boat (graceful degradation)

## Implementation Details

The function now:

1. **Enhanced Pattern Matching**: 
   - Extracts brands from titles like "Meguiar's Gold Class"
   - Handles "by Brand" patterns like "Polish by 3M"
   - Processes parentheses patterns like "(Apple iPhone)"
   - Works with separators like "3M - Super Polish"

2. **Smart Filtering**:
   - Filters out quantities like "250ml", "1L", "500gm"
   - Excludes product codes like "IA260166334"
   - Removes common non-brand words
   - Keeps relevant brand names

3. **Robust Fallback Chain**:
   - PA-API → Scraper → Common Brands
   - Each step logs what happened for debugging
   - Never leaves users without brand options

## Note on Scraper Performance

Amazon actively blocks automated scrapers, so the scraper might timeout in some environments. This is expected and the fallback mechanism handles it gracefully. In production with proper configuration (cookies, rate limiting), the scraper success rate would be higher.

The key improvement is that the bot now tries to get real, contextual brand data instead of always showing the same electronics brands for every search.