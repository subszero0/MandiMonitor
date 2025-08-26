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
        
        # Tolerance windows for near-matches
        self.tolerance_windows = {
            "refresh_rate": 0.1,   # ±10% tolerance for refresh rate
            "size": 0.05,          # ±5% tolerance for screen size
            "price": 0.15,         # ±15% tolerance for price matching
        }
        
        # Penalty multipliers for mismatches
        self.mismatch_penalties = {
            "refresh_rate": 0.8,   # 20% penalty for refresh rate mismatch
            "size": 0.9,           # 10% penalty for size mismatch
            "resolution": 0.7,     # 30% penalty for resolution mismatch
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

    def score_products(
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
            # Extract product features (this would be implemented in product analyzer)
            product_features = self._extract_product_features(product)
            
            # Score the product
            score_data = self.score_product(user_features, product_features, category)
            
            scored_products.append((product, score_data))
        
        # Sort by score (highest first), with tie-breaking
        scored_products.sort(
            key=lambda x: (
                x[1]["score"],                    # Primary: score
                x[1]["confidence"],               # Secondary: confidence  
                len(x[1]["matched_features"]),    # Tertiary: feature count
                x[0].get("asin", "")             # Final: ASIN for determinism
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
        """Calculate similarity score for a specific feature."""
        if not user_value or not product_value:
            return 0.0
        
        user_str = str(user_value).lower().strip()
        product_str = str(product_value).lower().strip()
        
        # Exact match
        if user_str == product_str:
            return 1.0
        
        # Numeric features with tolerance
        if feature_name in self.tolerance_windows:
            try:
                user_num = float(user_str)
                product_num = float(product_str)
                
                tolerance = self.tolerance_windows[feature_name]
                diff_ratio = abs(user_num - product_num) / user_num
                
                if diff_ratio <= tolerance:
                    # Within tolerance - high score with slight penalty
                    return 1.0 - (diff_ratio / tolerance) * 0.2
                else:
                    # Outside tolerance - apply penalty
                    penalty = self.mismatch_penalties.get(feature_name, 0.5)
                    return penalty * max(0, 1.0 - diff_ratio)
                    
            except ValueError:
                pass  # Fall through to string matching
        
        # String similarity for categorical features  
        if user_str in product_str or product_str in user_str:
            return 0.8  # Partial match
        
        # Brand/keyword matching
        user_words = set(user_str.split())
        product_words = set(product_str.split())
        common_words = user_words & product_words
        
        if common_words:
            overlap_ratio = len(common_words) / max(len(user_words), len(product_words))
            return overlap_ratio * 0.6  # Keyword overlap
        
        return 0.0  # No match

    def _generate_rationale(
        self,
        matched: List[str],
        mismatched: List[str], 
        missing: List[str],
        feature_scores: Dict[str, Dict[str, Any]]
    ) -> str:
        """Generate human-readable explanation for the score."""
        explanations = []
        
        # Add matched features
        if matched:
            matched_parts = []
            for feature in matched:
                if feature in feature_scores:
                    score_data = feature_scores[feature]
                    user_val = score_data["user_value"]
                    product_val = score_data["product_value"]
                    
                    if feature == "refresh_rate":
                        matched_parts.append(f"refresh_rate={product_val}Hz")
                    elif feature == "size":
                        matched_parts.append(f"size={product_val}″")
                    elif feature == "resolution":
                        matched_parts.append(f"resolution={product_val}")
                    else:
                        matched_parts.append(f"{feature}={product_val}")
            
            if matched_parts:
                explanations.append(f"Matched: {', '.join(matched_parts)}")
        
        # Add mismatches if any
        if mismatched:
            mismatch_parts = []
            for feature in mismatched:
                if feature in feature_scores:
                    score_data = feature_scores[feature]
                    user_val = score_data["user_value"]  
                    product_val = score_data["product_value"]
                    mismatch_parts.append(f"{feature}: wanted {user_val}, found {product_val}")
            
            if mismatch_parts:
                explanations.append(f"Mismatched: {', '.join(mismatch_parts)}")
        
        # Add missing features if critical
        critical_missing = [f for f in missing if f in ["refresh_rate", "size", "resolution"]]
        if critical_missing:
            explanations.append(f"Missing: {', '.join(critical_missing)}")
        
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

    def _extract_product_features(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract features from product data.
        
        This is a simplified version - full implementation would be in
        ProductFeatureAnalyzer (Phase 2).
        """
        features = {}
        
        title = product.get("title", "").lower()
        
        # Basic feature extraction from title (temporary implementation)
        if "144hz" in title or "144 hz" in title:
            features["refresh_rate"] = "144"
        elif "165hz" in title or "165 hz" in title:
            features["refresh_rate"] = "165"
        elif "240hz" in title or "240 hz" in title:
            features["refresh_rate"] = "240"
        
        if "27 inch" in title or "27\"" in title:
            features["size"] = "27"
        elif "32 inch" in title or "32\"" in title:
            features["size"] = "32"
        elif "24 inch" in title or "24\"" in title:
            features["size"] = "24"
        
        if "4k" in title or "uhd" in title:
            features["resolution"] = "4k"
        elif "1440p" in title or "qhd" in title:
            features["resolution"] = "1440p"
        elif "1080p" in title or "fhd" in title:
            features["resolution"] = "1080p"
        
        if "curved" in title:
            features["curvature"] = "curved"
        elif "flat" in title:
            features["curvature"] = "flat"
        
        if "ips" in title:
            features["panel_type"] = "ips"
        elif "va" in title:
            features["panel_type"] = "va"
        elif "oled" in title:
            features["panel_type"] = "oled"
        
        # Brand detection
        for brand in ["samsung", "lg", "dell", "asus", "acer", "msi", "benq"]:
            if brand in title:
                features["brand"] = brand
                break
        
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
