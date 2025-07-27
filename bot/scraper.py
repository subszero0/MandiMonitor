"""Playwright web scraper for fallback price fetching."""

from logging import getLogger
from pathlib import Path
from playwright.sync_api import sync_playwright

log = getLogger(__name__)


def scrape_price(asin: str) -> int:
    """Scrape product price from Amazon page using Playwright.

    Args:
        asin: Amazon Standard Identification Number

    Returns:
        Price in paise (integer)

    Raises:
        ValueError: If price cannot be extracted
    """
    url = f"https://www.amazon.in/dp/{asin}"

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )

            log.info("Scraping price for ASIN %s from %s", asin, url)
            page.goto(url, timeout=30_000)

            # Save HTML for debugging
            html = page.content()
            debug_path = Path(f"debug/{asin}.html")
            debug_path.parent.mkdir(exist_ok=True)
            debug_path.write_text(html, encoding="utf-8")
            log.debug("Saved debug HTML to %s", debug_path)

            # Try multiple price selectors (Amazon changes them frequently)
            price_selectors = [
                "#corePrice_feature_div span.a-price-whole",
                ".a-price-whole",
                "#priceblock_dealprice",
                "#priceblock_ourprice",
                ".a-price.a-text-price .a-price-whole",
            ]

            price_text = None
            for selector in price_selectors:
                try:
                    price_element = page.locator(selector).first
                    if price_element.is_visible():
                        price_text = price_element.text_content()
                        if price_text:
                            break
                except Exception:
                    continue

            browser.close()

            if not price_text:
                raise ValueError(f"No price found in page for ASIN: {asin}")

            # Clean and convert price
            price_clean = price_text.replace(",", "").replace("₹", "").strip()
            try:
                # Convert to paise (multiply by 100)
                price_float = float(price_clean)
                return int(price_float * 100)
            except (ValueError, TypeError) as e:
                raise ValueError(
                    f"Could not parse price '{price_text}' for ASIN: {asin}"
                ) from e

    except Exception as e:
        log.error("Scraping failed for ASIN %s: %s", asin, e)
        raise
