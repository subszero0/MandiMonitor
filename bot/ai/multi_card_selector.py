"""
Multi-Card Selector for intelligent product selection and comparison.

This module implements the intelligent selection of top-N products for user comparison,
transforming the single-card output into a smart multi-card carousel with comparison features.

Key features:
- Intelligent selection criteria based on score gaps and product diversity
- Comparison table generation for key feature differences
- Smart defaults (single card when AI confidence >90% or <2 viable options)
- Fallback logic to maintain existing UX
"""

import time
from typing import Dict, List, Tuple, Any, Optional
from logging import getLogger

log = getLogger(__name__)


class MultiCardSelector:
    """Intelligent selection of top-N products for user comparison."""

    def __init__(self):
        """Initialize the multi-card selector."""
        self.selection_cache = {}  # Cache for performance
        
        # Thresholds for multi-card decisions
        self.score_gap_threshold = 0.15  # Show multi-card if top scores are within 15%
        self.high_confidence_threshold = 0.9  # Single card if AI confidence >90%
        self.min_products_for_multi = 2  # Minimum products needed for multi-card
        self.max_cards = 3  # Maximum cards to show

    async def select_products_for_comparison(
        self,
        scored_products: List[Tuple[Dict, Dict]],
        user_features: Dict[str, Any],
        max_cards: int = 3
    ) -> Dict[str, Any]:
        """
        Select optimal number of products for user choice.

        Args:
        ----
            scored_products: List of (product, score_data) tuples sorted by score
            user_features: User requirements from query
            max_cards: Maximum number of cards to show (default 3)

        Returns:
        -------
            {
                'products': List[Dict],        # Top products with rationale
                'comparison_table': Dict,      # Feature differences
                'selection_reason': str,       # Why these specific products
                'presentation_mode': str,      # 'single', 'duo', 'trio'
                'ai_metadata': Dict           # Selection metadata for analytics
            }
        """
        log.info(f"🎯 MULTI_CARD_SELECTOR: Starting selection for {len(scored_products)} scored products")
        log.info(f"   📝 User features: {user_features}")
        log.info(f"   🔢 Max cards: {max_cards}")

        if len(scored_products) == 0:
            log.warning(f"❌ MULTI_CARD_SELECTOR: No scored products available")
            return {
                "products": [],
                "presentation_mode": "none",
                "selection_reason": "No products available for comparison",
                "ai_metadata": {"selection_type": "empty"}
            }
        elif len(scored_products) == 1:
            # Handle single product case
            product, score_data = scored_products[0]
            return self._single_card_selection(scored_products[0], "Only one viable product available")

        # Log top product details
        if scored_products:
            top_product, top_score = scored_products[0]
            log.info(f"   🥇 Top product: {top_product.get('asin', 'N/A')} - Score: {top_score.get('score', 'N/A')}")
            log.info(f"   📊 Top features: {top_score.get('matched_features', [])}")

        # Continue with existing logic...
        start_time = time.time()
        
        if not scored_products:
            return self._empty_selection("No products to select from")
        
        # Single product fallback
        if len(scored_products) < self.min_products_for_multi:
            processing_time = (time.time() - start_time) * 1000
            result = self._single_card_selection(scored_products[0], "Only one viable product found")
            result['ai_metadata']['processing_time_ms'] = processing_time
            return result
        
        # High confidence single card
        top_score_data = scored_products[0][1]
        if top_score_data["confidence"] > self.high_confidence_threshold:
            processing_time = (time.time() - start_time) * 1000
            result = self._single_card_selection(
                scored_products[0], 
                f"High AI confidence ({top_score_data['confidence']:.1%}) - clear best choice"
            )
            result['ai_metadata']['processing_time_ms'] = processing_time
            return result
        
        # Check if multiple cards provide value
        if not self._should_show_multiple_cards(scored_products):
            processing_time = (time.time() - start_time) * 1000
            result = self._single_card_selection(
                scored_products[0], 
                "Clear winner identified by AI scoring"
            )
            result['ai_metadata']['processing_time_ms'] = processing_time
            return result
        
        # Select diverse products for comparison
        selected_products = self._select_diverse_products(scored_products, user_features, max_cards)
        comparison_table = await self._generate_comparison_table(selected_products, user_features)
        selection_reason = self._explain_selection(selected_products, user_features)
        
        processing_time = (time.time() - start_time) * 1000
        
        result = {
            'products': [product for product, _ in selected_products],
            'comparison_table': comparison_table,
            'selection_reason': selection_reason,
            'presentation_mode': self._get_presentation_mode(len(selected_products)),
            'ai_metadata': {
                'selection_type': 'multi_card',
                'card_count': len(selected_products),
                'processing_time_ms': processing_time,
                'selection_criteria': 'diversity_and_competition',
                'top_scores': [score_data["score"] for _, score_data in selected_products[:3]]
            }
        }
        
        log.info("MultiCard Selection: %d cards, mode=%s, processing=%.1fms", 
                len(selected_products), result['presentation_mode'], processing_time)
        
        return result

    def _should_show_multiple_cards(self, scored_products: List[Tuple[Dict, Dict]]) -> bool:
        """
        OPTIMIZED: More flexible multi-card decision criteria.
        
        Args:
        ----
            scored_products: Scored products sorted by relevance
            
        Returns:
        -------
            True if multi-card experience adds value
        """
        if len(scored_products) < 2:
            return False
        
        top_score = scored_products[0][1]["score"]
        second_score = scored_products[1][1]["score"]
        
        # ENHANCED CRITERIA: Show multi-card if ANY condition is met
        conditions = {
            "close_competition": (top_score - second_score) < 0.20,  # Increased from 0.15
            "different_strengths": self._products_have_different_strengths(scored_products[:3]),
            "price_value_choice": self._price_ranges_offer_value_choice(scored_products[:3]),
            "high_feature_count": len(self._get_all_features(scored_products[:3])) >= 3,  # NEW
            "gaming_specific": self._has_gaming_specific_features(scored_products[:3])  # NEW
        }
        
        # Log decision process for debugging
        log.info(f"MULTI_CARD_DECISION: {conditions}")
        
        # Show multi-card if ANY criterion is met (more liberal)
        decision = any(conditions.values())
        
        # Override: Force single card only if top score is VERY high
        if top_score > 0.95 and (top_score - second_score) > 0.30:
            log.info("OVERRIDE: Single card due to overwhelming top choice")
            return False
        
        return decision

    def _products_have_different_strengths(self, scored_products: List[Tuple[Dict, Dict]]) -> bool:
        """Check if products have meaningfully different strengths."""
        if len(scored_products) < 2:
            return False
        
        # Check if products excel in different features
        feature_leaders = {}
        
        for product, score_data in scored_products:
            matched_features = score_data.get("matched_features", [])
            
            # Identify which features this product excels in
            for feature in matched_features:
                if feature not in feature_leaders:
                    feature_leaders[feature] = []
                feature_leaders[feature].append(product.get("asin", "unknown"))
        
        # If different products lead in different features, show multiple cards
        unique_leaders = set()
        for leaders in feature_leaders.values():
            if leaders:
                unique_leaders.add(leaders[0])  # First product to excel in this feature
        
        return len(unique_leaders) > 1

    def _price_ranges_offer_value_choice(self, scored_products: List[Tuple[Dict, Dict]]) -> bool:
        """Check if price ranges offer meaningful choice (budget vs premium)."""
        if len(scored_products) < 2:
            return False
        
        prices = []
        for product, _ in scored_products:
            price = product.get("price")
            # Ensure price is not None and is a valid number
            if price is not None and isinstance(price, (int, float)) and price > 0:
                prices.append(price)
        
        if len(prices) < 2:
            return False
        
        # Convert to rupees if in paise
        prices = [p/100 if p > 10000 else p for p in prices]
        
        min_price = min(prices)
        max_price = max(prices)
        
        # Show multi-card if there's >25% price difference (meaningful value choice)
        price_variation = (max_price - min_price) / min_price if min_price > 0 else 0
        
        return price_variation > 0.25

    def _select_diverse_products(
        self, 
        scored_products: List[Tuple[Dict, Dict]], 
        user_features: Dict[str, Any], 
        max_cards: int
    ) -> List[Tuple[Dict, Dict]]:
        """
        Select diverse products that offer meaningful choice.
        
        Args:
        ----
            scored_products: All scored products sorted by relevance
            user_features: User requirements
            max_cards: Maximum cards to select
            
        Returns:
        -------
            Selected products for comparison
        """
        if len(scored_products) <= max_cards:
            return scored_products
        
        selected = [scored_products[0]]  # Always include top choice
        
        for candidate_product, candidate_score in scored_products[1:]:
            if len(selected) >= max_cards:
                break
            
            # Check if this candidate adds meaningful diversity
            if self._adds_meaningful_diversity(candidate_product, candidate_score, selected, user_features):
                selected.append((candidate_product, candidate_score))
        
        return selected

    def _adds_meaningful_diversity(
        self, 
        candidate: Dict, 
        candidate_score: Dict,
        selected: List[Tuple[Dict, Dict]], 
        user_features: Dict
    ) -> bool:
        """Check if candidate product adds meaningful diversity to selection."""
        
        # Always add if we have less than 2 products
        if len(selected) < 2:
            return True
        
        candidate_price = candidate.get("price", 0)
        candidate_brand = (candidate.get("brand") or "").lower()
        candidate_features = set(candidate_score.get("matched_features", []))

        # Check diversity across selected products
        for selected_product, selected_score in selected:
            selected_price = selected_product.get("price", 0)
            selected_brand = (selected_product.get("brand") or "").lower()
            selected_features = set(selected_score.get("matched_features", []))
            
            # Price diversity (convert to rupees for comparison)
            # Ensure both prices are valid numbers, not None
            if (candidate_price is not None and isinstance(candidate_price, (int, float)) and candidate_price > 0 and
                selected_price is not None and isinstance(selected_price, (int, float)) and selected_price > 0):
                
                candidate_price_rs = candidate_price/100 if candidate_price > 10000 else candidate_price
                selected_price_rs = selected_price/100 if selected_price > 10000 else selected_price
                
                price_diff = abs(candidate_price_rs - selected_price_rs) / min(candidate_price_rs, selected_price_rs)
                if price_diff > 0.20:  # >20% price difference
                    return True
            
            # Brand diversity
            if candidate_brand and selected_brand and candidate_brand != selected_brand:
                return True
            
            # Feature diversity (different strengths)
            if candidate_features and selected_features:
                unique_features = candidate_features - selected_features
                if len(unique_features) > 0:
                    return True
        
        return False

    async def _generate_comparison_table(
        self, 
        selected_products: List[Tuple[Dict, Dict]], 
        user_features: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate optimized side-by-side feature comparison table.
        Phase R4.2: Enhanced with smart feature prioritization and cleaner formatting.
        
        Args:
        ----
            selected_products: Products selected for comparison
            user_features: User requirements
            
        Returns:
        -------
            Optimized comparison table with prioritized features and better insights
        """
        if not selected_products:
            return {"error": "No products to compare"}
        
        comparison = {
            'headers': ['Feature'] + [f'Option {i+1}' for i in range(len(selected_products))],
            'key_differences': [],
            'strengths': {},  # Which product excels in what
            'trade_offs': [],  # What user gains/loses with each choice
            'summary': "",
            'priority_features': [],  # R4.2: Most important features first
            'user_focused_insights': []  # R4.2: Insights based on user query
        }
        
        # R4.2: Smart feature prioritization based on user intent
        comparison_features = self._prioritize_features_for_user(user_features)
        comparison['priority_features'] = comparison_features[:5]  # Top 5 features
        
        for feature in comparison_features:
            values = []
            user_preference = user_features.get(feature, "Not specified")
            
            # Get feature values for each product
            for i, (product, score_data) in enumerate(selected_products):
                value = self._get_product_feature_value(product, feature, score_data)
                values.append(value)
            
            # Only show if products differ or user specified this feature
            if len(set(values)) > 1 or feature in user_features:
                comparison['key_differences'].append({
                    'feature': feature.replace('_', ' ').title(),
                    'values': values,
                    'user_preference': user_preference,
                    'highlight_best': self._identify_best_value(feature, values, user_preference)
                })
        
        # Identify product strengths
        comparison['strengths'] = self._identify_product_strengths(selected_products)
        
        # Generate trade-offs analysis
        comparison['trade_offs'] = self._analyze_trade_offs(selected_products, user_features)
        
        # Create summary
        comparison['summary'] = self._create_comparison_summary(selected_products, comparison)
        
        return comparison

    def _get_product_feature_value(self, product: Dict, feature: str, score_data: Dict) -> str:
        """Get formatted feature value for display in comparison table."""
        
        if feature == "price":
            price = product.get("price")
            if price is not None and isinstance(price, (int, float)) and price > 0:
                price_rs = price/100 if price > 10000 else price
                return f"₹{price_rs:,.0f}"
            return "Price updating"
        
        elif feature == "brand":
            brand = product.get("brand", "")
            if brand:
                return brand.title()
            # Try to extract from title
            title = product.get("title", "").lower()
            for brand_name in ["lg", "samsung", "acer", "msi", "asus", "dell", "aoc", "benq", "lenovo"]:
                if brand_name in title:
                    return brand_name.upper()
            return "Unknown"
        
        # For technical features, check the analyzed features first
        analyzed_features = score_data.get("feature_scores", {})
        if feature in analyzed_features:
            product_value = analyzed_features[feature]["product_value"]
            if product_value:
                if feature == "refresh_rate":
                    # Extract numeric value and format
                    import re
                    match = re.search(r'(\d+)', str(product_value))
                    if match:
                        return f"{match.group(1)}Hz"
                    return str(product_value)
                elif feature == "size":
                    # Extract numeric value and format
                    import re
                    match = re.search(r'(\d+(?:\.\d+)?)', str(product_value))
                    if match:
                        return f"{match.group(1)}\""
                    return str(product_value)
                elif feature == "resolution":
                    # Standardize resolution naming
                    res_str = str(product_value).lower()
                    if "4k" in res_str or "2160" in res_str:
                        return "4K UHD"
                    elif "1440" in res_str or "qhd" in res_str:
                        return "QHD 1440p"
                    elif "1080" in res_str or "fhd" in res_str:
                        return "FHD 1080p"
                    return str(product_value)
                elif feature == "panel_type":
                    # Standardize panel naming
                    panel_str = str(product_value).upper()
                    if "IPS" in panel_str:
                        return "IPS"
                    elif "VA" in panel_str:
                        return "VA"
                    elif "TN" in panel_str:
                        return "TN"
                    elif "OLED" in panel_str:
                        return "OLED"
                    return str(product_value)
                else:
                    return str(product_value)
        
        # Enhanced fallback to extract from title/product data
        title = product.get("title", "").lower()
        
        if feature == "refresh_rate":
            import re
            # Look for refresh rate patterns in title
            patterns = [r'(\d+)\s*hz', r'(\d+)\s*hertz', r'(\d+)hz']
            for pattern in patterns:
                match = re.search(pattern, title)
                if match:
                    return f"{match.group(1)}Hz"
            return "60Hz (std)"
            
        elif feature == "size":
            import re
            # Look for size patterns in title
            patterns = [r'(\d+(?:\.\d+)?)\s*inch', r'(\d+(?:\.\d+)?)\s*"', r'(\d+(?:\.\d+)?)"']
            for pattern in patterns:
                match = re.search(pattern, title)
                if match:
                    return f"{match.group(1)}\""
            return "24\" (est)"
            
        elif feature == "resolution":
            if any(term in title for term in ["4k", "uhd", "2160"]):
                return "4K UHD"
            elif any(term in title for term in ["qhd", "1440", "wqhd"]):
                return "QHD 1440p"
            elif any(term in title for term in ["fhd", "1080", "full hd"]):
                return "FHD 1080p"
            else:
                return "FHD 1080p"
                
        elif feature == "panel_type":
            if "ips" in title:
                return "IPS"
            elif "va" in title:
                return "VA"
            elif "tn" in title:
                return "TN"
            elif "oled" in title:
                return "OLED"
            else:
                return "IPS (likely)"
                
        elif feature == "curvature":
            if "curved" in title:
                return "Curved"
            else:
                return "Flat"
        
        # Final fallback
        value = product.get(feature, "Not specified")
        return str(value) if value else "Not specified"

    def _identify_best_value(self, feature: str, values: List[str], user_preference: Any) -> int:
        """Identify which option has the best value for this feature."""
        
        if feature == "price" and all("₹" in v for v in values if v != "Price unavailable"):
            # For price, lower is better
            prices = []
            for v in values:
                if v != "Price unavailable":
                    try:
                        price_str = v.replace("₹", "").replace(",", "")
                        prices.append(float(price_str))
                    except:
                        prices.append(float('inf'))
                else:
                    prices.append(float('inf'))
            return prices.index(min(prices))
        
        elif feature in ["refresh_rate", "size"] and user_preference != "Not specified":
            # For technical features, closest to user preference is best
            try:
                user_val = float(str(user_preference).replace("Hz", "").replace('"', ""))
                distances = []
                for v in values:
                    try:
                        val = float(str(v).replace("Hz", "").replace('"', ""))
                        distances.append(abs(val - user_val))
                    except:
                        distances.append(float('inf'))
                return distances.index(min(distances))
            except:
                pass
        
        return 0  # Default to first option

    def _identify_product_strengths(self, selected_products: List[Tuple[Dict, Dict]]) -> Dict[int, List[str]]:
        """Identify what each product excels at."""
        strengths = {}
        
        for i, (product, score_data) in enumerate(selected_products):
            product_strengths = []
            
            matched_features = score_data.get("matched_features", [])
            feature_scores = score_data.get("feature_scores", {})
            
            # Check for exact matches
            for feature in matched_features:
                if feature in feature_scores:
                    feature_score = feature_scores[feature]["score"]
                    if feature_score >= 0.95:  # Nearly perfect match
                        feature_name = feature.replace("_", " ").title()
                        product_strengths.append(f"Exact {feature_name} match")
            
            # Check for high scores in important features
            if score_data["score"] > 0.8:
                product_strengths.append("High overall match")
            
            # Price positioning
            price = product.get("price")
            if price is not None and isinstance(price, (int, float)) and price > 0:
                price_rs = price/100 if price > 10000 else price
                if price_rs < 20000:
                    product_strengths.append("Budget-friendly")
                elif price_rs > 40000:
                    product_strengths.append("Premium features")
            
            strengths[i] = product_strengths
        
        return strengths

    def _analyze_trade_offs(self, selected_products: List[Tuple[Dict, Dict]], user_features: Dict) -> List[str]:
        """Analyze trade-offs between selected products."""
        trade_offs = []
        
        if len(selected_products) < 2:
            return trade_offs
        
        # Price vs features trade-off
        prices = []
        scores = []
        for product, score_data in selected_products:
            price = product.get("price")
            if price is not None and isinstance(price, (int, float)) and price > 0:
                price_rs = price/100 if price > 10000 else price
                prices.append(price_rs)
                scores.append(score_data["score"])
        
        if len(prices) == len(scores) and len(prices) > 1:
            # Check if higher price correlates with higher score
            price_score_pairs = list(zip(prices, scores))
            price_score_pairs.sort()
            
            if price_score_pairs[-1][1] > price_score_pairs[0][1]:
                trade_offs.append("Higher price options offer better feature matches")
        
        return trade_offs

    def _create_comparison_summary(self, selected_products: List[Tuple[Dict, Dict]], comparison: Dict) -> str:
        """Create a concise summary of the comparison."""
        
        if len(selected_products) == 1:
            return "Single best option identified by AI"
        
        summary_parts = []
        
        # Mention number of options
        summary_parts.append(f"{len(selected_products)} competitive options found")
        
        # Mention key differentiators
        key_diffs = comparison.get('key_differences', [])
        if key_diffs:
            diff_features = [diff['feature'] for diff in key_diffs[:2]]  # Top 2
            summary_parts.append(f"Key differences: {', '.join(diff_features)}")
        
        # Mention trade-offs if any
        trade_offs = comparison.get('trade_offs', [])
        if trade_offs:
            summary_parts.append(trade_offs[0])  # First trade-off
        
        return " • ".join(summary_parts)

    def _single_card_selection(self, product_score_tuple: Tuple[Dict, Dict], reason: str) -> Dict[str, Any]:
        """Create single card selection result."""
        product, score_data = product_score_tuple
        
        return {
            'products': [product],
            'comparison_table': {"summary": "Single best option - no comparison needed"},
            'selection_reason': reason,
            'presentation_mode': 'single',
            'ai_metadata': {
                'selection_type': 'single_card',
                'card_count': 1,
                'processing_time_ms': 0,
                'selection_criteria': 'high_confidence_or_clear_winner',
                'top_scores': [score_data["score"]]
            }
        }

    def _empty_selection(self, reason: str) -> Dict[str, Any]:
        """Create empty selection result."""
        return {
            'products': [],
            'comparison_table': {"error": "No products available"},
            'selection_reason': reason,
            'presentation_mode': 'none',
            'ai_metadata': {
                'selection_type': 'empty',
                'card_count': 0,
                'processing_time_ms': 0,
                'selection_criteria': 'no_products',
                'top_scores': []
            }
        }

    def _get_presentation_mode(self, card_count: int) -> str:
        """Get presentation mode based on card count."""
        if card_count == 1:
            return 'single'
        elif card_count == 2:
            return 'duo'
        elif card_count == 3:
            return 'trio'
        else:
            return 'multi'

    def _explain_selection(self, selected_products: List[Tuple[Dict, Dict]], user_features: Dict) -> str:
        """Generate explanation for why these products were selected."""
        
        if not selected_products:
            return "No suitable products found"
        
        if len(selected_products) == 1:
            score_data = selected_products[0][1]
            confidence = score_data["confidence"]
            return f"Single best match with {confidence:.1%} AI confidence"
        
        # Multi-card explanation
        top_score = selected_products[0][1]["score"]
        scores = [score_data["score"] for _, score_data in selected_products]
        score_range = max(scores) - min(scores)
        
        explanation_parts = []
        
        if score_range < 0.2:
            explanation_parts.append("Close competition between top choices")
        
        # Check for feature diversity
        all_features = set()
        for _, score_data in selected_products:
            all_features.update(score_data.get("matched_features", []))
        
        if len(all_features) > 3:
            explanation_parts.append("Products excel in different areas")
        
        # Check for price diversity
        prices = []
        for p, _ in selected_products:
            price = p.get("price")
            if price is not None and isinstance(price, (int, float)) and price > 0:
                price_rs = price/100 if price > 10000 else price
                prices.append(price_rs)
        if len(prices) > 1:
            price_range = (max(prices) - min(prices)) / min(prices)
            if price_range > 0.25:
                explanation_parts.append("Different price points offer value choices")
        
        if not explanation_parts:
            explanation_parts.append("Multiple good options found")
        
        return " • ".join(explanation_parts)

    def _get_all_features(self, scored_products: List[Tuple[Dict, Dict]]) -> set:
        """Get all unique features across products."""
        all_features = set()
        for product, score_data in scored_products:
            all_features.update(score_data.get("matched_features", []))
            # Also check product features
            title = product.get("title", "").lower()
            # Extract additional features from title
            if "gaming" in title:
                all_features.add("gaming")
            if "curved" in title:
                all_features.add("curved")
            if "4k" in title:
                all_features.add("4k")
            if "hdr" in title:
                all_features.add("hdr")
        return all_features

    def _has_gaming_specific_features(self, scored_products: List[Tuple[Dict, Dict]]) -> bool:
        """Check if products have gaming-specific features that warrant comparison."""
        gaming_indicators = ["gaming", "hz", "fps", "curved", "g-sync", "freesync", "low latency", "esports"]
        
        for product, score_data in scored_products:
            title = product.get("title", "").lower()
            features = score_data.get("matched_features", [])
            
            # Check title and features for gaming indicators
            for indicator in gaming_indicators:
                if indicator in title or any(indicator in str(f).lower() for f in features):
                    return True
        
        return False

    def _prioritize_features_for_user(self, user_features: Dict[str, Any]) -> List[str]:
        """
        R4.2: Intelligently prioritize features based on user intent and query.
        
        Args:
        ----
            user_features: User requirements and preferences
            
        Returns:
        -------
            Ordered list of features by importance to user
        """
        # Base feature set
        all_features = ['price', 'refresh_rate', 'size', 'resolution', 'panel_type', 'brand', 'curvature', 'connectivity']
        
        # Analyze user query for intent
        user_query = str(user_features.get('user_query', '')).lower()
        
        # Priority weights based on user intent
        feature_weights = {}
        
        # Gaming intent - prioritize performance
        if any(word in user_query for word in ['gaming', 'game', 'fps', 'esports', 'competitive']):
            feature_weights.update({
                'refresh_rate': 10,
                'size': 8,
                'resolution': 7,
                'panel_type': 6,
                'price': 5
            })
        
        # Professional/work intent - prioritize display quality
        elif any(word in user_query for word in ['work', 'office', 'programming', 'design', 'productivity']):
            feature_weights.update({
                'size': 10,
                'resolution': 9,
                'panel_type': 7,
                'connectivity': 6,
                'price': 5
            })
        
        # Budget-conscious - prioritize value
        elif any(word in user_query for word in ['cheap', 'budget', 'affordable', 'under']):
            feature_weights.update({
                'price': 10,
                'size': 7,
                'resolution': 6,
                'refresh_rate': 5,
                'brand': 4
            })
        
        # Default prioritization
        else:
            feature_weights.update({
                'price': 8,
                'size': 7,
                'resolution': 6,
                'refresh_rate': 5,
                'brand': 4
            })
        
        # Sort features by weight (higher weight = higher priority)
        prioritized = sorted(all_features, key=lambda f: feature_weights.get(f, 1), reverse=True)
        
        return prioritized

    def build_enhanced_comparison_table(self, products: List[Dict], score_breakdowns: List[Dict]) -> Dict[str, Any]:
        """
        Build enhanced comparison table with score insights and explanations - Phase 3 Transparency

        Args:
            products: List of product dictionaries
            score_breakdowns: List of score breakdown dictionaries

        Returns:
            Enhanced comparison table with transparency features
        """
        if not products or not score_breakdowns:
            return {"error": "No products or score data available"}

        # Calculate score statistics
        scores = [breakdown.get('final_score', 0) for breakdown in score_breakdowns]
        min_score = min(scores) if scores else 0
        max_score = max(scores) if scores else 0

        # Identify highest scoring product
        highest_idx = scores.index(max_score) if scores else 0
        highest_product = products[highest_idx]

        # Generate key differentiators
        key_diffs = self._identify_key_differences(products, score_breakdowns)

        # Build enhanced table
        table = {
            "score_analysis": {
                "highest_score_product": highest_product.get('asin', 'N/A'),
                "score_range": f"{min_score:.2f} - {max_score:.2f}",
                "average_score": sum(scores) / len(scores) if scores else 0,
                "key_differentiators": key_diffs,
                "recommendation_reason": self._generate_recommendation_reason(highest_product, score_breakdowns[highest_idx])
            },
            "products": []
        }

        # Add detailed product information
        for product, breakdown in zip(products, score_breakdowns):
            # Import here to avoid circular imports
            from .enhanced_product_selection import generate_user_explanations, extract_key_specs_text

            explanations = generate_user_explanations(breakdown, product)
            key_specs = extract_key_specs_text(product)

            table["products"].append({
                "asin": product.get("asin", "N/A"),
                "title": product.get("title", "Unknown Product"),
                "price": product.get("price", 0),
                "score": breakdown.get("final_score", 0),
                "rank": scores.index(breakdown.get('final_score', 0)) + 1 if breakdown.get('final_score', 0) in scores else 0,
                "key_specs": key_specs,
                "why_recommended": explanations,
                "score_components": {
                    "technical": breakdown.get("technical_score", 0),
                    "value": breakdown.get("value_score", 0),
                    "budget": breakdown.get("budget_score", 0),
                    "excellence": breakdown.get("excellence_bonus", 0)
                }
            })

        return table

    def _identify_key_differences(self, products: List[Dict], score_breakdowns: List[Dict]) -> List[str]:
        """Identify the key factors that differentiate the top products"""
        differences = []

        if len(products) < 2:
            return differences

        # Compare refresh rates
        refresh_rates = [p.get('refresh_rate', 0) for p in products]
        if max(refresh_rates) - min(refresh_rates) >= 60:
            differences.append("Refresh Rate (higher = better for gaming)")

        # Compare resolutions
        resolutions = [p.get('resolution', '') for p in products]
        if len(set(resolutions)) > 1:
            differences.append("Resolution (4K > QHD > FHD)")

        # Compare prices
        prices = [p.get('price', 0) for p in products]
        price_range = max(prices) - min(prices)
        if price_range > 5000:
            differences.append("Price (value per rupee)")

        return differences[:3]  # Limit to top 3 differences

    def _generate_recommendation_reason(self, top_product: Dict, top_breakdown: Dict) -> str:
        """Generate a clear reason for why this product is recommended"""
        reasons = []

        score = top_breakdown.get('final_score', 0)
        if score > 0.85:
            reasons.append("exceptional overall performance")
        elif score > 0.75:
            reasons.append("excellent balance of features and value")
        else:
            reasons.append("strong performance within budget")

        excellence = top_breakdown.get('excellence_bonus', 0)
        if excellence > 0.1:
            reasons.append("superior technical specifications")

        value = top_breakdown.get('value_score', 0)
        if value > 0.9:
            reasons.append("outstanding value for money")

        return f"Best choice due to {', '.join(reasons)}"
