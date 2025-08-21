"""Performance monitoring system for MandiMonitor Bot.

This module provides comprehensive performance monitoring and metrics
collection for tracking system health, API performance, and user activity.
"""

import asyncio
import statistics
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from logging import getLogger
from typing import Any, Dict, List, Optional

import psutil

from .config import settings

log = getLogger(__name__)


class PerformanceMonitor:
    """Comprehensive performance monitoring for MandiMonitor Bot.
    
    Tracks:
    - API call performance and success rates
    - Cache hit rates and performance
    - System resource usage
    - User activity patterns
    - Error rates and patterns
    """

    def __init__(self):
        """Initialize the performance monitor."""
        # API performance tracking
        self.api_metrics = {
            "calls_total": 0,
            "calls_successful": 0,
            "calls_failed": 0,
            "response_times": deque(maxlen=1000),
            "errors_by_type": defaultdict(int),
            "calls_by_endpoint": defaultdict(int)
        }
        
        # Cache performance tracking
        self.cache_metrics = {
            "hits_total": 0,
            "misses_total": 0,
            "hits_by_tier": defaultdict(int),  # memory, redis, database
            "invalidations": 0,
            "evictions": 0
        }
        
        # System resource tracking
        self.system_metrics = {
            "cpu_usage": deque(maxlen=100),
            "memory_usage": deque(maxlen=100),
            "disk_usage": deque(maxlen=100),
            "network_io": deque(maxlen=100)
        }
        
        # User activity tracking
        self.user_metrics = {
            "active_users_daily": set(),
            "active_users_hourly": set(),
            "commands_processed": 0,
            "watches_created": 0,
            "price_alerts_sent": 0,
            "user_sessions": defaultdict(list)
        }
        
        # Error tracking
        self.error_metrics = {
            "errors_total": 0,
            "errors_by_category": defaultdict(int),
            "critical_errors": 0,
            "error_rate_history": deque(maxlen=100)
        }
        
        # Performance thresholds
        self.thresholds = {
            "api_response_time_warning": 5.0,  # seconds
            "api_response_time_critical": 10.0,
            "cache_hit_rate_warning": 0.7,  # 70%
            "error_rate_warning": 0.05,  # 5%
            "error_rate_critical": 0.1,  # 10%
            "cpu_usage_warning": 80.0,  # %
            "memory_usage_warning": 80.0  # %
        }
        
        # Alert history to prevent spam
        self.alert_history = defaultdict(float)
        self.alert_cooldown = 300  # 5 minutes
        
        # Background monitoring task
        self._monitoring_task = None
        self._shutdown_event = asyncio.Event()

    async def start_monitoring(self) -> None:
        """Start background performance monitoring."""
        if self._monitoring_task is None:
            self._monitoring_task = asyncio.create_task(self._monitor_system_resources())
            log.info("Performance monitoring started")

    async def stop_monitoring(self) -> None:
        """Stop background performance monitoring."""
        if self._monitoring_task:
            self._shutdown_event.set()
            await self._monitoring_task
            self._monitoring_task = None
            log.info("Performance monitoring stopped")

    # API Performance Tracking

    async def track_api_call(
        self,
        operation: str,
        duration: float,
        success: bool = True,
        error_type: Optional[str] = None
    ) -> None:
        """Track an API call's performance.
        
        Args:
            operation: API operation name
            duration: Call duration in seconds
            success: Whether the call was successful
            error_type: Type of error if call failed
        """
        self.api_metrics["calls_total"] += 1
        self.api_metrics["calls_by_endpoint"][operation] += 1
        self.api_metrics["response_times"].append(duration)
        
        if success:
            self.api_metrics["calls_successful"] += 1
        else:
            self.api_metrics["calls_failed"] += 1
            if error_type:
                self.api_metrics["errors_by_type"][error_type] += 1
                
        # Check for performance alerts
        if duration > self.thresholds["api_response_time_critical"]:
            await self._alert_if_needed(
                "api_critical_response_time",
                f"Critical API response time: {operation} took {duration:.2f}s"
            )
        elif duration > self.thresholds["api_response_time_warning"]:
            await self._alert_if_needed(
                "api_warning_response_time",
                f"Slow API response: {operation} took {duration:.2f}s"
            )

    def get_api_performance_summary(self) -> Dict[str, Any]:
        """Get API performance summary."""
        response_times = list(self.api_metrics["response_times"])
        
        if not response_times:
            return {"error": "No API calls recorded"}
            
        success_rate = (
            self.api_metrics["calls_successful"] / 
            max(self.api_metrics["calls_total"], 1)
        )
        
        return {
            "total_calls": self.api_metrics["calls_total"],
            "success_rate": success_rate,
            "average_response_time": statistics.mean(response_times),
            "median_response_time": statistics.median(response_times),
            "p95_response_time": self._percentile(response_times, 95),
            "p99_response_time": self._percentile(response_times, 99),
            "slowest_endpoints": self._get_slowest_endpoints(),
            "most_called_endpoints": dict(
                sorted(
                    self.api_metrics["calls_by_endpoint"].items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:10]
            )
        }

    # Cache Performance Tracking

    async def track_cache_operation(
        self,
        operation: str,
        tier: str,
        hit: bool = True
    ) -> None:
        """Track cache operation performance.
        
        Args:
            operation: Cache operation (get, set, invalidate, etc.)
            tier: Cache tier (memory, redis, database)
            hit: Whether it was a cache hit
        """
        if hit:
            self.cache_metrics["hits_total"] += 1
            self.cache_metrics["hits_by_tier"][tier] += 1
        else:
            self.cache_metrics["misses_total"] += 1
            
        if operation == "invalidate":
            self.cache_metrics["invalidations"] += 1
        elif operation == "evict":
            self.cache_metrics["evictions"] += 1
            
        # Check cache hit rate
        total_operations = (
            self.cache_metrics["hits_total"] + 
            self.cache_metrics["misses_total"]
        )
        if total_operations > 100:  # Only alert after sufficient data
            hit_rate = self.cache_metrics["hits_total"] / total_operations
            if hit_rate < self.thresholds["cache_hit_rate_warning"]:
                await self._alert_if_needed(
                    "cache_low_hit_rate",
                    f"Low cache hit rate: {hit_rate:.2%}"
                )

    def get_cache_performance_summary(self) -> Dict[str, Any]:
        """Get cache performance summary."""
        total_operations = (
            self.cache_metrics["hits_total"] + 
            self.cache_metrics["misses_total"]
        )
        
        hit_rate = (
            self.cache_metrics["hits_total"] / max(total_operations, 1)
        )
        
        return {
            "total_operations": total_operations,
            "hit_rate": hit_rate,
            "hits_by_tier": dict(self.cache_metrics["hits_by_tier"]),
            "total_invalidations": self.cache_metrics["invalidations"],
            "total_evictions": self.cache_metrics["evictions"]
        }

    # User Activity Tracking

    async def track_user_activity(
        self,
        user_id: int,
        activity_type: str,
        details: Optional[Dict] = None
    ) -> None:
        """Track user activity.
        
        Args:
            user_id: Telegram user ID
            activity_type: Type of activity (command, watch_create, etc.)
            details: Optional activity details
        """
        now = datetime.utcnow()
        
        # Track active users
        self.user_metrics["active_users_daily"].add(user_id)
        self.user_metrics["active_users_hourly"].add(user_id)
        
        # Track specific activities
        if activity_type == "command":
            self.user_metrics["commands_processed"] += 1
        elif activity_type == "watch_create":
            self.user_metrics["watches_created"] += 1
        elif activity_type == "price_alert":
            self.user_metrics["price_alerts_sent"] += 1
            
        # Track user session
        self.user_metrics["user_sessions"][user_id].append({
            "timestamp": now,
            "activity": activity_type,
            "details": details
        })
        
        # Clean old session data (keep last 24 hours)
        cutoff = now - timedelta(hours=24)
        self.user_metrics["user_sessions"][user_id] = [
            session for session in self.user_metrics["user_sessions"][user_id]
            if session["timestamp"] > cutoff
        ]

    def get_user_activity_summary(self) -> Dict[str, Any]:
        """Get user activity summary."""
        return {
            "active_users_daily": len(self.user_metrics["active_users_daily"]),
            "active_users_hourly": len(self.user_metrics["active_users_hourly"]),
            "commands_processed": self.user_metrics["commands_processed"],
            "watches_created": self.user_metrics["watches_created"],
            "price_alerts_sent": self.user_metrics["price_alerts_sent"],
            "total_tracked_users": len(self.user_metrics["user_sessions"])
        }

    # Error Tracking

    async def track_error(
        self,
        error_type: str,
        error_message: str,
        critical: bool = False,
        context: Optional[Dict] = None
    ) -> None:
        """Track error occurrence.
        
        Args:
            error_type: Type/category of error
            error_message: Error message
            critical: Whether this is a critical error
            context: Optional error context
        """
        self.error_metrics["errors_total"] += 1
        self.error_metrics["errors_by_category"][error_type] += 1
        
        if critical:
            self.error_metrics["critical_errors"] += 1
            await self._alert_if_needed(
                f"critical_error_{error_type}",
                f"Critical error: {error_message}",
                immediate=True
            )
            
        # Calculate current error rate
        total_operations = (
            self.api_metrics["calls_total"] + 
            self.user_metrics["commands_processed"]
        )
        if total_operations > 0:
            error_rate = self.error_metrics["errors_total"] / total_operations
            self.error_metrics["error_rate_history"].append(error_rate)
            
            # Check error rate thresholds
            if error_rate > self.thresholds["error_rate_critical"]:
                await self._alert_if_needed(
                    "critical_error_rate",
                    f"Critical error rate: {error_rate:.2%}"
                )
            elif error_rate > self.thresholds["error_rate_warning"]:
                await self._alert_if_needed(
                    "warning_error_rate",
                    f"High error rate: {error_rate:.2%}"
                )

    def get_error_summary(self) -> Dict[str, Any]:
        """Get error tracking summary."""
        error_rates = list(self.error_metrics["error_rate_history"])
        
        return {
            "total_errors": self.error_metrics["errors_total"],
            "critical_errors": self.error_metrics["critical_errors"],
            "errors_by_category": dict(self.error_metrics["errors_by_category"]),
            "current_error_rate": error_rates[-1] if error_rates else 0,
            "average_error_rate": statistics.mean(error_rates) if error_rates else 0
        }

    # System Resource Monitoring

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system resource metrics."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            net_io = psutil.net_io_counters()
            
            return {
                "cpu_usage_percent": cpu_percent,
                "memory_usage_percent": memory.percent,
                "memory_used_mb": memory.used // (1024 * 1024),
                "memory_total_mb": memory.total // (1024 * 1024),
                "disk_usage_percent": disk.percent,
                "disk_used_gb": disk.used // (1024 * 1024 * 1024),
                "disk_total_gb": disk.total // (1024 * 1024 * 1024),
                "network_bytes_sent": net_io.bytes_sent,
                "network_bytes_recv": net_io.bytes_recv
            }
        except Exception as e:
            log.warning("Failed to get system metrics: %s", e)
            return {"error": str(e)}

    # Comprehensive Performance Summary

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "api_performance": self.get_api_performance_summary(),
            "cache_performance": self.get_cache_performance_summary(),
            "user_activity": self.get_user_activity_summary(),
            "error_summary": self.get_error_summary(),
            "system_metrics": self.get_system_metrics()
        }

    def reset_metrics(self, metric_type: Optional[str] = None) -> None:
        """Reset performance metrics.
        
        Args:
            metric_type: Specific metric type to reset, or None for all
        """
        if metric_type is None or metric_type == "api":
            self.api_metrics = {
                "calls_total": 0,
                "calls_successful": 0,
                "calls_failed": 0,
                "response_times": deque(maxlen=1000),
                "errors_by_type": defaultdict(int),
                "calls_by_endpoint": defaultdict(int)
            }
            
        if metric_type is None or metric_type == "cache":
            self.cache_metrics = {
                "hits_total": 0,
                "misses_total": 0,
                "hits_by_tier": defaultdict(int),
                "invalidations": 0,
                "evictions": 0
            }
            
        if metric_type is None or metric_type == "user":
            self.user_metrics["active_users_daily"].clear()
            self.user_metrics["active_users_hourly"].clear()
            
        if metric_type is None or metric_type == "error":
            self.error_metrics = {
                "errors_total": 0,
                "errors_by_category": defaultdict(int),
                "critical_errors": 0,
                "error_rate_history": deque(maxlen=100)
            }
            
        log.info("Performance metrics reset: %s", metric_type or "all")

    # Private methods

    async def _monitor_system_resources(self) -> None:
        """Background task to monitor system resources."""
        log.info("System resource monitoring started")
        
        while not self._shutdown_event.is_set():
            try:
                metrics = self.get_system_metrics()
                
                if "error" not in metrics:
                    # Store metrics
                    self.system_metrics["cpu_usage"].append(metrics["cpu_usage_percent"])
                    self.system_metrics["memory_usage"].append(metrics["memory_usage_percent"])
                    self.system_metrics["disk_usage"].append(metrics["disk_usage_percent"])
                    
                    # Check thresholds
                    if metrics["cpu_usage_percent"] > self.thresholds["cpu_usage_warning"]:
                        await self._alert_if_needed(
                            "high_cpu_usage",
                            f"High CPU usage: {metrics['cpu_usage_percent']:.1f}%"
                        )
                        
                    if metrics["memory_usage_percent"] > self.thresholds["memory_usage_warning"]:
                        await self._alert_if_needed(
                            "high_memory_usage",
                            f"High memory usage: {metrics['memory_usage_percent']:.1f}%"
                        )
                
                # Reset hourly active users every hour
                if int(time.time()) % 3600 == 0:
                    self.user_metrics["active_users_hourly"].clear()
                    
                # Reset daily active users every day
                if int(time.time()) % 86400 == 0:
                    self.user_metrics["active_users_daily"].clear()
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                log.error("Error in system resource monitoring: %s", e)
                await asyncio.sleep(60)
                
        log.info("System resource monitoring stopped")

    async def _alert_if_needed(
        self,
        alert_key: str,
        message: str,
        immediate: bool = False
    ) -> None:
        """Send alert if cooldown period has passed.
        
        Args:
            alert_key: Unique key for the alert type
            message: Alert message
            immediate: Whether to send immediately (bypass cooldown)
        """
        now = time.time()
        last_alert = self.alert_history.get(alert_key, 0)
        
        if immediate or (now - last_alert) >= self.alert_cooldown:
            log.warning("PERFORMANCE ALERT: %s", message)
            self.alert_history[alert_key] = now
            
            # Here you could integrate with external alerting systems
            # like Sentry, Slack, email, etc.

    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile of a dataset."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = (percentile / 100.0) * (len(sorted_data) - 1)
        lower = int(index)
        upper = min(lower + 1, len(sorted_data) - 1)
        weight = index - lower
        return sorted_data[lower] * (1 - weight) + sorted_data[upper] * weight

    def _get_slowest_endpoints(self) -> List[Dict[str, Any]]:
        """Get the slowest API endpoints."""
        # This is a simplified version - in practice you'd track per-endpoint metrics
        response_times = list(self.api_metrics["response_times"])
        if not response_times:
            return []
            
        # Return placeholder data
        return [
            {"endpoint": "get_item", "avg_time": statistics.mean(response_times[-10:])},
            {"endpoint": "search_products", "avg_time": statistics.mean(response_times[-20:-10]) if len(response_times) > 20 else 0}
        ]


