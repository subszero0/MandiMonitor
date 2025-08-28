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
        """
        if not user_features:
            return False
        
        # Check confidence level
        confidence = user_features.get("confidence", 0.0)
        if confidence < 0.3:  # Low confidence suggests non-technical query
            return False
        
        # Check for explicit technical features first
        technical_features = [
            "refresh_rate", "size", "resolution", "curvature", "panel_type"
        ]
        
        found_features = [f for f in technical_features if f in user_features]
        
        # If user has specific technical features, definitely use AI
        if len(found_features) >= 1:
            log.debug(f"Technical features found: {found_features} - using AI")
            return True
        
        # Even for simple queries, use AI to analyze and showcase technical features
        # This allows the AI to extract product features and present comparisons
        technical_density = user_features.get("technical_density", 0.0)
        use_ai = technical_density > 0.4
        
        log.debug(f"No explicit features, technical_density={technical_density:.3f}, use_ai={use_ai}")
        return use_ai
    
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


def get_selection_model(user_query: str, product_count: int) -> BaseProductSelectionModel:
    """
    Determine which model to use based on query complexity and product count.
    
    FIXED: More intelligent model selection based on query analysis.
    Lowered thresholds to enable AI more frequently as per Phase R2 roadmap.
    
    Args:
    ----
        user_query: User's search query
        product_count: Number of available products
        
    Returns:
    -------
        Appropriate product selection model
    """
    # Use has_technical_features for better AI detection
    has_tech_features = has_technical_features(user_query)
    
    # Use Feature Match AI for technical queries with sufficient products  
    if product_count >= 3 and has_tech_features:  # Lowered from 5 to 3
        log.info(f"Using FeatureMatchModel: {product_count} products, tech_features={has_tech_features}")
        return FeatureMatchModel()
    
    # Use Popularity for moderate datasets
    elif product_count >= 2:  # Lowered from 3 to 2
        log.info(f"Using PopularityModel: {product_count} products")
        return PopularityModel()
    
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
    ENHANCED: Better logging and decision transparency.
    
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
    if not products:
        log.warning("smart_product_selection: No products available")
        return None
    
    # Log selection decision process
    product_count = len(products)
    has_tech = has_technical_features(user_query)
    
    log.info(f"SELECTION_DECISION: query='{user_query}', products={product_count}, has_tech={has_tech}")
    
    # Get primary model with detailed logging
    primary_model = get_selection_model(user_query, product_count)
    
    log.info(f"PRIMARY_MODEL: {primary_model.__class__.__name__}")
    
    try:
        result = await primary_model.select_product(products, user_query, **kwargs)
        if result:
            log.info(f"PRIMARY_SUCCESS: {primary_model.model_name} selected product {result.get('asin', 'unknown')}")
            return result
    except Exception as e:
        log.warning(f"PRIMARY_FAILURE: {primary_model.model_name} failed: {e}")
    
    # Fallback to Popularity if primary was AI
    if hasattr(primary_model, 'model_name') and primary_model.model_name == "FeatureMatchModel":
        try:
            log.info("FALLBACK_ATTEMPT: Trying PopularityModel after AI failure")
            popularity_model = PopularityModel()
            result = await popularity_model.select_product(products, user_query, **kwargs)
            if result:
                log.info(f"FALLBACK_SUCCESS: PopularityModel selected product {result.get('asin', 'unknown')}")
                return result
        except Exception as e:
            log.warning(f"FALLBACK_FAILURE: PopularityModel failed: {e}")
    
    # Final fallback to Random
    try:
        log.info("FINAL_FALLBACK: Trying RandomSelectionModel")
        random_model = RandomSelectionModel()
        result = await random_model.select_product(products, user_query, **kwargs)
        if result:
            log.info(f"FINAL_SUCCESS: RandomSelectionModel selected product {result.get('asin', 'unknown')}")
            return result
    except Exception as e:
        log.error(f"FINAL_FAILURE: All selection models failed: {e}")
    
    # Ultimate fallback - return first product
    log.warning("ULTIMATE_FALLBACK: All models failed, returning first product")
    fallback_product = products[0].copy()
    fallback_product["_fallback_metadata"] = {
        "fallback_selection": True,
        "reason": "All selection models failed",
        "model_name": "UltimateFallback"
    }
    
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
        # Gaming terms
        "gaming", "monitor", "display", "screen",
        # Tech brands (often indicate technical searches)
        "samsung", "lg", "dell", "asus", "acer", "msi", "benq"
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
