"""
Enhanced Product Selection Model for Phase 6 Multi-Card Experience.

This module extends the existing product selection framework to support intelligent
multi-card selection with comparison features and user choice.
"""

import time
from typing import Dict, List, Any, Optional
from logging import getLogger

from .matching_engine import FeatureMatchingEngine
from .feature_extractor import FeatureExtractor
from .enhanced_carousel import build_ai_selection_message, get_carousel_analytics_metadata

log = getLogger(__name__)


class EnhancedFeatureMatchModel:
    """
    Enhanced AI-powered product selection with multi-card support.
    
    This extends the existing FeatureMatchModel to support intelligent multi-card
    selection, comparison features, and smart defaults.
    """

    def __init__(self):
        """Initialize the enhanced feature match model."""
        self.feature_extractor = FeatureExtractor()
        self.matching_engine = FeatureMatchingEngine()
        
        # Multi-card configuration
        self.enable_multi_card = True  # A/B testing flag
        self.max_cards = 3
        self.min_products_for_ai = 5
        self.min_technical_words = 3

    async def select_products(
        self, 
        products: List[Dict], 
        user_query: str, 
        user_preferences: Optional[Dict] = None,
        enable_multi_card: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Enhanced product selection with multi-card support.
        
        Args:
        ----
            products: List of product data
            user_query: User's search query
            user_preferences: Additional user preferences
            enable_multi_card: Override multi-card setting for A/B testing
            
        Returns:
        -------
            Dict with selected products and carousel data
        """
        start_time = time.time()
        
        # Use override or instance setting for multi-card
        multi_card_enabled = enable_multi_card if enable_multi_card is not None else self.enable_multi_card
        log.info(f"🎯 ENHANCED_SELECTION_CONFIG: multi_card_enabled={multi_card_enabled}, products={len(products)}")

        # Extract user features
        user_features = self.feature_extractor.extract_features(user_query, category="gaming_monitor")
        log.info(f"🔍 FEATURE_EXTRACTION: found {len(user_features.get('features', []))} features")
        
        if not user_features:
            return await self._fallback_to_popularity(products, user_query, "No technical features detected")
        
        # Check if we have enough products for AI selection
        if len(products) < self.min_products_for_ai:
            return await self._fallback_to_popularity(products, user_query, f"Only {len(products)} products (need {self.min_products_for_ai})")
        
        # Use multi-card selection if enabled and conditions are met
        if multi_card_enabled and self._should_use_multi_card(user_features, products):
            return await self._multi_card_selection(user_features, products, user_query, user_preferences)
        else:
            return await self._single_card_selection(user_features, products, user_query, user_preferences)

    def _should_use_multi_card(self, user_features: Dict, products: List[Dict]) -> bool:
        """Determine if multi-card selection should be used."""

        # Enhanced: More permissive conditions for multi-card eligibility
        # Need sufficient products
        if len(products) < 3:
            return False

        # If we have user features, use them for decision
        if user_features:
            # Need at least 1 technical feature (lowered from 2)
            technical_features = [k for k in user_features.keys() if k not in ['confidence', 'processing_time_ms', 'technical_query']]
            if len(technical_features) < 1:
                log.debug(f"Only {len(technical_features)} technical features found, checking other indicators")

            # Check technical density (lowered from 0.3 to 0.2)
            technical_density = user_features.get('technical_density', 0)
            if technical_density >= 0.2:  # At least 20% technical words
                return True

            # Check confidence level (lowered from 0.3 to 0.2)
            confidence = user_features.get('confidence', 0)
            if confidence >= 0.2:
                return True

        # Fallback: If no user features but we have sufficient products,
        # assume it's worth trying multi-card (will fallback gracefully if needed)
        log.debug("No user features extracted, using fallback multi-card logic")
        return True

    async def _multi_card_selection(
        self, 
        user_features: Dict, 
        products: List[Dict], 
        user_query: str,
        user_preferences: Optional[Dict]
    ) -> Dict[str, Any]:
        """Perform multi-card selection with comparison features."""
        
        # Use the matching engine's carousel selection
        carousel_result = await self.matching_engine.select_products_for_carousel(
            user_features=user_features,
            products=products,
            category="gaming_monitor",
            max_cards=self.max_cards
        )
        
        if not carousel_result.get('products'):
            return await self._fallback_to_popularity(products, user_query, "Multi-card selection failed")
        
        # Enhanced AI selection message with transparency - Phase 3
        enhanced_reason = carousel_result['selection_reason']

        # Add score range information
        if carousel_result.get('products'):
            scores = [p.get('score', 0) for p in carousel_result['products']]
            if scores:
                min_score = min(scores)
                max_score = max(scores)
                score_range = f"Score range: {min_score:.2f} - {max_score:.2f}"
                enhanced_reason += f"\n\n📊 {score_range}"

        ai_message = build_ai_selection_message(
            presentation_mode=carousel_result['presentation_mode'],
            selection_reason=enhanced_reason,
            product_count=len(carousel_result['products']),
            user_query=user_query
        )
        
        # Enhanced metadata for analytics
        metadata = get_carousel_analytics_metadata(
            presentation_mode=carousel_result['presentation_mode'],
            product_count=len(carousel_result['products']),
            selection_criteria='ai_multi_card',
            processing_time_ms=carousel_result['ai_metadata']['processing_time_ms']
        )
        
        return {
            'selection_type': 'multi_card',
            'products': carousel_result['products'],
            'comparison_table': carousel_result['comparison_table'],
            'presentation_mode': carousel_result['presentation_mode'],
            'ai_message': ai_message,
            'selection_reason': carousel_result['selection_reason'],
            'metadata': {
                **carousel_result['ai_metadata'],
                **metadata,
                'user_features': len([k for k in user_features.keys() if k not in ['confidence', 'processing_time_ms']]),
                'model_used': 'EnhancedFeatureMatchModel',
                'multi_card_enabled': True
            }
        }

    async def _single_card_selection(
        self, 
        user_features: Dict, 
        products: List[Dict], 
        user_query: str,
        user_preferences: Optional[Dict]
    ) -> Dict[str, Any]:
        """Perform single-card selection (traditional approach)."""
        
        # Score all products and get the best one
        scored_products = await self.matching_engine.score_products(
            user_features=user_features,
            products=products,
            category="gaming_monitor"
        )
        
        if not scored_products:
            return await self._fallback_to_popularity(products, user_query, "AI scoring failed")
        
        best_product, best_score = scored_products[0]

        # Generate user-friendly explanations - Phase 3 Transparency
        score_breakdown = best_score.get('hybrid_breakdown', {})
        user_explanations = generate_user_explanations(score_breakdown, best_product)

        # Enhanced AI selection message with transparency
        enhanced_rationale = best_score['rationale']
        if user_explanations:
            enhanced_rationale += "\n\n🎯 Why Recommended:\n" + "\n".join(f"• {exp}" for exp in user_explanations[:2])

        ai_message = build_ai_selection_message(
            presentation_mode='single',
            selection_reason=enhanced_rationale,
            product_count=1,
            user_query=user_query
        )
        
        return {
            'selection_type': 'single_card',
            'products': [best_product],
            'comparison_table': {"summary": "Single best option - no comparison needed"},
            'presentation_mode': 'single',
            'ai_message': ai_message,
            'selection_reason': best_score['rationale'],
            'metadata': {
                'model_used': 'EnhancedFeatureMatchModel',
                'ai_score': best_score['score'],
                'ai_confidence': best_score['confidence'],
                'matched_features': best_score['matched_features'],
                'processing_time_ms': best_score['processing_time_ms'],
                'selection_type': 'single_card',
                'multi_card_enabled': False,
                'fallback_reason': 'single_card_criteria_met'
            }
        }

    async def _fallback_to_popularity(
        self, 
        products: List[Dict], 
        user_query: str, 
        reason: str
    ) -> Dict[str, Any]:
        """Fallback to popularity-based selection."""
        
        # Simple popularity selection (highest rating count * average rating)
        scored_products = []
        for product in products:
            rating_count = product.get("rating_count", 0)
            avg_rating = product.get("average_rating", 0)
            popularity_score = rating_count * avg_rating if rating_count and avg_rating else 0
            scored_products.append((product, popularity_score))
        
        # Sort by popularity score
        scored_products.sort(key=lambda x: x[1], reverse=True)
        
        if not scored_products:
            # Ultimate fallback - first product
            best_product = products[0] if products else None
        else:
            best_product = scored_products[0][0]
        
        return {
            'selection_type': 'popularity_fallback',
            'products': [best_product] if best_product else [],
            'comparison_table': {"summary": "Popularity-based selection"},
            'presentation_mode': 'single',
            'ai_message': f"📈 **Popular Choice Selected**\n\nFor your search: *{user_query}*\n\nSelected based on customer ratings and popularity.",
            'selection_reason': f"Fallback to popularity: {reason}",
            'metadata': {
                'model_used': 'PopularityFallback',
                'fallback_reason': reason,
                'processing_time_ms': 0,
                'selection_type': 'popularity_fallback'
            }
        }


def has_sufficient_technical_features(user_query: str, min_features: int = 2) -> bool:
    """
    Check if query has sufficient technical features for AI selection.
    
    Args:
    ----
        user_query: User's search query
        min_features: Minimum number of technical features required
        
    Returns:
    -------
        True if query has sufficient technical features
    """
    extractor = FeatureExtractor()
    features = extractor.extract_features(user_query, category="gaming_monitor")
    
    if not features:
        return False
    
    # Count actual technical features (exclude metadata)
    technical_features = [k for k in features.keys() if k not in ['confidence', 'processing_time_ms', 'technical_query', 'category_detected']]
    
    return len(technical_features) >= min_features


def get_smart_selection_strategy(
    user_query: str, 
    product_count: int, 
    enable_multi_card: bool = True
) -> str:
    """
    Determine the best selection strategy based on query and context.
    
    Args:
    ----
        user_query: User's search query
        product_count: Number of available products
        enable_multi_card: Whether multi-card is enabled
        
    Returns:
    -------
        Selection strategy: 'multi_card_ai', 'single_card_ai', 'popularity', 'random'
    """
    # Check for technical features
    has_tech_features = has_sufficient_technical_features(user_query)
    
    # Minimum product requirements
    if product_count < 3:
        return 'popularity' if product_count >= 2 else 'random'
    
    if not has_tech_features:
        return 'popularity'
    
    # AI selection strategies
    if enable_multi_card and product_count >= 5:
        return 'multi_card_ai'
    elif product_count >= 3:
        return 'single_card_ai'
    else:
        return 'popularity'


def generate_user_explanations(score_breakdown: Dict[str, Any], product_features: Dict[str, Any]) -> List[str]:
    """
    Convert technical scores to user-friendly explanations - Phase 3 Transparency

    Args:
        score_breakdown: Detailed score breakdown from hybrid scoring
        product_features: Extracted product features

    Returns:
        List of user-friendly explanation strings
    """
    explanations = []

    # Technical excellence explanations
    if score_breakdown["excellence_bonus"] > 0.1:
        refresh_rate = product_features.get("refresh_rate", 0)
        if refresh_rate >= 180:
            explanations.append("⚡ Blazing fast 180Hz+ refresh rate for ultra-smooth gaming")
        elif refresh_rate >= 144:
            explanations.append("⚡ Fast 144Hz+ refresh rate for smooth gaming performance")

        resolution = product_features.get("resolution", "").lower()
        if "4k" in resolution:
            explanations.append("🎯 Ultra-sharp 4K resolution for crystal clear visuals")
        elif "1440p" in resolution:
            explanations.append("🎯 High-quality QHD resolution for excellent clarity")

        size = product_features.get("size", 0)
        if 27 <= size <= 35:
            explanations.append("📺 Perfect size for gaming (27-35 inches)")

    # Value explanations
    if score_breakdown["value_score"] > 0.9:
        explanations.append("💰 Excellent value - outstanding performance for the price")
    elif score_breakdown["value_score"] > 0.8:
        explanations.append("💰 Great value proposition with solid performance")
    elif score_breakdown["value_score"] > 0.7:
        explanations.append("👍 Good value with reliable performance")

    # Budget explanations
    if score_breakdown["budget_score"] > 0.9:
        explanations.append("📊 Perfectly fits within your budget")
    elif score_breakdown["budget_score"] > 0.8:
        explanations.append("📊 Well within your budget range")
    elif score_breakdown["budget_score"] > 0.7:
        explanations.append("📊 Reasonable fit for your budget")
    elif score_breakdown["budget_score"] < 0.5:
        explanations.append("⚠️ Slightly over budget but excellent performance")

    # Technical performance explanations
    if score_breakdown["technical_score"] > 0.8:
        explanations.append("🏆 Top-tier technical specifications")
    elif score_breakdown["technical_score"] > 0.7:
        explanations.append("✅ Strong technical performance")

    # Brand and panel type bonuses
    panel_type = product_features.get("panel_type", "").lower()
    if "ips" in panel_type:
        explanations.append("🎨 IPS panel for accurate colors and wide viewing angles")

    brand = product_features.get("brand", "").lower()
    if brand in ["samsung", "lg", "asus", "msi", "acer"]:
        explanations.append(f"🏷️ Trusted {brand.title()} brand with good reputation")

    return explanations[:4]  # Limit to top 4 explanations


def extract_key_specs_text(product_features: Dict[str, Any]) -> str:
    """
    Extract key specifications for display in user messages - Phase 3 Transparency

    Args:
        product_features: Product features dictionary

    Returns:
        Formatted string of key specifications
    """
    specs = []

    # Size
    size = product_features.get("size", 0)
    if size:
        specs.append(f"{size}\"")

    # Resolution
    resolution = product_features.get("resolution", "")
    if resolution:
        specs.append(resolution.upper())

    # Refresh rate
    refresh_rate = product_features.get("refresh_rate", 0)
    if refresh_rate:
        specs.append(f"{refresh_rate}Hz")

    # Panel type
    panel_type = product_features.get("panel_type", "")
    if panel_type:
        specs.append(panel_type.upper())

    return " • ".join(specs) if specs else "Standard specifications"
