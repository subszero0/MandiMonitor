# Amazon Product Advertising API (PA-API) 5.0 - Complete Reference

## Table of Contents
1. [Overview](#overview)
2. [Operations](#operations)
3. [Resources](#resources)
4. [Common Request Parameters](#common-request-parameters)
5. [Best Programming Practices](#best-programming-practices)
6. [Use Case Scenarios](#use-case-scenarios)
7. [Quick Start Guide](#quick-start-guide)
8. [Implementation Examples](#implementation-examples)

---

## Overview

Amazon Product Advertising API (PA-API) 5.0 is a RESTful web service that allows developers to advertise Amazon products on their websites and mobile applications. It provides access to Amazon's product catalog, customer reviews, and other features to help drive traffic and sales.

### Key Features
- Access to millions of products in Amazon's catalog
- Real-time pricing and availability information
- Product images, descriptions, and features
- Customer reviews and ratings
- Browse node information for categorization
- Affiliate link generation for commission tracking

---

## Operations

PA-API 5.0 provides four main operations to interact with Amazon's product data:

### 1. GetItems
**Purpose**: Retrieve detailed information about specific products using ASINs.

**Request Parameters**:
- `ItemIds` (required): Array of ASINs (up to 10 per request)
- `Resources` (required): Array of resources to retrieve
- `PartnerTag` (required): Your Associate tag
- `PartnerType` (required): Always "Associates"
- `Marketplace` (required): Target marketplace (e.g., "www.amazon.com")

**Example Use Cases**:
- Get current price and availability for tracked products
- Retrieve detailed product information for display
- Fetch product images and descriptions

**Rate Limits**: 1 request per second, burst up to 10 requests

### 2. SearchItems
**Purpose**: Search for products using keywords, categories, or other criteria.

**Request Parameters**:
- `Keywords` (conditional): Search terms
- `SearchIndex` (optional): Product category to search within
- `Title` (conditional): Search by product title
- `Actor` (conditional): Search by actor name
- `Artist` (conditional): Search by artist name
- `Author` (conditional): Search by author name
- `Brand` (conditional): Search by brand name
- `ItemCount` (optional): Number of items to return (1-10, default 1)
- `ItemPage` (optional): Page number for pagination (1-10)
- `SortBy` (optional): Sort criteria
- `Resources` (required): Array of resources to retrieve

**Search Indices**: All, Apparel, Automotive, Baby, Beauty, Books, Classical, DigitalMusic, Electronics, EverythingElse, Fashion, ForeignBooks, GardenAndOutdoor, GiftCards, GroceryAndGourmetFood, Handmade, HealthPersonalCare, HomeAndGarden, Industrial, Jewelry, KindleStore, Kitchen, LawnAndGarden, Luggage, Magazines, MobileApps, MoviesAndTV, Music, MusicalInstruments, OfficeProducts, PetSupplies, Photo, Software, SportsAndOutdoors, ToolsAndHomeImprovement, ToysAndGames, VHS, Video, VideoGames, Watches

**Rate Limits**: 1 request per second, burst up to 10 requests

### 3. GetBrowseNodes
**Purpose**: Retrieve browse node information to understand Amazon's product categorization.

**Request Parameters**:
- `BrowseNodeIds` (required): Array of browse node IDs (up to 10 per request)
- `Resources` (required): Array of resources to retrieve
- `LanguagesOfPreference` (optional): Language preferences

**Example Use Cases**:
- Build category navigation
- Understand product hierarchies
- Implement category-based filtering

**Rate Limits**: 1 request per second

### 4. GetVariations
**Purpose**: Retrieve variations of a parent product (different sizes, colors, etc.).

**Request Parameters**:
- `ASIN` (required): Parent ASIN
- `Resources` (required): Array of resources to retrieve
- `VariationCount` (optional): Number of variations to return (default 10, max 10)
- `VariationPage` (optional): Page number for pagination

**Example Use Cases**:
- Show different color/size options
- Compare variations of the same product
- Build product comparison pages

**Rate Limits**: 1 request per second

---

## Resources

Resources define what data fields to retrieve in API responses. You must specify which resources you want to avoid unnecessary data transfer.

### ItemInfo Resources
- `ItemInfo.ByLineInfo`: Author, brand, contributor, manufacturer
- `ItemInfo.ContentInfo`: Languages, page count, publication date
- `ItemInfo.ContentRating`: Age rating, audience rating
- `ItemInfo.Classifications`: Binding, product group, product type
- `ItemInfo.ExternalIds`: EAN, ISBN, UPC codes
- `ItemInfo.Features`: Key product features
- `ItemInfo.ManufactureInfo`: Manufacturer, model
- `ItemInfo.ProductInfo`: Color, is adult product, item dimensions
- `ItemInfo.TechnicalInfo`: Formats, technical details
- `ItemInfo.Title`: Product title
- `ItemInfo.TradeInInfo`: Trade-in price and eligibility

### Offers Resources
- `Offers.Listings.Availability.MaxOrderQuantity`: Maximum order quantity
- `Offers.Listings.Availability.Message`: Availability message
- `Offers.Listings.Availability.MinOrderQuantity`: Minimum order quantity
- `Offers.Listings.Availability.Type`: Availability status
- `Offers.Listings.Condition`: Item condition (new, used, etc.)
- `Offers.Listings.Condition.SubCondition`: Detailed condition
- `Offers.Listings.DeliveryInfo.IsAmazonFulfilled`: Fulfillment by Amazon
- `Offers.Listings.DeliveryInfo.IsFreeShippingEligible`: Free shipping eligibility
- `Offers.Listings.DeliveryInfo.IsPrimeEligible`: Prime eligibility
- `Offers.Listings.DeliveryInfo.ShippingCharges`: Shipping cost
- `Offers.Listings.IsBuyBoxWinner`: Buy box status
- `Offers.Listings.LoyaltyPoints.Points`: Loyalty points earned
- `Offers.Listings.MerchantInfo`: Seller information
- `Offers.Listings.Price`: Current price
- `Offers.Listings.ProgramEligibility.IsPrimeExclusive`: Prime exclusive
- `Offers.Listings.ProgramEligibility.IsPrimePantry`: Prime Pantry eligible
- `Offers.Listings.Promotions`: Available promotions
- `Offers.Listings.SavingBasis`: Original price for savings calculation
- `Offers.Summaries.HighestPrice`: Highest price across all offers
- `Offers.Summaries.LowestPrice`: Lowest price across all offers
- `Offers.Summaries.OfferCount`: Number of offers

### Images Resources
- `Images.Primary.Small`: Small primary image (75x75)
- `Images.Primary.Medium`: Medium primary image (160x160)
- `Images.Primary.Large`: Large primary image (500x500)
- `Images.Variants.Small`: Small variant images
- `Images.Variants.Medium`: Medium variant images
- `Images.Variants.Large`: Large variant images

### CustomerReviews Resources
- `CustomerReviews.Count`: Number of customer reviews
- `CustomerReviews.StarRating`: Average star rating

### BrowseNodeInfo Resources
- `BrowseNodeInfo.BrowseNodes`: Browse node hierarchy
- `BrowseNodeInfo.BrowseNodes.Ancestor`: Parent browse nodes
- `BrowseNodeInfo.BrowseNodes.Children`: Child browse nodes
- `BrowseNodeInfo.WebsiteSalesRank`: Sales rank in category

### ParentASIN Resources
- `ParentASIN`: Parent ASIN for variations

### RentalOffers Resources
- `RentalOffers.Listings.Availability`: Rental availability
- `RentalOffers.Listings.BasePrice`: Base rental price
- `RentalOffers.Listings.Condition`: Rental item condition
- `RentalOffers.Listings.DeliveryInfo`: Rental delivery information
- `RentalOffers.Listings.MerchantInfo`: Rental merchant info

### SearchRefinements Resources
- `SearchRefinements.BinName`: Refinement category name
- `SearchRefinements.Bins`: Available refinement options

---

## Common Request Parameters

These parameters are common across most PA-API operations:

### Required Parameters
- **PartnerTag**: Your Amazon Associate tag for tracking commissions
- **PartnerType**: Always set to "Associates"
- **Marketplace**: Target Amazon marketplace (e.g., "www.amazon.com", "www.amazon.in")

### Optional Parameters
- **LanguagesOfPreference**: Array of language codes (e.g., ["en_US", "es_ES"])
- **CurrencyOfPreference**: Preferred currency code (e.g., "USD", "INR")
- **Merchant**: Filter by merchant ("Amazon" for Amazon-sold items, "All" for all merchants)

### Marketplace URLs by Region
- **US**: www.amazon.com
- **Canada**: www.amazon.ca
- **Mexico**: www.amazon.com.mx
- **Brazil**: www.amazon.com.br
- **UK**: www.amazon.co.uk
- **Germany**: www.amazon.de
- **France**: www.amazon.fr
- **Italy**: www.amazon.it
- **Spain**: www.amazon.es
- **Netherlands**: www.amazon.nl
- **India**: www.amazon.in
- **Japan**: www.amazon.co.jp
- **China**: www.amazon.cn
- **Singapore**: www.amazon.sg
- **Australia**: www.amazon.com.au
- **Turkey**: www.amazon.com.tr
- **UAE**: www.amazon.ae
- **Saudi Arabia**: www.amazon.sa

---

## Best Programming Practices

### 1. Rate Limiting and Throttling
**Guidelines**:
- Maximum 1 request per second for all operations
- Burst capacity: up to 10 requests can be made quickly
- Implement exponential backoff for throttling errors
- Use HTTP 429 (Too Many Requests) as throttling indicator

**Implementation**:
```python
import time
import random

def make_request_with_backoff(api_call, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = api_call()
            return response
        except ThrottlingException:
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                time.sleep(wait_time)
            else:
                raise
```

### 2. Caching Strategy
**Recommendations**:
- Cache product data for 24 hours minimum
- Cache browse node data for longer periods (7 days)
- Use cache keys based on ASIN + requested resources
- Implement cache invalidation for price-sensitive data

### 3. Error Handling
**Common Error Types**:
- **InvalidParameterValue**: Invalid parameter values
- **MissingParameter**: Required parameter missing
- **RequestThrottled**: Rate limit exceeded
- **AccessDenied**: Invalid credentials or permissions
- **ItemNotAccessible**: Product not available via PA-API

**Implementation Pattern**:
```python
try:
    response = api.get_items(request)
    return process_response(response)
except RequestThrottled:
    # Implement backoff and retry
    return handle_throttling()
except AccessDenied:
    # Check credentials and permissions
    return handle_auth_error()
except ItemNotAccessible:
    # Product not available via API
    return handle_unavailable_item()
```

### 4. Resource Optimization
**Best Practices**:
- Only request resources you actually need
- Use batch operations when possible (up to 10 ASINs per GetItems request)
- Prefer GetItems over SearchItems for known ASINs
- Cache frequently accessed data

### 5. Data Quality
**Validation Steps**:
- Always check if requested resources are present in response
- Handle missing or null values gracefully
- Validate price data before displaying
- Check offer availability before promoting products

---

## Use Case Scenarios

### 1. Price Comparison Website
**Operations**: GetItems, SearchItems
**Resources**: 
- `ItemInfo.Title`
- `Offers.Listings.Price`
- `Offers.Summaries.LowestPrice`
- `Images.Primary.Medium`

**Implementation Flow**:
1. Search for products using SearchItems
2. Get detailed pricing with GetItems
3. Compare prices across different sellers
4. Display results with affiliate links

### 2. Product Recommendation Engine
**Operations**: GetItems, GetBrowseNodes, SearchItems
**Resources**:
- `ItemInfo.Title`
- `ItemInfo.Features`
- `CustomerReviews.StarRating`
- `BrowseNodeInfo.BrowseNodes`

**Implementation Flow**:
1. Analyze customer browsing/purchase history
2. Use browse nodes to find related categories
3. Search for similar products
4. Rank by ratings and features

### 3. Inventory Management System
**Operations**: GetItems
**Resources**:
- `Offers.Listings.Availability`
- `Offers.Listings.Price`
- `Offers.Listings.Availability.MaxOrderQuantity`

**Implementation Flow**:
1. Monitor product availability regularly
2. Track price changes over time
3. Alert when products go out of stock
4. Update local inventory based on Amazon data

### 4. Affiliate Marketing Platform
**Operations**: SearchItems, GetItems, GetVariations
**Resources**:
- `ItemInfo.Title`
- `ItemInfo.Features`
- `Offers.Listings.Price`
- `Images.Primary.Large`
- `CustomerReviews`

**Implementation Flow**:
1. Create product comparison content
2. Generate affiliate links for products
3. Track click-through rates
4. Optimize content based on performance

### 5. Mobile Shopping App
**Operations**: SearchItems, GetItems, GetBrowseNodes
**Resources**:
- `ItemInfo.Title`
- `ItemInfo.ProductInfo`
- `Offers.Listings.Price`
- `Images.Primary.Large`
- `CustomerReviews.StarRating`

**Implementation Flow**:
1. Implement search functionality
2. Display product categories using browse nodes
3. Show detailed product pages
4. Enable price tracking and alerts

---

## Quick Start Guide

### Step 1: Prerequisites
1. **Amazon Associate Account**: Register at https://affiliate-program.amazon.com/
2. **PA-API Access**: Apply for PA-API access through your Associate account
3. **Credentials**: Obtain Access Key, Secret Key, and Associate Tag

### Step 2: Environment Setup
```bash
# Install the official Python SDK
pip install paapi5-python-sdk

# Or use the popular wrapper
pip install amazon-paapi
```

### Step 3: Configuration
```python
# config.py
import os

PAAPI_CONFIG = {
    'access_key': os.getenv('PAAPI_ACCESS_KEY'),
    'secret_key': os.getenv('PAAPI_SECRET_KEY'),
    'partner_tag': os.getenv('PAAPI_TAG'),
    'host': 'webservices.amazon.com',  # US marketplace
    'region': 'us-east-1'
}
```

### Step 4: Basic Implementation
```python
from paapi5_python_sdk.api.default_api import DefaultApi
from paapi5_python_sdk.models.get_items_request import GetItemsRequest
from paapi5_python_sdk.models.get_items_resource import GetItemsResource
from paapi5_python_sdk.models.partner_type import PartnerType

def get_product_details(asin):
    api = DefaultApi(
        access_key=PAAPI_CONFIG['access_key'],
        secret_key=PAAPI_CONFIG['secret_key'],
        host=PAAPI_CONFIG['host'],
        region=PAAPI_CONFIG['region']
    )
    
    request = GetItemsRequest(
        partner_tag=PAAPI_CONFIG['partner_tag'],
        partner_type=PartnerType.ASSOCIATES,
        marketplace="www.amazon.com",
        item_ids=[asin],
        resources=[
            GetItemsResource.ITEMINFO_TITLE,
            GetItemsResource.OFFERS_LISTINGS_PRICE,
            GetItemsResource.IMAGES_PRIMARY_LARGE
        ]
    )
    
    try:
        response = api.get_items(request)
        if response.items_result and response.items_result.items:
            item = response.items_result.items[0]
            return {
                'title': item.item_info.title.display_value,
                'price': item.offers.listings[0].price.display_amount,
                'image': item.images.primary.large.url
            }
    except Exception as e:
        print(f"Error: {e}")
        return None
```

### Step 5: Testing
```python
# Test with a known ASIN
product = get_product_details('B08N5WRWNW')
if product:
    print(f"Title: {product['title']}")
    print(f"Price: {product['price']}")
    print(f"Image: {product['image']}")
```

---

## Implementation Examples

### Example 1: Product Search with Filtering
```python
from paapi5_python_sdk.models.search_items_request import SearchItemsRequest
from paapi5_python_sdk.models.search_items_resource import SearchItemsResource

def search_products(keywords, category=None, min_price=None, max_price=None):
    request = SearchItemsRequest(
        partner_tag=PAAPI_CONFIG['partner_tag'],
        partner_type=PartnerType.ASSOCIATES,
        marketplace="www.amazon.com",
        keywords=keywords,
        search_index=category or "All",
        item_count=10,
        resources=[
            SearchItemsResource.ITEMINFO_TITLE,
            SearchItemsResource.OFFERS_LISTINGS_PRICE,
            SearchItemsResource.IMAGES_PRIMARY_MEDIUM,
            SearchItemsResource.CUSTOMERREVIEWS_STARRATING
        ]
    )
    
    # Add price filters if specified
    if min_price or max_price:
        request.min_price = min_price * 100 if min_price else None  # Convert to cents
        request.max_price = max_price * 100 if max_price else None
    
    try:
        response = api.search_items(request)
        return process_search_results(response)
    except Exception as e:
        print(f"Search error: {e}")
        return []
```

### Example 2: Price Tracking System
```python
import sqlite3
from datetime import datetime

def track_price_changes(asins):
    conn = sqlite3.connect('price_history.db')
    cursor = conn.cursor()
    
    # Create table if not exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS price_history (
            asin TEXT,
            price REAL,
            timestamp DATETIME,
            title TEXT
        )
    ''')
    
    for asin in asins:
        product = get_product_details(asin)
        if product:
            cursor.execute('''
                INSERT INTO price_history (asin, price, timestamp, title)
                VALUES (?, ?, ?, ?)
            ''', (asin, extract_price(product['price']), datetime.now(), product['title']))
    
    conn.commit()
    conn.close()

def extract_price(price_string):
    # Extract numeric value from price string like "$29.99"
    import re
    match = re.search(r'[\d,]+\.?\d*', price_string.replace(',', ''))
    return float(match.group()) if match else 0.0
```

### Example 3: Category Browse Implementation
```python
from paapi5_python_sdk.models.get_browse_nodes_request import GetBrowseNodesRequest
from paapi5_python_sdk.models.get_browse_nodes_resource import GetBrowseNodesResource

def get_category_hierarchy(browse_node_id):
    request = GetBrowseNodesRequest(
        partner_tag=PAAPI_CONFIG['partner_tag'],
        partner_type=PartnerType.ASSOCIATES,
        marketplace="www.amazon.com",
        browse_node_ids=[browse_node_id],
        resources=[
            GetBrowseNodesResource.BROWSENODEINFO_BROWSENODES,
            GetBrowseNodesResource.BROWSENODEINFO_BROWSENODES_ANCESTOR,
            GetBrowseNodesResource.BROWSENODEINFO_BROWSENODES_CHILDREN
        ]
    )
    
    try:
        response = api.get_browse_nodes(request)
        if response.browse_nodes_result and response.browse_nodes_result.browse_nodes:
            node = response.browse_nodes_result.browse_nodes[0]
            return {
                'id': node.id,
                'name': node.display_name,
                'children': [{'id': child.id, 'name': child.display_name} 
                           for child in node.children] if node.children else [],
                'ancestors': [{'id': ancestor.id, 'name': ancestor.display_name} 
                            for ancestor in node.ancestor] if node.ancestor else []
            }
    except Exception as e:
        print(f"Browse node error: {e}")
        return None
```

### Example 4: Affiliate Link Generation
```python
def generate_affiliate_link(asin, tag=None):
    partner_tag = tag or PAAPI_CONFIG['partner_tag']
    base_url = "https://www.amazon.com/dp/"
    affiliate_params = f"?tag={partner_tag}&linkCode=ogi&th=1&psc=1"
    return f"{base_url}{asin}{affiliate_params}"

def create_product_widget(asin):
    product = get_product_details(asin)
    if product:
        affiliate_link = generate_affiliate_link(asin)
        return {
            'title': product['title'],
            'price': product['price'],
            'image': product['image'],
            'affiliate_link': affiliate_link,
            'asin': asin
        }
    return None
```

---

## Error Handling Reference

### Common HTTP Status Codes
- **200**: Success
- **400**: Bad Request (invalid parameters)
- **401**: Unauthorized (invalid credentials)
- **403**: Forbidden (access denied or rate limit exceeded)
- **404**: Not Found (invalid endpoint)
- **429**: Too Many Requests (rate limit exceeded)
- **500**: Internal Server Error
- **503**: Service Unavailable (temporary)

### Error Response Structure
```json
{
  "Errors": [
    {
      "Code": "InvalidParameterValue",
      "Message": "The ItemId B000000000 provided in the request is invalid."
    }
  ]
}
```

### Retry Strategy Implementation
```python
import time
import random
from functools import wraps

def retry_with_backoff(max_retries=3, base_delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    
                    # Calculate exponential backoff with jitter
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    print(f"Attempt {attempt + 1} failed, retrying in {delay:.2f}s")
                    time.sleep(delay)
            
        return wrapper
    return decorator

@retry_with_backoff(max_retries=3)
def robust_api_call(api_function, *args, **kwargs):
    return api_function(*args, **kwargs)
```

---

## Performance Optimization Tips

### 1. Batch Requests
- Use GetItems with multiple ASINs (up to 10) instead of individual calls
- Group related operations together

### 2. Efficient Resource Selection
- Only request resources you actually need
- Use specific resource paths instead of broad categories

### 3. Caching Strategy
```python
import redis
import json
from datetime import timedelta

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def cached_api_call(cache_key, api_function, ttl_hours=24):
    # Try to get from cache first
    cached_result = redis_client.get(cache_key)
    if cached_result:
        return json.loads(cached_result)
    
    # Make API call if not in cache
    result = api_function()
    if result:
        redis_client.setex(
            cache_key, 
            timedelta(hours=ttl_hours), 
            json.dumps(result)
        )
    
    return result
```

### 4. Connection Pooling
```python
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import requests

def create_session_with_retries():
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        status_forcelist=[429, 500, 502, 503, 504],
        method_whitelist=["HEAD", "GET", "OPTIONS"],
        backoff_factor=1
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session
```

---

This comprehensive reference document provides everything needed to effectively implement and use Amazon PA-API 5.0 in your MandiMonitor project. Refer to specific sections as needed during development and implementation.
