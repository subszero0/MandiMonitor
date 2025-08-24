"""Enhanced PA-API resource management with proper enum usage.

This module provides centralized resource management for both legacy and official PA-API SDKs,
with proper enum usage for the official SDK and string fallbacks for the legacy SDK.
"""

from typing import List, Union
from logging import getLogger

# Import official SDK enums (with fallback for legacy compatibility)
try:
    from paapi5_python_sdk.models.get_items_resource import GetItemsResource
    from paapi5_python_sdk.models.search_items_resource import SearchItemsResource
    from paapi5_python_sdk.models.get_browse_nodes_resource import GetBrowseNodesResource
    OFFICIAL_SDK_AVAILABLE = True
except ImportError:
    OFFICIAL_SDK_AVAILABLE = False
    GetItemsResource = None
    SearchItemsResource = None
    GetBrowseNodesResource = None

from .config import settings

log = getLogger(__name__)


class ResourceManager:
    """Centralized resource management for PA-API requests."""
    
    def __init__(self):
        """Initialize the resource manager."""
        self.use_official_sdk = settings.USE_NEW_PAAPI_SDK and OFFICIAL_SDK_AVAILABLE
        
        # Cache for resource lookups
        self._resource_cache = {}
        
        # Define resource sets for different use cases
        self._define_resource_sets()
    
    def _define_resource_sets(self):
        """Define resource sets for different contexts."""
        if self.use_official_sdk and OFFICIAL_SDK_AVAILABLE:
            self._define_official_resources()
        else:
            self._define_legacy_resources()
    
    def _define_official_resources(self):
        """Define resources using official SDK enums."""
        # Minimal resources for basic product information
        self.minimal_get_items_resources = [
            GetItemsResource.ITEMINFO_TITLE,
            GetItemsResource.OFFERSV2_LISTINGS_PRICE,
            GetItemsResource.IMAGES_PRIMARY_LARGE,
        ]
        
        self.minimal_search_resources = [
            SearchItemsResource.ITEMINFO_TITLE,
            SearchItemsResource.OFFERS_LISTINGS_PRICE,
            SearchItemsResource.IMAGES_PRIMARY_MEDIUM,
        ]
        
        # Detailed resources for comprehensive product information
        self.detailed_get_items_resources = [
            GetItemsResource.ITEMINFO_TITLE,
            GetItemsResource.ITEMINFO_BYLINEINFO,
            GetItemsResource.ITEMINFO_FEATURES,
            GetItemsResource.ITEMINFO_PRODUCTINFO,
            GetItemsResource.OFFERSV2_LISTINGS_PRICE,
            GetItemsResource.OFFERSV2_LISTINGS_AVAILABILITY,
            GetItemsResource.OFFERSV2_LISTINGS_CONDITION,
            GetItemsResource.OFFERSV2_LISTINGS_MERCHANTINFO,
            GetItemsResource.IMAGES_PRIMARY_LARGE,
            GetItemsResource.IMAGES_PRIMARY_MEDIUM,
            GetItemsResource.IMAGES_PRIMARY_SMALL,
            GetItemsResource.CUSTOMERREVIEWS_COUNT,
            GetItemsResource.CUSTOMERREVIEWS_STARRATING,
        ]
        
        self.detailed_search_resources = [
            SearchItemsResource.ITEMINFO_TITLE,
            SearchItemsResource.ITEMINFO_BYLINEINFO,
            SearchItemsResource.OFFERS_LISTINGS_PRICE,
            SearchItemsResource.OFFERS_LISTINGS_AVAILABILITY_TYPE,
            SearchItemsResource.IMAGES_PRIMARY_MEDIUM,
            SearchItemsResource.CUSTOMERREVIEWS_COUNT,
            SearchItemsResource.CUSTOMERREVIEWS_STARRATING,
        ]
        
        # Full resources for complete data enrichment
        self.full_get_items_resources = [
            GetItemsResource.ITEMINFO_TITLE,
            GetItemsResource.ITEMINFO_BYLINEINFO,
            GetItemsResource.ITEMINFO_FEATURES,
            GetItemsResource.ITEMINFO_MANUFACTUREINFO,
            GetItemsResource.ITEMINFO_PRODUCTINFO,
            GetItemsResource.ITEMINFO_TECHNICALINFO,
            GetItemsResource.ITEMINFO_TRADEININFO,
            GetItemsResource.ITEMINFO_EXTERNALIDS,
            GetItemsResource.ITEMINFO_CLASSIFICATIONS,
            GetItemsResource.ITEMINFO_CONTENTINFO,
            GetItemsResource.OFFERSV2_LISTINGS_PRICE,
            GetItemsResource.OFFERSV2_LISTINGS_AVAILABILITY,
            GetItemsResource.OFFERSV2_LISTINGS_CONDITION,
            GetItemsResource.OFFERSV2_LISTINGS_MERCHANTINFO,
            GetItemsResource.IMAGES_PRIMARY_LARGE,
            GetItemsResource.IMAGES_PRIMARY_MEDIUM,
            GetItemsResource.IMAGES_PRIMARY_SMALL,
            GetItemsResource.IMAGES_VARIANTS_LARGE,
            GetItemsResource.CUSTOMERREVIEWS_COUNT,
            GetItemsResource.CUSTOMERREVIEWS_STARRATING,
            GetItemsResource.BROWSENODEINFO_BROWSENODES,
        ]
        
        # Browse nodes resources
        self.browse_nodes_resources = [
            GetBrowseNodesResource.ANCESTOR,
            GetBrowseNodesResource.CHILDREN,
        ]
    
    def _define_legacy_resources(self):
        """Define resources using legacy string format."""
        # Import the legacy resources
        from .paapi_resources import (
            MINIMAL_RESOURCES,
            DETAILED_RESOURCES, 
            FULL_RESOURCES,
            get_resources_for_context
        )
        
        # Map to legacy string resources
        self.minimal_get_items_resources = MINIMAL_RESOURCES
        self.minimal_search_resources = MINIMAL_RESOURCES
        self.detailed_get_items_resources = DETAILED_RESOURCES
        self.detailed_search_resources = DETAILED_RESOURCES
        self.full_get_items_resources = FULL_RESOURCES
        
        # Browse nodes resources for legacy
        self.browse_nodes_resources = get_resources_for_context("browse_nodes")
    
    def get_resources_for_context(
        self, 
        context: str, 
        operation: str = "get_items"
    ) -> List[Union[str, object]]:
        """Get appropriate resources for a given context and operation.
        
        Args:
        ----
            context: The use case context ('minimal', 'detailed', 'full', 'browse_nodes')
            operation: The PA-API operation ('get_items', 'search_items', 'browse_nodes')
            
        Returns:
        -------
            List of resources (enums for official SDK, strings for legacy)
        """
        # Check cache first for performance
        cache_key = f"{context}:{operation}"
        if cache_key in self._resource_cache:
            return self._resource_cache[cache_key]
        
        if context == "browse_nodes":
            resources = self.browse_nodes_resources
        else:
            # Map context and operation to appropriate resource set
            resource_map = {
                ("minimal", "get_items"): self.minimal_get_items_resources,
                ("minimal", "search_items"): self.minimal_search_resources,
                ("detailed", "get_items"): self.detailed_get_items_resources,
                ("detailed", "search_items"): self.detailed_search_resources,
                ("full", "get_items"): self.full_get_items_resources,
                ("full", "search_items"): self.detailed_search_resources,  # Use detailed for search
                ("product_details", "get_items"): self.detailed_get_items_resources,
                ("product_details", "search_items"): self.detailed_search_resources,
            }
            
            key = (context, operation)
            resources = resource_map.get(key)
            
            if resources is None:
                log.warning("Unknown context/operation combination: %s/%s, using detailed", context, operation)
                if operation == "search_items":
                    resources = self.detailed_search_resources
                else:
                    resources = self.detailed_get_items_resources
        
        # Cache the result for future lookups
        self._resource_cache[cache_key] = resources
        return resources
    
    def get_minimal_resources(self, operation: str = "get_items") -> List[Union[str, object]]:
        """Get minimal resources for fast requests."""
        return self.get_resources_for_context("minimal", operation)
    
    def get_detailed_resources(self, operation: str = "get_items") -> List[Union[str, object]]:
        """Get detailed resources for comprehensive information."""
        return self.get_resources_for_context("detailed", operation)
    
    def get_full_resources(self, operation: str = "get_items") -> List[Union[str, object]]:
        """Get full resources for complete data enrichment."""
        return self.get_resources_for_context("full", operation)


# Global resource manager instance
_resource_manager = None


def get_resource_manager() -> ResourceManager:
    """Get the global resource manager instance."""
    global _resource_manager
    if _resource_manager is None:
        _resource_manager = ResourceManager()
    return _resource_manager


def get_resources_for_context(context: str, operation: str = "get_items") -> List[Union[str, object]]:
    """Convenience function to get resources for a context.
    
    This maintains backward compatibility with the existing paapi_resources module.
    """
    manager = get_resource_manager()
    return manager.get_resources_for_context(context, operation)


def refresh_resource_manager():
    """Refresh the resource manager (useful when feature flag changes)."""
    global _resource_manager
    _resource_manager = None
    return get_resource_manager()
