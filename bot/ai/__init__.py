"""
Feature Match AI Module
=======================

Intelligent product selection algorithm that uses Natural Language Processing and 
feature extraction to understand user intent and match products based on specific 
technical specifications and requirements.

Key Components:
- FeatureExtractor: Parse user queries into structured feature requirements
- ProductFeatureAnalyzer: Extract technical specs from Amazon product data  
- FeatureMatchingEngine: Score products based on feature alignment
- MultiCardSelector: Select optimal products for user comparison

Architecture Decision (POC Results):
- Using Pure Regex approach for feature extraction (92.9% success rate, 0.1ms avg)
- Memory footprint: ~1-5MB (well under 100MB requirement)
- Supports Hinglish queries and unit variants (cm/inch, Hz/FPS synonyms)
- Filters marketing fluff effectively
"""

from .feature_extractor import FeatureExtractor
from .matching_engine import FeatureMatchingEngine
from .product_analyzer import ProductFeatureAnalyzer
from .vocabularies import get_category_vocabulary

__version__ = "1.0.0"
__all__ = [
    "FeatureExtractor",
    "FeatureMatchingEngine",
    "ProductFeatureAnalyzer", 
    "get_category_vocabulary",
]

# Module-level configuration
AI_CONFIG = {
    "processing_timeout_ms": 500,  # Maximum processing time per request
    "memory_limit_mb": 100,       # Memory usage hard cap
    "confidence_threshold": 0.7,   # Minimum confidence for AI selection
    "feature_cache_ttl": 3600,    # Feature extraction cache TTL (1 hour)
}
