"""
AI Performance Monitor for tracking Feature Match AI model performance.

This module implements Phase 4 monitoring requirements by tracking:
- Model usage frequency and selection patterns
- Performance metrics (latency, accuracy indicators)
- User satisfaction proxies and implicit feedback
- Model selection decisions and fallback patterns

The monitoring data helps optimize AI performance and provides insights
for model improvement and parameter tuning.
"""

import time
import json
from typing import Dict, Any, Optional, List
from logging import getLogger
from collections import defaultdict, deque
from threading import Lock

log = getLogger(__name__)


class AIPerformanceMonitor:
    """Monitor and track AI model performance across sessions."""

    def __init__(self):
        """Initialize the performance monitor."""
        self._stats = defaultdict(lambda: defaultdict(int))
        self._latencies = defaultdict(deque)  # Keep last 100 measurements
        self._selections = deque(maxlen=1000)  # Keep last 1000 selections
        self._lock = Lock()
        
        # Performance thresholds
        self.latency_threshold_ms = 500  # Alert if p95 > 500ms
        self.confidence_threshold = 0.7   # Track low confidence selections
        
    def log_model_selection(
        self, 
        model_name: str, 
        user_query: str, 
        product_count: int,
        selection_metadata: Dict[str, Any],
        success: bool = True
    ):
        """
        Log a model selection event for monitoring.
        
        Args:
        ----
            model_name: Name of the model used
            user_query: User's search query
            product_count: Number of products available for selection
            selection_metadata: Metadata from the selection process
            success: Whether the selection was successful
        """
        with self._lock:
            timestamp = time.time()
            
            # Update basic stats
            self._stats[model_name]["total_selections"] += 1
            if success:
                self._stats[model_name]["successful_selections"] += 1
            else:
                self._stats[model_name]["failed_selections"] += 1
            
            # Track latency
            latency = selection_metadata.get("processing_time_ms", 0)
            self._latencies[model_name].append(latency)
            if len(self._latencies[model_name]) > 100:
                self._latencies[model_name].popleft()
            
            # Track selection event
            selection_event = {
                "timestamp": timestamp,
                "model_name": model_name,
                "query_length": len(user_query.split()),
                "product_count": product_count,
                "success": success,
                "latency_ms": latency,
                "confidence": selection_metadata.get("ai_confidence", 0),
                "matched_features": len(selection_metadata.get("matched_features", [])),
                "query_hash": hash(user_query) % 10000  # For privacy
            }
            
            self._selections.append(selection_event)
            
            # Log performance warnings
            if latency > self.latency_threshold_ms:
                log.warning(
                    "AI_PERFORMANCE: High latency detected - %s took %.1fms (threshold: %dms)",
                    model_name, latency, self.latency_threshold_ms
                )
            
            if model_name == "FeatureMatchModel":
                confidence = selection_metadata.get("ai_confidence", 1.0)
                if confidence < self.confidence_threshold:
                    log.warning(
                        "AI_PERFORMANCE: Low confidence selection - %.3f (threshold: %.3f)",
                        confidence, self.confidence_threshold
                    )
    
    def log_fallback_event(self, primary_model: str, fallback_model: str, reason: str):
        """Log when a model falls back to another model."""
        with self._lock:
            fallback_key = f"{primary_model}_to_{fallback_model}"
            self._stats["fallbacks"][fallback_key] += 1
            self._stats["fallbacks"]["total_fallbacks"] += 1
            
            log.info(
                "AI_FALLBACK: %s → %s (reason: %s)",
                primary_model, fallback_model, reason
            )
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary for all models."""
        with self._lock:
            summary = {
                "total_selections": sum(
                    model_stats["total_selections"] 
                    for model_stats in self._stats.values()
                    if isinstance(model_stats, dict)
                ),
                "models": {},
                "latency_stats": {},
                "fallback_stats": dict(self._stats["fallbacks"]),
                "recent_performance": self._get_recent_performance()
            }
            
            # Model-specific stats
            for model_name, model_stats in self._stats.items():
                if model_name == "fallbacks":
                    continue
                    
                if isinstance(model_stats, dict):
                    total = model_stats.get("total_selections", 0)
                    successful = model_stats.get("successful_selections", 0)
                    
                    summary["models"][model_name] = {
                        "total_selections": total,
                        "successful_selections": successful,
                        "success_rate": successful / total if total > 0 else 0,
                        "usage_percentage": (total / summary["total_selections"] * 100) 
                                          if summary["total_selections"] > 0 else 0
                    }
            
            # Latency statistics
            for model_name, latencies in self._latencies.items():
                if latencies:
                    latency_list = list(latencies)
                    latency_list.sort()
                    n = len(latency_list)
                    
                    summary["latency_stats"][model_name] = {
                        "count": n,
                        "avg_ms": sum(latency_list) / n,
                        "p50_ms": latency_list[n // 2] if n > 0 else 0,
                        "p95_ms": latency_list[int(n * 0.95)] if n > 0 else 0,
                        "max_ms": max(latency_list) if latency_list else 0
                    }
            
            return summary
    
    def _get_recent_performance(self, minutes: int = 60) -> Dict[str, Any]:
        """Get performance metrics for the last N minutes."""
        current_time = time.time()
        cutoff_time = current_time - (minutes * 60)
        
        recent_selections = [
            s for s in self._selections 
            if s["timestamp"] >= cutoff_time
        ]
        
        if not recent_selections:
            return {"period_minutes": minutes, "selections": 0}
        
        # Analyze recent selections
        model_counts = defaultdict(int)
        successful_selections = 0
        total_latency = 0
        low_confidence_count = 0
        
        for selection in recent_selections:
            model_counts[selection["model_name"]] += 1
            if selection["success"]:
                successful_selections += 1
            total_latency += selection["latency_ms"]
            if selection["confidence"] < self.confidence_threshold:
                low_confidence_count += 1
        
        total_selections = len(recent_selections)
        
        return {
            "period_minutes": minutes,
            "selections": total_selections,
            "success_rate": successful_selections / total_selections,
            "avg_latency_ms": total_latency / total_selections,
            "low_confidence_rate": low_confidence_count / total_selections,
            "model_distribution": dict(model_counts),
            "selections_per_minute": total_selections / minutes
        }
    
    def check_health(self) -> Dict[str, Any]:
        """Check AI system health and return status."""
        summary = self.get_performance_summary()
        recent = summary["recent_performance"]
        
        health_status = {
            "status": "healthy",
            "issues": [],
            "recommendations": []
        }
        
        # Check if AI model is being used
        feature_match_usage = summary["models"].get("FeatureMatchModel", {}).get("usage_percentage", 0)
        if feature_match_usage < 10:  # Less than 10% usage
            health_status["issues"].append("Low AI model usage")
            health_status["recommendations"].append("Check if queries have sufficient technical features")
        
        # Check success rates
        for model_name, model_stats in summary["models"].items():
            success_rate = model_stats.get("success_rate", 0)
            if success_rate < 0.9:  # Less than 90% success
                health_status["issues"].append(f"{model_name} has low success rate: {success_rate:.1%}")
        
        # Check latency
        for model_name, latency_stats in summary["latency_stats"].items():
            p95_latency = latency_stats.get("p95_ms", 0)
            if p95_latency > self.latency_threshold_ms:
                health_status["issues"].append(f"{model_name} p95 latency high: {p95_latency:.1f}ms")
        
        # Check recent performance
        if recent["selections"] > 0:
            if recent["success_rate"] < 0.8:
                health_status["issues"].append("Recent success rate below 80%")
            
            if recent["low_confidence_rate"] > 0.3:
                health_status["issues"].append("High rate of low-confidence selections")
        
        # Set overall status
        if health_status["issues"]:
            health_status["status"] = "degraded" if len(health_status["issues"]) <= 2 else "unhealthy"
        
        return health_status
    
    def export_metrics(self) -> str:
        """Export metrics in JSON format for external monitoring systems."""
        summary = self.get_performance_summary()
        health = self.check_health()
        
        export_data = {
            "timestamp": time.time(),
            "performance_summary": summary,
            "health_check": health,
            "version": "1.0.0"
        }
        
        return json.dumps(export_data, indent=2)


# Global monitor instance
_monitor = None

def get_ai_monitor() -> AIPerformanceMonitor:
    """Get the global AI performance monitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = AIPerformanceMonitor()
    return _monitor


def log_ai_selection(
    model_name: str,
    user_query: str, 
    product_count: int,
    selection_metadata: Dict[str, Any],
    success: bool = True
):
    """Convenience function to log AI selection events."""
    monitor = get_ai_monitor()
    monitor.log_model_selection(
        model_name, user_query, product_count, selection_metadata, success
    )


def log_ai_fallback(primary_model: str, fallback_model: str, reason: str):
    """Convenience function to log AI fallback events."""
    monitor = get_ai_monitor()
    monitor.log_fallback_event(primary_model, fallback_model, reason)


def get_ai_performance_summary() -> Dict[str, Any]:
    """Get current AI performance summary."""
    monitor = get_ai_monitor()
    return monitor.get_performance_summary()


def check_ai_health() -> Dict[str, Any]:
    """Check AI system health status."""
    monitor = get_ai_monitor()
    return monitor.check_health()
