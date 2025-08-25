"""Smart Watch Builder for intelligent watch creation with AI-powered suggestions."""

import statistics
from logging import getLogger
from typing import Dict, List, Optional

from sqlmodel import Session, select

from .cache_service import engine
from .category_manager import CategoryManager
from .enhanced_models import Product, ProductOffers
from .models import Watch, Price
from .paapi_factory import search_items_advanced, get_item_detailed
from .smart_search import SmartSearchEngine
from .watch_parser import parse_watch, validate_watch_data

log = getLogger(__name__)


class SmartWatchBuilder:
    """Build intelligent price watches with AI-powered suggestions."""

    def __init__(self):
        """Initialize SmartWatchBuilder."""
        self.search_engine = SmartSearchEngine()
        self.category_manager = CategoryManager()

    async def create_smart_watch(
        self,
        user_input: str,
        user_id: int
    ) -> Dict:
        """Enhanced watch creation with intelligent suggestions.
        
        Args
        ----
            user_input: User's watch creation input
            user_id: User ID for personalization
            
        Returns
        -------
            Dict with enhanced watch data and suggestions
        """
        log.info("Creating smart watch for user %d: %s", user_id, user_input)
        
        # Step 1: Use existing parser as base
        basic_watch_data = parse_watch(user_input)
        log.info("Basic watch data: %s", basic_watch_data)
        
        # Step 2: Analyze intent and enhance with intelligence
        intent_analysis = self._analyze_watch_intent(user_input, basic_watch_data)
        log.info("Watch intent analysis: %s", intent_analysis)
        
        # Step 3: Enhance with intelligent suggestions
        enhanced_data = await self._enhance_watch_data(basic_watch_data, intent_analysis, user_id)
        
        # Step 4: Use existing validation
        validation_result = validate_watch_data(enhanced_data)
        
        # Step 5: Generate suggestions and alternatives
        suggestions = await self._generate_suggestions(enhanced_data, intent_analysis)
        alternatives = await self._find_alternatives(enhanced_data, intent_analysis)
        
        return {
            **enhanced_data,
            "intent_analysis": intent_analysis,
            "suggestions": suggestions,
            "alternatives": alternatives,
            "validation": validation_result,
            "smart_enhancements": True
        }

    async def suggest_watch_parameters(
        self,
        products: List[Dict],
        user_preferences: Optional[Dict] = None
    ) -> Dict:
        """Suggest optimal watch parameters based on product data and user preferences.
        
        Args
        ----
            products: List of relevant products
            user_preferences: User preferences from history
            
        Returns
        -------
            Dict with suggested parameters and rationale
        """
        log.info("Suggesting watch parameters for %d products", len(products))
        
        if not products:
            return self._get_default_parameters()
        
        # Analyze price patterns
        price_analysis = await self._analyze_price_patterns(products)
        
        # Analyze historical discount patterns  
        discount_analysis = await self._analyze_discount_patterns(products)
        
        # Generate smart suggestions
        suggestions = {
            "max_price_suggestion": price_analysis["suggested_threshold"],
            "min_discount_suggestion": discount_analysis["effective_discount"],
            "monitoring_frequency": self._suggest_monitoring_frequency(products),
            "rationale": {
                "price": f"Based on {len(products)} similar products, avg price ₹{price_analysis['avg_price']:,}",
                "discount": f"Historical data shows {discount_analysis['frequency']}% of products get {discount_analysis['effective_discount']}%+ discounts",
                "frequency": discount_analysis["volatility_reason"]
            },
            "market_insights": {
                "price_volatility": price_analysis["volatility"],
                "discount_frequency": discount_analysis["frequency"],
                "best_purchase_timing": discount_analysis["best_timing"],
                "seasonal_patterns": price_analysis.get("seasonal_patterns", [])
            }
        }
        
        # Apply user preferences if available
        if user_preferences:
            suggestions = self._apply_user_preferences(suggestions, user_preferences)
        
        log.info("Generated parameter suggestions: max_price=₹%d, min_discount=%d%%", 
                suggestions["max_price_suggestion"], suggestions["min_discount_suggestion"])
        
        return suggestions

    async def create_variant_watches(
        self,
        parent_asin: str,
        user_preferences: Dict
    ) -> List[Dict]:
        """Create watches for product variations.
        
        Args
        ----
            parent_asin: Parent product ASIN
            user_preferences: User preferences for filtering variants
            
        Returns
        -------
            List of variant watch suggestions
        """
        log.info("Creating variant watches for parent ASIN: %s", parent_asin)
        
        try:
            # Get product variations from PA-API (this would need get_variations implementation)
            # For now, we'll search for similar products
            parent_product = await get_item_detailed(parent_asin, priority="high")
            
            if not parent_product:
                log.warning("Could not get parent product details for %s", parent_asin)
                return []
            
            # Search for variations using brand and product type
            brand = parent_product.get("brand", "")
            title = parent_product.get("title", "")
            
            # Extract product type from title (simplified)
            product_type = self._extract_product_type(title)
            
            if brand and product_type:
                search_query = f"{brand} {product_type}"
                variations = await search_items_advanced(
                    keywords=search_query,
                    item_count=30,
                    priority="normal"
                )
                
                # Filter and create watch suggestions
                variant_watches = []
                for variation in variations:
                    if variation.get("asin") != parent_asin:  # Exclude parent
                        watch_suggestion = await self._create_variant_watch_suggestion(
                            variation, user_preferences
                        )
                        if watch_suggestion:
                            variant_watches.append(watch_suggestion)
                
                log.info("Created %d variant watch suggestions", len(variant_watches))
                return variant_watches[:5]  # Limit to top 5
            
        except Exception as e:
            log.error("Error creating variant watches for %s: %s", parent_asin, e)
        
        return []

    async def optimize_existing_watches(self, user_id: int) -> List[Dict]:
        """Optimize user's existing watches based on performance.
        
        Args
        ----
            user_id: User ID
            
        Returns
        -------
            List of optimization suggestions
        """
        log.info("Optimizing existing watches for user %d", user_id)
        
        try:
            with Session(engine) as session:
                # Get user's watches
                statement = select(Watch).where(Watch.user_id == user_id)
                watches = session.exec(statement).all()
                
                if not watches:
                    return []
                
                optimizations = []
                
                for watch in watches:
                    optimization = await self._analyze_watch_performance(watch)
                    if optimization:
                        optimizations.append(optimization)
                
                log.info("Generated %d optimization suggestions", len(optimizations))
                return optimizations
                
        except Exception as e:
            log.error("Error optimizing watches for user %d: %s", user_id, e)
            return []

    def _analyze_watch_intent(self, user_input: str, basic_data: Dict) -> Dict:
        """Analyze user intent from watch creation input.
        
        Args
        ----
            user_input: Original user input
            basic_data: Basic parsed watch data
            
        Returns
        -------
            Intent analysis results
        """
        input_lower = user_input.lower()
        intent = {
            "type": "general_watch",
            "specificity": "medium",
            "urgency": "normal",
            "price_focus": False,
            "brand_loyalty": False,
            "feature_requirements": [],
            "time_sensitivity": False
        }
        
        # Analyze specificity
        if basic_data.get("asin") or "model" in input_lower or "exact" in input_lower:
            intent["specificity"] = "high"
            intent["type"] = "specific_product_watch"
        elif len(input_lower.split()) >= 5:
            intent["specificity"] = "high"
        elif len(input_lower.split()) <= 2:
            intent["specificity"] = "low"
        
        # Analyze price focus
        price_words = ["cheap", "budget", "affordable", "under", "below", "maximum", "limit"]
        if any(word in input_lower for word in price_words):
            intent["price_focus"] = True
        
        # Analyze urgency
        urgent_words = ["urgent", "asap", "immediately", "quick", "fast", "need now"]
        if any(word in input_lower for word in urgent_words):
            intent["urgency"] = "high"
        
        # Analyze brand loyalty
        if basic_data.get("brand") or any(brand in input_lower for brand in 
                                        ["apple", "samsung", "sony", "lg", "oneplus"]):
            intent["brand_loyalty"] = True
        
        # Extract feature requirements
        feature_words = ["wireless", "waterproof", "gaming", "professional", "portable"]
        intent["feature_requirements"] = [word for word in feature_words if word in input_lower]
        
        # Time sensitivity
        time_words = ["sale", "offer", "limited time", "today", "weekend"]
        if any(word in input_lower for word in time_words):
            intent["time_sensitivity"] = True
            intent["urgency"] = "high"
        
        return intent

    async def _enhance_watch_data(
        self, 
        basic_data: Dict, 
        intent_analysis: Dict, 
        user_id: int
    ) -> Dict:
        """Enhance basic watch data with intelligent suggestions.
        
        Args
        ----
            basic_data: Basic parsed watch data
            intent_analysis: Intent analysis results
            user_id: User ID for personalization
            
        Returns
        -------
            Enhanced watch data
        """
        enhanced_data = basic_data.copy()
        
        # Get user context for personalization
        user_context = await self._get_user_context(user_id)
        
        # Enhance price parameters if not specified
        if not enhanced_data.get("max_price") and intent_analysis["price_focus"]:
            # Search for products to get price suggestions
            if enhanced_data.get("keywords"):
                products = await search_items_advanced(
                    keywords=enhanced_data["keywords"],
                    item_count=30,
                    priority="normal"
                )
                if products:
                    price_suggestions = await self.suggest_watch_parameters(products, user_context)
                    enhanced_data["suggested_max_price"] = price_suggestions["max_price_suggestion"]
        
        # Enhance brand if not specified but user has brand loyalty
        if not enhanced_data.get("brand") and user_context and user_context.get("preferred_brands"):
            enhanced_data["suggested_brand"] = user_context["preferred_brands"][0]
        
        # Enhance discount parameters based on intent
        if intent_analysis["time_sensitivity"] and not enhanced_data.get("min_discount"):
            enhanced_data["suggested_min_discount"] = 15  # Higher discount for time-sensitive searches
        elif not enhanced_data.get("min_discount"):
            enhanced_data["suggested_min_discount"] = 10  # Default suggestion
        
        # Enhance monitoring frequency based on urgency
        if intent_analysis["urgency"] == "high":
            enhanced_data["suggested_mode"] = "rt"  # Real-time monitoring
        else:
            enhanced_data["suggested_mode"] = "daily"
        
        return enhanced_data

    async def _generate_suggestions(self, watch_data: Dict, intent_analysis: Dict) -> List[Dict]:
        """Generate intelligent suggestions for watch improvement.
        
        Args
        ----
            watch_data: Watch data
            intent_analysis: Intent analysis
            
        Returns
        -------
            List of suggestions
        """
        suggestions = []
        
        # Price optimization suggestions
        if watch_data.get("suggested_max_price"):
            suggestions.append({
                "type": "price_optimization",
                "title": "Optimized Price Threshold",
                "description": f"Based on market analysis, set max price to ₹{watch_data['suggested_max_price']:,} for better deal detection",
                "action": "set_max_price",
                "value": watch_data["suggested_max_price"],
                "confidence": 0.8
            })
        
        # Brand suggestions
        if watch_data.get("suggested_brand"):
            suggestions.append({
                "type": "brand_suggestion", 
                "title": "Brand Recommendation",
                "description": f"Based on your history, you might prefer {watch_data['suggested_brand']} products",
                "action": "set_brand",
                "value": watch_data["suggested_brand"],
                "confidence": 0.7
            })
        
        # Monitoring frequency suggestions
        if watch_data.get("suggested_mode"):
            mode_desc = "real-time alerts" if watch_data["suggested_mode"] == "rt" else "daily summaries"
            suggestions.append({
                "type": "monitoring_frequency",
                "title": "Optimal Monitoring",
                "description": f"For this type of product, {mode_desc} work best",
                "action": "set_mode",
                "value": watch_data["suggested_mode"],
                "confidence": 0.6
            })
        
        # Discount suggestions
        if watch_data.get("suggested_min_discount"):
            suggestions.append({
                "type": "discount_optimization",
                "title": "Smart Discount Threshold", 
                "description": f"Set minimum discount to {watch_data['suggested_min_discount']}% based on typical deal patterns",
                "action": "set_min_discount",
                "value": watch_data["suggested_min_discount"],
                "confidence": 0.7
            })
        
        return suggestions

    async def _find_alternatives(self, watch_data: Dict, intent_analysis: Dict) -> List[Dict]:
        """Find alternative products for the watch.
        
        Args
        ----
            watch_data: Watch data
            intent_analysis: Intent analysis
            
        Returns
        -------
            List of alternative products
        """
        alternatives = []
        
        if not watch_data.get("keywords"):
            return alternatives
        
        try:
            # Search for similar products
            similar_products = await self.search_engine.intelligent_search(
                watch_data["keywords"],
                user_context={"user_id": None}  # Anonymous search for alternatives
            )
            
            for product in similar_products.get("results", [])[:3]:  # Top 3 alternatives
                alternative = {
                    "asin": product.get("asin"),
                    "title": product.get("title"),
                    "price": product.get("price"),
                    "rating": product.get("reviews", {}).get("average_rating"),
                    "image": product.get("images", {}).get("medium"),
                    "reason": "Similar product with good ratings"
                }
                
                # Add specific reasons based on analysis
                if product.get("offers", {}).get("savings_percentage", 0) > 10:
                    alternative["reason"] = "Currently on sale with good discount"
                elif product.get("reviews", {}).get("count", 0) > 100:
                    alternative["reason"] = "Highly reviewed alternative"
                elif product.get("offers", {}).get("is_prime_eligible"):
                    alternative["reason"] = "Prime eligible with fast delivery"
                
                alternatives.append(alternative)
                
        except Exception as e:
            log.error("Error finding alternatives: %s", e)
        
        return alternatives

    async def _analyze_price_patterns(self, products: List[Dict]) -> Dict:
        """Analyze price patterns from product list.
        
        Args
        ----
            products: List of products
            
        Returns
        -------
            Price analysis results
        """
        prices = []
        for product in products:
            price = product.get("price")
            if price and price > 0:
                prices.append(price / 100)  # Convert to rupees
        
        if not prices:
            return self._get_default_price_analysis()
        
        prices.sort()
        
        analysis = {
            "min_price": min(prices),
            "max_price": max(prices),
            "avg_price": int(sum(prices) / len(prices)),
            "median_price": int(statistics.median(prices)),
            "suggested_threshold": int(sum(prices) / len(prices) * 0.85),  # 15% below average
            "volatility": "high" if (max(prices) - min(prices)) > (sum(prices) / len(prices)) else "low"
        }
        
        return analysis

    async def _analyze_discount_patterns(self, products: List[Dict]) -> Dict:
        """Analyze discount patterns from products.
        
        Args
        ----
            products: List of products
            
        Returns
        -------
            Discount analysis results
        """
        discounts = []
        for product in products:
            discount = product.get("offers", {}).get("savings_percentage", 0)
            if discount > 0:
                discounts.append(discount)
        
        if not discounts:
            return {
                "effective_discount": 10,
                "frequency": 20,
                "best_timing": "weekends",
                "volatility_reason": "Standard monitoring recommended"
            }
        
        avg_discount = sum(discounts) / len(discounts)
        frequency = (len(discounts) / len(products)) * 100
        
        return {
            "effective_discount": max(10, int(avg_discount * 0.8)),  # 80% of average discount
            "frequency": int(frequency),
            "best_timing": "weekends and sales events",
            "volatility_reason": f"Products show {int(frequency)}% deal frequency"
        }

    def _suggest_monitoring_frequency(self, products: List[Dict]) -> str:
        """Suggest optimal monitoring frequency.
        
        Args
        ----
            products: List of products
            
        Returns
        -------
            Suggested monitoring frequency
        """
        # Analyze price volatility and discount frequency
        high_discount_count = sum(1 for p in products 
                                if p.get("offers", {}).get("savings_percentage", 0) > 15)
        
        discount_ratio = high_discount_count / len(products) if products else 0
        
        if discount_ratio > 0.3:  # 30% of products have high discounts
            return "rt"  # Real-time for volatile prices
        else:
            return "daily"  # Daily for stable prices

    def _get_default_parameters(self) -> Dict:
        """Get default watch parameters."""
        return {
            "max_price_suggestion": 25000,
            "min_discount_suggestion": 15,
            "monitoring_frequency": "daily",
            "rationale": {
                "price": "Default range for Indian marketplace",
                "discount": "Standard 15% discount threshold",
                "frequency": "Daily monitoring for most products"
            }
        }

    def _get_default_price_analysis(self) -> Dict:
        """Get default price analysis."""
        return {
            "min_price": 1000,
            "max_price": 50000,
            "avg_price": 15000,
            "median_price": 12000,
            "suggested_threshold": 12750,
            "volatility": "medium"
        }

    def _apply_user_preferences(self, suggestions: Dict, preferences: Dict) -> Dict:
        """Apply user preferences to suggestions.
        
        Args
        ----
            suggestions: Generated suggestions
            preferences: User preferences
            
        Returns
        -------
            Modified suggestions
        """
        if preferences.get("price_range"):
            pref_range = preferences["price_range"]
            # Adjust suggested price based on user's typical range
            suggestions["max_price_suggestion"] = min(
                suggestions["max_price_suggestion"], 
                pref_range["max"]
            )
        
        if preferences.get("preferred_discount"):
            suggestions["min_discount_suggestion"] = max(
                suggestions["min_discount_suggestion"],
                preferences["preferred_discount"]
            )
        
        return suggestions

    def _extract_product_type(self, title: str) -> str:
        """Extract product type from title.
        
        Args
        ----
            title: Product title
            
        Returns
        -------
            Extracted product type
        """
        title_lower = title.lower()
        
        product_types = {
            "laptop": ["laptop", "notebook"],
            "phone": ["phone", "smartphone", "mobile"],
            "headphone": ["headphone", "earphone", "earbuds"],
            "watch": ["watch", "smartwatch"],
            "speaker": ["speaker", "bluetooth speaker"],
            "camera": ["camera", "dslr"],
            "tablet": ["tablet", "ipad"],
            "monitor": ["monitor", "display", "screen"]
        }
        
        for product_type, keywords in product_types.items():
            if any(keyword in title_lower for keyword in keywords):
                return product_type
        
        # Default to first word if no match
        words = title.split()
        return words[0] if words else "product"

    async def _create_variant_watch_suggestion(
        self, 
        variation: Dict, 
        user_preferences: Dict
    ) -> Optional[Dict]:
        """Create watch suggestion for a product variation.
        
        Args
        ----
            variation: Product variation data
            user_preferences: User preferences
            
        Returns
        -------
            Watch suggestion or None if not suitable
        """
        # Filter based on user preferences
        if user_preferences.get("max_price"):
            variation_price = variation.get("price", 0)
            if variation_price > user_preferences["max_price"] * 100:  # Convert to paise
                return None
        
        if user_preferences.get("min_rating"):
            rating = variation.get("reviews", {}).get("average_rating", 0)
            if rating < user_preferences["min_rating"]:
                return None
        
        return {
            "asin": variation.get("asin"),
            "title": variation.get("title"),
            "price": variation.get("price"),
            "image": variation.get("images", {}).get("medium"),
            "rating": variation.get("reviews", {}).get("average_rating"),
            "suggestion_reason": "Product variation matching your criteria"
        }

    async def _analyze_watch_performance(self, watch: Watch) -> Optional[Dict]:
        """Analyze individual watch performance and suggest optimizations.
        
        Args
        ----
            watch: Watch object
            
        Returns
        -------
            Optimization suggestion or None
        """
        # This would analyze watch performance based on:
        # - How many deals it has found
        # - Price movements of watched products
        # - User engagement with alerts
        
        # For now, return basic optimization
        optimization = {
            "watch_id": watch.id,
            "current_keywords": watch.keywords,
            "suggestions": []
        }
        
        # Suggest price adjustment if max_price is too low
        if watch.max_price and watch.max_price < 5000:
            optimization["suggestions"].append({
                "type": "price_adjustment",
                "description": "Consider increasing max price for more deal opportunities",
                "current_value": watch.max_price,
                "suggested_value": watch.max_price * 1.5
            })
        
        # Suggest discount adjustment if min_discount is too high
        if watch.min_discount and watch.min_discount > 25:
            optimization["suggestions"].append({
                "type": "discount_adjustment", 
                "description": "High discount threshold might miss good deals",
                "current_value": watch.min_discount,
                "suggested_value": 15
            })
        
        return optimization if optimization["suggestions"] else None

    async def _get_user_context(self, user_id: int) -> Optional[Dict]:
        """Get user context for personalization.
        
        Args
        ----
            user_id: User ID
            
        Returns
        -------
            User context dict
        """
        try:
            with Session(engine) as session:
                # Get user's watch history for preferences
                statement = select(Watch).where(Watch.user_id == user_id).limit(20)
                watches = session.exec(statement).all()
                
                if not watches:
                    return None
                
                # Analyze user preferences
                brands = [w.brand for w in watches if w.brand]
                price_ranges = [w.max_price for w in watches if w.max_price]
                discount_prefs = [w.min_discount for w in watches if w.min_discount]
                
                context = {}
                
                if brands:
                    # Most common brands
                    brand_counts = {}
                    for brand in brands:
                        brand_counts[brand] = brand_counts.get(brand, 0) + 1
                    
                    sorted_brands = sorted(brand_counts.items(), key=lambda x: x[1], reverse=True)
                    context["preferred_brands"] = [brand for brand, _ in sorted_brands[:3]]
                
                if price_ranges:
                    avg_price = sum(price_ranges) / len(price_ranges)
                    context["price_range"] = {
                        "min": int(avg_price * 0.5),
                        "max": int(avg_price * 1.5)
                    }
                
                if discount_prefs:
                    context["preferred_discount"] = sum(discount_prefs) / len(discount_prefs)
                
                return context
                
        except Exception as e:
            log.error("Error getting user context for %d: %s", user_id, e)
            return None
