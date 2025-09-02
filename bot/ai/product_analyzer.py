"""
Product Feature Analyzer for extracting technical specifications from Amazon product data.

This module implements Phase 2 of the Feature Match AI system by analyzing PA-API
product responses and extracting structured technical features with confidence scoring.

Field Precedence Strategy (CRITICAL for data quality):
1. TechnicalInfo/Specifications (highest reliability) 
2. Features/DisplayValues (structured data)
3. Title (fallback only, noisy)

Confidence Scoring:
- Higher confidence for structured fields vs title parsing
- Validates extracted features against known ranges
- Accounts for data source reliability
"""

import re
import json
from typing import Dict, Any, Optional, List, Union
from logging import getLogger

from .vocabularies import get_category_vocabulary

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


class ProductFeatureAnalyzer:
    """Extract technical specifications from Amazon product data with confidence scoring."""

    def __init__(self):
        """Initialize the product feature analyzer."""
        self._setup_patterns()
        self._setup_validation_ranges()
        # Add simple in-memory cache for feature extraction
        self._feature_cache = {}
        self._cache_max_size = 100
        
    def _setup_patterns(self):
        """Set up regex patterns for extracting features from product text."""
        # Get gaming monitor vocabulary as the primary category for Phase 2
        vocab = get_category_vocabulary("gaming_monitor")
        
        self.patterns = {}
        for feature_name, pattern_list in vocab.items():
            self.patterns[feature_name] = [
                re.compile(pattern, re.IGNORECASE) 
                for pattern in pattern_list
            ]
            
        # Additional patterns for product-specific extraction
        self.product_patterns = {
            "refresh_rate": [
                re.compile(r"(\d+)\s*hz\b", re.IGNORECASE),
                re.compile(r"(\d+)\s*fps\b", re.IGNORECASE),
                re.compile(r"(\d+)\s*hertz\b", re.IGNORECASE),
                re.compile(r"refresh\s*rate[:\s]*(\d+)", re.IGNORECASE),
                re.compile(r"(\d+)hz\s*refresh", re.IGNORECASE),
                re.compile(r"(\d+)fps\s*refresh", re.IGNORECASE),
            ],
            "response_time": [
                re.compile(r"(\d+)\s*ms\b", re.IGNORECASE),
                re.compile(r"response\s*time[:\s]*(\d+)", re.IGNORECASE),
                re.compile(r"(\d+)ms\s*response", re.IGNORECASE),
                re.compile(r"gtg[:\s]*(\d+)", re.IGNORECASE),  # Gray-to-gray
                re.compile(r"mpprt[:\s]*(\d+)", re.IGNORECASE),  # Moving picture response time
            ],
            "size": [
                re.compile(r"(\d+(?:\.\d+)?)\s*inch\b", re.IGNORECASE),
                re.compile(r"(\d+(?:\.\d+)?)\s*\"\s*", re.IGNORECASE), 
                re.compile(r"(\d+(?:\.\d+)?)\s*in\b", re.IGNORECASE),
                re.compile(r"(\d+(?:\.\d+)?)-inch\b", re.IGNORECASE),  # Handle hyphenated format
                re.compile(r"screen\s*size[:\s]*(\d+(?:\.\d+)?)", re.IGNORECASE),
                re.compile(r"(\d+(?:\.\d+)?)\s*cm\b", re.IGNORECASE),  # Convert to inches
            ],
            "resolution": [
                re.compile(r"\b(4k|uhd|2160p|ultra\s*hd)\b", re.IGNORECASE),
                re.compile(r"\b(qhd|wqhd|1440p|quad\s*hd)\b", re.IGNORECASE),
                re.compile(r"\b(fhd|1080p|full\s*hd|fullhd)\b", re.IGNORECASE),
                re.compile(r"\b(hd|720p)\b", re.IGNORECASE),
                re.compile(r"(\d+)\s*x\s*(\d+)", re.IGNORECASE),  # Extract pixel dimensions
                re.compile(r"(\d{3,4})p\b", re.IGNORECASE),  # 1080p, 1440p, 2160p
                re.compile(r"(\d{3,4})\s*by\s*(\d{3,4})", re.IGNORECASE),  # 1920 by 1080
            ],
            "aspect_ratio": [
                re.compile(r"(\d+):(\d+)\s*aspect", re.IGNORECASE),
                re.compile(r"aspect\s*ratio[:\s]*(\d+):(\d+)", re.IGNORECASE),
                re.compile(r"(\d+):(\d+)\s*ar\b", re.IGNORECASE),
                re.compile(r"\b(ultrawide|ultra\s*wide)\b", re.IGNORECASE),
                re.compile(r"\b(widescreen|wide\s*screen)\b", re.IGNORECASE),
            ],
            "curvature": [
                re.compile(r"\b(curved)\b", re.IGNORECASE),
                re.compile(r"\b(flat)\b", re.IGNORECASE),
                re.compile(r"(\d+r)\b", re.IGNORECASE),  # Curvature radius like 1800R
            ],
            "panel_type": [
                re.compile(r"\b(ips|in-plane switching)\b", re.IGNORECASE),
                re.compile(r"\b(va|vertical alignment)\b", re.IGNORECASE),
                re.compile(r"\b(tn|twisted nematic)\b", re.IGNORECASE),
                re.compile(r"\b(oled|organic led|amoled)\b", re.IGNORECASE),
                re.compile(r"\b(qled|quantum dot)\b", re.IGNORECASE),
                re.compile(r"\b(led|light emitting diode)\b", re.IGNORECASE),
                re.compile(r"\b(lcd|liquid crystal)\b", re.IGNORECASE),
            ],
            "connectivity": [
                re.compile(r"\b(hdmi|hdmi2\.1|hdmi2\.0)\b", re.IGNORECASE),
                re.compile(r"\b(displayport|dp|dp1\.4|dp1\.2)\b", re.IGNORECASE),
                re.compile(r"\b(dvi)\b", re.IGNORECASE),
                re.compile(r"\b(vga)\b", re.IGNORECASE),
                re.compile(r"\b(usb|usb-c|type-c)\b", re.IGNORECASE),
                re.compile(r"\b(thunderbolt)\b", re.IGNORECASE),
            ],
            "hdr_support": [
                re.compile(r"\b(hdr|hdr10|hdr10\+|dolby vision)\b", re.IGNORECASE),
                re.compile(r"high\s*dynamic\s*range", re.IGNORECASE),
            ],
            "brand": [
                re.compile(r"\b(samsung|lg|dell|asus|acer|msi|benq|viewsonic|aoc|hp|lenovo)\b", re.IGNORECASE),
            ],
            "category": [
                re.compile(r"\b(monitor|display|screen)\b", re.IGNORECASE),
                re.compile(r"\b(laptop|notebook|computer)\b", re.IGNORECASE),
                re.compile(r"\b(headphone|earphone|headset)\b", re.IGNORECASE),
            ],
            "brightness": [
                re.compile(r"(\d+)\s*cd/m2\b", re.IGNORECASE),
                re.compile(r"(\d+)\s*nits\b", re.IGNORECASE),
                re.compile(r"brightness[:\s]*(\d+)", re.IGNORECASE),
                re.compile(r"(\d+)\s*cd\s*/\s*m²", re.IGNORECASE),
            ],
            "color_accuracy": [
                re.compile(r"(\d+)%\s*srgb\b", re.IGNORECASE),
                re.compile(r"(\d+)%\s*dci-p3\b", re.IGNORECASE),
                re.compile(r"(\d+)%\s*adobe\s*rgb\b", re.IGNORECASE),
                re.compile(r"sRGB[:\s]*(\d+)%", re.IGNORECASE),
                re.compile(r"DCI-P3[:\s]*(\d+)%", re.IGNORECASE),
            ],
            "usage_context": [
                re.compile(r"\b(gaming|game|gamer)\b", re.IGNORECASE),
                re.compile(r"\b(professional|work|office|business)\b", re.IGNORECASE),
                re.compile(r"\b(coding|programming|development|design)\b", re.IGNORECASE),
                re.compile(r"\b(content|creator|creation|streaming)\b", re.IGNORECASE),
                re.compile(r"\b(multimedia|entertainment|movie|cinema)\b", re.IGNORECASE),
            ],
            "price": [
                re.compile(r"₹\s*([\d,]+)", re.IGNORECASE),
                re.compile(r"price[:\s]*₹?\s*([\d,]+)", re.IGNORECASE),
            ]
        }

    def _setup_validation_ranges(self):
        """Set up validation ranges for extracted features."""
        self.validation_ranges = {
            "refresh_rate": {"min": 30, "max": 480, "common": [60, 75, 120, 144, 165, 240, 360]},
            "response_time": {"min": 1, "max": 20, "common": [1, 2, 4, 5, 8, 10, 15]},
            "size": {"min": 10.0, "max": 65.0, "common": [21.5, 24, 27, 32, 34, 43, 49, 55]},
            "brightness": {"min": 200, "max": 2000, "common": [250, 300, 350, 400, 500]},
            "color_accuracy": {"min": 60, "max": 100, "common": [72, 85, 90, 95, 99]},
            "resolution_pixels": {
                "4k": (3840, 2160),
                "1440p": (2560, 1440), 
                "1080p": (1920, 1080),
                "720p": (1280, 720)
            }
        }

    async def analyze_product_features(
        self, 
        product_data: Dict, 
        category: Optional[str] = "gaming_monitor"
    ) -> Dict[str, Any]:
        """
        Extract technical specifications from PA-API product data.
        
        Args:
        ----
            product_data: Product data from PA-API response
            category: Product category for context-specific extraction
            
        Returns:
        -------
            Dict with extracted features and confidence scores:
            {
                "refresh_rate": {"value": "144", "confidence": 0.95, "source": "technical_info"},
                "size": {"value": "27", "confidence": 0.90, "source": "features"},
                "resolution": {"value": "1440p", "confidence": 0.85, "source": "title"},
                "overall_confidence": 0.88,
                "extraction_metadata": {...}
            }
        """
        asin = product_data.get('asin', 'Unknown')
        cache_key = f"{asin}_{category}"

        # Check cache first
        if cache_key in self._feature_cache:
            log.debug(f"Using cached features for ASIN: {asin}")
            return self._feature_cache[cache_key]

        log.debug(f"Analyzing product features for ASIN: {asin}")

        extracted_features = {}
        extraction_sources = {}
        confidence_scores = {}
        
        # Field precedence: TechnicalInfo > Features > Title
        data_sources = self._prioritize_data_sources(product_data)

        # Special handling for price (direct field extraction)
        price_raw = product_data.get("price")
        if price_raw is not None:
            # Handle both string and numeric prices
            try:
                if isinstance(price_raw, str):
                    # Remove any non-numeric characters and convert
                    price_clean = ''.join(c for c in price_raw if c.isdigit() or c == '.')
                    price_numeric = float(price_clean) if price_clean else 0
                else:
                    price_numeric = float(price_raw) if price_raw else 0

                if price_numeric > 0:
                    # Convert paise to rupees for feature storage
                    price_rupees = price_numeric / 100 if price_numeric > 10000 else price_numeric
                    extracted_features["price"] = price_rupees
                    extraction_sources["price"] = "price_field"
                    confidence_scores["price"] = 1.0  # Direct field extraction = highest confidence
                    log.debug(f"Extracted price from direct field: ₹{price_rupees:,.2f}")
            except (ValueError, TypeError) as e:
                log.debug(f"Failed to parse price '{price_raw}': {e}")

        # Extract features from each source in priority order
        for source_name, source_data in data_sources.items():
            if not source_data:
                continue
                
            source_features = await self._extract_from_source(
                source_data, source_name, category
            )
            
            # Add features with precedence logic
            for feature_name, feature_data in source_features.items():
                should_add_feature = False
                
                if feature_name not in extracted_features:
                    # New feature, add it
                    should_add_feature = True
                else:
                    # Feature already exists, check if current source has higher precedence
                    current_source = extraction_sources[feature_name]
                    new_confidence = feature_data["confidence"]
                    current_confidence = confidence_scores[feature_name]
                    
                    # Source precedence order (highest to lowest)
                    source_priority = {
                        "technical_info": 4,
                        "features": 3,
                        "brand_info": 2,
                        "title": 1
                    }
                    
                    current_priority = source_priority.get(current_source, 0)
                    new_priority = source_priority.get(source_name, 0)
                    
                    # Replace if new source has higher priority OR same priority but higher confidence
                    if (new_priority > current_priority or 
                        (new_priority == current_priority and new_confidence > current_confidence)):
                        should_add_feature = True
                
                if should_add_feature:
                    extracted_features[feature_name] = feature_data["value"]
                    extraction_sources[feature_name] = source_name
                    confidence_scores[feature_name] = feature_data["confidence"]
        
        # Calculate overall confidence
        overall_confidence = self._calculate_overall_confidence(
            confidence_scores, extraction_sources
        )
        
        # Build result with metadata
        result = {}
        for feature_name in extracted_features:
            result[feature_name] = {
                "value": extracted_features[feature_name],
                "confidence": confidence_scores[feature_name],
                "source": extraction_sources[feature_name]
            }
        
        result["overall_confidence"] = overall_confidence
        result["extraction_metadata"] = {
            "asin": product_data.get("asin", ""),
            "sources_analyzed": list(data_sources.keys()),
            "features_extracted": len(extracted_features),
            "avg_confidence": sum(confidence_scores.values()) / len(confidence_scores) if confidence_scores else 0.0
        }
        
        log.info(f"Extracted {len(extracted_features)} features with overall confidence {overall_confidence:.3f}")

        # Cache the result for future use
        if len(self._feature_cache) >= self._cache_max_size:
            # Remove oldest entry (simple LRU approximation)
            oldest_key = next(iter(self._feature_cache))
            del self._feature_cache[oldest_key]

        return result

    def calculate_confidence(self, features: Dict) -> float:
        """
        Calculate overall confidence from extracted features.

        Args:
            features: Features dictionary returned by analyze_product_features

        Returns:
            float: Overall confidence score (0.0 to 1.0)
        """
        if not features:
            return 0.0

        # If it's the new format with overall_confidence
        if isinstance(features, dict) and "overall_confidence" in features:
            return features["overall_confidence"]

        # If it's the old format, calculate from individual feature confidences
        if isinstance(features, dict) and any(isinstance(v, dict) and "confidence" in v for v in features.values()):
            confidences = []
            for feature_value in features.values():
                if isinstance(feature_value, dict) and "confidence" in feature_value:
                    confidences.append(feature_value["confidence"])
            return sum(confidences) / len(confidences) if confidences else 0.0

        # Fallback for simple dict format
        return 0.5  # Neutral confidence

    def _prioritize_data_sources(self, product_data: Dict) -> Dict[str, Any]:
        """
        Prioritize data sources based on reliability.
        
        Returns data sources in order of precedence (highest to lowest confidence).
        """
        sources = {}
        
        # 1. TechnicalInfo/Specifications (highest reliability)
        technical_details = product_data.get("technical_details", {})
        if technical_details and isinstance(technical_details, (dict, str)):
            if isinstance(technical_details, str):
                try:
                    technical_details = json.loads(technical_details)
                except (json.JSONDecodeError, TypeError):
                    pass
            sources["technical_info"] = technical_details
        
        # 2. Features/DisplayValues (structured data)
        features_list = product_data.get("features", [])
        if features_list and isinstance(features_list, list):
            # Join features into a single text for pattern matching
            features_text = " ".join(str(f) for f in features_list if f)
            sources["features"] = features_text
        
        # 3. Title (fallback only, noisy)
        title = product_data.get("title", "")
        if title:
            sources["title"] = title
            
        # Additional sources (lower priority)
        # 4. Brand/manufacturer info
        brand = product_data.get("brand")
        manufacturer = product_data.get("manufacturer") 
        if brand or manufacturer:
            sources["brand_info"] = f"{brand or ''} {manufacturer or ''}".strip()
            
        log.debug(f"Data sources prioritized: {list(sources.keys())}")
        return sources

    async def _extract_from_source(
        self, 
        source_data: Union[str, Dict], 
        source_name: str, 
        category: str
    ) -> Dict[str, Dict[str, Any]]:
        """Extract features from a specific data source."""
        extracted = {}
        
        if source_name == "technical_info" and isinstance(source_data, dict):
            # Handle structured technical info
            extracted.update(await self._extract_from_technical_info(source_data))
        else:
            # Handle text-based extraction
            text_data = str(source_data) if source_data else ""
            extracted.update(await self._extract_from_text(text_data, source_name))
        
        return extracted

    async def _extract_from_technical_info(self, tech_info: Dict) -> Dict[str, Dict[str, Any]]:
        """Extract features from structured technical information."""
        extracted = {}
        
        # Map common technical info field names
        field_mappings = {
            "refresh_rate": ["refresh_rate", "refresh", "hz", "frequency"],
            "size": ["screen_size", "display_size", "size", "diagonal"],
            "resolution": ["resolution", "display_resolution", "native_resolution"],
            "panel_type": ["panel_type", "panel", "display_type", "lcd_type"],
            "curvature": ["curvature", "curve", "curved"]
        }
        
        for feature_name, possible_keys in field_mappings.items():
            for key in possible_keys:
                if key in tech_info:
                    value = tech_info[key]
                    normalized_value = self._normalize_feature_value(feature_name, str(value))
                    if normalized_value:
                        confidence = self._calculate_source_confidence("technical_info", feature_name)
                        extracted[feature_name] = {
                            "value": normalized_value,
                            "confidence": confidence
                        }
                        break  # Take first match
        
        return extracted

    async def _extract_from_text(
        self, 
        text: str, 
        source_name: str
    ) -> Dict[str, Dict[str, Any]]:
        """Extract features from text data using regex patterns."""
        extracted = {}
        
        for feature_name, patterns in self.product_patterns.items():
            for pattern in patterns:
                match = pattern.search(text)
                if match:
                    raw_value = match.group(1) if match.groups() else match.group(0)
                    normalized_value = self._normalize_feature_value(feature_name, raw_value)
                    
                    if normalized_value and self._validate_feature_value(feature_name, normalized_value):
                        confidence = self._calculate_source_confidence(source_name, feature_name)
                        extracted[feature_name] = {
                            "value": normalized_value, 
                            "confidence": confidence
                        }
                        break  # Take first valid match
        
        return extracted

    def _normalize_feature_value(self, feature_name: str, raw_value: str) -> Optional[str]:
        """Normalize extracted feature values to standard format."""
        if not raw_value:
            return None
            
        raw_value = safe_string_extract(raw_value).strip().lower()
        
        if feature_name == "refresh_rate":
            # Extract numeric value from refresh rate
            match = re.search(r"(\d+)", raw_value)
            return match.group(1) if match else None
            
        elif feature_name == "size":
            # Handle size conversion (cm to inches)
            match = re.search(r"(\d+(?:\.\d+)?)", raw_value)
            if match:
                size_value = float(match.group(1))
                if "cm" in raw_value:
                    # Convert cm to inches
                    size_value = size_value / 2.54
                return f"{size_value:.1f}".rstrip('0').rstrip('.')
            return None
            
        elif feature_name == "resolution":
            # Normalize resolution synonyms
            resolution_map = {
                "4k": "4k", "uhd": "4k", "2160p": "4k",
                "qhd": "1440p", "wqhd": "1440p", "1440p": "1440p",
                "fhd": "1080p", "1080p": "1080p", "full hd": "1080p", "fullhd": "1080p"
            }
            for key, value in resolution_map.items():
                if key in raw_value:
                    return value
            
            # Handle pixel dimensions (e.g., "3840x2160")
            pixel_match = re.search(r"(\d+)\s*x\s*(\d+)", raw_value)
            if pixel_match:
                width, height = int(pixel_match.group(1)), int(pixel_match.group(2))
                if (width, height) in [(3840, 2160), (4096, 2160)]:
                    return "4k"
                elif (width, height) == (2560, 1440):
                    return "1440p"
                elif (width, height) == (1920, 1080):
                    return "1080p"
            return None
            
        elif feature_name == "curvature":
            if "curved" in raw_value or re.search(r"\d+r", raw_value):
                return "curved"
            elif "flat" in raw_value:
                return "flat"
            return None
            
        elif feature_name == "panel_type":
            panel_types = ["ips", "va", "tn", "oled", "qled"]
            for panel_type in panel_types:
                if panel_type in raw_value:
                    return panel_type
            return None
            
        elif feature_name == "brand":
            brands = [
                "samsung", "lg", "dell", "asus", "acer", "msi", 
                "benq", "viewsonic", "aoc", "hp", "lenovo"
            ]
            for brand in brands:
                if brand in raw_value:
                    return brand
            return None
        
        # Default: return cleaned value
        return raw_value if raw_value else None

    def _validate_feature_value(self, feature_name: str, value: str) -> bool:
        """Validate extracted feature values against known ranges."""
        if feature_name == "refresh_rate":
            try:
                rate = int(value)
                return (self.validation_ranges["refresh_rate"]["min"] <= 
                       rate <= self.validation_ranges["refresh_rate"]["max"])
            except (ValueError, TypeError):
                return False
                
        elif feature_name == "size":
            try:
                size = float(value)
                return (self.validation_ranges["size"]["min"] <= 
                       size <= self.validation_ranges["size"]["max"])
            except (ValueError, TypeError):
                return False
                
        elif feature_name == "resolution":
            return value in ["4k", "1440p", "1080p", "720p", "8k"]
            
        elif feature_name == "curvature":
            return value in ["curved", "flat"]
            
        elif feature_name == "panel_type":
            return value in ["ips", "va", "tn", "oled", "qled"]
        
        # Default: accept non-empty values
        return bool(value and value.strip())

    def _calculate_source_confidence(self, source_name: str, feature_name: str) -> float:
        """Calculate confidence score based on data source reliability."""
        base_confidence = {
            "technical_info": 0.95,  # Highest reliability
            "features": 0.85,        # Structured data
            "title": 0.60,           # Noisy but sometimes accurate
            "brand_info": 0.70       # Moderate reliability
        }
        
        source_confidence = base_confidence.get(source_name, 0.50)
        
        # Adjust confidence based on feature type
        feature_adjustments = {
            "refresh_rate": 0.05,    # Critical spec, usually accurate
            "size": 0.03,            # Usually specified correctly  
            "resolution": 0.02,      # Common specification
            "brand": 0.08,           # Brand usually reliable
            "panel_type": -0.05,     # Less commonly specified
            "curvature": -0.02       # Sometimes inferred
        }
        
        adjustment = feature_adjustments.get(feature_name, 0.0)
        final_confidence = min(0.98, max(0.10, source_confidence + adjustment))
        
        return final_confidence

    def _calculate_overall_confidence(
        self, 
        confidence_scores: Dict[str, float], 
        extraction_sources: Dict[str, str]
    ) -> float:
        """Calculate overall confidence for the product feature extraction."""
        if not confidence_scores:
            return 0.0
        
        # Weight average by number of features from high-confidence sources
        high_confidence_features = sum(
            1 for source in extraction_sources.values() 
            if source in ["technical_info", "features"]
        )
        total_features = len(confidence_scores)
        
        # Base confidence is weighted average
        avg_confidence = sum(confidence_scores.values()) / len(confidence_scores)
        
        # Boost confidence if we have structured data sources
        structure_bonus = (high_confidence_features / total_features) * 0.10 if total_features > 0 else 0
        
        # Penalize if we only have title-based extraction
        title_only_penalty = 0.15 if all(
            source == "title" for source in extraction_sources.values()
        ) else 0
        
        final_confidence = avg_confidence + structure_bonus - title_only_penalty
        return min(0.98, max(0.05, final_confidence))


# Factory function for dependency injection  
def create_product_analyzer() -> ProductFeatureAnalyzer:
    """Create an instance of the ProductFeatureAnalyzer."""
    return ProductFeatureAnalyzer()
