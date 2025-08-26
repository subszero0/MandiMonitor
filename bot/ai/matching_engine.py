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
            "price": 0.20,          # ±20% tolerance for price matching
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
            return self._empty_score("No features to compare")
        
        # Get category-specific weights
        weights = get_feature_weights(category)
        
        total_score = 0.0
        total_weight = 0.0
        matched_features = []
        mismatched_features = []
        missing_features = []
        feature_scores = {}
        
        # Score each user requirement
        for feature_name, user_value in user_features.items():
            # Skip metadata fields
            if feature_name in ["confidence", "processing_time_ms", "technical_query", 
                               "category_detected", "matched_features_count", "technical_density"]:
                continue
                
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
                # Feature missing from product
                missing_features.append(feature_name)
                # Apply partial penalty for missing important features
                if weight > 2.0:  # Important features
                    penalty_weight = weight * 0.3  # 30% penalty
                    total_weight += penalty_weight
        
        # Calculate final score
        final_score = total_score / total_weight if total_weight > 0 else 0.0
        
        # Generate explanation
        rationale = self._generate_rationale(
            matched_features, mismatched_features, missing_features, feature_scores
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
            
            # Score the product
            score_data = self.score_product(user_features, product_features, category)
            
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
                    
                    # Check if within tolerance tier
                    acceptable_rates = self.categorical_tolerance[feature_name].get(user_rate, [])
                    if product_rate in acceptable_rates:
                        # Calculate upgrade bonus (higher refresh rate is better)
                        if product_rate > user_rate:
                            return 0.95  # Slight bonus for upgrade
                        else:
                            return 0.85  # Acceptable downgrade
                            
                elif feature_name == "resolution":
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
        feature_scores: Dict[str, Dict[str, Any]]
    ) -> str:
        """Generate human-readable explanation for the score with detailed context."""
        explanations = []
        
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
                                matched_parts.append(f"resolution={product_val} (upgrade!)")
                            else:
                                matched_parts.append(f"resolution={product_val}")
                        else:
                            matched_parts.append(f"resolution={product_val}")
                    elif feature == "curvature":
                        matched_parts.append(f"curvature={product_val}")
                    elif feature == "panel_type":
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
