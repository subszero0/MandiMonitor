"""
Feature Extractor for parsing user queries into structured technical requirements.

Based on POC results, this implementation uses a pure regex approach for optimal
performance (0.1ms average, 92.9% success rate, 73.3% accuracy).

Supports:
- Gaming monitor features: refresh_rate, size, resolution, curvature, panel_type
- Hinglish queries and unit variants (cm→inches, Hz/FPS/hertz synonyms)
- Marketing fluff filtering
- Confidence scoring based on technical density
"""

import re
import time
from typing import Dict, Any, Optional
from logging import getLogger

from .vocabularies import get_category_vocabulary

log = getLogger(__name__)


class FeatureExtractor:
    """Extract technical features from user queries using regex patterns."""

    def __init__(self):
        """Initialize the feature extractor with compiled patterns."""
        self._patterns_cache = {}
        self._compile_patterns()
        
        # Synonyms mapping for normalization
        self.synonyms = {
            "resolution": {
                "4k": "4k", "uhd": "4k", "2160p": "4k",
                "qhd": "1440p", "wqhd": "1440p", "1440p": "1440p", 
                "fhd": "1080p", "1080p": "1080p", "full hd": "1080p"
            },
            "refresh_rate": {
                # All normalized to Hz value (extracted number)
            },
            "size": {
                # Handled via conversion logic for cm→inches
            }
        }
        
        # Marketing words to detect and filter fluff
        self.marketing_words = {
            "cinematic", "eye", "care", "stunning", "amazing", "best", 
            "ultimate", "premium", "advanced", "perfect",
            "ideal", "excellent", "outstanding", "superb", "fantastic",
            "ever", "ultimate"
        }
        
        # Technical terms for context analysis
        self.tech_terms = {
            "gaming", "hz", "fps", "hertz", "inch", "cm", "curved", "flat",
            "4k", "1440p", "1080p", "qhd", "uhd", "fhd", "hdr", "refresh",
            "ips", "va", "tn", "oled", "qled", "panel", "display", "monitor",
            "coding", "programming", "development", "work", "professional", "office"
        }

    def _compile_patterns(self):
        """Compile regex patterns for better performance."""
        # Get gaming monitor vocabulary as default
        vocab = get_category_vocabulary("gaming_monitor")
        
        self.patterns = {}
        for feature_name, pattern_list in vocab.items():
            self.patterns[feature_name] = [
                re.compile(pattern, re.IGNORECASE) 
                for pattern in pattern_list
            ]

    def extract_features(
        self, 
        query: str, 
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Parse user query into structured feature requirements.
        
        Args:
        ----
            query: User's search query
            category: Optional product category hint
            
        Returns:
        -------
            Dict with extracted features and metadata:
            {
                "refresh_rate": "144",
                "size": "27", 
                "resolution": "1440p",
                "curvature": "curved",
                "confidence": 0.85,
                "processing_time_ms": 1.2,
                "category_detected": "gaming_monitor",
                "technical_query": True
            }
        """
        start_time = time.time()
        
        if not query or not query.strip():
            return {"confidence": 0.0, "processing_time_ms": 0.0}
        
        query_clean = query.lower().strip()
        features = {}
        
        # Early marketing fluff detection
        if self._is_marketing_heavy(query_clean):
            processing_time = (time.time() - start_time) * 1000
            return {
                "confidence": 0.1,
                "processing_time_ms": processing_time,
                "marketing_heavy": True
            }
        
        # Detect category if not provided
        detected_category = category or self._detect_category(query_clean)
        if detected_category:
            features["category_detected"] = detected_category
        
        # Extract features using patterns
        total_words = len(query_clean.split())
        matched_features = 0
        
        for feature_name, compiled_patterns in self.patterns.items():
            for pattern in compiled_patterns:
                matches = pattern.findall(query_clean)
                if matches:
                    value = matches[0].strip()
                    
                    # Apply normalization
                    normalized_value = self._normalize_feature_value(
                        feature_name, value, query_clean
                    )
                    
                    if normalized_value:
                        features[feature_name] = normalized_value
                        matched_features += 1
                        break  # Take first match for each feature
        
        # Calculate technical density for confidence scoring
        tech_word_count = sum(1 for word in query_clean.split() 
                             if word in self.tech_terms)
        technical_density = tech_word_count / total_words if total_words > 0 else 0
        
        # Calculate confidence score
        confidence = self._calculate_confidence(
            matched_features, total_words, technical_density
        )
        
        # Add metadata
        features.update({
            "confidence": confidence,
            "processing_time_ms": (time.time() - start_time) * 1000,
            "technical_query": technical_density > 0.3,
            "matched_features_count": matched_features,
            "technical_density": technical_density
        })
        
        log.debug(
            "Extracted features from '%s': %d features, %.3f confidence, %.1fms",
            query[:50], matched_features, confidence, features["processing_time_ms"]
        )
        
        return features

    def _is_marketing_heavy(self, query: str) -> bool:
        """Check if query is dominated by marketing language."""
        words = query.split()
        if len(words) < 2:
            return False
            
        marketing_count = sum(1 for word in words if word in self.marketing_words)
        marketing_ratio = marketing_count / len(words)
        
        # Consider marketing-heavy if >25% marketing words or contains certain key marketing terms
        has_strong_marketing = any(word in query for word in ["cinematic", "experience", "ever"])
        
        return marketing_ratio > 0.25 or has_strong_marketing

    def _detect_category(self, query: str) -> Optional[str]:
        """Detect product category from query."""
        category_keywords = {
            "gaming_monitor": ["monitor", "display", "screen", "gaming"],
            "laptop": ["laptop", "notebook", "computer"],
            "headphones": ["headphone", "earphone", "earbuds", "headset"],
            "smartphone": ["phone", "smartphone", "mobile"]
        }
        
        scores = {}
        for category, keywords in category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in query)
            if score > 0:
                scores[category] = score
        
        return max(scores, key=scores.get) if scores else "gaming_monitor"

    def _normalize_feature_value(
        self, 
        feature_name: str, 
        value: str, 
        full_query: str
    ) -> Optional[str]:
        """Normalize extracted feature values."""
        if not value:
            return None
            
        value = value.strip().lower()
        
        # Apply synonyms
        if feature_name in self.synonyms and value in self.synonyms[feature_name]:
            return self.synonyms[feature_name][value]
        
        # Special handling for size (cm to inches conversion)
        if feature_name == "size" and "cm" in full_query:
            try:
                cm_value = float(value)
                inches = round(cm_value / 2.54, 1)
                return str(inches)
            except ValueError:
                pass
        
        # Special handling for refresh rate (extract number only)
        if feature_name == "refresh_rate":
            # Extract just the number
            number_match = re.search(r'(\d+)', value)
            if number_match:
                return number_match.group(1)
        
        # Return cleaned value
        return value

    def _calculate_confidence(
        self, 
        matched_features: int, 
        total_words: int, 
        technical_density: float
    ) -> float:
        """Calculate confidence score for feature extraction."""
        if total_words == 0:
            return 0.0
        
        # Base confidence from feature matches (more generous for fewer words)
        if total_words <= 3:
            feature_density = matched_features / total_words
            base_confidence = min(feature_density * 0.6, 0.8)
        else:
            feature_density = matched_features / total_words
            base_confidence = min(feature_density * 0.5, 0.7)
        
        # Boost from technical vocabulary
        tech_boost = technical_density * 0.3
        
        # Final confidence
        confidence = base_confidence + tech_boost
        return min(confidence, 1.0)

    def validate_extraction(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate extracted features against known ranges and patterns.
        
        Args:
        ----
            features: Extracted features dict
            
        Returns:
        -------
            Updated features dict with validation results
        """
        validation = {
            "valid": True,
            "warnings": [],
            "errors": []
        }
        
        # Validate refresh rate
        if "refresh_rate" in features:
            try:
                rate = int(features["refresh_rate"])
                if rate < 30 or rate > 500:
                    validation["warnings"].append(
                        f"Unusual refresh rate: {rate}Hz (expected 30-500Hz)"
                    )
                elif rate < 60:
                    validation["warnings"].append(
                        f"Low refresh rate for gaming: {rate}Hz"
                    )
            except ValueError:
                validation["errors"].append(
                    f"Invalid refresh rate format: {features['refresh_rate']}"
                )
        
        # Validate size
        if "size" in features:
            try:
                size = float(features["size"])
                if size < 10 or size > 65:
                    validation["warnings"].append(
                        f"Unusual monitor size: {size}\" (expected 10-65\")"
                    )
            except ValueError:
                validation["errors"].append(
                    f"Invalid size format: {features['size']}"
                )
        
        # Set validation status
        validation["valid"] = len(validation["errors"]) == 0
        features["validation"] = validation
        
        return features

    def get_feature_explanation(self, features: Dict[str, Any]) -> str:
        """
        Generate human-readable explanation of extracted features.
        
        Args:
        ----
            features: Extracted features dict
            
        Returns:
        -------
            Formatted explanation string
        """
        explanations = []
        
        if "refresh_rate" in features:
            explanations.append(f"Refresh rate: {features['refresh_rate']}Hz")
        
        if "size" in features:
            explanations.append(f"Screen size: {features['size']}\"")
        
        if "resolution" in features:
            explanations.append(f"Resolution: {features['resolution']}")
        
        if "curvature" in features:
            explanations.append(f"Curvature: {features['curvature']}")
        
        if "panel_type" in features:
            explanations.append(f"Panel type: {features['panel_type'].upper()}")
        
        if "brand" in features:
            explanations.append(f"Brand: {features['brand'].title()}")
        
        if not explanations:
            return "No specific technical features detected"
        
        confidence = features.get("confidence", 0)
        explanation = " • ".join(explanations)
        explanation += f" (Confidence: {confidence:.0%})"
        
        return explanation
