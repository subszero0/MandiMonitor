"""
Category-specific feature vocabularies for different product types.

This module contains regex patterns and synonyms for extracting technical
specifications from user queries across different product categories.

Based on POC results, using pure regex patterns optimized for:
- Gaming monitors (Phase 1 focus)
- Future expansion: laptops, headphones, smartphones
"""

from typing import Dict, List


# Gaming Monitor Vocabulary (Phase 1 Implementation)
GAMING_MONITOR_VOCABULARY = {
    "refresh_rate": [
        r"(\d+)\s*hz\b",
        r"(\d+)\s*fps\b", 
        r"(\d+)\s*hertz\b",
        r"(\d+)\s*refresh\b"
    ],
    "size": [
        r"(\d+(?:\.\d+)?)\s*inch\b",
        r"(\d+(?:\.\d+)?)\s*\"\s*",
        r"(\d+(?:\.\d+)?)\s*in\b",
        r"(\d+(?:\.\d+)?)\s*cm\b"  # Will be converted to inches
    ],
    "resolution": [
        r"\b(4k|uhd|2160p)\b",
        r"\b(qhd|wqhd|1440p)\b", 
        r"\b(fhd|1080p|full\s*hd)\b",
        r"\b(8k)\b",
        r"\b(720p|hd)\b"
    ],
    "curvature": [
        r"\b(curved)\b",
        r"\b(flat)\b"
    ],
    "panel_type": [
        r"\b(ips)\b",
        r"\b(va)\b", 
        r"\b(tn)\b",
        r"\b(oled)\b",
        r"\b(qled)\b"
    ],
    "brand": [
        r"\b(samsung)\b",
        r"\b(lg)\b",
        r"\b(dell)\b", 
        r"\b(asus)\b",
        r"\b(acer)\b",
        r"\b(msi)\b",
        r"\b(benq)\b",
        r"\b(viewsonic)\b",
        r"\b(aoc)\b",
        r"\b(hp)\b",
        r"\b(lenovo)\b"
    ],
    "category": [
        r"\b(monitor)\b",
        r"\b(display)\b",
        r"\b(screen)\b"
    ],
    "usage_context": [
        r"\b(gaming)\b",
        r"\b(professional)\b",
        r"\b(coding)\b",
        r"\b(design)\b",
        r"\b(office)\b"
    ]
}

# Laptop Vocabulary (Future Phase 7 Implementation)
LAPTOP_VOCABULARY = {
    "processor": [
        r"\b(intel|amd|ryzen|core\s*i[357]|i[357])\b",
        r"\b(m1|m2|apple\s*silicon)\b"
    ],
    "ram": [
        r"(\d+)\s*gb\s*ram\b",
        r"(\d+)\s*gb\s*memory\b",
        r"(\d+)gb\b(?=.*\b(?:ram|memory)\b)"
    ],
    "storage": [
        r"(\d+)\s*gb\s*ssd\b",
        r"(\d+)\s*tb\s*ssd\b", 
        r"(\d+)\s*gb\s*hdd\b",
        r"(\d+)\s*tb\s*hdd\b"
    ],
    "screen_size": [
        r"(\d+(?:\.\d+)?)\s*inch\b",
        r"(\d+(?:\.\d+)?)\s*\"\b"
    ],
    "graphics": [
        r"\b(rtx\s*\d+)\b",
        r"\b(gtx\s*\d+)\b", 
        r"\b(radeon)\b",
        r"\b(integrated\s*graphics)\b"
    ],
    "brand": [
        r"\b(dell|hp|lenovo|asus|acer|msi|apple|macbook)\b"
    ],
    "category": [
        r"\b(laptop|notebook|computer|macbook)\b"
    ]
}

# Headphones Vocabulary (Future Phase 7 Implementation)  
HEADPHONES_VOCABULARY = {
    "type": [
        r"\b(over[-\s]*ear)\b",
        r"\b(on[-\s]*ear)\b",
        r"\b(in[-\s]*ear)\b",
        r"\b(true\s*wireless)\b",
        r"\b(bluetooth)\b",
        r"\b(wired)\b"
    ],
    "noise_cancellation": [
        r"\b(anc|noise\s*cancel)\b",
        r"\b(active\s*noise)\b"
    ],
    "wireless": [
        r"\b(bluetooth)\b",
        r"\b(wireless)\b",
        r"\b(wired)\b"
    ],
    "brand": [
        r"\b(sony|bose|sennheiser|audio[-\s]*technica|jbl|beats)\b"
    ],
    "category": [
        r"\b(headphone|earphone|earbuds|headset)\b"
    ]
}

