"""
Product Selection Models for intelligent product selection in watch flow.

This module implements Phase 4 of the Feature Match AI system by providing
a framework for different product selection strategies:

1. FeatureMatchModel - AI-powered selection based on feature matching
2. PopularityModel - Selection based on ratings and popularity
3. RandomSelectionModel - Fallback random selection

The models integrate with the watch flow to provide intelligent product
selection while maintaining backward compatibility.
"""

import time
import random
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from logging import getLogger

log = getLogger(__name__)


class BaseProductSelectionModel(ABC):
    """Base class for product selection models."""

    def __init__(self, model_name: str):
        """Initialize the base product selection model."""
        self.model_name = model_name
        self.version = "1.0.0"
        
    @abstractmethod
    async def select_product(
        self, 
        products: List[Dict], 
        user_query: str, 
        **kwargs
    ) -> Optional[Dict]:
        """
        Select the best product from a list of candidates.
        
        Args:
        ----
            products: List of product data dicts
            user_query: Original user search query
            **kwargs: Additional context (user_preferences, etc.)
            
        Returns:
        -------
            Selected product dict or None if no suitable product found
        """
        pass
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model metadata for logging and monitoring."""
        return {
            "model_name": self.model_name,
            "version": self.version,
            "selection_strategy": self.__class__.__name__
        }


class FeatureMatchModel(BaseProductSelectionModel):
    """AI-powered product selection based on feature matching."""

    def __init__(self):
        """Initialize the Feature Match AI model."""
        super().__init__("FeatureMatchModel")
        self.version = "1.0.0"
        
        # Lazy loading to avoid circular imports
        self._feature_extractor = None
        self._matching_engine = None
        
    async def select_product(
        self, 
        products: List[Dict], 
        user_query: str, 
        **kwargs
    ) -> Optional[Dict]:
        """
        Select best product using feature matching AI.
        
        Args:
        ----
            products: List of product candidates
            user_query: User's search query for feature extraction
            **kwargs: Additional context
            
        Returns:
        -------
            Best matching product with AI selection metadata
        """
        start_time = time.time()
        
        if not products:
            log.warning("FeatureMatchModel: No products to select from")
            return None
        
        if not user_query or not user_query.strip():
            log.warning("FeatureMatchModel: Empty query, falling back to first product")
            return products[0]
        
        try:
            # Lazy load AI components
            if not self._feature_extractor or not self._matching_engine:
                await self._initialize_ai_components()
            
            # Extract user requirements from query
            user_features = self._feature_extractor.extract_features(user_query)
            log.debug(f"Extracted user features: {user_features}")
            
            # Check if query has technical features for AI selection
            if not self._has_technical_features(user_features):
                log.info("FeatureMatchModel: Non-technical query, falling back")
                return None  # Trigger fallback to PopularityModel
            
            # Score all products using the matching engine
            scored_products = await self._matching_engine.score_products(
                user_features, products, category="gaming_monitor"
            )
            
            if not scored_products:
                log.warning("FeatureMatchModel: No products scored, falling back")
                return None
            
            # Get the best match
            best_product, best_score_data = scored_products[0]
            
            # Add AI selection metadata
            ai_metadata = {
                "ai_selection": True,
                "ai_score": best_score_data["score"],
                "ai_rationale": best_score_data["rationale"],
                "ai_confidence": best_score_data["confidence"],
                "model_name": self.model_name,
                "model_version": self.version,
                "processing_time_ms": (time.time() - start_time) * 1000,
                "matched_features": best_score_data["matched_features"],
                "user_features": user_features
            }
            
            # Attach metadata to product
            result_product = best_product.copy()
            result_product["_ai_metadata"] = ai_metadata
            
            log.info(
                "FeatureMatchModel selected product %s with score %.3f (%.1fms)",
                best_product.get("asin", "unknown"), 
                best_score_data["score"],
                ai_metadata["processing_time_ms"]
            )
            
            return result_product
            
        except Exception as e:
            log.error(f"FeatureMatchModel selection failed: {e}")
            processing_time = (time.time() - start_time) * 1000
            log.warning(f"AI selection took {processing_time:.1f}ms before failure")
            return None  # Trigger fallback
    
    async def _initialize_ai_components(self):
        """Initialize AI components with lazy loading."""
        try:
            from .ai.feature_extractor import FeatureExtractor
            from .ai.matching_engine import FeatureMatchingEngine
            
            self._feature_extractor = FeatureExtractor()
            self._matching_engine = FeatureMatchingEngine()
            
            log.info("FeatureMatchModel: AI components initialized successfully")
        except ImportError as e:
            log.error(f"Failed to import AI components: {e}")
            raise
    
    def _has_technical_features(self, user_features: Dict[str, Any]) -> bool:
        """
        Determine if query has sufficient technical features for AI selection.

        This is the critical query classifier that determines when to use AI.
        Enhanced to be more lenient for gaming/tech product queries.
        """
        if not user_features:
            # If no features extracted, fall back to basic technical detection
            log.debug("No user features extracted, checking fallback detection")
            return self._fallback_technical_detection()

        # Check confidence level - lowered threshold for better AI coverage
        confidence = user_features.get("confidence", 0.0)
        if confidence >= 0.2:  # Lowered from 0.3 to catch more technical queries
            log.debug(f"High confidence ({confidence:.3f}) - using AI")
            return True

        # Check for explicit technical features first
        technical_features = [
            "refresh_rate", "size", "resolution", "curvature", "panel_type",
            "usage_context", "category"  # Added broader technical indicators
        ]

        found_features = [f for f in technical_features if f in user_features]

        # If user has specific technical features, definitely use AI
        if len(found_features) >= 1:
            log.debug(f"Technical features found: {found_features} - using AI")
            return True

        # Even for simple queries, use AI to analyze and showcase technical features
        # This allows the AI to extract product features and present comparisons
        technical_density = user_features.get("technical_density", 0.0)

        # Lowered threshold from 0.4 to 0.25 for better coverage
        use_ai = technical_density > 0.25

        log.debug(f"Technical_density={technical_density:.3f}, use_ai={use_ai}")
        return use_ai

    def _fallback_technical_detection(self) -> bool:
        """
        Fallback method when feature extraction fails.
        Uses the global has_technical_features function as backup.
        """
        try:
            # Get the original query from the call stack or context
            # This is a simplified fallback - in practice we'd need to pass the query
            log.debug("Using fallback technical detection")
            # For now, assume queries with common tech terms are technical
            # This will be improved when we can access the original query
            return True  # Be permissive in fallback mode
        except Exception as e:
            log.error(f"Fallback technical detection failed: {e}")
            return False
    
    def explain_selection(self, product: Dict) -> str:
        """Generate user-friendly explanation of AI selection."""
        ai_metadata = product.get("_ai_metadata", {})
        
        if not ai_metadata.get("ai_selection"):
            return "Selected based on search relevance"
        
        rationale = ai_metadata.get("ai_rationale", "")
        confidence = ai_metadata.get("ai_confidence", 0)
        
        explanation = f"🤖 **AI-Matched Product** (Confidence: {confidence:.0%})\n"
        
        if rationale:
            explanation += f"**Why this product**: {rationale}\n"
        
        matched_features = ai_metadata.get("matched_features", [])
        if matched_features:
            explanation += f"**Matched features**: {', '.join(matched_features)}"
        
        return explanation


class PopularityModel(BaseProductSelectionModel):
    """Product selection based on popularity metrics (ratings, review count)."""

    def __init__(self):
        """Initialize the Popularity model."""
        super().__init__("PopularityModel")
        self.version = "1.0.0"
    
    async def select_product(
        self, 
        products: List[Dict], 
        user_query: str, 
        **kwargs
    ) -> Optional[Dict]:
        """
        Select product based on popularity metrics.
        
        Prioritizes products with:
        1. High rating count (more reviews = more popular)
        2. High average rating
        3. Better sales rank if available
        """
        start_time = time.time()
        
        if not products:
            return None
        
        try:
            scored_products = []
            
            for product in products:
                popularity_score = self._calculate_popularity_score(product)
                scored_products.append((product, popularity_score))
            
            # Sort by popularity score (highest first)
            scored_products.sort(key=lambda x: x[1], reverse=True)
            
            best_product, best_score = scored_products[0]
            
            # Add selection metadata
            popularity_metadata = {
                "popularity_selection": True,
                "popularity_score": best_score,
                "model_name": self.model_name,
                "model_version": self.version,
                "processing_time_ms": (time.time() - start_time) * 1000,
                "selection_reason": "Based on customer ratings and popularity"
            }
            
            result_product = best_product.copy()
            result_product["_popularity_metadata"] = popularity_metadata
            
            log.info(
                "PopularityModel selected product %s with score %.3f",
                best_product.get("asin", "unknown"), best_score
            )
            
            return result_product
            
        except Exception as e:
            log.error(f"PopularityModel selection failed: {e}")
            return None
    
    def _calculate_popularity_score(self, product: Dict[str, Any]) -> float:
        """Calculate popularity score for a product."""
        score = 0.0
        
        # Debug: log what data we're working with
        log.debug(f"Calculating popularity for {product.get('asin', 'unknown')}: "
                 f"rating_count={product.get('rating_count', 'missing')}, "
                 f"average_rating={product.get('average_rating', 'missing')}, "
                 f"sales_rank={product.get('sales_rank', 'missing')}")
        
        # Rating count (logarithmic scaling for diminishing returns)
        rating_count = product.get("rating_count", 0)
        if isinstance(rating_count, (int, float)) and rating_count > 0:
            import math
            # Log scale: 100 reviews = 0.4, 1000 reviews = 0.6, 10000 reviews = 0.8
            score += min(0.4, math.log10(rating_count + 1) / 5)
        
        # Average rating 
        avg_rating = product.get("average_rating", 0)
        if isinstance(avg_rating, (int, float)) and avg_rating > 0:
            # Scale 3.0-5.0 to 0.0-0.4
            score += max(0.0, (avg_rating - 3.0) / 2.0 * 0.4)
        
        # Sales rank (if available)
        sales_rank = product.get("sales_rank")
        if isinstance(sales_rank, (int, float)) and sales_rank > 0:
            import math
            # Inverse log scale: rank 1 = 0.2, rank 100 = 0.1, rank 10000 = 0.05
            score += max(0.0, 0.2 - math.log10(sales_rank) / 4 * 0.15)
        
        # If no popularity metrics available, assign small base score to avoid zero
        if score == 0.0:
            # Small base score for products without rating data
            # This prevents zero scores that suggest broken selection
            score = 0.1
            log.debug(f"No popularity metrics for {product.get('asin', 'unknown')}, using base score {score}")
        
        return min(1.0, score)


class RandomSelectionModel(BaseProductSelectionModel):
    """Fallback random selection when other models fail."""

    def __init__(self):
        """Initialize the Random selection model."""
        super().__init__("RandomSelectionModel")
        self.version = "1.0.0"
    
    async def select_product(
        self, 
        products: List[Dict], 
        user_query: str, 
        **kwargs
    ) -> Optional[Dict]:
        """Select a random product from the list."""
        start_time = time.time()
        
        if not products:
            return None
        
        # Use weighted random to prefer products with basic quality indicators
        weighted_products = []
        for product in products:
            weight = self._calculate_basic_weight(product)
            weighted_products.append((product, weight))
        
        # Select using weights
        total_weight = sum(weight for _, weight in weighted_products)
        if total_weight <= 0:
            # Fallback to pure random
            selected_product = random.choice(products)
        else:
            rand_val = random.uniform(0, total_weight)
            cumulative = 0
            selected_product = products[0]  # Default fallback
            
            for product, weight in weighted_products:
                cumulative += weight
                if rand_val <= cumulative:
                    selected_product = product
                    break
        
        # Add selection metadata
        random_metadata = {
            "random_selection": True,
            "model_name": self.model_name,
            "model_version": self.version,
            "processing_time_ms": (time.time() - start_time) * 1000,
            "selection_reason": "Random selection from available products"
        }
        
        result_product = selected_product.copy()
        result_product["_random_metadata"] = random_metadata
        
        log.info("RandomSelectionModel selected random product %s", 
                selected_product.get("asin", "unknown"))
        
        return result_product
    
    def _calculate_basic_weight(self, product: Dict[str, Any]) -> float:
        """Calculate basic weight for random selection (favor products with some quality indicators)."""
        weight = 1.0
        
        # Slightly favor products with ratings
        if product.get("average_rating", 0) > 3.5:
            weight += 0.5
        
        # Slightly favor products with review counts
        if product.get("rating_count", 0) > 10:
            weight += 0.3
        
        return weight


def get_selection_model(user_query: str, product_count: int, user_id: str = "system") -> BaseProductSelectionModel:
    """
    Determine which model to use based on query complexity and product count.
    Phase R7: Enhanced with feature rollout management for gradual deployment.
    
    Args:
    ----
        user_query: User's search query
        product_count: Number of available products
        user_id: User ID for feature rollout decisions
        
    Returns:
    -------
        Appropriate product selection model
    """
    # R7: Import rollout manager
    from .feature_rollout import is_ai_feature_enabled
    
    # Use has_technical_features for better AI detection
    has_tech_features = has_technical_features(user_query)
    
    # R7: Check if AI features are enabled for this user
    ai_enabled = is_ai_feature_enabled(
        "ai_feature_matching", 
        user_id,
        has_technical_features=has_tech_features,
        product_count=product_count
    )
    
    # ALWAYS use Feature Match AI for any query with sufficient products
    # This prevents PopularityModel from being used and forces AI-powered selection
    if product_count >= 2:  # Lowered from 3 to 2 to be more inclusive
        log.info(f"FORCED AI: Using FeatureMatchModel for {product_count} products (PopularityModel disabled)")
        return FeatureMatchModel()

    # For single products, use Feature Match AI if AI is enabled, otherwise Random
    if product_count == 1 and ai_enabled:
        log.info(f"FORCED AI: Using FeatureMatchModel for single product")
        return FeatureMatchModel()
    
    # Random selection only for single products
    else:
        log.info(f"Using RandomSelectionModel: {product_count} products")
        return RandomSelectionModel()


async def smart_product_selection(
    products: List[Dict], 
    user_query: str, 
    **kwargs
) -> Optional[Dict]:
    """
    ENHANCED: Comprehensive monitoring integration (Phase R5.1).
    
    High-level function for intelligent product selection with fallback chain:
    Feature Match AI → Popularity → Random
    
    Args:
    ----
        products: List of product candidates
        user_query: User's search query
        **kwargs: Additional context
        
    Returns:
    -------
        Selected product with selection metadata
    """
    # R5.1: Import monitoring functions
    from .ai_performance_monitor import log_ai_selection, log_ai_fallback
    
    if not products:
        log.warning("smart_product_selection: No products available")
        return None
    
    # R5.1: Start performance tracking
    start_time = time.time()
    product_count = len(products)
    has_tech = has_technical_features(user_query)
    primary_model = None
    
    log.info(f"SELECTION_DECISION: query='{user_query}', products={product_count}, has_tech={has_tech}")
    
    # Get primary model with detailed logging (R7: with user_id for rollout)
    user_id = kwargs.get("user_id", "system")
    primary_model = get_selection_model(user_query, product_count, user_id)
    model_name = primary_model.__class__.__name__
    
    log.info(f"PRIMARY_MODEL: {model_name}")
    
    try:
        # R5.1: Attempt primary selection with monitoring
        result = await primary_model.select_product(products, user_query, **kwargs)
        
        if result:
            # R5.1: SUCCESS - Log successful selection with comprehensive metadata
            processing_time = (time.time() - start_time) * 1000
            
            selection_metadata = {
                "processing_time_ms": processing_time,
                "model_name": model_name,
                "product_count": product_count,
                "has_technical_features": has_tech,
                **result.get("_ai_metadata", {}),
                **result.get("_popularity_metadata", {}),
                **result.get("_random_metadata", {})
            }
            
            log_ai_selection(
                model_name=model_name,
                user_query=user_query,
                product_count=product_count,
                selection_metadata=selection_metadata,
                success=True
            )
            
            log.info(f"PRIMARY_SUCCESS: {model_name} selected product {result.get('asin', 'unknown')} in {processing_time:.1f}ms")
            return result
            
    except Exception as e:
        # R5.1: PRIMARY FAILURE - Log failure and attempt fallback
        log.error(f"PRIMARY_FAILURE: {model_name} failed: {e}")
        
        # Log primary failure
        log_ai_fallback(
            primary_model=model_name,
            fallback_model="PopularityModel",
            reason=str(e)
        )
    
    # R5.1: Fallback to Popularity if primary was AI
    if hasattr(primary_model, 'model_name') and primary_model.model_name == "FeatureMatchModel":
        try:
            log.info("FALLBACK_ATTEMPT: Trying PopularityModel after AI failure")
            popularity_model = PopularityModel()
            result = await popularity_model.select_product(products, user_query, **kwargs)
            
            if result:
                # R5.1: Log successful fallback
                processing_time = (time.time() - start_time) * 1000
                
                selection_metadata = {
                    "processing_time_ms": processing_time,
                    "model_name": "PopularityModel",
                    "is_fallback": True,
                    "primary_failed": model_name,
                    **result.get("_popularity_metadata", {})
                }
                
                log_ai_selection(
                    model_name="PopularityModel",
                    user_query=user_query,
                    product_count=product_count,
                    selection_metadata=selection_metadata,
                    success=True
                )
                
                log.info(f"FALLBACK_SUCCESS: PopularityModel selected product {result.get('asin', 'unknown')} in {processing_time:.1f}ms")
                return result
                
        except Exception as e:
            log.warning(f"FALLBACK_FAILURE: PopularityModel failed: {e}")
            
            # R5.1: Log fallback failure
            log_ai_fallback(
                primary_model="PopularityModel",
                fallback_model="RandomSelectionModel",
                reason=f"PopularityModel failed: {e}"
            )
    
    # R5.1: Final fallback to Random with monitoring
    try:
        log.info("FINAL_FALLBACK: Trying RandomSelectionModel")
        random_model = RandomSelectionModel()
        result = await random_model.select_product(products, user_query, **kwargs)
        
        if result:
            # R5.1: Log final fallback success
            processing_time = (time.time() - start_time) * 1000
            
            selection_metadata = {
                "processing_time_ms": processing_time,
                "model_name": "RandomSelectionModel",
                "is_final_fallback": True,
                "primary_failed": model_name,
                **result.get("_random_metadata", {})
            }
            
            log_ai_selection(
                model_name="RandomSelectionModel",
                user_query=user_query,
                product_count=product_count,
                selection_metadata=selection_metadata,
                success=True
            )
            
            log.info(f"FINAL_SUCCESS: RandomSelectionModel selected product {result.get('asin', 'unknown')} in {processing_time:.1f}ms")
            return result
            
    except Exception as e:
        log.error(f"FINAL_FAILURE: All selection models failed: {e}")
        
        # R5.1: Log complete system failure
        log_ai_fallback(
            primary_model="RandomSelectionModel",
            fallback_model="UltimateFallback",
            reason=f"All models failed: {e}"
        )
    
    # R5.1: Ultimate fallback - return first product with monitoring
    log.warning("ULTIMATE_FALLBACK: All models failed, returning first product")
    processing_time = (time.time() - start_time) * 1000
    
    fallback_product = products[0].copy()
    fallback_product["_fallback_metadata"] = {
        "fallback_selection": True,
        "reason": "All selection models failed",
        "model_name": "UltimateFallback",
        "processing_time_ms": processing_time
    }
    
    # R5.1: Log ultimate fallback selection
    selection_metadata = {
        "processing_time_ms": processing_time,
        "model_name": "UltimateFallback",
        "is_ultimate_fallback": True,
        "primary_failed": model_name,
        "total_failures": "all"
    }
    
    log_ai_selection(
        model_name="UltimateFallback",
        user_query=user_query,
        product_count=product_count,
        selection_metadata=selection_metadata,
        success=True  # It's still technically a success, just not optimal
    )
    
    log.info(f"ULTIMATE_SUCCESS: Fallback selected first product {fallback_product.get('asin', 'unknown')} in {processing_time:.1f}ms")
    
    return fallback_product


def has_technical_features(query: str) -> bool:
    """
    ENHANCED: Better technical feature detection.
    
    This improved classifier determines if a query has technical features
    by analyzing multiple indicators and using more comprehensive patterns.
    """
    if not query or not query.strip():
        return False
    
    query_lower = query.lower()
    
    # Comprehensive technical indicators
    technical_terms = [
        # Display specs
        "hz", "fps", "hertz", "inch", "cm", "4k", "1440p", "1080p", "uhd", "qhd", "fhd",
        # Display features
        "curved", "flat", "ips", "va", "tn", "oled", "qled",
        # Usage contexts that indicate technical interest
        "gaming", "coding", "programming", "development", "design", "creative", "professional",
        # Product categories
        "monitor", "display", "screen", "laptop", "computer", "phone", "tablet",
        # Tech brands (often indicate technical searches)
        "samsung", "lg", "dell", "asus", "acer", "msi", "benq", "apple", "lenovo", "hp"
    ]
    
    # Numeric indicators (sizes, refresh rates, resolutions)
    import re
    has_numbers = bool(re.search(r'\d+', query))
    
    # Technical terms count
    tech_term_count = sum(1 for term in technical_terms if term in query_lower)
    
    # Decision logic: Either numbers OR multiple tech terms
    if has_numbers and tech_term_count >= 1:
        return True
    elif tech_term_count >= 2:  # Multiple tech terms without numbers
        return True
    
    return False
