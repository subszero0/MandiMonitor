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
        Determine if multiple cards provide value to user.
        
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
        
        # Show multiple cards if:
        # 1. Multiple products are close in score (competitive options)
        # 2. Products have different key features (meaningful choice)
        # 3. Price ranges offer different value propositions
        
        close_competition = (top_score - second_score) < self.score_gap_threshold
        different_strengths = self._products_have_different_strengths(scored_products[:3])
        price_value_choice = self._price_ranges_offer_value_choice(scored_products[:3])
        
        # If scores are very far apart (>30% gap), require strong evidence
        large_score_gap = (top_score - second_score) > 0.30
        if large_score_gap:
            # Need both different strengths AND price choice for very different scores
            decision = different_strengths and price_value_choice
        else:
            # Normal decision logic for closer scores
            decision = close_competition or different_strengths or price_value_choice
        
        log.debug("Multi-card decision: close_competition=%s, different_strengths=%s, price_choice=%s -> %s",
                 close_competition, different_strengths, price_value_choice, decision)
        
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
            price = product.get("price", 0)
            if price > 0:
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
        candidate_brand = candidate.get("brand", "").lower()
        candidate_features = set(candidate_score.get("matched_features", []))
        
        # Check diversity across selected products
        for selected_product, selected_score in selected:
            selected_price = selected_product.get("price", 0)
            selected_brand = selected_product.get("brand", "").lower()
            selected_features = set(selected_score.get("matched_features", []))
            
            # Price diversity (convert to rupees for comparison)
            candidate_price_rs = candidate_price/100 if candidate_price > 10000 else candidate_price
            selected_price_rs = selected_price/100 if selected_price > 10000 else selected_price
            
            if candidate_price_rs > 0 and selected_price_rs > 0:
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
        Generate side-by-side feature comparison table.
        
        Args:
        ----
            selected_products: Products selected for comparison
            user_features: User requirements
            
        Returns:
        -------
            Comparison table with feature differences and strengths
        """
        if not selected_products:
            return {"error": "No products to compare"}
        
        comparison = {
            'headers': ['Feature'] + [f'Option {i+1}' for i in range(len(selected_products))],
            'key_differences': [],
            'strengths': {},  # Which product excels in what
            'trade_offs': [],  # What user gains/loses with each choice
            'summary': ""
        }
        
        # Extract key differentiating features
        comparison_features = ['refresh_rate', 'size', 'resolution', 'price', 'brand', 'curvature']
        
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
            price = product.get("price", 0)
            if price > 0:
                price_rs = price/100 if price > 10000 else price
                return f"₹{price_rs:,.0f}"
            return "Price unavailable"
        
        elif feature == "brand":
            return product.get("brand", "Unknown brand")
        
        # For technical features, check the analyzed features first
        analyzed_features = score_data.get("feature_scores", {})
        if feature in analyzed_features:
            product_value = analyzed_features[feature]["product_value"]
            if product_value:
                if feature == "refresh_rate":
                    return f"{product_value}Hz"
                elif feature == "size":
                    return f"{product_value}\""
                else:
                    return str(product_value)
        
        # Fallback to direct product data
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
            price = product.get("price", 0)
            if price > 0:
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
            price = product.get("price", 0)
            if price > 0:
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
        prices = [p.get("price", 0) for p, _ in selected_products]
        prices = [p/100 if p > 10000 else p for p in prices if p > 0]
        if len(prices) > 1:
            price_range = (max(prices) - min(prices)) / min(prices)
            if price_range > 0.25:
                explanation_parts.append("Different price points offer value choices")
        
        if not explanation_parts:
            explanation_parts.append("Multiple good options found")
        
        return " • ".join(explanation_parts)