# Feature importance weights for scoring (Phase 3 implementation)
FEATURE_WEIGHTS = {
    "gaming_monitor": {
        "usage_context": 2.5,   # 🎯 HIGHEST: Gaming purpose is critical
        "refresh_rate": 2.0,    # Very important for gaming
        "resolution": 1.8,      # Important for image quality
        "size": 1.5,           # User preference (lower than gaming purpose)
        "curvature": 1.2,      # Nice to have feature
        "panel_type": 1.0,     # Technical preference
        "brand": 0.8,          # Brand preference
        "category": 0.3        # 🎯 LOWEST: Usually correct anyway
    },
    "laptop": {
        "processor": 3.0,
        "ram": 2.5,
        "storage": 2.0,
        "graphics": 2.0,
        "screen_size": 1.5,
        "brand": 0.8,
        "category": 0.5
    },
    "headphones": {
        "type": 2.5,
        "noise_cancellation": 2.0,
        "wireless": 1.5,
        "brand": 1.0,
        "category": 0.5
    }
}

# Synonym mappings for normalization
FEATURE_SYNONYMS = {
    "resolution": {
        "4k": "4k", "uhd": "4k", "2160p": "4k",
        "qhd": "1440p", "wqhd": "1440p", "1440p": "1440p",
        "fhd": "1080p", "1080p": "1080p", "full hd": "1080p",
        "hd": "720p", "720p": "720p"
    },
    "panel_type": {
        "ips": "IPS",
        "va": "VA", 
        "tn": "TN",
        "oled": "OLED",
        "qled": "QLED"
    },
    "curvature": {
        "curved": "curved",
        "flat": "flat"
    }
}

# Category detection keywords
CATEGORY_KEYWORDS = {
    "gaming_monitor": ["monitor", "display", "screen", "gaming"],
    "laptop": ["laptop", "notebook", "computer", "macbook"],
    "headphones": ["headphone", "earphone", "earbuds", "headset"],
    "smartphone": ["phone", "smartphone", "mobile"]
}


def get_category_vocabulary(category: str) -> Dict[str, List[str]]:
    """
    Get vocabulary patterns for a specific product category.
    
    Args:
    ----
        category: Product category name
        
    Returns:
    -------
        Dict mapping feature names to regex patterns
        
    Example:
    -------
        >>> vocab = get_category_vocabulary("gaming_monitor")
        >>> vocab["refresh_rate"]
        [r"(\d+)\s*hz\b", r"(\d+)\s*fps\b", ...]
    """
    vocabularies = {
        "gaming_monitor": GAMING_MONITOR_VOCABULARY,
        "laptop": LAPTOP_VOCABULARY,
        "headphones": HEADPHONES_VOCABULARY,
    }
    
    return vocabularies.get(category, GAMING_MONITOR_VOCABULARY)


def get_feature_weights(category: str) -> Dict[str, float]:
    """
    Get feature importance weights for scoring algorithm.
    
    Args:
    ----
        category: Product category name
        
    Returns:
    -------
        Dict mapping feature names to importance weights
    """
    return FEATURE_WEIGHTS.get(category, FEATURE_WEIGHTS["gaming_monitor"])


def get_synonyms(feature_name: str) -> Dict[str, str]:
    """
    Get synonym mappings for feature normalization.
    
    Args:
    ----
        feature_name: Name of the feature
        
    Returns:
    -------
        Dict mapping variations to normalized values
    """
    return FEATURE_SYNONYMS.get(feature_name, {})


def get_category_keywords() -> Dict[str, List[str]]:
    """
    Get category detection keywords.
    
    Returns:
    -------
        Dict mapping category names to detection keywords
    """
    return CATEGORY_KEYWORDS.copy()


def validate_category(category: str) -> bool:
    """
    Check if category is supported.
    
    Args:
    ----
        category: Category name to validate
        
    Returns:
    -------
        True if category is supported
    """
    return category in FEATURE_WEIGHTS


def get_supported_categories() -> List[str]:
    """
    Get list of all supported categories.
    
    Returns:
    -------
        List of supported category names
    """
    return list(FEATURE_WEIGHTS.keys())


# Marketing/fluff words to filter out
MARKETING_FLUFF = {
    "cinematic", "eye", "care", "stunning", "amazing", "best", 
    "ultimate", "professional", "premium", "advanced", "perfect",
    "ideal", "excellent", "outstanding", "superb", "fantastic",
    "incredible", "awesome", "brilliant", "remarkable", "exceptional"
}


def is_marketing_word(word: str) -> bool:
    """
    Check if a word is marketing fluff.
    
    Args:
    ----
        word: Word to check
        
    Returns:
    -------
        True if word is marketing fluff
    """
    return word.lower() in MARKETING_FLUFF


# Version tracking for vocabulary updates
VOCABULARY_VERSION = "1.0.0"
LAST_UPDATED = "2025-08-26"
