"""
Feature Matching Engine for scoring products based on feature alignment.

This engine implements the core scoring algorithm that matches user requirements
against product features and ranks products by relevance with explainability.

Key features:
- Weighted scoring based on category-specific feature importance
- Exact match vs partial match scoring with tolerance windows
- Tie-breaking logic for deterministic results  
- Explainable scoring with rationale generation
"""

import time
from typing import Dict, List, Tuple, Any, Optional
from logging import getLogger

from .vocabularies import get_feature_weights

log = getLogger(__name__)


class FeatureMatchingEngine:
    """Core engine for scoring products based on feature alignment."""

    def __init__(self):
        """Initialize the matching engine."""
        self.scoring_cache = {}  # Cache for performance
        
        # Tolerance windows for near-matches (percentage tolerance)
        self.tolerance_windows = {
            "refresh_rate": 0.15,   # ±15% tolerance for refresh rate (144Hz accepts 120-165Hz)
            "size": 0.10,           # ±10% tolerance for screen size (27" accepts 24-30")
            "price": 0.15,          # ±15% tolerance for price matching (stricter for value analysis)
        }
        
        # Penalty multipliers for mismatches
        self.mismatch_penalties = {
            "refresh_rate": 0.7,    # 30% penalty for refresh rate mismatch
            "size": 0.8,            # 20% penalty for size mismatch  
            "resolution": 0.6,      # 40% penalty for resolution mismatch
            "curvature": 0.9,       # 10% penalty for curvature mismatch
            "panel_type": 0.85,     # 15% penalty for panel type mismatch
        }
        
        # Special tolerance cases for categorical features
        self.categorical_tolerance = {
            "refresh_rate": {
                # Gaming-friendly refresh rate tiers
                60: [75, 120],      # 60Hz can accept 75Hz or 120Hz as upgrades
                75: [60, 120, 144], # 75Hz accepts 60Hz, 120Hz, 144Hz
                120: [75, 144],     # 120Hz accepts 75Hz or 144Hz
                144: [120, 165],    # 144Hz accepts 120Hz or 165Hz  
                165: [144, 240],    # 165Hz accepts 144Hz or 240Hz
                240: [165, 360],    # 240Hz accepts 165Hz or 360Hz
            },
            "resolution": {
                # Resolution upgrade paths
                "1080p": ["1440p"],  # 1080p can accept 1440p as upgrade
                "1440p": ["4k"],     # 1440p can accept 4K as upgrade
                "4k": [],            # 4K is top tier
            }
        }

    def score_product(
        self, 
        user_features: Dict[str, Any], 
        product_features: Dict[str, Any], 
        category: str = "gaming_monitor"
    ) -> Dict[str, Any]:
        """
        Calculate feature match score for a single product.
        
        Args:
        ----
            user_features: User requirements from query
            product_features: Product specifications  
            category: Product category for weight selection
            
        Returns:
        -------
            Dict with score and explanation:
            {
                "score": 0.85,
                "rationale": "Matched: refresh_rate=144Hz, size=27″",
                "matched_features": ["refresh_rate", "size"],
                "mismatched_features": ["resolution"],
                "missing_features": ["curvature"],
                "confidence": 0.9
            }
        """
        start_time = time.time()
        
        if not user_features or not product_features:
            log.warning(f"Empty features - user: {bool(user_features)}, product: {bool(product_features)}")
            log.warning(f"User features: {user_features}")
            log.warning(f"Product features: {product_features}")
            return self._empty_score("No features to compare")
        
        # Get category-specific weights
        weights = get_feature_weights(category)
        
        total_score = 0.0
        total_weight = 0.0
        matched_features = []
        mismatched_features = []
        missing_features = []
        feature_scores = {}
        
        # Handle usage context for better scoring when no technical specs provided
        usage_context = user_features.get("usage_context")
        if usage_context and len([k for k in user_features if k not in ["confidence", "processing_time_ms", "technical_query", 
                                  "category_detected", "matched_features_count", "technical_density", "category", "usage_context"]]) == 0:
            # No technical specs, but we have usage context - apply context-based scoring
            log.info(f"Applying usage context scoring for '{usage_context}'")
            final_score = self._calculate_usage_context_score(product_features, usage_context, category)
            
            return {
                "score": final_score,
                "rationale": f"Optimized for {usage_context} usage",
                "matched_features": ["usage_context"],
                "mismatched_features": [],
                "missing_features": [],
                "confidence": 0.6,  # Medium confidence for context-based scoring
                "processing_time_ms": (time.time() - start_time) * 1000
            }
        
        # Score each user requirement
        for feature_name, user_value in user_features.items():
                        # Skip pure metadata fields (not user requirements)
            if feature_name in ["confidence", "processing_time_ms", "technical_query",
                               "category_detected", "matched_features_count", "technical_density"]:
                continue

            # Include category and usage_context in scoring (they are user requirements)
            # These were previously skipped as metadata but should be scored
                
            weight = weights.get(feature_name, 1.0)
            total_weight += weight
            
            if feature_name in product_features:
                product_value = product_features[feature_name]
                
                # Calculate feature-specific score
                feature_score = self._calculate_feature_score(
                    user_value, product_value, feature_name
                )
                
                feature_scores[feature_name] = {
                    "score": feature_score,
                    "user_value": user_value,
                    "product_value": product_value,
                    "weight": weight
                }
                
                if feature_score >= 0.8:  # Strong match
                    matched_features.append(feature_name)
                elif feature_score < 0.5:  # Poor match
                    mismatched_features.append(feature_name)
                
                total_score += feature_score * weight
            else:
                # Feature missing from product - NO PENALTY (removed unfair scoring)
                missing_features.append(feature_name)
                # Note: Removed penalty system that created artificial score differences
        
        # Calculate final score
        if total_weight > 0:
            final_score = total_score / total_weight
            log.info(f"🎯 SCORING_BREAKDOWN: total_score={total_score:.3f}, total_weight={total_weight:.3f}, final={final_score:.3f}")
            log.info(f"   📊 Feature_scores: {feature_scores}")
            log.info(f"   ✅ Matched: {matched_features}, ❌ Missing: {missing_features}")
        else:
            # If no specific user requirements, use product quality scoring
            # This allows AI to rank products by their technical specifications
            final_score = self._calculate_product_quality_score(product_features, category)
            
            # Log detailed information for debugging
            log.warning(
                "Using product quality scoring (total_weight=0): features=%s, score=%.3f",
                list(product_features.keys()) if product_features else "none",
                final_score
            )
        
        # Generate explanation with usage context
        rationale = self._generate_rationale(
            matched_features, mismatched_features, missing_features, feature_scores, usage_context
        )
        
        # Calculate confidence based on feature coverage
        confidence = self._calculate_match_confidence(
            user_features, matched_features, mismatched_features, missing_features
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        result = {
            "score": final_score,
            "rationale": rationale,
            "matched_features": matched_features,
            "mismatched_features": mismatched_features, 
            "missing_features": missing_features,
            "feature_scores": feature_scores,
            "confidence": confidence,
            "processing_time_ms": processing_time
        }
        
        log.debug(
            "Scored product: %.3f score, %d/%d features matched, %.1fms",
            final_score, len(matched_features), len(user_features), processing_time
        )
        
        return result

    async def score_products(
        self,
        user_features: Dict[str, Any],
        products: List[Dict[str, Any]],
        category: str = "gaming_monitor"
    ) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
        """
        Score multiple products and return sorted by relevance.
        
        Args:
        ----
            user_features: User requirements
            products: List of product data dicts
            category: Product category
            
        Returns:
        -------
            List of (product, score_data) tuples sorted by score (highest first)
        """
        if not products:
            return []
        
        scored_products = []
        
        for product in products:
            # Extract product features using Phase 2 analyzer
            product_features = await self._extract_product_features(product)
            
            # Score the product using hybrid scoring system (Phase 2)
            hybrid_score, detailed_breakdown = self.calculate_hybrid_score(user_features, product_features, category)

            # Create score_data compatible with existing system
            score_data = {
                "score": hybrid_score,
                "rationale": f"Hybrid Score: {hybrid_score:.3f}",
                "matched_features": ["hybrid_scoring"],  # Placeholder
                "mismatched_features": [],
                "missing_features": [],
                "confidence": detailed_breakdown.get("technical_score", 0.5),
                "feature_scores": detailed_breakdown,
                "hybrid_breakdown": detailed_breakdown
            }
            
            scored_products.append((product, score_data))
        
        # Sort by score (highest first), with sophisticated tie-breaking
        scored_products.sort(
            key=lambda x: (
                x[1]["score"],                              # Primary: AI feature match score
                x[1]["confidence"],                         # Secondary: confidence in matching
                len(x[1]["matched_features"]),              # Tertiary: number of matched features
                self._get_popularity_score(x[0]),           # Quaternary: product popularity
                self._get_price_tier_score(x[0]),           # Quinary: price positioning
                -len(x[1]["missing_features"]),             # Senary: fewer missing features
                x[0].get("asin", "")                       # Final: ASIN for determinism
            ),
            reverse=True
        )
        
        log.info(
            "Scored %d products, top score: %.3f, avg: %.3f",
            len(scored_products),
            scored_products[0][1]["score"] if scored_products else 0,
            sum(p[1]["score"] for p in scored_products) / len(scored_products) if scored_products else 0
        )
        
        return scored_products

    def _calculate_feature_score(
        self, 
        user_value: Any, 
        product_value: Any, 
        feature_name: str
    ) -> float:
        """Calculate similarity score for a specific feature with advanced tolerance logic."""
        if not user_value or not product_value:
            return 0.0
        
        user_str = str(user_value).lower().strip()
        product_str = str(product_value).lower().strip()
        
        # Exact match
        if user_str == product_str:
            return 1.0
        
        # Special handling for categorical tolerance (like refresh rate tiers)
        if feature_name in self.categorical_tolerance:
            try:
                if feature_name == "refresh_rate":
                    user_rate = int(user_str)
                    product_rate = int(product_str)

                    # 🎯 EXACT MATCH: Same refresh rate gets perfect score
                    if user_rate == product_rate:
                        return 1.0

                    # Check if within tolerance tier
                    acceptable_rates = self.categorical_tolerance[feature_name].get(user_rate, [])
                    if product_rate in acceptable_rates:
                        # Calculate upgrade bonus (higher refresh rate is better)
                        if product_rate > user_rate:
                            return 0.95  # Slight bonus for upgrade
                        else:
                            return 0.85  # Acceptable downgrade
                            
                elif feature_name == "resolution":
                    # 🎯 EXACT MATCH: Same resolution gets perfect score
                    if user_str == product_str:
                        return 1.0

                    acceptable_resolutions = self.categorical_tolerance[feature_name].get(user_str, [])
                    if product_str in acceptable_resolutions:
                        return 0.90  # Resolution upgrade is good
                        
            except (ValueError, KeyError):
                pass  # Fall through to numeric tolerance
        
        # Numeric features with percentage tolerance
        if feature_name in self.tolerance_windows:
            try:
                user_num = float(user_str)
                product_num = float(product_str)
                
                tolerance = self.tolerance_windows[feature_name]
                diff_ratio = abs(user_num - product_num) / user_num
                
                if diff_ratio <= tolerance:
                    # Within tolerance - high score with graduated penalty
                    score = 1.0 - (diff_ratio / tolerance) * 0.15  # Max 15% penalty within tolerance
                    return max(0.85, score)  # Minimum 85% score for tolerance matches
                else:
                    # Outside tolerance - apply mismatch penalty
                    penalty = self.mismatch_penalties.get(feature_name, 0.5)
                    # Gradual penalty based on how far outside tolerance
                    distance_penalty = min(1.0, diff_ratio / tolerance - 1.0)
                    return penalty * (1.0 - distance_penalty * 0.5)
                    
            except ValueError:
                pass  # Fall through to string matching
        
        # String similarity for categorical features  
        if user_str in product_str or product_str in user_str:
            return 0.75  # Good partial match
        
        # Brand/keyword matching
        user_words = set(user_str.split())
        product_words = set(product_str.split())
        common_words = user_words & product_words
        
        if common_words:
            overlap_ratio = len(common_words) / max(len(user_words), len(product_words))
            return overlap_ratio * 0.6  # Keyword overlap
        
        # Apply mismatch penalty for complete mismatch
        penalty = self.mismatch_penalties.get(feature_name, 0.3)
        return penalty * 0.1  # Very low score for complete mismatch

    def _generate_rationale(
        self,
        matched: List[str],
        mismatched: List[str],
        missing: List[str],
        feature_scores: Dict[str, Dict[str, Any]],
        usage_context: str = None
    ) -> str:
        """Generate human-readable explanation for the score with detailed context."""
        explanations = []

        # Add context-specific introduction
        if usage_context == "coding":
            if matched:
                explanations.append("💻 Perfect for coding: High resolution, accurate colors")
            else:
                explanations.append("💻 Coding monitor: Focus on IPS panel, 1440p resolution")
        elif usage_context == "gaming":
            if matched:
                explanations.append("🎮 Gaming optimized: High refresh rate, fast response")
            else:
                explanations.append("🎮 Gaming monitor: Prioritizes refresh rate and response time")
        elif usage_context == "professional":
            if matched:
                explanations.append("💼 Professional grade: 4K resolution, color accuracy")
            else:
                explanations.append("💼 Professional monitor: Focus on resolution and color fidelity")
        
        # Add matched features with quality indicators
        if matched:
            matched_parts = []
            for feature in matched:
                if feature in feature_scores:
                    score_data = feature_scores[feature]
                    user_val = score_data["user_value"]
                    product_val = score_data["product_value"]
                    score = score_data["score"]
                    
                    # Format feature with quality indicator
                    if feature == "refresh_rate":
                        if score >= 0.95:
                            if int(product_val) > int(user_val):
                                matched_parts.append(f"refresh_rate={product_val}Hz (upgrade!)")
                            else:
                                matched_parts.append(f"refresh_rate={product_val}Hz (exact)")
                        elif score >= 0.85:
                            matched_parts.append(f"refresh_rate={product_val}Hz (close)")
                        else:
                            matched_parts.append(f"refresh_rate={product_val}Hz")
                    elif feature == "size":
                        if score >= 0.95:
                            matched_parts.append(f"size={product_val}″ (exact)")
                        elif score >= 0.85:
                            matched_parts.append(f"size={product_val}″ (close)")
                        else:
                            matched_parts.append(f"size={product_val}″")
                    elif feature == "resolution":
                        if score >= 0.90:
                            if product_val in ["4k", "1440p"] and user_val in ["1080p", "1440p"]:
                                if usage_context == "coding":
                                    matched_parts.append(f"{product_val} resolution (perfect for coding - sharp text)")
                                elif usage_context == "professional":
                                    matched_parts.append(f"{product_val} resolution (professional grade clarity)")
                                else:
                                    matched_parts.append(f"resolution={product_val} (upgrade!)")
                            else:
                                matched_parts.append(f"resolution={product_val}")
                        else:
                            matched_parts.append(f"resolution={product_val}")
                    elif feature == "curvature":
                        matched_parts.append(f"curvature={product_val}")
                    elif feature == "panel_type":
                        if usage_context == "coding" and product_val.lower() == "ips":
                            matched_parts.append(f"IPS panel (ideal for coding - accurate colors)")
                        elif usage_context == "gaming" and product_val.lower() in ["tn", "va"]:
                            matched_parts.append(f"{product_val.upper()} panel (fast response for gaming)")
                        else:
                            matched_parts.append(f"panel={product_val.upper()}")
                    elif feature == "brand":
                        matched_parts.append(f"brand={product_val.title()}")
                    else:
                        matched_parts.append(f"{feature}={product_val}")
            
            if matched_parts:
                explanations.append(f"✓ {', '.join(matched_parts)}")
        
        # Add tolerance matches (scored 0.8-0.95)
        tolerance_matches = []
        for feature, score_data in feature_scores.items():
            score = score_data["score"]
            if 0.8 <= score < 0.95 and feature not in matched:
                user_val = score_data["user_value"]
                product_val = score_data["product_value"]
                if feature == "refresh_rate":
                    tolerance_matches.append(f"refresh_rate={product_val}Hz (vs {user_val}Hz)")
                elif feature == "size":
                    tolerance_matches.append(f"size={product_val}″ (vs {user_val}″)")
                else:
                    tolerance_matches.append(f"{feature}={product_val}")
        
        if tolerance_matches:
            explanations.append(f"≈ {', '.join(tolerance_matches)}")
        
        # Add significant mismatches only (not minor ones)
        if mismatched:
            significant_mismatches = []
            for feature in mismatched:
                if feature in feature_scores:
                    score_data = feature_scores[feature]
                    score = score_data["score"]
                    if score < 0.5:  # Only show significant mismatches
                        user_val = score_data["user_value"]  
                        product_val = score_data["product_value"]
                        significant_mismatches.append(f"{feature}: {user_val}→{product_val}")
            
            if significant_mismatches:
                explanations.append(f"✗ {', '.join(significant_mismatches)}")
        
        # Add missing critical features only
        critical_missing = [f for f in missing if f in ["refresh_rate", "size", "resolution"]]
        if critical_missing:
            explanations.append(f"? Missing: {', '.join(critical_missing)}")
        
        return " • ".join(explanations) if explanations else "No clear feature alignment"

    def _calculate_match_confidence(
        self,
        user_features: Dict[str, Any],
        matched: List[str],
        mismatched: List[str], 
        missing: List[str]
    ) -> float:
        """Calculate confidence in the feature matching."""
        # Count meaningful features (exclude metadata)
        meaningful_features = [
            f for f in user_features.keys() 
            if f not in ["confidence", "processing_time_ms", "technical_query", 
                        "category_detected", "matched_features_count", "technical_density"]
        ]
        
        if not meaningful_features:
            return 0.0
        
        total_features = len(meaningful_features)
        match_score = len(matched) / total_features
        mismatch_penalty = len(mismatched) / total_features * 0.5
        missing_penalty = len(missing) / total_features * 0.3
        
        confidence = match_score - mismatch_penalty - missing_penalty
        return max(0.0, min(1.0, confidence))

    async def _extract_product_features(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract features from product data using ProductFeatureAnalyzer.
        
        This integrates with Phase 2 implementation for proper feature extraction.
        """
        from .product_analyzer import ProductFeatureAnalyzer
        
        analyzer = ProductFeatureAnalyzer()
        feature_result = await analyzer.analyze_product_features(product, "gaming_monitor")
        
        # Extract just the values from the feature analysis result
        features = {}
        for feature_name, feature_data in feature_result.items():
            if isinstance(feature_data, dict) and "value" in feature_data:
                features[feature_name] = feature_data["value"]
            elif feature_name not in ["overall_confidence", "extraction_metadata"]:
                # Handle direct value assignment
                features[feature_name] = feature_data
        
        return features

    def _empty_score(self, reason: str) -> Dict[str, Any]:
        """Return empty score result with reason."""
        return {
            "score": 0.0,
            "rationale": reason,
            "matched_features": [],
            "mismatched_features": [],
            "missing_features": [],
            "feature_scores": {},
            "confidence": 0.0,
            "processing_time_ms": 0.0
        }

    def explain_scoring(
        self, 
        score_result: Dict[str, Any], 
        user_features: Dict[str, Any]
    ) -> str:
        """
        Generate detailed scoring explanation for debugging.
        
        Args:
        ----
            score_result: Result from score_product()
            user_features: Original user requirements
            
        Returns:
        -------
            Detailed explanation string
        """
        lines = [
            f"Feature Matching Score: {score_result['score']:.3f}",
            f"Confidence: {score_result['confidence']:.3f}",
            f"Processing Time: {score_result['processing_time_ms']:.1f}ms",
            "",
            "Feature Breakdown:"
        ]
        
        feature_scores = score_result.get("feature_scores", {})
        for feature, score_data in feature_scores.items():
            score = score_data["score"]
            weight = score_data["weight"]  
            user_val = score_data["user_value"]
            product_val = score_data["product_value"]
            
            lines.append(
                f"  {feature}: {score:.3f} (weight: {weight:.1f}) "
                f"[{user_val} → {product_val}]"
            )
        
        if score_result["missing_features"]:
            lines.append(f"Missing: {', '.join(score_result['missing_features'])}")
        
        lines.append("")
        lines.append(f"Rationale: {score_result['rationale']}")
        
        return "\n".join(lines)
    
    def _get_popularity_score(self, product: Dict[str, Any]) -> float:
        """
        Calculate popularity score for tie-breaking.
        
        Uses rating count, average rating, and sales rank if available.
        """
        popularity = 0.0
        
        # Rating count (more reviews = more popular)
        rating_count = product.get("rating_count", 0)
        if isinstance(rating_count, (int, float)) and rating_count > 0:
            # Logarithmic scaling for rating count (diminishing returns)
            import math
            popularity += min(0.4, math.log10(rating_count + 1) / 4)
        
        # Average rating (higher rating = better)
        avg_rating = product.get("average_rating", 0)
        if isinstance(avg_rating, (int, float)) and avg_rating > 0:
            # Normalize to 0-0.3 scale (4.5+ stars get full score)
            popularity += min(0.3, (avg_rating - 3.0) / 2.0 * 0.3)
        
        # Sales rank (lower rank = more popular)
        sales_rank = product.get("sales_rank")
        if isinstance(sales_rank, (int, float)) and sales_rank > 0:
            # Inverse logarithmic scaling (rank 1 = 0.3, rank 10000 = ~0.1)
            import math
            popularity += max(0.0, 0.3 - math.log10(sales_rank) / 4 * 0.2)
        
        return min(1.0, popularity)
    
    def _get_price_tier_score(self, product: Dict[str, Any]) -> float:
        """
        Calculate price tier score for tie-breaking.
        
        Favors products in the value/premium range over ultra-budget or ultra-premium.
        """
        price = product.get("price")
        if not price:
            return 0.5  # Neutral score for missing price
        
        # Extract numeric price (handle currency symbols)
        import re
        price_str = str(price)
        price_match = re.search(r'[\d,]+\.?\d*', price_str.replace(',', ''))
        if not price_match:
            return 0.5
        
        try:
            price_value = float(price_match.group())
        except ValueError:
            return 0.5
        
        # Gaming monitor price tiers (adjust for other categories)
        if price_value < 5000:      # Budget (<₹5k)
            return 0.3
        elif price_value < 15000:   # Value (₹5k-15k)
            return 0.8
        elif price_value < 35000:   # Premium (₹15k-35k)
            return 1.0
        elif price_value < 60000:   # High-end (₹35k-60k)
            return 0.7
        else:                       # Ultra-premium (>₹60k)
            return 0.4
    
    def add_tie_breaking_context(
        self, 
        scored_products: List[Tuple[Dict[str, Any], Dict[str, Any]]]
    ) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
        """
        Add tie-breaking context to scored products for debugging.
        
        Useful for understanding why products were ranked in a specific order.
        """
        for product, score_data in scored_products:
            score_data["tie_breaking"] = {
                "popularity_score": self._get_popularity_score(product),
                "price_tier_score": self._get_price_tier_score(product),
                "rating_count": product.get("rating_count", 0),
                "avg_rating": product.get("average_rating", 0),
                "price": product.get("price", "N/A")
            }
        
        return scored_products

    async def select_products_for_carousel(
        self,
        user_features: Dict[str, Any],
        products: List[Dict[str, Any]],
        category: str = "gaming_monitor",
        max_cards: int = 3
    ) -> Dict[str, Any]:
        """
        Select products for multi-card carousel with comparison features.
        
        This is the main entry point for Phase 6 multi-card selection.
        
        Args:
        ----
            user_features: User requirements from query
            products: List of product data dicts
            category: Product category
            max_cards: Maximum number of cards to show
            
        Returns:
        -------
            Dict with products, comparison table, and presentation mode
        """
        # Score all products first
        scored_products = await self.score_products(user_features, products, category)
        
        if not scored_products:
            return {
                'products': [],
                'comparison_table': {"error": "No products available"},
                'selection_reason': "No products found to score",
                'presentation_mode': 'none',
                'ai_metadata': {
                    'selection_type': 'empty',
                    'card_count': 0,
                    'processing_time_ms': 0
                }
            }
        
        # Use MultiCardSelector for intelligent selection
        from .multi_card_selector import MultiCardSelector
        selector = MultiCardSelector()
        
        result = await selector.select_products_for_comparison(
            scored_products=scored_products,
            user_features=user_features,
            max_cards=max_cards
        )
        
        return result
    
    def _calculate_product_quality_score(self, product_features: Dict[str, Any], category: str) -> float:
        """
        Calculate product quality score when no specific user requirements exist.
        
        This allows the AI to rank products by their technical specifications
        and help users discover good options even with simple queries.
        """
        if not product_features:
            log.debug("No product features available for quality scoring")
            return 0.1  # Minimal score for products with no features
        
        weights = get_feature_weights(category)
        quality_score = 0.0
        total_weight = 0.0
        scored_features = {}
        
        # Score based on technical feature quality
        for feature_name, weight in weights.items():
            if feature_name in product_features:
                feature_value = product_features[feature_name]
                
                # Handle structured feature data format
                if isinstance(feature_value, dict) and "value" in feature_value:
                    actual_value = feature_value["value"]
                else:
                    actual_value = feature_value
                
                # Calculate quality score for different feature types
                feature_quality = self._calculate_feature_quality(feature_name, actual_value)
                quality_score += feature_quality * weight
                total_weight += weight
                scored_features[feature_name] = {
                    "value": actual_value,
                    "quality": feature_quality,
                    "weight": weight,
                    "contribution": feature_quality * weight
                }
        
        # Normalize score and add base quality for having features
        base_score = min(len(product_features) * 0.05, 0.3)  # Up to 0.3 for having many features
        normalized_score = quality_score / total_weight if total_weight > 0 else 0.0
        
        final_score = base_score + (normalized_score * 0.7)  # 30% base + 70% weighted quality
        
        # Debug logging
        log.debug(
            "Quality scoring: base=%.3f, normalized=%.3f, final=%.3f, features=%s",
            base_score, normalized_score, final_score, scored_features
        )
        
        return min(final_score, 1.0)  # Cap at 1.0

    def calculate_hybrid_score(self, user_features: Dict[str, Any], product_features: Dict[str, Any], category: str = "gaming_monitor") -> Tuple[float, Dict[str, Any]]:
        """
        Calculate hybrid score combining technical performance, value ratio, budget adherence, and excellence bonuses.

        Returns:
            Tuple of (final_score, detailed_breakdown)
        """
        start_time = time.time()

        # 1. Calculate pure technical score
        tech_score = self.score_product(user_features, product_features, category)

        # 2. Calculate value ratio score (performance per rupee)
        value_score = self._calculate_value_ratio_score(product_features, user_features)

        # 3. Calculate budget adherence score
        budget_score = self._calculate_budget_adherence_score(product_features, user_features)

        # 4. Apply technical excellence bonus
        excellence_bonus = self._calculate_excellence_bonus(tech_score, product_features)

        # 5. Context-aware weighting (gaming vs general)
        weights = self._get_context_weights(user_features, category)

        # 6. Calculate final weighted score
        final_score = (
            tech_score * weights["technical"] +
            value_score * weights["value"] +
            budget_score * weights["budget"] +
            excellence_bonus * weights["excellence"]
        )

        # Ensure final score is within bounds
        final_score = max(0.0, min(1.0, final_score))

        # Create detailed breakdown
        detailed_breakdown = {
            "technical_score": tech_score,
            "value_score": value_score,
            "budget_score": budget_score,
            "excellence_bonus": excellence_bonus,
            "weights_used": weights,
            "final_score": final_score,
            "processing_time_ms": (time.time() - start_time) * 1000
        }

        # Enhanced transparency logging - Phase 3
        product_title = product_features.get('title', 'Unknown Product')[:50]  # Truncate long titles
        usage_context = user_features.get('usage_context', '').lower()
        context_type = 'Gaming' if 'gaming' in usage_context else 'General'

        log.info(f"🎯 HYBRID_SCORE_BREAKDOWN: {final_score:.3f} for '{product_title}'")
        log.info(f"   📊 Components: Tech={tech_score:.3f} | Value={value_score:.3f} | Budget={budget_score:.3f} | Excellence={excellence_bonus:.3f}")
        log.info(f"   ⚖️ Weights: Tech={weights['technical']:.0%} | Value={weights['value']:.0%} | Budget={weights['budget']:.0%} | Excellence={weights['excellence']:.0%}")
        log.info(f"   💰 Price: ₹{product_features.get('price', 0):,} | Tech Performance: {self._calculate_technical_performance(product_features):.3f}")
        log.info(f"   🎮 Context: {context_type} | User Query: '{user_features.get('original_query', 'N/A')[:30]}'")
        log.info(f"   📈 Final Calculation: ({tech_score:.3f}×{weights['technical']:.3f}) + ({value_score:.3f}×{weights['value']:.3f}) + ({budget_score:.3f}×{weights['budget']:.3f}) + ({excellence_bonus:.3f}×{weights['excellence']:.3f}) = {final_score:.3f}")

        return final_score, detailed_breakdown

    def _calculate_value_ratio_score(self, product_features: Dict[str, Any], user_features: Dict[str, Any]) -> float:
        """Calculate performance-per-rupee score to reward better value"""
        price = product_features.get("price", 0)
        if not price or price <= 0:
            return 0.5  # Neutral score for missing price

        # Get technical performance score (0-1)
        tech_performance = self._calculate_technical_performance(product_features)

        # Value ratio = performance / price (normalized per ₹1000)
        value_ratio = tech_performance / (price / 1000)

        # Normalize to 0-1 scale (assume max expected ratio is ~0.8 for top products)
        max_expected_ratio = 0.8
        normalized_value = min(1.0, value_ratio / max_expected_ratio)

        log.debug(f"💰 VALUE_RATIO: price=₹{price}, tech_perf={tech_performance:.3f}, ratio={value_ratio:.3f}, score={normalized_value:.3f}")
        return normalized_value

    def _calculate_budget_adherence_score(self, product_features: Dict[str, Any], user_features: Dict[str, Any]) -> float:
        """Calculate how well product fits within user's budget"""
        product_price = product_features.get("price", 0)
        user_budget = user_features.get("max_price") or user_features.get("budget")

        if not product_price or not user_budget:
            return 0.7  # Neutral score when budget info missing

        ratio = product_price / user_budget

        if ratio <= 0.6: return 1.0      # Excellent value (60% of budget)
        elif ratio <= 0.8: return 0.9    # Good value (80% of budget)
        elif ratio <= 0.9: return 0.8    # Acceptable (90% of budget)
        elif ratio <= 1.0: return 0.7    # At budget limit
        elif ratio <= 1.2: return 0.5    # Slightly over budget
        elif ratio <= 1.5: return 0.3    # Moderately over budget
        else: return 0.2                 # Significantly over budget

    def _calculate_excellence_bonus(self, tech_score: float, product_features: Dict[str, Any]) -> float:
        """Apply bonuses for superior specifications"""
        bonus = 0.0

        # Refresh rate excellence
        refresh_rate = product_features.get("refresh_rate", 0)
        if refresh_rate >= 240: bonus += 0.15  # 240Hz+ excellence
        elif refresh_rate >= 165: bonus += 0.10  # 165Hz+ very good
        elif refresh_rate >= 144: bonus += 0.05  # 144Hz+ good

        # Resolution excellence
        resolution = product_features.get("resolution", "")
        if "4k" in resolution.lower(): bonus += 0.10
        elif "1440p" in resolution.lower(): bonus += 0.05

        # Size appropriateness (27-35" optimal for gaming)
        size = product_features.get("size", 0)
        if 27 <= size <= 35: bonus += 0.05  # Optimal gaming size range

        # Cap excellence bonus at 25%
        final_bonus = min(0.25, bonus)
        log.debug(f"🏆 EXCELLENCE_BONUS: refresh={refresh_rate}Hz, resolution={resolution}, size={size}\", bonus={final_bonus:.3f}")
        return final_bonus

    def _get_context_weights(self, user_features: Dict[str, Any], category: str) -> Dict[str, float]:
        """Get context-appropriate weights based on usage"""
        usage_context = user_features.get("usage_context", "").lower()

        if "gaming" in usage_context or category == "gaming_monitor":
            return {
                "technical": 0.45,  # High technical priority for gaming
                "value": 0.30,      # Value matters for gamers
                "budget": 0.20,     # Budget consideration
                "excellence": 0.05  # Excellence bonus
            }
        else:
            return {
                "technical": 0.35,  # Moderate technical priority
                "value": 0.40,      # Value more important for general use
                "budget": 0.20,     # Budget consideration
                "excellence": 0.05  # Excellence bonus
            }

    def _calculate_technical_performance(self, product_features: Dict[str, Any]) -> float:
        """Calculate overall technical performance score (0-1)"""
        performance_score = 0.0
        weights_used = 0

        # Refresh rate performance (high weight for gaming)
        refresh_rate = product_features.get("refresh_rate", 0)
        if refresh_rate >= 240: refresh_perf = 1.0
        elif refresh_rate >= 165: refresh_perf = 0.8
        elif refresh_rate >= 144: refresh_perf = 0.7
        elif refresh_rate >= 120: refresh_perf = 0.6
        elif refresh_rate >= 75: refresh_perf = 0.4
        else: refresh_perf = 0.2

        performance_score += refresh_perf * 0.4  # 40% weight
        weights_used += 0.4

        # Resolution performance
        resolution = product_features.get("resolution", "").lower()
        if "4k" in resolution: res_perf = 1.0
        elif "1440p" in resolution: res_perf = 0.8
        elif "1080p" in resolution: res_perf = 0.6
        else: res_perf = 0.4

        performance_score += res_perf * 0.3  # 30% weight
        weights_used += 0.3

        # Size appropriateness
        size = product_features.get("size", 0)
        if 24 <= size <= 40:  # Reasonable size range
            size_perf = 1.0
        elif 20 <= size <= 50:  # Acceptable range
            size_perf = 0.8
        else:
            size_perf = 0.5

        performance_score += size_perf * 0.2  # 20% weight
        weights_used += 0.2

        # Panel type bonus
        panel = product_features.get("panel_type", "").lower()
        if "ips" in panel: panel_perf = 0.1
        elif "va" in panel: panel_perf = 0.05
        else: panel_perf = 0.0

        performance_score += panel_perf * 0.1  # 10% weight
        weights_used += 0.1

        final_performance = performance_score / weights_used if weights_used > 0 else 0.5
        return min(1.0, final_performance)
    
    def _calculate_feature_quality(self, feature_name: str, feature_value: Any) -> float:
        """Calculate quality score for a specific feature."""
        if not feature_value:
            return 0.0
        
        try:
            value_str = str(feature_value).lower().strip()
            
            if feature_name == "refresh_rate":
                # Higher refresh rates are better for gaming
                # Extract numeric value
                import re
                match = re.search(r'(\d+)', value_str)
                if match:
                    rate = int(match.group(1))
                    if rate >= 240: return 1.0
                    elif rate >= 165: return 0.9
                    elif rate >= 144: return 0.8
                    elif rate >= 120: return 0.6
                    elif rate >= 75: return 0.4
                    else: return 0.2
                return 0.2  # Default for unmatched
                
            elif feature_name == "resolution":
                # Higher resolutions are generally better
                if any(x in value_str for x in ["4k", "uhd", "2160p"]): return 1.0
                elif any(x in value_str for x in ["1440p", "qhd", "wqhd"]): return 0.8
                elif any(x in value_str for x in ["1080p", "fhd", "full hd"]): return 0.6
                elif any(x in value_str for x in ["720p", "hd"]): return 0.4
                # Try to match pixel dimensions
                import re
                pixel_match = re.search(r'(\d+)\s*x\s*(\d+)', value_str)
                if pixel_match:
                    width = int(pixel_match.group(1))
                    if width >= 3840: return 1.0
                    elif width >= 2560: return 0.8
                    elif width >= 1920: return 0.6
                    else: return 0.4
                return 0.4  # Default for unmatched
                
            elif feature_name == "size":
                # Moderate sizes are preferred (24-32 inches)
                import re
                size_match = re.search(r'(\d+(?:\.\d+)?)', value_str)
                if size_match:
                    size = float(size_match.group(1))
                    # Handle cm to inch conversion
                    if size > 50:  # Likely cm
                        size = size / 2.54
                    if 27 <= size <= 32: return 1.0
                    elif 24 <= size < 27: return 0.8
                    elif 21 <= size < 24: return 0.6
                    else: return 0.4
                return 0.4  # Default for unmatched
                
            elif feature_name == "curvature":
                # Curved is a feature preference
                return 0.7 if "curved" in value_str else 0.5
                
            elif feature_name == "panel_type":
                # IPS > VA > TN for general use
                if "ips" in value_str: return 1.0
                elif "va" in value_str: return 0.7
                elif "tn" in value_str: return 0.5
                elif any(x in value_str for x in ["oled", "qled"]): return 0.9
                else: return 0.6
                
            elif feature_name == "brand":
                # All brands get equal quality score (preference is subjective)
                known_brands = ["samsung", "lg", "dell", "asus", "acer", "msi", "benq", "viewsonic", "aoc", "hp", "lenovo"]
                return 0.8 if any(brand in value_str for brand in known_brands) else 0.5
                
            else:
                # Default quality for other features that have values
                return 0.6
                
        except (ValueError, TypeError) as e:
            log.debug(f"Error calculating feature quality for {feature_name}={feature_value}: {e}")
            return 0.3  # Some quality for unparseable features

    def _calculate_usage_context_score(self, product_features: Dict[str, Any], usage_context: str, category: str) -> float:
        """
        Calculate score based on usage context when no specific technical requirements are provided.
        
        This provides meaningful product differentiation for simple queries like "coding monitor".
        """
        if not product_features:
            return 0.1
        
        # Define context-specific preferences
        context_preferences = {
            "coding": {
                "resolution": {"1440p": 0.9, "4k": 0.8, "1080p": 0.6},  # Higher resolution preferred
                "size": {"27": 0.9, "24": 0.8, "32": 0.7},  # Medium-large sizes
                "panel_type": {"ips": 0.9, "va": 0.7, "tn": 0.5},  # IPS for accurate colors
                "refresh_rate": {"60": 0.8, "75": 0.9, "144": 0.7}  # Don't need super high refresh
            },
            "gaming": {
                "refresh_rate": {"144": 0.9, "120": 0.8, "240": 1.0},  # High refresh preferred
                "resolution": {"1440p": 0.9, "1080p": 0.8, "4k": 0.7},  # Balance of performance
                "panel_type": {"tn": 0.8, "ips": 0.9, "va": 0.7}
            },
            "professional": {
                "resolution": {"4k": 1.0, "1440p": 0.8, "1080p": 0.5},  # Highest resolution
                "size": {"27": 0.8, "32": 0.9, "24": 0.6},  # Larger screens
                "panel_type": {"ips": 1.0, "va": 0.6, "tn": 0.3}  # Color accuracy critical
            }
        }
        
        preferences = context_preferences.get(usage_context, context_preferences.get("coding", {}))
        
        score = 0.0
        total_features = 0
        
        for feature_name, feature_prefs in preferences.items():
            if feature_name in product_features:
                product_value = product_features[feature_name]
                
                # Handle structured feature data
                if isinstance(product_value, dict) and "value" in product_value:
                    actual_value = str(product_value["value"]).lower()
                else:
                    actual_value = str(product_value).lower()
                
                # Find matching preference
                feature_score = 0.0
                for pref_value, pref_score in feature_prefs.items():
                    if pref_value.lower() in actual_value:
                        feature_score = max(feature_score, pref_score)
                
                score += feature_score
                total_features += 1
        
        # Add base quality score for having features
        base_score = min(len(product_features) * 0.02, 0.3)
        
        # Calculate final score
        if total_features > 0:
            avg_score = score / total_features
            final_score = base_score + (avg_score * 0.7)
        else:
            # No matching features, use product quality scoring
            final_score = self._calculate_product_quality_score(product_features, category)
        
        log.debug(f"Usage context scoring for '{usage_context}': {total_features} features, score={final_score:.3f}")
        
        return min(1.0, max(0.1, final_score))