"""Playwright web scraper for fallback price fetching."""

from logging import getLogger
from pathlib import Path

from playwright.async_api import async_playwright

log = getLogger(__name__)


async def scrape_product_data(asin: str) -> dict:
    """Scrape product data from Amazon page using Playwright.

    Args:
    ----
        asin: Amazon Standard Identification Number

    Returns:
    -------
        Dictionary with price (in paise), title, and image URL

    Raises:
    ------
        ValueError: If data cannot be extracted

    """
    url = f"https://www.amazon.in/dp/{asin}"

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            page = await browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            )

            log.info("Scraping price for ASIN %s from %s", asin, url)
            await page.goto(url, timeout=30_000)

            # Save HTML for debugging
            html = await page.content()
            debug_path = Path(f"debug/{asin}.html")
            debug_path.parent.mkdir(exist_ok=True)
            debug_path.write_text(html, encoding="utf-8")
            log.debug("Saved debug HTML to %s", debug_path)

            # Extract product title
            title_selectors = [
                "#productTitle",
                "h1.a-size-large",
                "h1 span",
                ".product-title",
            ]
            
            title = None
            for selector in title_selectors:
                try:
                    title_element = page.locator(selector).first
                    if await title_element.is_visible():
                        title = await title_element.text_content()
                        if title and title.strip():
                            title = title.strip()
                            break
                except Exception:
                    continue

            # Extract product image
            image_selectors = [
                "#landingImage",
                ".a-dynamic-image",
                "#imgBlkFront",
                ".a-spacing-small img",
            ]
            
            image_url = None
            for selector in image_selectors:
                try:
                    img_element = page.locator(selector).first
                    if await img_element.is_visible():
                        image_url = await img_element.get_attribute("src")
                        if image_url and image_url.startswith("http"):
                            break
                except Exception:
                    continue

            # Try multiple price selectors (Amazon changes them frequently)
            price_selectors = [
                "#corePrice_feature_div span.a-price-whole",
                ".a-price-whole",
                "#priceblock_dealprice",
                "#priceblock_ourprice",
                ".a-price.a-text-price .a-price-whole",
                ".a-price-range .a-price-whole",
            ]

            price_text = None
            for selector in price_selectors:
                try:
                    price_element = page.locator(selector).first
                    if await price_element.is_visible():
                        price_text = await price_element.text_content()
                        if price_text:
                            break
                except Exception:
                    continue

            await browser.close()

            # Parse price if found
            price = None
            if price_text:
                try:
                    # Clean and convert price
                    price_clean = price_text.replace(",", "").replace("₹", "").strip()
                    price_float = float(price_clean)
                    price = int(price_float * 100)  # Convert to paise
                except (ValueError, TypeError):
                    log.warning("Could not parse price '%s' for ASIN: %s", price_text, asin)

            # Return available data
            result = {
                "asin": asin,
                "title": title or f"Product {asin}",
                "price": price,
                "image": image_url or "https://m.media-amazon.com/images/I/81.png",
            }
            
            log.info("Scraped data for ASIN %s: title=%s, price=%s", asin, title, price)
            return result

    except Exception as e:
        log.error("Scraping failed for ASIN %s: %s", asin, e)
        raise


async def scrape_price(asin: str) -> int:
    """Scrape product price from Amazon page (compatibility function).

    Args:
    ----
        asin: Amazon Standard Identification Number

    Returns:
    -------
        Price in paise (integer)

    Raises:
    ------
        ValueError: If price cannot be extracted

    """
    try:
        product_data = await scrape_product_data(asin)
        if product_data.get("price") is None:
            raise ValueError(f"No price found for ASIN: {asin}")
        return product_data["price"]
    except Exception as e:
        log.error("Price scraping failed for ASIN %s: %s", asin, e)
        raise