# Global performance monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


async def track_api_performance(
    operation: str,
    duration: float,
    success: bool = True,
    error_type: Optional[str] = None
) -> None:
    """Convenience function to track API performance.
    
    Args:
        operation: API operation name
        duration: Call duration in seconds
        success: Whether the call was successful
        error_type: Type of error if call failed
    """
    monitor = get_performance_monitor()
    await monitor.track_api_call(operation, duration, success, error_type)


async def track_cache_performance(
    operation: str,
    tier: str,
    hit: bool = True
) -> None:
    """Convenience function to track cache performance.
    
    Args:
        operation: Cache operation
        tier: Cache tier
        hit: Whether it was a cache hit
    """
    monitor = get_performance_monitor()
    await monitor.track_cache_operation(operation, tier, hit)


async def track_user_action(
    user_id: int,
    activity_type: str,
    details: Optional[Dict] = None
) -> None:
    """Convenience function to track user activity.
    
    Args:
        user_id: Telegram user ID
        activity_type: Type of activity
        details: Optional activity details
    """
    monitor = get_performance_monitor()
    await monitor.track_user_activity(user_id, activity_type, details)


async def track_system_error(
    error_type: str,
    error_message: str,
    critical: bool = False,
    context: Optional[Dict] = None
) -> None:
    """Convenience function to track errors.
    
    Args:
        error_type: Type/category of error
        error_message: Error message
        critical: Whether this is a critical error
        context: Optional error context
    """
    monitor = get_performance_monitor()
    await monitor.track_error(error_type, error_message, critical, context)
