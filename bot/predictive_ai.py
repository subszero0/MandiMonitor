"""AI-Powered Predictive Engine for user interest prediction and deal analysis."""

import json
import statistics
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from logging import getLogger
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
from sqlmodel import Session, select, func

from .cache_service import engine
from .enhanced_models import (
    Product,
    ProductOffers,
    CustomerReviews,
    PriceHistory,
    SearchQuery,
    DealAlert,
)
from .models import User, Watch, Price, Click

log = getLogger(__name__)


class PredictiveEngine:
    """AI-powered predictions using existing data and machine learning models."""

    def __init__(self):
        """Initialize predictive engine with ML models."""
        self.user_interest_model = None
        self.price_prediction_model = None
        self.deal_success_model = None
        self.category_vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
        self.scaler = StandardScaler()
        
        # Cache for user patterns
        self._user_patterns_cache = {}
        self._cache_expiry = {}
        
    async def predict_user_interests(self, user_id: int, limit: int = 10) -> List[Dict]:
        """ML-based interest prediction using user's watch history and behavior.
        
        Args:
        ----
            user_id: User ID to predict interests for
            limit: Maximum number of recommendations to return
            
        Returns:
        -------
            List of predicted interest recommendations with confidence scores
        """
        try:
            log.info("Predicting interests for user %d", user_id)
            
            with Session(engine) as session:
                # Get user's watch history
                user_watches = session.exec(
                    select(Watch).where(Watch.user_id == user_id)
                ).all()
                
                if not user_watches:
                    return await self._get_default_recommendations(session)
                
                # Analyze user patterns
                user_patterns = await self._analyze_user_patterns(user_id, user_watches, session)
                
                # Find similar users using collaborative filtering
                similar_users = await self._find_similar_users(user_id, user_patterns, session)
                
                # Generate personalized recommendations
                recommendations = await self._generate_ml_recommendations(
                    user_patterns, similar_users, session, limit
                )
                
                # Add confidence scores and explanations
                enhanced_recommendations = []
                for rec in recommendations:
                    enhanced_rec = {
                        **rec,
                        "confidence_score": self._calculate_recommendation_confidence(rec, user_patterns),
                        "explanation": self._generate_recommendation_explanation(rec, user_patterns),
                        "predicted_interest_level": self._predict_interest_level(rec, user_patterns)
                    }
                    enhanced_recommendations.append(enhanced_rec)
                
                return enhanced_recommendations[:limit]
                
        except Exception as e:
            log.error("Error predicting user interests for user %d: %s", user_id, e)
            return await self._get_fallback_recommendations()
    
    async def predict_deal_success(self, asin: str, proposed_price: int) -> Dict:
        """Predict likelihood of deal success based on historical data and user behavior.
        
        Args:
        ----
            asin: Product ASIN
            proposed_price: Proposed deal price in paise
            
        Returns:
        -------
            Dict with success probability and analysis
        """
        try:
            log.info("Predicting deal success for ASIN %s at price %d", asin, proposed_price)
            
            with Session(engine) as session:
                # Get product data
                product = session.get(Product, asin)
                if not product:
                    return {"success_probability": 0.5, "confidence": "low", "reason": "No product data"}
                
                # Get historical price data
                price_history = session.exec(
                    select(PriceHistory)
                    .where(PriceHistory.asin == asin)
                    .where(PriceHistory.timestamp >= datetime.utcnow() - timedelta(days=180))
                ).all()
                
                # Get historical deal alerts and their outcomes
                deal_alerts = session.exec(
                    select(DealAlert)
                    .where(DealAlert.asin == asin)
                    .where(DealAlert.sent_at >= datetime.utcnow() - timedelta(days=90))
                ).all()
                
                # Calculate historical metrics
                historical_metrics = self._calculate_historical_deal_metrics(
                    price_history, deal_alerts, proposed_price
                )
                
                # Predict using ML model if available, otherwise use heuristics
                if self.deal_success_model:
                    features = self._extract_deal_features(product, historical_metrics, proposed_price)
                    success_probability = self.deal_success_model.predict_proba([features])[0][1]
                else:
                    success_probability = self._heuristic_deal_success(historical_metrics, proposed_price)
                
                return {
                    "success_probability": float(success_probability),
                    "confidence": self._calculate_prediction_confidence(historical_metrics),
                    "historical_metrics": historical_metrics,
                    "recommendation": self._generate_deal_recommendation(success_probability),
                    "optimal_price_range": self._suggest_optimal_price_range(historical_metrics),
                }
                
        except Exception as e:
            log.error("Error predicting deal success for ASIN %s: %s", asin, e)
            return {"success_probability": 0.5, "confidence": "low", "error": str(e)}
    
    async def predict_inventory_alerts(self, asin: str) -> Dict:
        """Predict optimal timing for inventory alerts based on stock patterns and user behavior.
        
        Args:
        ----
            asin: Product ASIN to analyze
            
        Returns:
        -------
            Dict with inventory predictions and alert recommendations
        """
        try:
            with Session(engine) as session:
                # Get product and recent offers data
                recent_offers = session.exec(
                    select(ProductOffers)
                    .where(ProductOffers.asin == asin)
                    .where(ProductOffers.fetched_at >= datetime.utcnow() - timedelta(days=30))
                ).all()
                
                if not recent_offers:
                    return {"prediction": "insufficient_data", "confidence": "low"}
                
                # Analyze stock availability patterns
                stock_patterns = self._analyze_stock_patterns(recent_offers)
                
                # Predict stock-out probability
                stockout_probability = self._predict_stockout_probability(stock_patterns)
                
                # Suggest alert timing
                alert_timing = self._suggest_alert_timing(stock_patterns, stockout_probability)
                
                return {
                    "stockout_probability": stockout_probability,
                    "days_until_stockout": alert_timing.get("days_until_stockout"),
                    "optimal_alert_time": alert_timing.get("optimal_alert_time"),
                    "urgency_level": self._calculate_urgency_level(stockout_probability),
                    "stock_patterns": stock_patterns,
                    "recommendation": self._generate_inventory_recommendation(stockout_probability, alert_timing)
                }
                
        except Exception as e:
            log.error("Error predicting inventory alerts for ASIN %s: %s", asin, e)
            return {"prediction": "error", "confidence": "low", "error": str(e)}
    
    async def train_user_interest_model(self) -> bool:
        """Train collaborative filtering model using user behavior data.
        
        Returns:
        -------
            bool: True if training successful
        """
        try:
            log.info("Training user interest prediction model")
            
            with Session(engine) as session:
                # Get user behavior data
                users = session.exec(select(User)).all()
                
                if len(users) < 10:  # Need minimum users for collaborative filtering
                    log.warning("Insufficient users for training collaborative filtering model")
                    return False
                
                # Prepare training data
                user_item_matrix = await self._build_user_item_matrix(session)
                
                if user_item_matrix.empty:
                    log.warning("No user-item interactions found for training")
                    return False
                
                # Train clustering model for user segmentation
                user_features = self._extract_user_features(user_item_matrix)
                self.user_interest_model = KMeans(n_clusters=min(5, len(users) // 3), random_state=42)
                self.user_interest_model.fit(user_features)
                
                log.info("User interest model trained successfully with %d clusters", self.user_interest_model.n_clusters)
                return True
                
        except Exception as e:
            log.error("Error training user interest model: %s", e)
            return False
    
    async def train_deal_success_model(self) -> bool:
        """Train deal success prediction model using historical deal data.
        
        Returns:
        -------
            bool: True if training successful
        """
        try:
            log.info("Training deal success prediction model")
            
            with Session(engine) as session:
                # Get historical deal data
                deal_alerts = session.exec(
                    select(DealAlert)
                    .where(DealAlert.sent_at >= datetime.utcnow() - timedelta(days=180))
                ).all()
                
                if len(deal_alerts) < 50:  # Need minimum deals for training
                    log.warning("Insufficient deal data for training model")
                    return False
                
                # Prepare training data
                features, labels = await self._prepare_deal_training_data(deal_alerts, session)
                
                if len(features) == 0:
                    log.warning("No valid training data extracted")
                    return False
                
                # Train model
                self.deal_success_model = RandomForestClassifier(
                    n_estimators=100, 
                    random_state=42,
                    max_depth=10
                )
                self.deal_success_model.fit(features, labels)
                
                log.info("Deal success model trained successfully with %d samples", len(features))
                return True
                
        except Exception as e:
            log.error("Error training deal success model: %s", e)
            return False
    
    # Private helper methods
    
    async def _analyze_user_patterns(self, user_id: int, user_watches: List[Watch], session: Session) -> Dict:
        """Analyze user behavior patterns from watch history."""
        # Check cache first
        cache_key = f"user_patterns_{user_id}"
        if (cache_key in self._user_patterns_cache and 
            cache_key in self._cache_expiry and 
            self._cache_expiry[cache_key] > datetime.utcnow()):
            return self._user_patterns_cache[cache_key]
        
        patterns = {
            "preferred_categories": defaultdict(int),
            "preferred_brands": defaultdict(int),
            "price_ranges": [],
            "discount_preferences": [],
            "search_keywords": [],
            "activity_times": [],
            "purchase_behavior": {"clicks": 0, "searches": 0, "watches": len(user_watches)}
        }
        
        # Analyze watches
        for watch in user_watches:
            if watch.brand:
                patterns["preferred_brands"][watch.brand] += 1
            if watch.max_price:
                patterns["price_ranges"].append(watch.max_price)
            if watch.min_discount:
                patterns["discount_preferences"].append(watch.min_discount)
            if watch.keywords:
                patterns["search_keywords"].extend(watch.keywords.lower().split())
            patterns["activity_times"].append(watch.created.hour)
        
        # Get search history
        search_queries = session.exec(
            select(SearchQuery).where(SearchQuery.user_id == user_id)
        ).all()
        
        patterns["purchase_behavior"]["searches"] = len(search_queries)
        
        for query in search_queries:
            if query.search_index:
                patterns["preferred_categories"][query.search_index] += 1
            patterns["search_keywords"].extend(query.query.lower().split())
        
        # Get click history
        clicks = session.exec(
            select(Click).join(Watch).where(Watch.user_id == user_id)
        ).all()
        
        patterns["purchase_behavior"]["clicks"] = len(clicks)
        
        # Cache results for 1 hour
        self._user_patterns_cache[cache_key] = patterns
        self._cache_expiry[cache_key] = datetime.utcnow() + timedelta(hours=1)
        
        return patterns
    
    async def _find_similar_users(self, user_id: int, user_patterns: Dict, session: Session) -> List[int]:
        """Find users with similar behavior patterns using collaborative filtering."""
        try:
            # Get all users
            all_users = session.exec(select(User)).all()
            
            similarity_scores = []
            
            for user in all_users:
                if user.id == user_id:
                    continue
                
                # Get patterns for comparison user
                user_watches = session.exec(
                    select(Watch).where(Watch.user_id == user.id)
                ).all()
                
                if not user_watches:
                    continue
                
                compare_patterns = await self._analyze_user_patterns(user.id, user_watches, session)
                
                # Calculate similarity score
                similarity = self._calculate_user_similarity(user_patterns, compare_patterns)
                
                if similarity > 0.3:  # Minimum similarity threshold
                    similarity_scores.append((user.id, similarity))
            
            # Sort by similarity and return top 10
            similarity_scores.sort(key=lambda x: x[1], reverse=True)
            return [user_id for user_id, _ in similarity_scores[:10]]
            
        except Exception as e:
            log.error("Error finding similar users: %s", e)
            return []
    
    def _calculate_user_similarity(self, patterns1: Dict, patterns2: Dict) -> float:
        """Calculate similarity between two user behavior patterns."""
        similarity_scores = []
        
        # Brand similarity
        brands1 = set(patterns1["preferred_brands"].keys())
        brands2 = set(patterns2["preferred_brands"].keys())
        if brands1 or brands2:
            brand_similarity = len(brands1.intersection(brands2)) / len(brands1.union(brands2))
            similarity_scores.append(brand_similarity)
        
        # Category similarity  
        cats1 = set(patterns1["preferred_categories"].keys())
        cats2 = set(patterns2["preferred_categories"].keys())
        if cats1 or cats2:
            cat_similarity = len(cats1.intersection(cats2)) / len(cats1.union(cats2))
            similarity_scores.append(cat_similarity)
        
        # Price range similarity
        if patterns1["price_ranges"] and patterns2["price_ranges"]:
            avg_price1 = statistics.mean(patterns1["price_ranges"])
            avg_price2 = statistics.mean(patterns2["price_ranges"])
            price_diff = abs(avg_price1 - avg_price2)
            max_price = max(avg_price1, avg_price2)
            price_similarity = 1 - (price_diff / max_price) if max_price > 0 else 1
            similarity_scores.append(price_similarity)
        
        return statistics.mean(similarity_scores) if similarity_scores else 0
    
    async def _generate_ml_recommendations(
        self, 
        user_patterns: Dict, 
        similar_users: List[int], 
        session: Session, 
        limit: int
    ) -> List[Dict]:
        """Generate ML-based recommendations using collaborative filtering."""
        recommendations = []
        
        # Get products liked by similar users
        similar_user_products = defaultdict(int)
        
        for similar_user_id in similar_users:
            similar_watches = session.exec(
                select(Watch).where(Watch.user_id == similar_user_id)
            ).all()
            
            for watch in similar_watches:
                if watch.asin:
                    similar_user_products[watch.asin] += 1
        
        # Score and rank recommendations
        for asin, count in similar_user_products.most_common(limit * 2):
            try:
                product = session.get(Product, asin)
                if not product:
                    continue
                
                # Calculate recommendation score
                score = self._calculate_recommendation_score(
                    product, user_patterns, count, len(similar_users)
                )
                
                if score > 0.4:  # Minimum score threshold
                    recommendations.append({
                        "asin": asin,
                        "title": product.title,
                        "brand": product.brand,
                        "category": product.product_group,
                        "score": score,
                        "source": "collaborative_filtering",
                        "similar_user_count": count
                    })
                    
            except Exception as e:
                log.warning("Error processing recommendation for ASIN %s: %s", asin, e)
                continue
        
        # Sort by score and return top recommendations
        recommendations.sort(key=lambda x: x["score"], reverse=True)
        return recommendations[:limit]
    
    def _calculate_recommendation_score(
        self, 
        product: Product, 
        user_patterns: Dict, 
        similar_user_count: int, 
        total_similar_users: int
    ) -> float:
        """Calculate recommendation score for a product based on user patterns."""
        score = 0.0
        
        # Base score from similar user preference
        base_score = similar_user_count / max(total_similar_users, 1)
        score += base_score * 0.4
        
        # Brand preference bonus
        if product.brand and product.brand in user_patterns["preferred_brands"]:
            brand_strength = user_patterns["preferred_brands"][product.brand]
            score += min(brand_strength * 0.1, 0.3)
        
        # Category preference bonus
        if product.product_group and product.product_group in user_patterns["preferred_categories"]:
            cat_strength = user_patterns["preferred_categories"][product.product_group]
            score += min(cat_strength * 0.1, 0.2)
        
        # Keyword matching bonus
        if user_patterns["search_keywords"] and product.title:
            title_words = set(product.title.lower().split())
            user_keywords = set(user_patterns["search_keywords"])
            keyword_overlap = len(title_words.intersection(user_keywords))
            score += min(keyword_overlap * 0.05, 0.1)
        
        return min(score, 1.0)
    
    def _calculate_recommendation_confidence(self, recommendation: Dict, user_patterns: Dict) -> float:
        """Calculate confidence score for a recommendation."""
        confidence = recommendation["score"]
        
        # Boost confidence if multiple similar users liked it
        if recommendation.get("similar_user_count", 0) > 3:
            confidence += 0.1
        
        # Boost confidence if it matches user's preferred brands/categories
        if (recommendation.get("brand") in user_patterns["preferred_brands"] or
            recommendation.get("category") in user_patterns["preferred_categories"]):
            confidence += 0.1
            
        return min(confidence, 1.0)
    
    def _generate_recommendation_explanation(self, recommendation: Dict, user_patterns: Dict) -> str:
        """Generate human-readable explanation for recommendation."""
        reasons = []
        
        if recommendation.get("similar_user_count", 0) > 0:
            reasons.append(f"{recommendation['similar_user_count']} similar users are interested in this")
        
        if recommendation.get("brand") in user_patterns["preferred_brands"]:
            reasons.append(f"You've shown interest in {recommendation['brand']} products")
        
        if recommendation.get("category") in user_patterns["preferred_categories"]:
            reasons.append(f"Matches your {recommendation['category']} category preference")
        
        if not reasons:
            reasons.append("Based on your overall browsing patterns")
        
        return " • ".join(reasons)
    
    def _predict_interest_level(self, recommendation: Dict, user_patterns: Dict) -> str:
        """Predict user's interest level in the recommendation."""
        score = recommendation["score"]
        
        if score >= 0.8:
            return "very_high"
        elif score >= 0.6:
            return "high" 
        elif score >= 0.4:
            return "medium"
        else:
            return "low"
    
    async def _get_default_recommendations(self, session: Session) -> List[Dict]:
        """Get default recommendations for new users."""
        try:
            # Get popular products based on watch count
            popular_products = session.exec(
                select(Watch.asin, func.count(Watch.id).label('watch_count'))
                .where(Watch.asin.isnot(None))
                .group_by(Watch.asin)
                .order_by(func.count(Watch.id).desc())
                .limit(10)
            ).all()
            
            recommendations = []
            for asin, watch_count in popular_products:
                product = session.get(Product, asin)
                if product:
                    recommendations.append({
                        "asin": asin,
                        "title": product.title,
                        "brand": product.brand,
                        "category": product.product_group,
                        "score": 0.5,
                        "source": "trending",
                        "explanation": f"Popular product with {watch_count} users tracking it",
                        "confidence_score": 0.6,
                        "predicted_interest_level": "medium"
                    })
            
            return recommendations
            
        except Exception as e:
            log.error("Error getting default recommendations: %s", e)
            return await self._get_fallback_recommendations()
    
    async def _get_fallback_recommendations(self) -> List[Dict]:
        """Get basic fallback recommendations when all else fails."""
        return [
            {
                "asin": "fallback",
                "title": "Check out trending deals",
                "brand": "Various",
                "category": "General",
                "score": 0.3,
                "source": "fallback",
                "explanation": "Explore popular categories to discover new products",
                "confidence_score": 0.3,
                "predicted_interest_level": "low"
            }
        ]
    
    def _calculate_historical_deal_metrics(
        self, 
        price_history: List[PriceHistory], 
        deal_alerts: List[DealAlert], 
        proposed_price: int
    ) -> Dict:
        """Calculate historical metrics for deal success prediction."""
        if not price_history:
            return {"insufficient_data": True}
        
        prices = [p.price for p in price_history]
        
        metrics = {
            "avg_price": statistics.mean(prices),
            "min_price": min(prices),
            "max_price": max(prices),
            "price_volatility": statistics.stdev(prices) if len(prices) > 1 else 0,
            "proposed_vs_avg": proposed_price / statistics.mean(prices) if prices else 1,
            "proposed_vs_min": proposed_price / min(prices) if prices else 1,
            "historical_deals": len(deal_alerts),
            "recent_trend": self._calculate_price_trend(prices[-10:] if len(prices) > 10 else prices)
        }
        
        return metrics
    
    def _calculate_price_trend(self, recent_prices: List[int]) -> str:
        """Calculate recent price trend direction."""
        if len(recent_prices) < 2:
            return "stable"
        
        first_half = recent_prices[:len(recent_prices)//2]
        second_half = recent_prices[len(recent_prices)//2:]
        
        avg_first = statistics.mean(first_half)
        avg_second = statistics.mean(second_half)
        
        change_pct = (avg_second - avg_first) / avg_first * 100
        
        if change_pct > 5:
            return "increasing"
        elif change_pct < -5:
            return "decreasing"
        else:
            return "stable"
    
    def _heuristic_deal_success(self, metrics: Dict, proposed_price: int) -> float:
        """Calculate deal success probability using heuristics when ML model unavailable."""
        if metrics.get("insufficient_data"):
            return 0.5
        
        score = 0.5  # Base probability
        
        # Price attractiveness
        if metrics["proposed_vs_min"] < 1.1:  # Within 10% of historical minimum
            score += 0.3
        elif metrics["proposed_vs_avg"] < 0.8:  # 20% below average
            score += 0.2
        
        # Trend consideration
        if metrics["recent_trend"] == "increasing":
            score += 0.1  # Good time to buy before price goes up more
        elif metrics["recent_trend"] == "decreasing":
            score -= 0.1  # Might drop further
        
        # Historical deal frequency
        if metrics["historical_deals"] > 5:
            score += 0.1  # Product has deal history
        
        return max(0.0, min(1.0, score))
    
    def _calculate_prediction_confidence(self, metrics: Dict) -> str:
        """Calculate confidence level for predictions."""
        if metrics.get("insufficient_data"):
            return "low"
        
        # Base confidence on data availability
        data_points = len(metrics)
        if data_points > 6:
            return "high"
        elif data_points > 4:
            return "medium"
        else:
            return "low"
    
    def _generate_deal_recommendation(self, success_probability: float) -> str:
        """Generate actionable recommendation based on success probability."""
        if success_probability >= 0.8:
            return "Excellent deal - highly recommended!"
        elif success_probability >= 0.6:
            return "Good deal - worth considering"
        elif success_probability >= 0.4:
            return "Fair deal - compare with alternatives"
        else:
            return "Poor deal - wait for better opportunity"
    
    def _suggest_optimal_price_range(self, metrics: Dict) -> Dict:
        """Suggest optimal price range for the product."""
        if metrics.get("insufficient_data"):
            return {"suggestion": "insufficient_data"}
        
        # Calculate price ranges based on historical data
        avg_price = metrics["avg_price"]
        min_price = metrics["min_price"]
        
        return {
            "excellent_deal": f"₹{min_price / 100:.2f} - ₹{min_price * 1.1 / 100:.2f}",
            "good_deal": f"₹{min_price * 1.1 / 100:.2f} - ₹{avg_price * 0.8 / 100:.2f}",
            "fair_price": f"₹{avg_price * 0.8 / 100:.2f} - ₹{avg_price / 100:.2f}",
            "current_range": f"Around ₹{avg_price / 100:.2f}"
        }
    
    def _analyze_stock_patterns(self, offers: List[ProductOffers]) -> Dict:
        """Analyze stock availability patterns from offer history."""
        patterns = {
            "total_checks": len(offers),
            "in_stock_count": 0,
            "out_of_stock_count": 0,
            "stock_changes": 0,
            "avg_stock_duration": 0
        }
        
        previous_stock = None
        stock_periods = []
        current_period_start = None
        
        for offer in sorted(offers, key=lambda x: x.fetched_at):
            is_in_stock = offer.availability_type == "InStock"
            patterns["in_stock_count" if is_in_stock else "out_of_stock_count"] += 1
            
            # Track stock changes
            if previous_stock is not None and previous_stock != is_in_stock:
                patterns["stock_changes"] += 1
                if current_period_start:
                    period_duration = (offer.fetched_at - current_period_start).total_seconds() / 3600  # hours
                    stock_periods.append(period_duration)
                current_period_start = offer.fetched_at
            elif current_period_start is None:
                current_period_start = offer.fetched_at
            
            previous_stock = is_in_stock
        
        if stock_periods:
            patterns["avg_stock_duration"] = statistics.mean(stock_periods)
        
        return patterns
    
    def _predict_stockout_probability(self, stock_patterns: Dict) -> float:
        """Predict probability of stock-out based on patterns."""
        if stock_patterns["total_checks"] < 5:
            return 0.5  # Insufficient data
        
        # Calculate stock-out frequency
        stockout_rate = stock_patterns["out_of_stock_count"] / stock_patterns["total_checks"]
        
        # Adjust for stock change frequency (higher changes = more unstable)
        change_rate = stock_patterns["stock_changes"] / max(stock_patterns["total_checks"] - 1, 1)
        
        # Combine factors
        probability = (stockout_rate * 0.7) + (change_rate * 0.3)
        
        return min(max(probability, 0.0), 1.0)
    
    def _suggest_alert_timing(self, stock_patterns: Dict, stockout_probability: float) -> Dict:
        """Suggest optimal timing for inventory alerts."""
        timing = {}
        
        if stockout_probability > 0.7:
            timing["days_until_stockout"] = 1
            timing["optimal_alert_time"] = "immediate"
        elif stockout_probability > 0.5:
            timing["days_until_stockout"] = 3
            timing["optimal_alert_time"] = "within_24_hours"
        elif stockout_probability > 0.3:
            timing["days_until_stockout"] = 7
            timing["optimal_alert_time"] = "within_week"
        else:
            timing["days_until_stockout"] = 30
            timing["optimal_alert_time"] = "monitor_monthly"
        
        return timing
    
    def _calculate_urgency_level(self, stockout_probability: float) -> str:
        """Calculate urgency level for inventory alerts."""
        if stockout_probability >= 0.8:
            return "critical"
        elif stockout_probability >= 0.6:
            return "high"
        elif stockout_probability >= 0.4:
            return "medium"
        else:
            return "low"
    
    def _generate_inventory_recommendation(self, stockout_probability: float, alert_timing: Dict) -> str:
        """Generate inventory management recommendation."""
        if stockout_probability >= 0.8:
            return "Stock-out imminent - alert users immediately!"
        elif stockout_probability >= 0.6:
            return "High stock-out risk - send proactive alerts"
        elif stockout_probability >= 0.4:
            return "Monitor closely - prepare alerts"
        else:
            return "Stock levels stable - routine monitoring"
    
    async def _build_user_item_matrix(self, session: Session) -> pd.DataFrame:
        """Build user-item interaction matrix for collaborative filtering."""
        try:
            # Get all user-product interactions (watches, clicks, searches)
            interactions = []
            
            # Watches (highest weight)
            watches = session.exec(select(Watch)).all()
            for watch in watches:
                if watch.asin:
                    interactions.append({
                        "user_id": watch.user_id,
                        "asin": watch.asin,
                        "interaction_type": "watch",
                        "weight": 3.0,
                        "timestamp": watch.created
                    })
            
            # Clicks (medium weight)
            clicks = session.exec(select(Click).join(Watch)).all()
            for click in clicks:
                interactions.append({
                    "user_id": click.watch_id,  # This should be improved to get actual user_id
                    "asin": click.asin,
                    "interaction_type": "click",
                    "weight": 2.0,
                    "timestamp": click.clicked_at
                })
            
            # Create DataFrame
            if not interactions:
                return pd.DataFrame()
            
            df = pd.DataFrame(interactions)
            
            # Create user-item matrix
            user_item_matrix = df.pivot_table(
                index='user_id',
                columns='asin',
                values='weight',
                aggfunc='sum',
                fill_value=0
            )
            
            return user_item_matrix
            
        except Exception as e:
            log.error("Error building user-item matrix: %s", e)
            return pd.DataFrame()
    
    def _extract_user_features(self, user_item_matrix: pd.DataFrame) -> np.ndarray:
        """Extract user features for clustering."""
        if user_item_matrix.empty:
            return np.array([])
        
        # Simple feature extraction - can be enhanced with more sophisticated methods
        features = []
        
        for user_id in user_item_matrix.index:
            user_data = user_item_matrix.loc[user_id]
            
            user_features = [
                user_data.sum(),  # Total interactions
                (user_data > 0).sum(),  # Number of unique items
                user_data.mean(),  # Average interaction strength
                user_data.std(),  # Interaction variance
                (user_data >= 3).sum(),  # High-engagement items
            ]
            
            features.append(user_features)
        
        return np.array(features)
    
    async def _prepare_deal_training_data(self, deal_alerts: List[DealAlert], session: Session) -> Tuple[List, List]:
        """Prepare training data for deal success model."""
        features = []
        labels = []
        
        for alert in deal_alerts:
            try:
                # Get product data
                product = session.get(Product, alert.asin)
                if not product:
                    continue
                
                # Get price history around the deal
                price_history = session.exec(
                    select(PriceHistory)
                    .where(PriceHistory.asin == alert.asin)
                    .where(PriceHistory.timestamp <= alert.sent_at)
                    .where(PriceHistory.timestamp >= alert.sent_at - timedelta(days=30))
                ).all()
                
                # Extract features
                deal_features = self._extract_deal_features(
                    product,
                    self._calculate_historical_deal_metrics(price_history, [], alert.current_price),
                    alert.current_price
                )
                
                # Determine success label (simplified - can be enhanced)
                # For now, consider a deal successful if it was clicked on
                clicks_after_alert = session.exec(
                    select(Click)
                    .where(Click.asin == alert.asin)
                    .where(Click.clicked_at >= alert.sent_at)
                    .where(Click.clicked_at <= alert.sent_at + timedelta(days=7))
                ).all()
                
                success_label = 1 if len(clicks_after_alert) > 0 else 0
                
                features.append(deal_features)
                labels.append(success_label)
                
            except Exception as e:
                log.warning("Error processing deal alert %d: %s", alert.id, e)
                continue
        
        return features, labels
    
    def _extract_deal_features(self, product: Product, historical_metrics: Dict, proposed_price: int) -> List[float]:
        """Extract features for deal success prediction."""
        features = []
        
        # Price-based features
        features.append(historical_metrics.get("proposed_vs_avg", 1.0))
        features.append(historical_metrics.get("proposed_vs_min", 1.0))
        features.append(historical_metrics.get("price_volatility", 0.0))
        
        # Product features
        features.append(1.0 if product.brand else 0.0)
        features.append(len(product.title.split()) if product.title else 0)
        features.append(len(product.features_list) if product.features_list else 0)
        
        # Historical features
        features.append(historical_metrics.get("historical_deals", 0))
        
        # Trend features
        trend_mapping = {"increasing": 1.0, "stable": 0.0, "decreasing": -1.0}
        features.append(trend_mapping.get(historical_metrics.get("recent_trend"), 0.0))
        
        return features


# Global instance for use across the application
predictive_engine = PredictiveEngine()
