"""Natural Language Processing Handler for enhanced text parsing and intent detection."""

import re
from datetime import datetime, timezone
from logging import getLogger
from typing import Dict, List, Optional, Tuple

from .patterns import PAT_ASIN, PAT_BRAND, PAT_DISCOUNT, PAT_PRICE_UNDER, PAT_SIZE, PAT_MEMORY
from .watch_parser import parse_watch, normalize_price_input

log = getLogger(__name__)


class NaturalLanguageHandler:
    """Enhanced NLP built on existing text handling with intent detection."""

    def __init__(self):
        """Initialize NLP handler with patterns and models."""
        self.intent_patterns = self._build_intent_patterns()
        self.feature_extractors = self._build_feature_extractors()
        self.comparison_indicators = self._build_comparison_indicators()

    async def parse_product_query(self, user_message: str) -> Dict:
        """Enhanced version of existing parse_watch with intent detection.

        Args:
        ----
            user_message: User's natural language message

        Returns:
        -------
            Enhanced parsing results with intent, confidence, and suggestions
        """
        try:
            log.info("Parsing product query: %s", user_message[:50])

            # Start with existing parser
            basic_parse = parse_watch(user_message)

            # Add NLP enhancements
            enhanced_parse = await self._enhance_with_nlp(user_message, basic_parse)

            # Calculate confidence
            confidence = self._calculate_confidence(enhanced_parse)

            # Generate suggestions
            suggestions = await self._generate_suggestions(enhanced_parse)

            return {
                **basic_parse,
                **enhanced_parse,
                "nlp_confidence": confidence,
                "suggestions": suggestions,
                "processed_at": datetime.now(timezone.utc),
            }

        except Exception as e:
            log.error("Failed to parse product query: %s", e)
            return {
                **parse_watch(user_message),
                "nlp_confidence": 0.0,
                "error": str(e),
                "suggestions": [],
            }

    async def detect_intent(self, message: str) -> Dict:
        """Detect user intent from message with >80% target accuracy.

        Args:
        ----
            message: User message

        Returns:
        -------
            Intent detection results with confidence
        """
        try:
            message_lower = message.lower().strip()
            detected_intents = []

            # Check each intent pattern
            for intent_type, patterns in self.intent_patterns.items():
                matches = []
                for pattern in patterns:
                    if isinstance(pattern, str):
                        if pattern in message_lower:
                            matches.append(pattern)
                    else:  # regex pattern
                        if pattern.search(message_lower):
                            matches.append(pattern.pattern)

                if matches:
                    # Calculate intent confidence based on match quality
                    confidence = self._calculate_intent_confidence(
                        intent_type, matches, message_lower
                    )
                    detected_intents.append({
                        "intent": intent_type,
                        "confidence": confidence,
                        "matched_patterns": matches,
                    })

            # Sort by confidence and return top intent
            detected_intents.sort(key=lambda x: x["confidence"], reverse=True)

            if detected_intents:
                primary_intent = detected_intents[0]
                secondary_intents = detected_intents[1:3]  # Top 2 alternatives

                return {
                    "primary_intent": primary_intent["intent"],
                    "confidence": primary_intent["confidence"],
                    "all_intents": detected_intents,
                    "secondary_intents": [i["intent"] for i in secondary_intents],
                    "is_confident": primary_intent["confidence"] >= 0.8,
                }
            else:
                return {
                    "primary_intent": "unknown",
                    "confidence": 0.0,
                    "all_intents": [],
                    "secondary_intents": [],
                    "is_confident": False,
                }

        except Exception as e:
            log.error("Failed to detect intent: %s", e)
            return {
                "primary_intent": "unknown",
                "confidence": 0.0,
                "error": str(e),
                "is_confident": False,
            }

    async def generate_smart_response(
        self, intent_data: Dict, parse_data: Dict
    ) -> Dict:
        """Generate smart response based on intent and parsed data.

        Args:
        ----
            intent_data: Intent detection results
            parse_data: Parsed product query data

        Returns:
        -------
            Smart response with actions and suggestions
        """
        try:
            intent = intent_data.get("primary_intent", "unknown")
            confidence = intent_data.get("confidence", 0.0)

            response = {
                "response_type": intent,
                "confidence": confidence,
                "actions": [],
                "message": "",
                "follow_up_questions": [],
            }

            if intent == "search_product":
                response.update(await self._handle_search_intent(parse_data))
            elif intent == "create_watch":
                response.update(await self._handle_watch_intent(parse_data))
            elif intent == "compare_products":
                response.update(await self._handle_comparison_intent(parse_data))
            elif intent == "price_inquiry":
                response.update(await self._handle_price_inquiry(parse_data))
            elif intent == "deal_hunting":
                response.update(await self._handle_deal_hunting(parse_data))
            elif intent == "feature_search":
                response.update(await self._handle_feature_search(parse_data))
            else:
                response.update(await self._handle_unknown_intent(parse_data))

            return response

        except Exception as e:
            log.error("Failed to generate smart response: %s", e)
            return {
                "response_type": "error",
                "confidence": 0.0,
                "actions": [],
                "message": "I couldn't understand your request. Could you try rephrasing?",
                "error": str(e),
            }

    async def handle_comparison_request(
        self, message: str, products: Optional[List[str]] = None
    ) -> Dict:
        """Handle comparison requests with enhanced understanding.

        Args:
        ----
            message: User's comparison request
            products: Optional list of ASINs to compare

        Returns:
        -------
            Comparison handling results
        """
        try:
            # Detect comparison type
            comparison_type = self._detect_comparison_type(message)

            # Extract comparison criteria
            criteria = self._extract_comparison_criteria(message)

            # If no products provided, try to extract from message
            if not products:
                products = self._extract_products_from_message(message)

            return {
                "comparison_type": comparison_type,
                "criteria": criteria,
                "products": products or [],
                "comparison_aspects": self._determine_comparison_aspects(message),
                "priority_factors": self._extract_priority_factors(message),
                "user_preferences": self._extract_user_preferences(message),
            }

        except Exception as e:
            log.error("Failed to handle comparison request: %s", e)
            return {
                "comparison_type": "unknown",
                "criteria": [],
                "products": [],
                "error": str(e),
            }

    # Private helper methods

    async def _enhance_with_nlp(self, message: str, basic_parse: Dict) -> Dict:
        """Add NLP enhancements to basic parse results."""
        enhancements = {}

        # Extract additional features
        enhancements["extracted_features"] = self._extract_features(message)

        # Detect intent
        intent_data = await self.detect_intent(message)
        enhancements["intent"] = intent_data

        # Extract urgency indicators
        enhancements["urgency"] = self._detect_urgency(message)

        # Extract price sensitivity
        enhancements["price_sensitivity"] = self._detect_price_sensitivity(message)

        # Extract quality preferences
        enhancements["quality_preferences"] = self._extract_quality_preferences(message)

        # Extract usage context
        enhancements["usage_context"] = self._extract_usage_context(message)

        return enhancements

    def _calculate_confidence(self, enhanced_parse: Dict) -> float:
        """Calculate overall confidence score for parsing results."""
        try:
            confidence_factors = []

            # Intent confidence
            intent_data = enhanced_parse.get("intent", {})
            if intent_data.get("confidence"):
                confidence_factors.append(intent_data["confidence"])

            # Feature extraction confidence
            features = enhanced_parse.get("extracted_features", {})
            if features:
                feature_confidence = len(features) / 10.0  # Max 10 features expected
                confidence_factors.append(min(1.0, feature_confidence))

            # Basic parsing confidence
            basic_confidence = 0.0
            if enhanced_parse.get("asin"):
                basic_confidence += 0.3
            if enhanced_parse.get("brand"):
                basic_confidence += 0.2
            if enhanced_parse.get("max_price"):
                basic_confidence += 0.2
            if enhanced_parse.get("keywords"):
                basic_confidence += 0.3

            confidence_factors.append(basic_confidence)

            # Return average confidence
            return sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.0

        except Exception:
            return 0.0

    async def _generate_suggestions(self, enhanced_parse: Dict) -> List[str]:
        """Generate helpful suggestions based on parsing results."""
        suggestions = []

        try:
            # Suggest based on missing information
            if not enhanced_parse.get("asin") and not enhanced_parse.get("brand"):
                suggestions.append("Try including a brand name for better results")

            if not enhanced_parse.get("max_price"):
                suggestions.append("Consider setting a price limit (e.g., 'under 30k')")

            # Suggest based on intent
            intent = enhanced_parse.get("intent", {}).get("primary_intent")
            if intent == "search_product":
                suggestions.append("I can help you find products. Try: 'Find Samsung phones under 25k'")
            elif intent == "create_watch":
                suggestions.append("I can create a price watch. Try: 'Watch iPhone deals with 20% off'")

            # Feature-based suggestions
            features = enhanced_parse.get("extracted_features", {})
            if "gaming" in str(features).lower():
                suggestions.append("For gaming, consider RAM, graphics, and refresh rate")

            return suggestions[:3]  # Limit to top 3 suggestions

        except Exception:
            return ["Try being more specific about what you're looking for"]

    def _build_intent_patterns(self) -> Dict[str, List]:
        """Build intent detection patterns."""
        return {
            "search_product": [
                "find", "search", "show", "looking for", "need", "want",
                re.compile(r"\b(find|search|show|need|want)\b"),
                re.compile(r"\b(looking for|searching for)\b"),
            ],
            "create_watch": [
                "watch", "alert", "notify", "track", "monitor", "follow",
                re.compile(r"\b(watch|alert|notify|track|monitor)\b"),
                re.compile(r"\b(price drop|deal alert)\b"),
            ],
            "compare_products": [
                "compare", "versus", "vs", "difference", "which is better",
                re.compile(r"\b(compare|versus|vs|difference)\b"),
                re.compile(r"\bwhich (is )?better\b"),
            ],
            "price_inquiry": [
                "price", "cost", "how much", "what's the price", "pricing",
                re.compile(r"\b(price|cost|pricing)\b"),
                re.compile(r"\bhow much\b"),
            ],
            "deal_hunting": [
                "deal", "discount", "offer", "sale", "cheap", "best price",
                re.compile(r"\b(deal|discount|offer|sale|cheap)\b"),
                re.compile(r"\bbest price\b"),
            ],
            "feature_search": [
                "features", "specs", "specifications", "what can it do",
                re.compile(r"\b(features|specs|specifications)\b"),
                re.compile(r"\bwhat (can it|does it)\b"),
            ],
        }

    def _build_feature_extractors(self) -> Dict[str, re.Pattern]:
        """Build feature extraction patterns."""
        return {
            "gaming": re.compile(r"\b(gaming|gamer|game|fps|rgb|mechanical)\b", re.I),
            "professional": re.compile(r"\b(professional|work|office|business|productivity)\b", re.I),
            "budget": re.compile(r"\b(budget|cheap|affordable|economical|low cost)\b", re.I),
            "premium": re.compile(r"\b(premium|high end|flagship|expensive|luxury)\b", re.I),
            "portable": re.compile(r"\b(portable|lightweight|travel|compact|mini)\b", re.I),
            "wireless": re.compile(r"\b(wireless|bluetooth|wifi|cordless)\b", re.I),
            "waterproof": re.compile(r"\b(waterproof|water resistant|ip67|ip68)\b", re.I),
            "fast_charging": re.compile(r"\b(fast charg|quick charg|rapid charg|fast charging|quick charging|rapid charging)\b", re.I),
        }

    def _build_comparison_indicators(self) -> List[str]:
        """Build comparison indicator patterns."""
        return [
            "vs", "versus", "compared to", "compare", "difference between",
            "which is better", "should I buy", "or", "alternative to"
        ]

    def _calculate_intent_confidence(
        self, intent_type: str, matches: List[str], message: str
    ) -> float:
        """Calculate confidence for specific intent detection."""
        try:
            base_confidence = len(matches) * 0.3  # Increased base score per match
            
            # Boost confidence for specific patterns
            message_lower = message.lower()
            if intent_type == "search_product" and any(word in message_lower for word in ["find", "search", "looking", "show", "need"]):
                base_confidence += 0.4
            elif intent_type == "create_watch" and any(word in message_lower for word in ["watch", "alert", "notify", "track", "monitor"]):
                base_confidence += 0.4
            elif intent_type == "compare_products" and any(word in message_lower for word in ["compare", "vs", "versus", "difference", "which is better"]):
                base_confidence += 0.5
            elif intent_type == "price_inquiry" and any(word in message_lower for word in ["price", "cost", "how much"]):
                base_confidence += 0.4
            elif intent_type == "deal_hunting" and any(word in message_lower for word in ["deal", "discount", "offer", "cheap", "best price"]):
                base_confidence += 0.4

            # Message length factor (longer messages tend to be more specific)
            length_factor = min(1.0, len(message.split()) / 8.0)
            base_confidence += length_factor * 0.15

            # Brand or product mention increases confidence
            if any(brand in message_lower for brand in ["samsung", "apple", "iphone", "macbook", "dell", "hp", "sony"]):
                base_confidence += 0.2

            return min(1.0, base_confidence)

        except Exception:
            return 0.0

    def _extract_features(self, message: str) -> Dict:
        """Extract product features from message."""
        features = {}
        
        for feature_name, pattern in self.feature_extractors.items():
            if pattern.search(message):
                features[feature_name] = True

        # Extract size if present
        size_match = PAT_SIZE.search(message)
        if size_match:
            features["size"] = size_match.group(1) + " inch"

        # Extract memory/storage
        memory_match = PAT_MEMORY.search(message)
        if memory_match:
            features["memory"] = memory_match.group(0)

        return features

    def _detect_urgency(self, message: str) -> str:
        """Detect urgency level from message."""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["urgent", "asap", "immediately", "right now", "today"]):
            return "high"
        elif any(word in message_lower for word in ["soon", "quick", "fast", "this week"]):
            return "medium"
        else:
            return "low"

    def _detect_price_sensitivity(self, message: str) -> str:
        """Detect price sensitivity from message."""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["cheap", "budget", "affordable", "low cost", "economical"]):
            return "high"
        elif any(word in message_lower for word in ["premium", "expensive", "high end", "luxury", "flagship"]):
            return "low"
        else:
            return "medium"

    def _extract_quality_preferences(self, message: str) -> List[str]:
        """Extract quality preferences from message."""
        preferences = []
        message_lower = message.lower()
        
        quality_indicators = {
            "durability": ["durable", "long lasting", "sturdy", "robust"],
            "performance": ["fast", "powerful", "high performance", "speed"],
            "design": ["beautiful", "sleek", "stylish", "design", "aesthetic"],
            "brand": ["branded", "reputed", "popular", "well known"],
        }
        
        for quality, indicators in quality_indicators.items():
            if any(indicator in message_lower for indicator in indicators):
                preferences.append(quality)
        
        return preferences

    def _extract_usage_context(self, message: str) -> List[str]:
        """Extract usage context from message."""
        contexts = []
        message_lower = message.lower()
        
        context_indicators = {
            "work": ["work", "office", "professional", "business"],
            "gaming": ["gaming", "games", "gamer", "fps"],
            "home": ["home", "family", "personal", "household"],
            "travel": ["travel", "portable", "mobile", "on the go"],
            "study": ["study", "student", "college", "school"],
        }
        
        for context, indicators in context_indicators.items():
            if any(indicator in message_lower for indicator in indicators):
                contexts.append(context)
        
        return contexts

    # Intent-specific handlers

    async def _handle_search_intent(self, parse_data: Dict) -> Dict:
        """Handle search product intent."""
        return {
            "actions": ["search_products"],
            "message": "I'll help you find products matching your criteria.",
            "follow_up_questions": [
                "What's your budget range?",
                "Any specific brand preference?",
                "Any particular features you need?"
            ] if not parse_data.get("max_price") else []
        }

    async def _handle_watch_intent(self, parse_data: Dict) -> Dict:
        """Handle create watch intent."""
        return {
            "actions": ["create_watch", "suggest_parameters"],
            "message": "I'll set up a price watch for you.",
            "follow_up_questions": [
                "What discount percentage would you like alerts for?",
                "How often should I check for deals?"
            ] if not parse_data.get("min_discount") else []
        }

    async def _handle_comparison_intent(self, parse_data: Dict) -> Dict:
        """Handle product comparison intent."""
        return {
            "actions": ["find_alternatives", "compare_products"],
            "message": "I'll help you compare products and find the best option.",
            "follow_up_questions": [
                "What factors are most important to you?",
                "Do you have specific products in mind to compare?"
            ]
        }

    async def _handle_price_inquiry(self, parse_data: Dict) -> Dict:
        """Handle price inquiry intent."""
        return {
            "actions": ["get_price_info", "show_price_history"],
            "message": "I'll get you the latest pricing information.",
            "follow_up_questions": [
                "Would you like price history?",
                "Should I set up a price alert?"
            ]
        }

    async def _handle_deal_hunting(self, parse_data: Dict) -> Dict:
        """Handle deal hunting intent."""
        return {
            "actions": ["find_deals", "setup_deal_alerts"],
            "message": "I'll find the best deals for you!",
            "follow_up_questions": [
                "What discount percentage makes it worth buying?",
                "Any specific time frame you're looking at?"
            ]
        }

    async def _handle_feature_search(self, parse_data: Dict) -> Dict:
        """Handle feature search intent."""
        return {
            "actions": ["show_features", "find_by_features"],
            "message": "I'll help you find products with the features you need.",
            "follow_up_questions": [
                "Which features are must-haves vs nice-to-haves?",
                "What will you primarily use this for?"
            ]
        }

    async def _handle_unknown_intent(self, parse_data: Dict) -> Dict:
        """Handle unknown intent."""
        return {
            "actions": ["ask_clarification"],
            "message": "I can help you search for products, create price watches, or compare options. What would you like to do?",
            "follow_up_questions": [
                "Are you looking to buy something specific?",
                "Do you want to compare products?",
                "Should I set up a price alert?"
            ]
        }

    # Comparison handling methods

    def _detect_comparison_type(self, message: str) -> str:
        """Detect type of comparison requested."""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["features", "specs", "camera", "battery", "display", "performance"]):
            return "feature_comparison"
        elif "price" in message_lower or "cost" in message_lower:
            return "price_comparison"
        elif "review" in message_lower or "rating" in message_lower:
            return "review_comparison"
        else:
            return "general_comparison"

    def _extract_comparison_criteria(self, message: str) -> List[str]:
        """Extract comparison criteria from message."""
        criteria = []
        message_lower = message.lower()
        
        criteria_keywords = {
            "price": ["price", "cost", "expensive", "cheap"],
            "performance": ["performance", "speed", "fast", "powerful"],
            "battery": ["battery", "battery life", "charge"],
            "camera": ["camera", "photo", "picture", "selfie"],
            "display": ["display", "screen", "resolution"],
            "storage": ["storage", "memory", "gb", "tb"],
        }
        
        for criterion, keywords in criteria_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                criteria.append(criterion)
        
        return criteria

    def _extract_products_from_message(self, message: str) -> List[str]:
        """Extract product ASINs from comparison message."""
        asins = []
        
        # Use existing ASIN pattern
        for match in PAT_ASIN.finditer(message):
            potential_asin = match.group(1) if match.group(1) else match.group(2)
            if potential_asin and len(potential_asin) == 10 and potential_asin.startswith("B"):
                asins.append(potential_asin)
        
        return asins

    def _determine_comparison_aspects(self, message: str) -> List[str]:
        """Determine what aspects to compare."""
        aspects = ["price", "features", "reviews"]  # Default aspects
        
        message_lower = message.lower()
        if "spec" in message_lower:
            aspects.extend(["specifications", "performance"])
        if "design" in message_lower:
            aspects.append("design")
        if "brand" in message_lower:
            aspects.append("brand")
        
        return list(set(aspects))

    def _extract_priority_factors(self, message: str) -> List[str]:
        """Extract priority factors from message."""
        factors = []
        message_lower = message.lower()
        
        priority_indicators = {
            "price": ["budget", "cheap", "affordable", "cost"],
            "quality": ["quality", "durable", "reliable"],
            "performance": ["performance", "speed", "fast"],
            "brand": ["brand", "branded", "popular"],
        }
        
        for factor, indicators in priority_indicators.items():
            if any(indicator in message_lower for indicator in indicators):
                factors.append(factor)
        
        return factors

    def _extract_user_preferences(self, message: str) -> Dict:
        """Extract user preferences from comparison message."""
        preferences = {}
        
        # Extract budget preference
        if "budget" in message.lower() or "cheap" in message.lower():
            preferences["budget_conscious"] = True
        
        # Extract quality preference
        if any(word in message.lower() for word in ["quality", "premium", "high end"]):
            preferences["quality_focused"] = True
        
        # Extract brand preference
        brand_match = PAT_BRAND.search(message)
        if brand_match:
            preferences["preferred_brand"] = brand_match.group(1).lower()
        
        return preferences
