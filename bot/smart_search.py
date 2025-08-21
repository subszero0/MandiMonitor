"""Smart Search Engine for AI-powered product search."""

import re
from logging import getLogger
from typing import Dict, List, Optional

from sqlmodel import Session, select

from .cache_service import engine
from .category_manager import CategoryManager
from .enhanced_models import SearchQuery, Product
from .models import Watch
from .paapi_enhanced import search_items_advanced

log = getLogger(__name__)


class SmartSearchEngine:
    """AI-powered product search with intelligent filtering and ranking."""

    def __init__(self):
        """Initialize SmartSearchEngine."""
        self.category_manager = CategoryManager()

    async def intelligent_search(
        self,
        query: str,
        user_context: Optional[Dict] = None
    ) -> Dict:
        """Multi-step intelligent search with context awareness.
        
        Args
        ----
            query: User search query
            user_context: User context including preferences and history
            
        Returns
        -------
            Dict with search results and metadata
        """
        log.info("Starting intelligent search for: %s", query)
        
        # Step 1: Query analysis and intent detection
        intent_analysis = self._analyze_search_intent(query)
        log.info("Search intent analysis: %s", intent_analysis)
        
        # Step 2: Category prediction
        category_suggestions = await self.category_manager.get_category_suggestions(query)
        log.info("Category suggestions: %s", [cat['name'] for cat in category_suggestions[:3]])
        
        # Step 3: Multi-source search (PA-API + historical data)
        search_params = self._build_search_parameters(query, intent_analysis, category_suggestions)
        
        # Primary search via PA-API
        primary_results = await self._search_with_paapi(search_params)
        
        # Step 4: Result ranking and filtering
        ranked_results = await self._rank_and_filter_results(
            primary_results, 
            intent_analysis, 
            user_context
        )
        
        # Step 5: Personalization based on user history
        if user_context and user_context.get("user_id"):
            personalized_results = await self._apply_personalization(
                ranked_results, 
                user_context["user_id"]
            )
        else:
            personalized_results = ranked_results
        
        # Store search query for analytics
        if user_context and user_context.get("user_id"):
            await self._store_search_query(query, user_context["user_id"], len(personalized_results))
        
        return {
            "query": query,
            "intent": intent_analysis,
            "categories": category_suggestions[:3],
            "results": personalized_results,
            "total_results": len(personalized_results),
            "search_metadata": {
                "primary_source": "paapi",
                "personalized": bool(user_context and user_context.get("user_id")),
                "categories_considered": len(category_suggestions)
            }
        }

    async def search_with_filters(
        self,
        base_query: str,
        filters: Dict
    ) -> List[Dict]:
        """Advanced filtering search.
        
        Args
        ----
            base_query: Base search terms
            filters: Advanced filter parameters
            
        Returns
        -------
            Filtered search results
        """
        log.info("Searching with filters: %s", filters)
        
        # Build search parameters with filters
        search_params = {
            "keywords": base_query,
            "item_count": filters.get("limit", 10),
            "priority": "normal"
        }
        
        # Apply filters
        if filters.get("price_range"):
            price_range = filters["price_range"]
            if price_range.get("min"):
                search_params["min_price"] = price_range["min"] * 100  # Convert to paise
            if price_range.get("max"):
                search_params["max_price"] = price_range["max"] * 100
        
        if filters.get("brand"):
            search_params["brand"] = filters["brand"]
        
        if filters.get("category"):
            search_params["browse_node_id"] = filters["category"]
        
        if filters.get("min_rating"):
            search_params["min_reviews_rating"] = filters["min_rating"]
        
        if filters.get("min_discount"):
            search_params["min_savings_percent"] = filters["min_discount"]
        
        if filters.get("prime_only"):
            search_params["merchant"] = "Amazon"
        
        if filters.get("condition"):
            search_params["condition"] = filters["condition"]
        
        # Perform search
        results = await search_items_advanced(**search_params)
        
        # Additional filtering that PA-API doesn't support directly
        filtered_results = self._apply_additional_filters(results, filters)
        
        log.info("Search with filters returned %d results", len(filtered_results))
        return filtered_results

    async def get_search_suggestions(
        self,
        partial_query: str,
        user_id: Optional[int] = None
    ) -> List[str]:
        """Real-time search suggestions.
        
        Args
        ----
            partial_query: Partial search query
            user_id: User ID for personalized suggestions
            
        Returns
        -------
            List of search suggestions
        """
        log.info("Getting search suggestions for: %s", partial_query)
        
        suggestions = []
        
        # Get category-based suggestions
        if len(partial_query) >= 3:
            category_suggestions = await self.category_manager.get_category_suggestions(partial_query)
            for category in category_suggestions[:3]:
                suggestions.append(f"{partial_query} in {category['name']}")
        
        # Get user history-based suggestions
        if user_id:
            history_suggestions = await self._get_user_history_suggestions(user_id, partial_query)
            suggestions.extend(history_suggestions)
        
        # Get common search completions
        common_suggestions = self._get_common_completions(partial_query)
        suggestions.extend(common_suggestions)
        
        # Remove duplicates and limit
        unique_suggestions = list(dict.fromkeys(suggestions))[:8]
        
        log.info("Generated %d search suggestions", len(unique_suggestions))
        return unique_suggestions

    async def find_similar_products(
        self,
        asin: str,
        similarity_factors: Optional[List[str]] = None
    ) -> List[Dict]:
        """Find similar products based on various factors.
        
        Args
        ----
            asin: Product ASIN to find similar products for
            similarity_factors: Factors to consider for similarity
            
        Returns
        -------
            List of similar products
        """
        log.info("Finding similar products for ASIN: %s", asin)
        
        if not similarity_factors:
            similarity_factors = ["brand", "category", "price_range", "features"]
        
        # Get product details first
        try:
            with Session(engine) as session:
                product = session.get(Product, asin)
                if not product:
                    log.warning("Product not found for ASIN: %s", asin)
                    return []
        except Exception as e:
            log.error("Error getting product details for %s: %s", asin, e)
            return []
        
        similar_products = []
        
        # Find by brand
        if "brand" in similarity_factors and product.brand:
            brand_products = await self._find_by_brand(product.brand, exclude_asin=asin)
            similar_products.extend(brand_products)
        
        # Find by category (would need browse node integration)
        if "category" in similarity_factors:
            category_products = await self._find_by_category(asin)
            similar_products.extend(category_products)
        
        # Find by price range
        if "price_range" in similarity_factors:
            price_products = await self._find_by_price_range(asin)
            similar_products.extend(price_products)
        
        # Remove duplicates and limit
        unique_products = []
        seen_asins = {asin}  # Exclude original product
        
        for product_data in similar_products:
            product_asin = product_data.get("asin")
            if product_asin and product_asin not in seen_asins:
                unique_products.append(product_data)
                seen_asins.add(product_asin)
                if len(unique_products) >= 10:  # Limit to 10 similar products
                    break
        
        log.info("Found %d similar products for %s", len(unique_products), asin)
        return unique_products

    def _analyze_search_intent(self, query: str) -> Dict:
        """Analyze search query to understand user intent.
        
        Args
        ----
            query: Search query
            
        Returns
        -------
            Intent analysis results
        """
        query_lower = query.lower()
        intent = {
            "type": "general",
            "confidence": 0.5,
            "modifiers": [],
            "price_sensitive": False,
            "brand_specific": False,
            "feature_focused": False
        }
        
        # Detect specific product intent
        if any(word in query_lower for word in ["asin", "model", "exact", "specific"]):
            intent["type"] = "specific_product"
            intent["confidence"] = 0.9
        
        # Detect comparison intent
        elif any(word in query_lower for word in ["vs", "versus", "compare", "comparison", "better"]):
            intent["type"] = "comparison"
            intent["confidence"] = 0.8
        
        # Detect deal hunting intent
        elif any(word in query_lower for word in ["cheap", "discount", "deal", "offer", "sale", "best price"]):
            intent["type"] = "deal_hunting"
            intent["confidence"] = 0.8
            intent["price_sensitive"] = True
        
        # Detect feature-focused intent
        elif any(word in query_lower for word in ["with", "features", "specs", "specifications"]):
            intent["type"] = "feature_search"
            intent["confidence"] = 0.7
            intent["feature_focused"] = True
        
        # Detect brand-specific intent
        brands = ["apple", "samsung", "lg", "sony", "oneplus", "xiaomi", "mi", "realme", "oppo", "vivo"]
        if any(brand in query_lower for brand in brands):
            intent["brand_specific"] = True
            intent["confidence"] = min(intent["confidence"] + 0.2, 1.0)
        
        # Detect price modifiers
        price_modifiers = ["under", "below", "less than", "maximum", "budget", "affordable"]
        if any(modifier in query_lower for modifier in price_modifiers):
            intent["price_sensitive"] = True
            intent["modifiers"].append("price_constraint")
        
        # Detect quality modifiers
        quality_modifiers = ["best", "top", "premium", "high quality", "rated"]
        if any(modifier in query_lower for modifier in quality_modifiers):
            intent["modifiers"].append("quality_focused")
        
        return intent

    def _build_search_parameters(
        self, 
        query: str, 
        intent_analysis: Dict, 
        category_suggestions: List[Dict]
    ) -> Dict:
        """Build search parameters based on intent and categories.
        
        Args
        ----
            query: Original search query
            intent_analysis: Intent analysis results
            category_suggestions: Category suggestions
            
        Returns
        -------
            Search parameters for PA-API
        """
        params = {
            "keywords": query,
            "item_count": 10,
            "priority": "normal"
        }
        
        # Adjust based on intent
        if intent_analysis["type"] == "deal_hunting":
            params["min_savings_percent"] = 10  # At least 10% discount
            params["sort_by"] = "Price:LowToHigh"
        elif intent_analysis["type"] == "feature_search":
            params["item_count"] = 15  # More results for feature comparison
        elif intent_analysis["type"] == "comparison":
            params["item_count"] = 20  # Even more for comparison
        
        # Use top category if available
        if category_suggestions:
            top_category = category_suggestions[0]
            params["browse_node_id"] = top_category["node_id"]
        
        return params

    async def _search_with_paapi(self, search_params: Dict) -> List[Dict]:
        """Perform search using PA-API.
        
        Args
        ----
            search_params: Search parameters
            
        Returns
        -------
            Search results from PA-API
        """
        try:
            results = await search_items_advanced(**search_params)
            log.info("PA-API search returned %d results", len(results))
            return results
        except Exception as e:
            log.error("PA-API search failed: %s", e)
            return []

    async def _rank_and_filter_results(
        self, 
        results: List[Dict], 
        intent_analysis: Dict, 
        user_context: Optional[Dict]
    ) -> List[Dict]:
        """Rank and filter search results based on intent and context.
        
        Args
        ----
            results: Raw search results
            intent_analysis: Intent analysis
            user_context: User context
            
        Returns
        -------
            Ranked and filtered results
        """
        if not results:
            return results
        
        # Apply scoring based on intent
        scored_results = []
        for result in results:
            score = self._calculate_result_score(result, intent_analysis, user_context)
            scored_results.append({
                **result,
                "_search_score": score
            })
        
        # Sort by score (highest first)
        ranked_results = sorted(scored_results, key=lambda x: x["_search_score"], reverse=True)
        
        log.info("Ranked %d results", len(ranked_results))
        return ranked_results

    def _calculate_result_score(
        self, 
        result: Dict, 
        intent_analysis: Dict, 
        user_context: Optional[Dict]
    ) -> float:
        """Calculate relevance score for a search result.
        
        Args
        ----
            result: Individual search result
            intent_analysis: Intent analysis
            user_context: User context
            
        Returns
        -------
            Relevance score (0-1)
        """
        base_score = 0.5
        
        # Price-based scoring for deal hunters
        if intent_analysis.get("price_sensitive"):
            offers = result.get("offers", {})
            savings_percent = offers.get("savings_percentage", 0)
            if savings_percent > 0:
                base_score += min(savings_percent / 100, 0.3)  # Up to 0.3 bonus for discounts
        
        # Review-based scoring
        reviews = result.get("reviews", {})
        rating = reviews.get("average_rating")
        review_count = reviews.get("count", 0)
        
        if rating and rating >= 4.0:
            base_score += 0.1
        if review_count > 100:
            base_score += 0.1
        
        # Brand preference (if available in user context)
        if user_context and user_context.get("preferred_brands"):
            product_brand = result.get("brand", "").lower()
            if product_brand in [b.lower() for b in user_context["preferred_brands"]]:
                base_score += 0.2
        
        # Availability scoring
        offers = result.get("offers", {})
        if offers.get("is_prime_eligible"):
            base_score += 0.05
        if offers.get("availability_type") == "InStock":
            base_score += 0.05
        
        return min(base_score, 1.0)  # Cap at 1.0

    async def _apply_personalization(self, results: List[Dict], user_id: int) -> List[Dict]:
        """Apply personalization based on user history.
        
        Args
        ----
            results: Search results
            user_id: User ID
            
        Returns
        -------
            Personalized results
        """
        # Get user preferences from watch history
        user_preferences = await self._get_user_preferences(user_id)
        
        if not user_preferences:
            return results
        
        # Re-score results based on user preferences
        personalized_results = []
        for result in results:
            personal_score = result.get("_search_score", 0.5)
            
            # Brand preference boost
            if user_preferences.get("preferred_brands"):
                result_brand = result.get("brand", "").lower()
                if result_brand in [b.lower() for b in user_preferences["preferred_brands"]]:
                    personal_score += 0.15
            
            # Category preference boost
            if user_preferences.get("preferred_categories"):
                # This would need browse node integration
                pass
            
            # Price range preference
            if user_preferences.get("price_range"):
                result_price = result.get("offers", {}).get("price", 0)
                if result_price > 0:
                    price_rs = result_price / 100
                    pref_range = user_preferences["price_range"]
                    if pref_range["min"] <= price_rs <= pref_range["max"]:
                        personal_score += 0.1
            
            personalized_results.append({
                **result,
                "_search_score": min(personal_score, 1.0)
            })
        
        # Re-sort by updated scores
        return sorted(personalized_results, key=lambda x: x["_search_score"], reverse=True)

    async def _get_user_preferences(self, user_id: int) -> Optional[Dict]:
        """Get user preferences from watch history.
        
        Args
        ----
            user_id: User ID
            
        Returns
        -------
            User preferences dict
        """
        try:
            with Session(engine) as session:
                # Get user's watch history
                statement = select(Watch).where(Watch.user_id == user_id).limit(50)
                watches = session.exec(statement).all()
                
                if not watches:
                    return None
                
                # Analyze preferences
                brands = []
                price_ranges = []
                
                for watch in watches:
                    if watch.brand:
                        brands.append(watch.brand)
                    if watch.max_price:
                        price_ranges.append(watch.max_price)
                
                preferences = {}
                
                # Most common brands
                if brands:
                    brand_counts = {}
                    for brand in brands:
                        brand_counts[brand] = brand_counts.get(brand, 0) + 1
                    
                    top_brands = sorted(brand_counts.items(), key=lambda x: x[1], reverse=True)
                    preferences["preferred_brands"] = [brand for brand, _ in top_brands[:5]]
                
                # Price range preferences
                if price_ranges:
                    avg_price = sum(price_ranges) / len(price_ranges)
                    preferences["price_range"] = {
                        "min": int(avg_price * 0.5),
                        "max": int(avg_price * 1.5)
                    }
                
                return preferences
                
        except Exception as e:
            log.error("Error getting user preferences for %d: %s", user_id, e)
            return None

    async def _store_search_query(self, query: str, user_id: int, results_count: int) -> None:
        """Store search query for analytics.
        
        Args
        ----
            query: Search query
            user_id: User ID
            results_count: Number of results returned
        """
        try:
            with Session(engine) as session:
                search_query = SearchQuery(
                    user_id=user_id,
                    query=query,
                    results_count=results_count
                )
                session.add(search_query)
                session.commit()
        except Exception as e:
            log.error("Error storing search query: %s", e)

    async def _get_user_history_suggestions(self, user_id: int, partial_query: str) -> List[str]:
        """Get search suggestions based on user history.
        
        Args
        ----
            user_id: User ID
            partial_query: Partial search query
            
        Returns
        -------
            History-based suggestions
        """
        try:
            with Session(engine) as session:
                statement = select(SearchQuery).where(
                    SearchQuery.user_id == user_id,
                    SearchQuery.query.like(f"%{partial_query}%")
                ).limit(5)
                
                past_queries = session.exec(statement).all()
                return [q.query for q in past_queries if q.query != partial_query]
        except Exception as e:
            log.error("Error getting user history suggestions: %s", e)
            return []

    def _get_common_completions(self, partial_query: str) -> List[str]:
        """Get common search completions.
        
        Args
        ----
            partial_query: Partial search query
            
        Returns
        -------
            Common completions
        """
        common_completions = {
            "phone": ["phone case", "phone cover", "phone charger", "phone holder"],
            "laptop": ["laptop bag", "laptop stand", "laptop cooling pad", "laptop screen"],
            "headphone": ["headphones wireless", "headphones gaming", "headphones noise cancelling"],
            "watch": ["watch men", "watch women", "smartwatch", "watch strap"],
            "speaker": ["speaker bluetooth", "speaker portable", "speaker home"],
            "camera": ["camera lens", "camera tripod", "camera bag", "camera flash"],
        }
        
        suggestions = []
        for base_word, completions in common_completions.items():
            if base_word in partial_query.lower():
                suggestions.extend([comp for comp in completions if partial_query.lower() in comp])
        
        return suggestions[:5]

    def _apply_additional_filters(self, results: List[Dict], filters: Dict) -> List[Dict]:
        """Apply additional filters not supported by PA-API directly.
        
        Args
        ----
            results: Search results
            filters: Additional filters
            
        Returns
        -------
            Filtered results
        """
        filtered = results
        
        # Filter by availability status
        if filters.get("availability_filter"):
            availability = filters["availability_filter"]
            if availability == "in_stock":
                filtered = [r for r in filtered 
                          if r.get("offers", {}).get("availability_type") == "InStock"]
            elif availability == "prime_eligible":
                filtered = [r for r in filtered 
                          if r.get("offers", {}).get("is_prime_eligible")]
        
        # Filter by review count
        if filters.get("min_reviews"):
            min_reviews = filters["min_reviews"]
            filtered = [r for r in filtered 
                      if r.get("reviews", {}).get("count", 0) >= min_reviews]
        
        return filtered

    async def _find_by_brand(self, brand: str, exclude_asin: str) -> List[Dict]:
        """Find products by brand."""
        try:
            results = await search_items_advanced(
                brand=brand,
                item_count=5,
                priority="low"
            )
            return [r for r in results if r.get("asin") != exclude_asin]
        except Exception as e:
            log.error("Error finding products by brand %s: %s", brand, e)
            return []

    async def _find_by_category(self, asin: str) -> List[Dict]:
        """Find products in same category."""
        # This would need browse node integration with the product
        # For now, return empty list
        return []

    async def _find_by_price_range(self, asin: str) -> List[Dict]:
        """Find products in similar price range."""
        try:
            with Session(engine) as session:
                product = session.get(Product, asin)
                if not product:
                    return []
                
                # Get recent price from offers (would need integration with ProductOffers model)
                # For now, return empty list
                return []
        except Exception as e:
            log.error("Error finding products by price range for %s: %s", asin, e)
            return []
