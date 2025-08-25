"""Enhanced PA-API functions - Re-exports from paapi_factory for compatibility."""

# Re-export existing functions from paapi_factory and paapi_resource_manager
from .paapi_factory import (
    get_item_detailed,
    search_items_advanced,
)
from .paapi_resource_manager import get_resources_for_context

# These functions might be planned for future implementation
# For now, create stub implementations to prevent import errors

async def batch_get_items(*args, **kwargs):
    """Stub implementation - planned for future."""
    raise NotImplementedError("batch_get_items not yet implemented")

async def get_browse_nodes_hierarchy(*args, **kwargs):
    """Stub implementation - planned for future."""
    raise NotImplementedError("get_browse_nodes_hierarchy not yet implemented")

async def get_product_variations(*args, **kwargs):
    """Stub implementation - planned for future."""
    raise NotImplementedError("get_product_variations not yet implemented")

# Re-export for compatibility
__all__ = [
    "get_item_detailed",
    "search_items_advanced", 
    "get_resources_for_context",
    "batch_get_items",
    "get_browse_nodes_hierarchy",
    "get_product_variations",
]
