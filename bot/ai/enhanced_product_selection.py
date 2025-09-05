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


def safe_string_extract(value: Any, default: str = "") -> str:
    """
    Safely extract string value from potentially complex data structures.

    Handles cases where Amazon API returns nested dictionaries instead of simple strings.
    """
    if value is None:
        return default

    if isinstance(value, str):
        return value

    if isinstance(value, dict):
        # Try to extract from common dictionary structures
        if 'value' in value:
            return str(value['value'])
        # Fallback to string representation
        return str(value)

    # For any other type, convert to string
    try:
        return str(value)
    except Exception:
        return default


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
        self.max_cards = 5  # FIXED: Show 5 cards instead of 3
        self.min_products_for_ai = 3  # FIXED: Lowered from 5 to 3 to prevent popularity fallback
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

        # Count actual features (excluding metadata)
        metadata_keys = {'confidence', 'processing_time_ms', 'technical_query', 'matched_features_count', 'technical_density', 'category_detected', 'marketing_heavy'}
        actual_features = {k: v for k, v in user_features.items() if k not in metadata_keys}

        log.info(f"🔍 FEATURE_EXTRACTION: found {len(actual_features)} features (total keys: {len(user_features)})")
        
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
            scores = []
            for p in carousel_result['products']:
                # Try different possible score fields
                score = None

                # Check for direct score field
                if 'score' in p and p['score'] is not None:
                    score = p['score']
                # Check for hybrid_score
                elif 'hybrid_score' in p and p['hybrid_score'] is not None:
                    score = p['hybrid_score']
                # Check for scoring_breakdown final_score
                elif 'scoring_breakdown' in p and isinstance(p['scoring_breakdown'], dict):
                    if 'final_score' in p['scoring_breakdown']:
                        score = p['scoring_breakdown']['final_score']
                # Check if we can calculate from components
                elif 'scoring_breakdown' in p and isinstance(p['scoring_breakdown'], dict):
                    breakdown = p['scoring_breakdown']
                    if all(k in breakdown for k in ['technical_score', 'value_score', 'budget_score', 'excellence_score']):
                        # Recalculate using same weights as matching_engine
                        tech = breakdown['technical_score']
                        value = breakdown['value_score']
                        budget = breakdown['budget_score']
                        excellence = breakdown['excellence_score']
                        score = (tech * 0.45) + (value * 0.30) + (budget * 0.20) + (excellence * 0.05)

                if score is not None and isinstance(score, (int, float)) and score > 0:
                    scores.append(score)

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
        
        # DEBUG: Check carousel_result structure
        log.info(f"DEBUG: EnhancedFeatureMatchModel received carousel_result with {len(carousel_result.get('products', []))} products")
        products_from_carousel = carousel_result.get('products', [])
        if products_from_carousel:
            log.info(f"DEBUG: First product from carousel type: {type(products_from_carousel[0])}")
            log.info(f"DEBUG: First product from carousel keys: {list(products_from_carousel[0].keys()) if isinstance(products_from_carousel[0], dict) else 'Not a dict'}")

        # CRITICAL FIX: Validate carousel_result structure
        if not isinstance(carousel_result, dict):
            log.error(f"CRITICAL: carousel_result is not a dict: {type(carousel_result)}")
            # Fallback to single card
            best_product = products[0]
            best_score = {"score": 0, "confidence": 0, "rationale": "Data validation failure"}
            return self._create_single_card_result(best_product, best_score, user_query, user_features, metadata)
        
        carousel_products = carousel_result.get('products', [])
        carousel_comparison_table = carousel_result.get('comparison_table', {})
        
        # Validate products structure
        if not isinstance(carousel_products, list):
            log.error(f"CRITICAL: carousel_result['products'] is not a list: {type(carousel_products)}")
            best_product = products[0]
            best_score = {"score": 0, "confidence": 0, "rationale": "Data validation failure"}
            return self._create_single_card_result(best_product, best_score, user_query, user_features, metadata)
        
        # Validate comparison_table structure
        if not isinstance(carousel_comparison_table, dict):
            log.error(f"CRITICAL: carousel_result['comparison_table'] is not a dict: {type(carousel_comparison_table)}")
            # Force creation of proper comparison table
            carousel_comparison_table = {
                'headers': ['Feature', 'Product'],
                'key_differences': [],
                'strengths': {},
                'trade_offs': [],
                'summary': "Comparison data corrected due to validation failure"
            }
        
        # Validate each product in the list
        for i, product in enumerate(carousel_products):
            if not isinstance(product, dict):
                log.error(f"CRITICAL: carousel_products[{i}] is not a dict: {type(product)}")
                # Fallback to single card
                best_product = products[0]
                best_score = {"score": 0, "confidence": 0, "rationale": "Data validation failure"}
                return self._create_single_card_result(best_product, best_score, user_query, user_features, metadata)
        
        log.info(f"✅ VALIDATION: carousel_result structure validated successfully - {len(carousel_products)} products, comparison_table is dict")

        return {
            'selection_type': 'multi_card',
            'products': carousel_products,
            'comparison_table': carousel_comparison_table,
            'presentation_mode': carousel_result.get('presentation_mode', 'multi'),
            'ai_message': ai_message,
            'selection_reason': carousel_result.get('selection_reason', 'Multi-card comparison'),
            'metadata': {
                **carousel_result.get('ai_metadata', {}),
                **metadata,
                'user_features': len([k for k in user_features.keys() if k not in ['confidence', 'processing_time_ms']]),
                'model_used': 'EnhancedFeatureMatchModel',
                'model_name': 'EnhancedFeatureMatchModel',
                'multi_card_enabled': True,
                'validation_passed': True
            }
        }

    def _create_single_card_result(self, best_product: Dict, best_score: Dict, user_query: str, user_features: Dict, metadata: Dict) -> Dict:
        """Create a single card result with proper structure."""
        ai_message = f"🎯 **AI Analysis Complete**\\n\\nFor your search: *{user_query}*\\n\\nFound 1 excellent match based on your requirements."
        
        return {
            'selection_type': 'single_card',
            'products': [best_product],
            'comparison_table': {"summary": "Single best option - no comparison needed"},
            'presentation_mode': 'single',
            'ai_message': ai_message,
            'selection_reason': best_score.get('rationale', 'Best match found'),
            'metadata': {
                'model_used': 'EnhancedFeatureMatchModel',
                'model_name': 'EnhancedFeatureMatchModel',
                'ai_score': best_score.get('score', 0),
                'ai_confidence': best_score.get('confidence', 0),
                'matched_features': best_score.get('matched_features', []),
                'processing_time_ms': best_score.get('processing_time_ms', 0),
                'selection_type': 'single_card',
                'multi_card_enabled': False,
                'fallback_reason': 'data_validation_failure',
                **metadata
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
                'model_name': 'EnhancedFeatureMatchModel',  # FIX: Ensure model_name is set
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
            # Safely extract and convert rating_count to numeric
            rating_count_raw = product.get("rating_count", 0)
            try:
                rating_count = float(rating_count_raw) if rating_count_raw else 0
            except (ValueError, TypeError):
                rating_count = 0

            # Safely extract and convert avg_rating to numeric
            avg_rating_raw = product.get("average_rating", 0)
            try:
                avg_rating = float(avg_rating_raw) if avg_rating_raw else 0
            except (ValueError, TypeError):
                avg_rating = 0

            popularity_score = rating_count * avg_rating if rating_count > 0 and avg_rating > 0 else 0
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
                'model_name': 'PopularityFallback',  # FIX: Ensure model_name is set
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

        # Safely extract and convert size to numeric
        size_raw = product_features.get("size", 0)
        try:
            size = float(size_raw) if size_raw else 0
        except (ValueError, TypeError):
            size = 0

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
    panel_type = safe_string_extract(product_features.get("panel_type", "")).lower()
    if "ips" in panel_type:
        explanations.append("🎨 IPS panel for accurate colors and wide viewing angles")

    brand = safe_string_extract(product_features.get("brand", "")).lower()
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
