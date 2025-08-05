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
            browser = await pw.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                ]
            )
            
            # Prepare headers with optional cookies
            from bot.config import settings
            
            headers = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
            
            # Add cookies if available
            amazon_cookies = getattr(settings, 'AMAZON_COOKIES', None)
            if amazon_cookies:
                headers["Cookie"] = amazon_cookies
                log.debug("Using Amazon cookies for enhanced access")
            
            # Create context with realistic browser settings
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="en-IN",
                timezone_id="Asia/Kolkata",
                permissions=["geolocation"],
                geolocation={"latitude": 28.6139, "longitude": 77.2090},  # Delhi coordinates
                extra_http_headers=headers
            )
            
            page = await context.new_page()
            
            # Block unnecessary resources to speed up loading
            await page.route("**/*.{png,jpg,jpeg,gif,svg,css,woff,woff2}", lambda route: route.abort())
            
            log.info("Scraping price for ASIN %s from %s", asin, url)
            
            # Add random delay and try to bypass bot detection
            import asyncio
            await asyncio.sleep(1 + (hash(asin) % 3))  # 1-4 second delay based on ASIN
            
            await page.goto(url, timeout=60_000, wait_until="domcontentloaded")

            # Save HTML for debugging
            html = await page.content()
            debug_path = Path(f"debug/{asin}.html")
            debug_path.parent.mkdir(exist_ok=True)
            debug_path.write_text(html, encoding="utf-8")
            log.debug("Saved debug HTML to %s", debug_path)

            # Check for captcha or error pages first
            if await page.locator("form[action*='validateCaptcha']").count() > 0:
                log.warning("Captcha detected for ASIN %s", asin)
                raise ValueError(f"Captcha required for ASIN: {asin}")
                
            if await page.locator("text=Looking for something?").count() > 0:
                log.warning("Product not found page for ASIN %s", asin)
                raise ValueError(f"Product not found for ASIN: {asin}")
            
            # Extract product title with updated selectors
            title_selectors = [
                "#productTitle",
                "h1[data-automation-id='title']",
                "h1.a-size-large.a-spacing-none.a-color-base",
                "span#productTitle",
                "h1 span.a-size-large",
                ".product-title",
                "h1.a-size-base-plus",
                "[data-testid='product-title']",
            ]
            
            title = None
            for selector in title_selectors:
                try:
                    title_element = page.locator(selector).first
                    if await title_element.count() > 0:
                        title = await title_element.text_content()
                        if title and title.strip():
                            title = title.strip()
                            log.debug("Found title with selector %s: %s", selector, title[:50])
                            break
                except Exception as e:
                    log.debug("Title selector %s failed: %s", selector, e)
                    continue

            # Extract product image with updated selectors
            image_selectors = [
                "#landingImage",
                "img[data-old-hires]",
                ".a-dynamic-image",
                "#imgBlkFront", 
                ".a-spacing-small img",
                "img.a-dynamic-image.a-stretch-horizontal",
                "div[data-asin] img",
                ".imageThumbnail img",
            ]
            
            image_url = None
            for selector in image_selectors:
                try:
                    img_element = page.locator(selector).first
                    if await img_element.count() > 0:
                        # Try different attributes
                        for attr in ["data-old-hires", "src", "data-src"]:
                            image_url = await img_element.get_attribute(attr)
                            if image_url and image_url.startswith("http"):
                                log.debug("Found image with selector %s attr %s", selector, attr)
                                break
                        if image_url and image_url.startswith("http"):
                            break
                except Exception as e:
                    log.debug("Image selector %s failed: %s", selector, e)
                    continue

            # Try multiple price selectors (Amazon changes them frequently)
            price_selectors = [
                # Current price selectors (2024/2025)
                "span.a-price.a-text-price.a-size-medium.a-color-base span.a-price-whole",
                ".a-price.a-text-price .a-price-whole",
                "#corePrice_feature_div span.a-price-whole",
                "span[class*='a-price-whole']",
                ".a-price-whole",
                
                # Deal/offer price selectors  
                "#corePrice_desktop .a-offscreen",
                ".a-price.a-text-price.a-size-medium.a-color-base .a-offscreen",
                
                # Legacy selectors
                "#priceblock_dealprice",
                "#priceblock_ourprice", 
                ".a-price-range .a-price-whole",
                
                # Alternative formats
                "span[aria-label*='₹']",
                "[data-testid='price-current-price'] .a-price-whole",
                ".a-price.a-text-normal .a-price-whole",
            ]

            price_text = None
            mrp_text = None
            
            # Try to find current price
            for selector in price_selectors:
                try:
                    price_elements = page.locator(selector)
                    count = await price_elements.count()
                    if count > 0:
                        for i in range(count):
                            element = price_elements.nth(i)
                            text = await element.text_content()
                            if text and text.strip():
                                # Clean the text and check if it looks like a price
                                clean_text = text.strip().replace(",", "").replace("₹", "")
                                try:
                                    float(clean_text)
                                    price_text = text.strip()
                                    log.debug("Found price with selector %s: %s", selector, price_text)
                                    break
                                except ValueError:
                                    continue
                        if price_text:
                            break
                except Exception as e:
                    log.debug("Price selector %s failed: %s", selector, e)
                    continue
            
            # Try to find MRP/list price
            mrp_selectors = [
                ".a-price.a-text-price .a-offscreen", 
                "span.a-price.a-text-price.a-size-base .a-offscreen",
                "span[aria-label*='M.R.P']",
                ".a-text-strike .a-offscreen",
                "span.a-price-was .a-offscreen",
            ]
            
            for selector in mrp_selectors:
                try:
                    mrp_element = page.locator(selector).first
                    if await mrp_element.count() > 0:
                        mrp_text = await mrp_element.text_content()
                        if mrp_text and mrp_text.strip():
                            log.debug("Found MRP with selector %s: %s", selector, mrp_text.strip())
                            break
                except Exception as e:
                    log.debug("MRP selector %s failed: %s", selector, e)
                    continue

            await browser.close()

            # Parse prices if found
            price = None
            mrp = None
            
            if price_text:
                try:
                    # Clean and convert current price
                    price_clean = price_text.replace(",", "").replace("₹", "").replace("Rs.", "").strip()
                    price_float = float(price_clean)
                    price = int(price_float * 100)  # Convert to paise
                    log.debug("Parsed current price: ₹%.2f", price_float)
                except (ValueError, TypeError):
                    log.warning("Could not parse price '%s' for ASIN: %s", price_text, asin)
            
            if mrp_text:
                try:
                    # Clean and convert MRP
                    mrp_clean = mrp_text.replace(",", "").replace("₹", "").replace("Rs.", "").replace("M.R.P.:", "").strip()
                    mrp_float = float(mrp_clean)
                    mrp = int(mrp_float * 100)  # Convert to paise
                    log.debug("Parsed MRP: ₹%.2f", mrp_float)
                except (ValueError, TypeError):
                    log.warning("Could not parse MRP '%s' for ASIN: %s", mrp_text, asin)

            # Return available data with enhanced information
            result = {
                "asin": asin,
                "title": title or f"Product {asin}",
                "price": price,
                "mrp": mrp,
                "image": image_url or "https://m.media-amazon.com/images/I/81.png",
                "url": url,
            }
            
            log.info("Scraped data for ASIN %s: title=%s, price=%s, mrp=%s", 
                    asin, title[:50] if title else None, 
                    f"₹{price/100:.2f}" if price else None,
                    f"₹{mrp/100:.2f}" if mrp else None)
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
