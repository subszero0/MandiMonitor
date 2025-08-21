"""PA-API resource configuration for different use cases."""

from typing import List

# Minimal resources for basic product information
MINIMAL_RESOURCES = ["ItemInfo.Title", "Offers.Listings.Price", "Images.Primary.Large"]

# Detailed resources for comprehensive product display
DETAILED_RESOURCES = MINIMAL_RESOURCES + [
    "ItemInfo.ByLineInfo",
    "ItemInfo.Features",
    "ItemInfo.ProductInfo",
    "CustomerReviews.Count",
    "CustomerReviews.StarRating",
    "Offers.Listings.Availability.Type",
    "Offers.Listings.Condition",
    "Offers.Listings.DeliveryInfo.IsPrimeEligible",
    "Offers.Listings.DeliveryInfo.IsFreeShippingEligible",
    "Images.Primary.Medium",
    "Images.Primary.Small",
]

# Full resources for complete data enrichment
FULL_RESOURCES = [
    # ItemInfo resources
    "ItemInfo.Title",
    "ItemInfo.ByLineInfo",
    "ItemInfo.ContentInfo",
    "ItemInfo.Classifications",
    "ItemInfo.ExternalIds",
    "ItemInfo.Features",
    "ItemInfo.ManufactureInfo",
    "ItemInfo.ProductInfo",
    "ItemInfo.TechnicalInfo",
    "ItemInfo.TradeInInfo",
    # Offers resources
    "Offers.Listings.Availability.MaxOrderQuantity",
    "Offers.Listings.Availability.Message",
    "Offers.Listings.Availability.MinOrderQuantity",
    "Offers.Listings.Availability.Type",
    "Offers.Listings.Condition",
    "Offers.Listings.Condition.SubCondition",
    "Offers.Listings.DeliveryInfo.IsAmazonFulfilled",
    "Offers.Listings.DeliveryInfo.IsFreeShippingEligible",
    "Offers.Listings.DeliveryInfo.IsPrimeEligible",
    "Offers.Listings.DeliveryInfo.ShippingCharges",
    "Offers.Listings.IsBuyBoxWinner",
    "Offers.Listings.LoyaltyPoints.Points",
    "Offers.Listings.MerchantInfo",
    "Offers.Listings.Price",
    "Offers.Listings.ProgramEligibility.IsPrimeExclusive",
    "Offers.Listings.ProgramEligibility.IsPrimePantry",
    "Offers.Listings.Promotions",
    "Offers.Listings.SavingBasis",
    "Offers.Summaries.HighestPrice",
    "Offers.Summaries.LowestPrice",
    "Offers.Summaries.OfferCount",
    # Images resources
    "Images.Primary.Small",
    "Images.Primary.Medium",
    "Images.Primary.Large",
    "Images.Variants.Small",
    "Images.Variants.Medium",
    "Images.Variants.Large",
    # Reviews resources
    "CustomerReviews.Count",
    "CustomerReviews.StarRating",
    # Browse Node resources
    "BrowseNodeInfo.BrowseNodes",
    "BrowseNodeInfo.BrowseNodes.Ancestor",
    "BrowseNodeInfo.BrowseNodes.Children",
    "BrowseNodeInfo.WebsiteSalesRank",
    # Parent ASIN for variations
    "ParentASIN",
]

# Search-specific resources
SEARCH_RESOURCES = [
    "ItemInfo.Title",
    "ItemInfo.ByLineInfo",
    "Offers.Listings.Price",
    "Offers.Summaries.LowestPrice",
    "CustomerReviews.StarRating",
    "CustomerReviews.Count",
    "Images.Primary.Medium",
    "BrowseNodeInfo.BrowseNodes",
]

# Browse node resources
BROWSE_NODE_RESOURCES = [
    "BrowseNodeInfo.BrowseNodes",
    "BrowseNodeInfo.BrowseNodes.Ancestor",
    "BrowseNodeInfo.BrowseNodes.Children",
    "BrowseNodeInfo.WebsiteSalesRank",
]


def get_resources_for_context(context: str) -> List[str]:
    """Get appropriate resources based on use case.

    Args:
    ----
        context: Use case context
                - "search_preview": Basic search results
                - "product_details": Detailed product view
                - "data_enrichment": Complete data collection
                - "browse_nodes": Category information
                - "price_tracking": Price monitoring

    Returns:
    -------
        List of PA-API resource strings
    """
    context_mapping = {
        "search_preview": MINIMAL_RESOURCES,
        "search_results": SEARCH_RESOURCES,
        "product_details": DETAILED_RESOURCES,
        "data_enrichment": FULL_RESOURCES,
        "browse_nodes": BROWSE_NODE_RESOURCES,
        "price_tracking": [
            "ItemInfo.Title",
            "Offers.Listings.Price",
            "Offers.Listings.Availability.Type",
            "Offers.Summaries.LowestPrice",
        ],
    }

    return context_mapping.get(context, MINIMAL_RESOURCES)


# Indian marketplace top-level browse nodes
INDIAN_TOP_LEVEL_NODES = {
    1951048031: "Electronics",
    1951049031: "Computers & Accessories",
    1350380031: "Clothing & Accessories",
    1350384031: "Home & Kitchen",
    1350387031: "Sports, Fitness & Outdoors",
    1350388031: "Health & Personal Care",
    1355016031: "Books",
    1350389031: "Toys & Games",
    1350390031: "Baby",
    1350391031: "Beauty",
    1951050031: "Car & Motorbike",
    1350392031: "Grocery & Gourmet Foods",
    1350393031: "Tools & Hardware",
    1350394031: "Garden & Outdoors",
    1350395031: "Pet Supplies",
    1350396031: "Office Products",
    1350397031: "Musical Instruments",
    1350398031: "Watches",
    1350399031: "Jewelry",
    1350400031: "Shoes & Handbags",
}
