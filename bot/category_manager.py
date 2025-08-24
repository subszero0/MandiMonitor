"""Category Management System for Amazon browse node hierarchy."""

import asyncio
from logging import getLogger
from typing import Dict, List, Optional

from sqlmodel import Session, select

from .api_rate_limiter import acquire_api_permission
from .cache_service import engine
from .enhanced_models import BrowseNode, ProductBrowseNode
from .errors import QuotaExceededError
from .paapi_factory import get_browse_nodes_hierarchy

log = getLogger(__name__)


class CategoryManager:
    """Manage Amazon browse node hierarchy for India marketplace."""

    # Indian marketplace top-level browse nodes
    INDIAN_TOP_LEVEL_NODES = {
        1951048031: "Electronics",
        1951049031: "Computers & Accessories",
        1350380031: "Clothing & Accessories",
        1350384031: "Home & Kitchen",
        1350387031: "Books",
        1951046031: "Sports, Fitness & Outdoors",
        1350385031: "Health & Personal Care",
        1951051031: "Watches",
        1350383031: "Toys & Games",
        1350381031: "Beauty",
        1951052031: "Baby",
        1951047031: "Automotive",
        1350382031: "Garden & Outdoors",
        1350386031: "Luggage & Bags",
        1951050031: "Musical Instruments",
        1951053031: "Office Products",
        1351068031: "Pet Supplies",
        1951054031: "Video Games",
        1351069031: "Industrial & Scientific",
        1951055031: "Software",
    }

    def __init__(self):
        """Initialize CategoryManager."""
        self._category_cache = {}

    async def build_category_tree(self) -> Dict:
        """Build complete category hierarchy for India marketplace.
        
        Returns
        -------
            Dict with complete category tree structure
        """
        category_tree = {}
        
        log.info("Building category tree for %d top-level nodes", len(self.INDIAN_TOP_LEVEL_NODES))
        
        for node_id, name in self.INDIAN_TOP_LEVEL_NODES.items():
            try:
                log.info("Fetching hierarchy for node %d: %s", node_id, name)
                
                # Check if we have cached data first
                with Session(engine) as session:
                    cached_node = session.get(BrowseNode, node_id)
                    
                if cached_node:
                    log.info("Using cached data for node %d", node_id)
                    node_data = {
                        "id": cached_node.id,
                        "name": cached_node.name,
                        "parent_id": cached_node.parent_id,
                        "sales_rank": cached_node.sales_rank,
                        "children": [],
                        "ancestors": []
                    }
                else:
                    # Fetch from PA-API with rate limiting
                    try:
                        node_data = await get_browse_nodes_hierarchy(node_id, priority="low")
                        
                        # Store in database
                        await self._store_browse_node(node_data)
                        log.info("Stored browse node data for %d", node_id)
                        
                    except QuotaExceededError:
                        log.warning("Quota exceeded while fetching node %d, using fallback", node_id)
                        node_data = {
                            "id": node_id,
                            "name": name,
                            "children": [],
                            "ancestors": []
                        }
                    except Exception as e:
                        log.error("Error fetching node %d: %s", node_id, e)
                        node_data = {
                            "id": node_id,
                            "name": name,
                            "children": [],
                            "ancestors": []
                        }
                
                category_tree[node_id] = node_data
                
                # Small delay to respect rate limits
                await asyncio.sleep(1.1)
                
            except Exception as e:
                log.error("Error processing node %d (%s): %s", node_id, name, e)
                # Continue with next node
                continue
        
        log.info("Built category tree with %d nodes", len(category_tree))
        return category_tree

    async def get_category_suggestions(self, query: str) -> List[Dict]:
        """Suggest relevant categories for search query.
        
        Args
        ----
            query: User search query
            
        Returns
        -------
            List of suggested category dictionaries
        """
        log.info("Getting category suggestions for query: %s", query)
        
        # Use both keyword matching and ML prediction
        keyword_matches = await self._keyword_category_matching(query)
        
        # Combine and rank suggestions
        suggestions = self._rank_category_suggestions(keyword_matches)
        
        log.info("Generated %d category suggestions for '%s'", len(suggestions), query)
        return suggestions[:5]  # Top 5 suggestions

    async def get_popular_products_in_category(
        self, 
        browse_node_id: int,
        time_period: str = "week"
    ) -> List[Dict]:
        """Get trending products in category.
        
        Args
        ----
            browse_node_id: Category browse node ID
            time_period: Time period for trends ("week", "month")
            
        Returns
        -------
            List of popular products in category
        """
        log.info("Getting popular products for category %d", browse_node_id)
        
        # For now, return empty list - this would require tracking product popularity
        # In a full implementation, this would query database for trending products
        return []

    async def get_price_ranges_for_category(self, browse_node_id: int) -> Dict:
        """Get typical price ranges in category.
        
        Args
        ----
            browse_node_id: Category browse node ID
            
        Returns
        -------
            Dict with price range statistics
        """
        log.info("Getting price ranges for category %d", browse_node_id)
        
        # For now, return default ranges - this would require historical price data
        return {
            "min_price": 100,
            "max_price": 100000,
            "average_price": 5000,
            "median_price": 3000,
            "price_buckets": [
                {"range": "Under ₹1k", "min": 0, "max": 1000, "count": 0},
                {"range": "₹1k-5k", "min": 1000, "max": 5000, "count": 0},
                {"range": "₹5k-25k", "min": 5000, "max": 25000, "count": 0},
                {"range": "₹25k+", "min": 25000, "max": None, "count": 0}
            ]
        }

    async def _keyword_category_matching(self, query: str) -> List[Dict]:
        """Basic keyword-based category matching.
        
        Args
        ----
            query: Search query
            
        Returns
        -------
            List of category matches with scores
        """
        query_lower = query.lower()
        matches = []
        
        # Define keyword mappings for Indian market
        category_keywords = {
            1951048031: ["mobile", "phone", "smartphone", "electronics", "gadget", "device"],
            1951049031: ["laptop", "computer", "pc", "keyboard", "mouse", "monitor", "webcam"],
            1350380031: ["shirt", "dress", "clothing", "apparel", "fashion", "wear", "clothes"],
            1350384031: ["kitchen", "home", "cookware", "appliance", "furniture", "decor"],
            1350387031: ["book", "novel", "magazine", "reading", "literature", "textbook"],
            1951046031: ["sports", "fitness", "gym", "exercise", "outdoor", "cycling", "running"],
            1350385031: ["health", "personal care", "skincare", "beauty", "wellness", "hygiene"],
            1951051031: ["watch", "smartwatch", "timepiece", "clock", "wearable"],
            1350383031: ["toy", "game", "kids", "children", "play", "puzzle", "action figure"],
            1350381031: ["makeup", "cosmetics", "beauty", "skincare", "fragrance", "perfume"],
            1951052031: ["baby", "infant", "toddler", "diaper", "feeding", "stroller"],
            1951047031: ["car", "automotive", "vehicle", "bike", "motorcycle", "accessories"],
            1350382031: ["garden", "outdoor", "plant", "gardening", "lawn", "patio"],
            1350386031: ["luggage", "bag", "backpack", "suitcase", "travel", "handbag"],
            1951050031: ["music", "instrument", "guitar", "keyboard", "piano", "drums"],
            1951053031: ["office", "stationery", "desk", "chair", "supplies", "printer"],
            1351068031: ["pet", "dog", "cat", "animal", "food", "toy", "supplies"],
            1951054031: ["video game", "gaming", "console", "controller", "playstation", "xbox"],
            1351069031: ["industrial", "scientific", "professional", "tools", "equipment"],
            1951055031: ["software", "program", "application", "antivirus", "operating system"]
        }
        
        for node_id, keywords in category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in query_lower)
            if score > 0:
                category_name = self.INDIAN_TOP_LEVEL_NODES.get(node_id, f"Category {node_id}")
                matches.append({
                    "node_id": node_id,
                    "name": category_name,
                    "score": score,
                    "matched_keywords": [kw for kw in keywords if kw in query_lower]
                })
        
        return sorted(matches, key=lambda x: x["score"], reverse=True)

    def _rank_category_suggestions(self, keyword_matches: List[Dict]) -> List[Dict]:
        """Rank category suggestions based on multiple factors.
        
        Args
        ----
            keyword_matches: List of keyword-based matches
            
        Returns
        -------
            Ranked list of category suggestions
        """
        # For now, just return keyword matches sorted by score
        # In a full implementation, this would include ML predictions and user history
        return keyword_matches

    async def _store_browse_node(self, node_data: Dict) -> None:
        """Store browse node data in database.
        
        Args
        ----
            node_data: Browse node data from PA-API
        """
        try:
            with Session(engine) as session:
                # Store main node
                browse_node = BrowseNode(
                    id=node_data["id"],
                    name=node_data["name"],
                    parent_id=None,  # Top-level nodes have no parent
                    sales_rank=node_data.get("sales_rank")
                )
                session.merge(browse_node)
                
                # Store children if present
                for child in node_data.get("children", []):
                    child_node = BrowseNode(
                        id=child["id"],
                        name=child["name"],
                        parent_id=node_data["id"],
                        sales_rank=child.get("sales_rank")
                    )
                    session.merge(child_node)
                
                session.commit()
                
        except Exception as e:
            log.error("Error storing browse node %d: %s", node_data["id"], e)

    async def get_category_by_id(self, browse_node_id: int) -> Optional[Dict]:
        """Get category information by browse node ID.
        
        Args
        ----
            browse_node_id: Browse node ID
            
        Returns
        -------
            Category information dict or None
        """
        try:
            with Session(engine) as session:
                node = session.get(BrowseNode, browse_node_id)
                if node:
                    return {
                        "id": node.id,
                        "name": node.name,
                        "parent_id": node.parent_id,
                        "sales_rank": node.sales_rank
                    }
                return None
        except Exception as e:
            log.error("Error getting category %d: %s", browse_node_id, e)
            return None

    async def get_subcategories(self, parent_id: int) -> List[Dict]:
        """Get subcategories for a parent category.
        
        Args
        ----
            parent_id: Parent browse node ID
            
        Returns
        -------
            List of subcategory dictionaries
        """
        try:
            with Session(engine) as session:
                statement = select(BrowseNode).where(BrowseNode.parent_id == parent_id)
                subcategories = session.exec(statement).all()
                
                return [
                    {
                        "id": node.id,
                        "name": node.name,
                        "parent_id": node.parent_id,
                        "sales_rank": node.sales_rank
                    }
                    for node in subcategories
                ]
        except Exception as e:
            log.error("Error getting subcategories for %d: %s", parent_id, e)
            return []
