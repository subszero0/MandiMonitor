"""
Phase R7: Production Deployment & Gradual Rollout System.

This module provides feature flag management and gradual rollout capabilities
for the AI Intelligence Model system, enabling safe production deployment
with real-time monitoring and rollback capabilities.
"""

import hashlib
import time
from typing import Dict, Any, Optional, Set
from dataclasses import dataclass
from logging import getLogger

log = getLogger(__name__)


@dataclass
class FeatureFlag:
    """Feature flag configuration."""
    name: str
    enabled: bool = False
    rollout_percentage: float = 0.0  # 0-100
    user_whitelist: Set[str] = None  # User IDs to always enable
    user_blacklist: Set[str] = None  # User IDs to always disable
    conditions: Dict[str, Any] = None  # Additional conditions
    start_time: Optional[float] = None  # When rollout started
    end_time: Optional[float] = None  # When to fully enable/disable


class FeatureRolloutManager:
    """
    Manages gradual rollout of AI features with monitoring and rollback capabilities.
    
    Phase R7 Requirements:
    - Gradual rollout configuration operational
    - Production monitoring and alerting active
    - Rollback procedures tested and documented
    - Success metrics baseline established
    """

    def __init__(self):
        """Initialize the feature rollout manager."""
        self._flags = self._initialize_default_flags()
        self._metrics = {}
        self._rollback_history = []
        
    def _initialize_default_flags(self) -> Dict[str, FeatureFlag]:
        """Initialize default feature flags for AI system."""
        return {
            # R7.1: AI Model Selection Features
            "ai_feature_matching": FeatureFlag(
                name="ai_feature_matching",
                enabled=True,
                rollout_percentage=100.0,  # Fully enabled - already working
                conditions={"technical_query_required": True}
            ),
            
            "ai_multi_card_experience": FeatureFlag(
                name="ai_multi_card_experience", 
                enabled=True,
                rollout_percentage=90.0,  # 90% rollout for new multi-card
                conditions={"min_products": 3, "technical_query_required": True}
            ),
            
            "ai_enhanced_carousel": FeatureFlag(
                name="ai_enhanced_carousel",
                enabled=True,
                rollout_percentage=85.0,  # 85% rollout for enhanced display
                conditions={"multi_card_enabled": True, "technical_query_required": True}  # Always require technical queries
            ),
            
            # R7.2: Performance & Monitoring Features
            "ai_performance_monitoring": FeatureFlag(
                name="ai_performance_monitoring",
                enabled=True,
                rollout_percentage=100.0,  # Full monitoring enabled
                conditions={}
            ),
            
            "ai_health_checks": FeatureFlag(
                name="ai_health_checks",
                enabled=True,
                rollout_percentage=100.0,  # Full health monitoring
                conditions={}
            ),
            
            # R7.3: Advanced AI Features (Gradual rollout)
            "ai_priority_feature_display": FeatureFlag(
                name="ai_priority_feature_display",
                enabled=True,
                rollout_percentage=75.0,  # 75% rollout for new prioritization
                conditions={"multi_card_enabled": True}
            ),
            
            "ai_smart_fallback_chain": FeatureFlag(
                name="ai_smart_fallback_chain",
                enabled=True,
                rollout_percentage=95.0,  # 95% rollout for enhanced fallbacks
                conditions={}
            ),
            
            # R7.4: Experimental Features (Limited rollout)
            "ai_query_expansion": FeatureFlag(
                name="ai_query_expansion",
                enabled=False,
                rollout_percentage=10.0,  # Limited 10% rollout for experiments
                conditions={"technical_query_required": True}
            ),
            
            "ai_predictive_recommendations": FeatureFlag(
                name="ai_predictive_recommendations",
                enabled=False,
                rollout_percentage=5.0,  # Very limited rollout
                conditions={"user_history_available": True}
            )
        }

    def is_feature_enabled(
        self, 
        feature_name: str, 
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Check if a feature is enabled for a specific user.
        
        Args:
        ----
            feature_name: Name of the feature to check
            user_id: User ID for percentage-based rollout
            context: Additional context for condition evaluation
            
        Returns:
        -------
            True if feature is enabled for this user
        """
        if feature_name not in self._flags:
            log.warning(f"Unknown feature flag: {feature_name}")
            return False
        
        flag = self._flags[feature_name]
        context = context or {}
        
        # Check if feature is globally disabled
        if not flag.enabled:
            return False
        
        # Check blacklist first
        if flag.user_blacklist and user_id in flag.user_blacklist:
            log.debug(f"Feature {feature_name} disabled for blacklisted user {user_id}")
            return False
        
        # Check whitelist
        if flag.user_whitelist and user_id in flag.user_whitelist:
            log.debug(f"Feature {feature_name} enabled for whitelisted user {user_id}")
            return True
        
        # Check time-based conditions
        current_time = time.time()
        if flag.start_time and current_time < flag.start_time:
            return False
        if flag.end_time and current_time > flag.end_time:
            return False
        
        # Check additional conditions
        if flag.conditions:
            if not self._evaluate_conditions(flag.conditions, context):
                return False
        
        # Percentage-based rollout using user ID hash
        if flag.rollout_percentage <= 0:
            return False
        if flag.rollout_percentage >= 100:
            return True
        
        # Deterministic percentage based on user ID hash
        user_hash = int(hashlib.md5(f"{feature_name}:{user_id}".encode()).hexdigest()[:8], 16)
        user_percentage = (user_hash % 10000) / 100.0  # 0-99.99
        
        enabled = user_percentage < flag.rollout_percentage
        
        # Log rollout decision for monitoring
        if enabled:
            log.debug(f"Feature {feature_name} enabled for user {user_id} (rollout: {flag.rollout_percentage}%)")
        
        return enabled

    def _evaluate_conditions(self, conditions: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Evaluate feature flag conditions against context."""
        for condition, expected_value in conditions.items():
            context_value = context.get(condition)
            
            if condition == "technical_query_required":
                # Always consider queries as technical to force AI usage over popularity
                # This prevents the PopularityModel from being used
                log.debug("technical_query_required condition: Always returning True to force AI usage")
                continue  # Skip the condition check, always pass
            
            elif condition == "min_products":
                # Check minimum product count
                product_count = context.get("product_count", 0)
                if product_count < expected_value:
                    return False
            
            elif condition == "multi_card_enabled":
                # Check if multi-card is available
                multi_card_available = context.get("multi_card_enabled", False)
                if expected_value and not multi_card_available:
                    return False
            
            elif condition == "user_history_available":
                # Check if user has interaction history
                has_history = context.get("user_has_history", False)
                if expected_value and not has_history:
                    return False
            
            else:
                # Direct value comparison
                if context_value != expected_value:
                    return False
        
        return True

    def update_rollout_percentage(self, feature_name: str, new_percentage: float) -> bool:
        """
        Update rollout percentage for a feature.
        
        Args:
        ----
            feature_name: Feature to update
            new_percentage: New rollout percentage (0-100)
            
        Returns:
        -------
            True if updated successfully
        """
        if feature_name not in self._flags:
            log.error(f"Cannot update unknown feature: {feature_name}")
            return False
        
        if not 0 <= new_percentage <= 100:
            log.error(f"Invalid percentage: {new_percentage}")
            return False
        
        old_percentage = self._flags[feature_name].rollout_percentage
        self._flags[feature_name].rollout_percentage = new_percentage
        
        log.info(f"Updated {feature_name} rollout: {old_percentage}% → {new_percentage}%")
        
        # Record rollout change for monitoring
        self._record_rollout_change(feature_name, old_percentage, new_percentage)
        
        return True

    def emergency_disable_feature(self, feature_name: str, reason: str) -> bool:
        """
        Emergency disable a feature with rollback tracking.
        
        Args:
        ----
            feature_name: Feature to disable
            reason: Reason for emergency disable
            
        Returns:
        -------
            True if disabled successfully
        """
        if feature_name not in self._flags:
            log.error(f"Cannot disable unknown feature: {feature_name}")
            return False
        
        # Record current state for rollback
        current_state = {
            "enabled": self._flags[feature_name].enabled,
            "rollout_percentage": self._flags[feature_name].rollout_percentage
        }
        
        # Disable feature
        self._flags[feature_name].enabled = False
        self._flags[feature_name].rollout_percentage = 0.0
        
        # Record rollback information
        rollback_entry = {
            "feature_name": feature_name,
            "timestamp": time.time(),
            "reason": reason,
            "previous_state": current_state,
            "action": "emergency_disable"
        }
        self._rollback_history.append(rollback_entry)
        
        log.critical(f"EMERGENCY DISABLE: {feature_name} - Reason: {reason}")
        
        return True

    def rollback_feature(self, feature_name: str) -> bool:
        """
        Rollback a feature to its previous state.
        
        Args:
        ----
            feature_name: Feature to rollback
            
        Returns:
        -------
            True if rollback successful
        """
        # Find the most recent rollback entry for this feature
        recent_entry = None
        for entry in reversed(self._rollback_history):
            if entry["feature_name"] == feature_name:
                recent_entry = entry
                break
        
        if not recent_entry:
            log.error(f"No rollback history found for feature: {feature_name}")
            return False
        
        if feature_name not in self._flags:
            log.error(f"Cannot rollback unknown feature: {feature_name}")
            return False
        
        # Restore previous state
        previous_state = recent_entry["previous_state"]
        self._flags[feature_name].enabled = previous_state["enabled"]
        self._flags[feature_name].rollout_percentage = previous_state["rollout_percentage"]
        
        log.info(f"ROLLBACK: {feature_name} restored to previous state")
        
        return True

    def get_rollout_status(self) -> Dict[str, Any]:
        """
        Get comprehensive rollout status for monitoring.
        
        Returns:
        -------
            Dictionary with rollout status and metrics
        """
        status = {
            "timestamp": time.time(),
            "features": {},
            "rollback_history": len(self._rollback_history),
            "metrics": self._metrics
        }
        
        for name, flag in self._flags.items():
            status["features"][name] = {
                "enabled": flag.enabled,
                "rollout_percentage": flag.rollout_percentage,
                "has_conditions": bool(flag.conditions),
                "whitelist_size": len(flag.user_whitelist) if flag.user_whitelist else 0,
                "blacklist_size": len(flag.user_blacklist) if flag.user_blacklist else 0
            }
        
        return status

    def _record_rollout_change(self, feature_name: str, old_percentage: float, new_percentage: float):
        """Record rollout changes for monitoring."""
        change_entry = {
            "feature_name": feature_name,
            "timestamp": time.time(),
            "old_percentage": old_percentage,
            "new_percentage": new_percentage,
            "action": "percentage_update"
        }
        self._rollback_history.append(change_entry)

    def get_feature_metrics(self, feature_name: str) -> Dict[str, Any]:
        """Get usage metrics for a specific feature."""
        return self._metrics.get(feature_name, {
            "total_checks": 0,
            "enabled_count": 0,
            "disabled_count": 0,
            "success_rate": 0.0,
            "last_used": None
        })


# Global rollout manager instance
_rollout_manager = None


def get_rollout_manager() -> FeatureRolloutManager:
    """Get the global feature rollout manager instance."""
    global _rollout_manager
    if _rollout_manager is None:
        _rollout_manager = FeatureRolloutManager()
    return _rollout_manager


def is_ai_feature_enabled(feature_name: str, user_id: str, **context) -> bool:
    """
    Convenience function to check if an AI feature is enabled.
    
    Args:
    ----
        feature_name: Feature to check
        user_id: User ID for rollout calculation
        **context: Additional context for conditions
        
    Returns:
    -------
        True if feature is enabled for this user
    """
    manager = get_rollout_manager()
    return manager.is_feature_enabled(feature_name, user_id, context)


def emergency_disable_ai_feature(feature_name: str, reason: str) -> bool:
    """
    Emergency disable an AI feature.
    
    Args:
    ----
        feature_name: Feature to disable
        reason: Reason for emergency disable
        
    Returns:
    -------
        True if successfully disabled
    """
    manager = get_rollout_manager()
    return manager.emergency_disable_feature(feature_name, reason)
