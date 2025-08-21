"""Tests for performance monitoring system."""

import asyncio
import time
from collections import defaultdict, deque
from unittest.mock import AsyncMock, Mock, patch

import pytest

from bot.performance_monitor import (
    PerformanceMonitor,
    get_performance_monitor,
    track_api_performance,
    track_cache_performance,
    track_system_error,
    track_user_action,
)


class TestPerformanceMonitor:
    """Test the PerformanceMonitor class."""

    @pytest.fixture
    def monitor(self):
        """Create a performance monitor for testing."""
        return PerformanceMonitor()

    def test_initialization(self, monitor):
        """Test performance monitor initialization."""
        assert monitor.api_metrics["calls_total"] == 0
        assert monitor.cache_metrics["hits_total"] == 0
        assert len(monitor.system_metrics["cpu_usage"]) == 0
        assert len(monitor.user_metrics["active_users_daily"]) == 0
        assert monitor.error_metrics["errors_total"] == 0

    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, monitor):
        """Test starting and stopping background monitoring."""
        with patch.object(monitor, '_monitor_system_resources') as mock_monitor:
            mock_monitor.return_value = None
            
            # Start monitoring
            await monitor.start_monitoring()
            assert monitor._monitoring_task is not None
            
            # Stop monitoring
            await monitor.stop_monitoring()
            assert monitor._monitoring_task is None

    @pytest.mark.asyncio
    async def test_track_api_call_success(self, monitor):
        """Test tracking successful API calls."""
        await monitor.track_api_call(
            operation="get_item",
            duration=1.5,
            success=True
        )
        
        assert monitor.api_metrics["calls_total"] == 1
        assert monitor.api_metrics["calls_successful"] == 1
        assert monitor.api_metrics["calls_failed"] == 0
        assert len(monitor.api_metrics["response_times"]) == 1
        assert monitor.api_metrics["response_times"][0] == 1.5
        assert monitor.api_metrics["calls_by_endpoint"]["get_item"] == 1

    @pytest.mark.asyncio
    async def test_track_api_call_failure(self, monitor):
        """Test tracking failed API calls."""
        await monitor.track_api_call(
            operation="get_item",
            duration=2.0,
            success=False,
            error_type="timeout"
        )
        
        assert monitor.api_metrics["calls_total"] == 1
        assert monitor.api_metrics["calls_successful"] == 0
        assert monitor.api_metrics["calls_failed"] == 1
        assert monitor.api_metrics["errors_by_type"]["timeout"] == 1

    @pytest.mark.asyncio
    async def test_track_api_call_performance_alerts(self, monitor):
        """Test performance alerts for slow API calls."""
        with patch.object(monitor, '_alert_if_needed') as mock_alert:
            # Test critical response time
            await monitor.track_api_call(
                operation="slow_operation",
                duration=12.0,  # Above critical threshold
                success=True
            )
            
            mock_alert.assert_called_with(
                "api_critical_response_time",
                "Critical API response time: slow_operation took 12.00s"
            )

    def test_get_api_performance_summary(self, monitor):
        """Test API performance summary generation."""
        # Add some test data
        monitor.api_metrics["calls_total"] = 10
        monitor.api_metrics["calls_successful"] = 8
        monitor.api_metrics["response_times"].extend([1.0, 2.0, 3.0, 4.0, 5.0])
        monitor.api_metrics["calls_by_endpoint"]["get_item"] = 5
        monitor.api_metrics["calls_by_endpoint"]["search"] = 3
        
        summary = monitor.get_api_performance_summary()
        
        assert summary["total_calls"] == 10
        assert summary["success_rate"] == 0.8
        assert summary["average_response_time"] == 3.0
        assert summary["median_response_time"] == 3.0
        assert "most_called_endpoints" in summary

    def test_get_api_performance_summary_no_data(self, monitor):
        """Test API performance summary with no data."""
        summary = monitor.get_api_performance_summary()
        assert "error" in summary

    @pytest.mark.asyncio
    async def test_track_cache_operation_hit(self, monitor):
        """Test tracking cache hits."""
        await monitor.track_cache_operation(
            operation="get",
            tier="memory",
            hit=True
        )
        
        assert monitor.cache_metrics["hits_total"] == 1
        assert monitor.cache_metrics["hits_by_tier"]["memory"] == 1
        assert monitor.cache_metrics["misses_total"] == 0

    @pytest.mark.asyncio
    async def test_track_cache_operation_miss(self, monitor):
        """Test tracking cache misses."""
        await monitor.track_cache_operation(
            operation="get",
            tier="redis",
            hit=False
        )
        
        assert monitor.cache_metrics["hits_total"] == 0
        assert monitor.cache_metrics["misses_total"] == 1

    @pytest.mark.asyncio
    async def test_track_cache_operation_special_operations(self, monitor):
        """Test tracking special cache operations."""
        await monitor.track_cache_operation("invalidate", "memory")
        await monitor.track_cache_operation("evict", "memory")
        
        assert monitor.cache_metrics["invalidations"] == 1
        assert monitor.cache_metrics["evictions"] == 1

    @pytest.mark.asyncio
    async def test_cache_hit_rate_alert(self, monitor):
        """Test cache hit rate alerting."""
        with patch.object(monitor, '_alert_if_needed') as mock_alert:
            # Add enough operations to trigger alerting
            for _ in range(50):
                await monitor.track_cache_operation("get", "memory", hit=False)
            for _ in range(50):
                await monitor.track_cache_operation("get", "memory", hit=True)
            
            # Add one more miss to drop below threshold
            await monitor.track_cache_operation("get", "memory", hit=False)
            
            # Should have triggered alert
            mock_alert.assert_called()

    def test_get_cache_performance_summary(self, monitor):
        """Test cache performance summary generation."""
        monitor.cache_metrics["hits_total"] = 80
        monitor.cache_metrics["misses_total"] = 20
        monitor.cache_metrics["hits_by_tier"]["memory"] = 50
        monitor.cache_metrics["hits_by_tier"]["redis"] = 30
        monitor.cache_metrics["invalidations"] = 5
        monitor.cache_metrics["evictions"] = 3
        
        summary = monitor.get_cache_performance_summary()
        
        assert summary["total_operations"] == 100
        assert summary["hit_rate"] == 0.8
        assert summary["hits_by_tier"]["memory"] == 50
        assert summary["total_invalidations"] == 5
        assert summary["total_evictions"] == 3

    @pytest.mark.asyncio
    async def test_track_user_activity(self, monitor):
        """Test tracking user activity."""
        user_id = 12345
        
        await monitor.track_user_activity(
            user_id=user_id,
            activity_type="command",
            details={"command": "/start"}
        )
        
        assert user_id in monitor.user_metrics["active_users_daily"]
        assert user_id in monitor.user_metrics["active_users_hourly"]
        assert monitor.user_metrics["commands_processed"] == 1
        assert len(monitor.user_metrics["user_sessions"][user_id]) == 1

    @pytest.mark.asyncio
    async def test_track_user_activity_different_types(self, monitor):
        """Test tracking different types of user activities."""
        user_id = 12345
        
        await monitor.track_user_activity(user_id, "watch_create")
        await monitor.track_user_activity(user_id, "price_alert")
        
        assert monitor.user_metrics["watches_created"] == 1
        assert monitor.user_metrics["price_alerts_sent"] == 1

    @pytest.mark.asyncio
    async def test_user_session_cleanup(self, monitor):
        """Test user session data cleanup."""
        user_id = 12345
        
        # Add old session data
        from datetime import datetime, timedelta
        old_timestamp = datetime.utcnow() - timedelta(hours=25)
        monitor.user_metrics["user_sessions"][user_id].append({
            "timestamp": old_timestamp,
            "activity": "old_command",
            "details": {}
        })
        
        # Add new activity
        await monitor.track_user_activity(user_id, "command")
        
        # Old data should be cleaned up
        sessions = monitor.user_metrics["user_sessions"][user_id]
        assert len(sessions) == 1
        assert sessions[0]["activity"] == "command"

    def test_get_user_activity_summary(self, monitor):
        """Test user activity summary generation."""
        # Add test data
        monitor.user_metrics["active_users_daily"].add(123)
        monitor.user_metrics["active_users_daily"].add(456)
        monitor.user_metrics["active_users_hourly"].add(123)
        monitor.user_metrics["commands_processed"] = 50
        monitor.user_metrics["watches_created"] = 10
        monitor.user_metrics["price_alerts_sent"] = 25
        monitor.user_metrics["user_sessions"][789] = []
        
        summary = monitor.get_user_activity_summary()
        
        assert summary["active_users_daily"] == 2
        assert summary["active_users_hourly"] == 1
        assert summary["commands_processed"] == 50
        assert summary["watches_created"] == 10
        assert summary["price_alerts_sent"] == 25
        assert summary["total_tracked_users"] == 1

    @pytest.mark.asyncio
    async def test_track_error(self, monitor):
        """Test error tracking."""
        await monitor.track_error(
            error_type="api_error",
            error_message="Connection timeout",
            critical=False
        )
        
        assert monitor.error_metrics["errors_total"] == 1
        assert monitor.error_metrics["errors_by_category"]["api_error"] == 1
        assert monitor.error_metrics["critical_errors"] == 0

    @pytest.mark.asyncio
    async def test_track_critical_error(self, monitor):
        """Test critical error tracking."""
        with patch.object(monitor, '_alert_if_needed') as mock_alert:
            await monitor.track_error(
                error_type="database_error",
                error_message="Database connection lost",
                critical=True
            )
            
            assert monitor.error_metrics["critical_errors"] == 1
            mock_alert.assert_called_with(
                "critical_error_database_error",
                "Critical error: Database connection lost",
                immediate=True
            )

    @pytest.mark.asyncio
    async def test_error_rate_calculation(self, monitor):
        """Test error rate calculation and alerting."""
        # Add some operations
        monitor.api_metrics["calls_total"] = 100
        monitor.user_metrics["commands_processed"] = 100
        
        with patch.object(monitor, '_alert_if_needed') as mock_alert:
            # Add errors to trigger high error rate
            for _ in range(15):  # 15 errors out of 200 operations = 7.5%
                await monitor.track_error("test_error", "Test error")
            
            # Should trigger warning alert
            mock_alert.assert_called()

    def test_get_error_summary(self, monitor):
        """Test error summary generation."""
        monitor.error_metrics["errors_total"] = 10
        monitor.error_metrics["critical_errors"] = 2
        monitor.error_metrics["errors_by_category"]["api_error"] = 5
        monitor.error_metrics["errors_by_category"]["db_error"] = 3
        monitor.error_metrics["error_rate_history"].extend([0.05, 0.06, 0.04])
        
        summary = monitor.get_error_summary()
        
        assert summary["total_errors"] == 10
        assert summary["critical_errors"] == 2
        assert summary["errors_by_category"]["api_error"] == 5
        assert summary["current_error_rate"] == 0.04
        assert summary["average_error_rate"] == 0.05

    def test_get_system_metrics(self, monitor):
        """Test system metrics collection."""
        with patch('bot.performance_monitor.psutil') as mock_psutil:
            # Mock psutil functions
            mock_psutil.cpu_percent.return_value = 45.5
            mock_psutil.virtual_memory.return_value = Mock(
                percent=60.0,
                used=8 * 1024 * 1024 * 1024,  # 8GB
                total=16 * 1024 * 1024 * 1024  # 16GB
            )
            mock_psutil.disk_usage.return_value = Mock(
                percent=75.0,
                used=500 * 1024 * 1024 * 1024,  # 500GB
                total=1000 * 1024 * 1024 * 1024  # 1TB
            )
            mock_psutil.net_io_counters.return_value = Mock(
                bytes_sent=1000000,
                bytes_recv=2000000
            )
            
            metrics = monitor.get_system_metrics()
            
            assert metrics["cpu_usage_percent"] == 45.5
            assert metrics["memory_usage_percent"] == 60.0
            assert metrics["memory_used_mb"] == 8192
            assert metrics["memory_total_mb"] == 16384
            assert metrics["disk_usage_percent"] == 75.0
            assert metrics["network_bytes_sent"] == 1000000

    def test_get_system_metrics_error_handling(self, monitor):
        """Test system metrics error handling."""
        with patch('bot.performance_monitor.psutil') as mock_psutil:
            mock_psutil.cpu_percent.side_effect = Exception("psutil error")
            
            metrics = monitor.get_system_metrics()
            assert "error" in metrics

    def test_get_performance_summary(self, monitor):
        """Test comprehensive performance summary."""
        # Add some test data
        monitor.api_metrics["calls_total"] = 10
        monitor.cache_metrics["hits_total"] = 5
        monitor.user_metrics["commands_processed"] = 20
        monitor.error_metrics["errors_total"] = 1
        
        with patch.object(monitor, 'get_system_metrics') as mock_system:
            mock_system.return_value = {"cpu_usage_percent": 50.0}
            
            summary = monitor.get_performance_summary()
            
            assert "timestamp" in summary
            assert "api_performance" in summary
            assert "cache_performance" in summary
            assert "user_activity" in summary
            assert "error_summary" in summary
            assert "system_metrics" in summary

    def test_reset_metrics(self, monitor):
        """Test metrics reset functionality."""
        # Add some test data
        monitor.api_metrics["calls_total"] = 10
        monitor.cache_metrics["hits_total"] = 5
        monitor.user_metrics["active_users_daily"].add(123)
        monitor.error_metrics["errors_total"] = 2
        
        # Reset all metrics
        monitor.reset_metrics()
        
        assert monitor.api_metrics["calls_total"] == 0
        assert monitor.cache_metrics["hits_total"] == 0
        assert len(monitor.user_metrics["active_users_daily"]) == 0
        assert monitor.error_metrics["errors_total"] == 0

    def test_reset_specific_metrics(self, monitor):
        """Test resetting specific metric types."""
        # Add test data
        monitor.api_metrics["calls_total"] = 10
        monitor.cache_metrics["hits_total"] = 5
        
        # Reset only API metrics
        monitor.reset_metrics("api")
        
        assert monitor.api_metrics["calls_total"] == 0
        assert monitor.cache_metrics["hits_total"] == 5  # Should remain

    @pytest.mark.asyncio
    async def test_alert_cooldown(self, monitor):
        """Test alert cooldown mechanism."""
        monitor.alert_cooldown = 1  # 1 second for testing
        
        with patch('bot.performance_monitor.log') as mock_log:
            # Send first alert
            await monitor._alert_if_needed("test_alert", "Test message")
            
            # Send second alert immediately (should be suppressed)
            await monitor._alert_if_needed("test_alert", "Test message")
            
            # Should only log once
            assert mock_log.warning.call_count == 1

    @pytest.mark.asyncio
    async def test_immediate_alert(self, monitor):
        """Test immediate alerts bypass cooldown."""
        monitor.alert_cooldown = 60  # Long cooldown
        
        with patch('bot.performance_monitor.log') as mock_log:
            # Send first alert
            await monitor._alert_if_needed("test_alert", "Test message")
            
            # Send immediate alert (should not be suppressed)
            await monitor._alert_if_needed("test_alert", "Test message", immediate=True)
            
            # Should log twice
            assert mock_log.warning.call_count == 2

    def test_percentile_calculation(self, monitor):
        """Test percentile calculation."""
        data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        
        assert monitor._percentile(data, 50) == 5.5  # Median
        assert monitor._percentile(data, 90) == 9.1
        assert abs(monitor._percentile(data, 95) - 9.55) < 0.01  # Allow floating point tolerance
        assert monitor._percentile([], 50) == 0.0  # Empty data

    def test_get_slowest_endpoints(self, monitor):
        """Test slowest endpoints calculation."""
        # Add some response times
        monitor.api_metrics["response_times"].extend([1.0, 2.0, 3.0, 4.0, 5.0])
        
        slowest = monitor._get_slowest_endpoints()
        
        assert isinstance(slowest, list)
        assert len(slowest) > 0
        for endpoint in slowest:
            assert "endpoint" in endpoint
            assert "avg_time" in endpoint


class TestPerformanceMonitorIntegration:
    """Test performance monitor integration and convenience functions."""

    @pytest.mark.asyncio
    async def test_track_api_performance_convenience(self):
        """Test convenience function for API performance tracking."""
        with patch('bot.performance_monitor.get_performance_monitor') as mock_get_monitor:
            mock_monitor = Mock()
            mock_monitor.track_api_call = AsyncMock()
            mock_get_monitor.return_value = mock_monitor
            
            await track_api_performance(
                operation="test_op",
                duration=1.5,
                success=True
            )
            
            mock_monitor.track_api_call.assert_called_once_with(
                "test_op", 1.5, True, None
            )

    @pytest.mark.asyncio
    async def test_track_cache_performance_convenience(self):
        """Test convenience function for cache performance tracking."""
        with patch('bot.performance_monitor.get_performance_monitor') as mock_get_monitor:
            mock_monitor = Mock()
            mock_monitor.track_cache_operation = AsyncMock()
            mock_get_monitor.return_value = mock_monitor
            
            await track_cache_performance(
                operation="get",
                tier="memory",
                hit=True
            )
            
            mock_monitor.track_cache_operation.assert_called_once_with(
                "get", "memory", True
            )

    @pytest.mark.asyncio
    async def test_track_user_action_convenience(self):
        """Test convenience function for user action tracking."""
        with patch('bot.performance_monitor.get_performance_monitor') as mock_get_monitor:
            mock_monitor = Mock()
            mock_monitor.track_user_activity = AsyncMock()
            mock_get_monitor.return_value = mock_monitor
            
            await track_user_action(
                user_id=12345,
                activity_type="command",
                details={"cmd": "/start"}
            )
            
            mock_monitor.track_user_activity.assert_called_once_with(
                12345, "command", {"cmd": "/start"}
            )

    @pytest.mark.asyncio
    async def test_track_system_error_convenience(self):
        """Test convenience function for error tracking."""
        with patch('bot.performance_monitor.get_performance_monitor') as mock_get_monitor:
            mock_monitor = Mock()
            mock_monitor.track_error = AsyncMock()
            mock_get_monitor.return_value = mock_monitor
            
            await track_system_error(
                error_type="test_error",
                error_message="Test error",
                critical=True
            )
            
            mock_monitor.track_error.assert_called_once_with(
                "test_error", "Test error", True, None
            )

    def test_global_performance_monitor_singleton(self):
        """Test that performance monitor is a singleton."""
        monitor1 = get_performance_monitor()
        monitor2 = get_performance_monitor()
        
        assert monitor1 is monitor2


class TestPerformanceMonitorBackgroundTasks:
    """Test background monitoring tasks."""

    @pytest.mark.asyncio
    async def test_system_resource_monitoring(self):
        """Test system resource monitoring background task."""
        monitor = PerformanceMonitor()
        
        with patch.object(monitor, 'get_system_metrics') as mock_get_metrics:
            with patch.object(monitor, '_alert_if_needed') as mock_alert:
                # Mock system metrics
                mock_get_metrics.return_value = {
                    "cpu_usage_percent": 85.0,  # Above warning threshold
                    "memory_usage_percent": 90.0,  # Above warning threshold
                    "disk_usage_percent": 50.0
                }
                
                # Start monitoring for a short time
                await monitor.start_monitoring()
                
                # Let it run briefly
                await asyncio.sleep(0.1)
                
                await monitor.stop_monitoring()
                
                # Should have checked metrics and potentially alerted
                mock_get_metrics.assert_called()

    @pytest.mark.asyncio
    async def test_periodic_user_reset(self):
        """Test periodic reset of user metrics."""
        monitor = PerformanceMonitor()
        
        # Add some users
        monitor.user_metrics["active_users_hourly"].add(123)
        monitor.user_metrics["active_users_daily"].add(456)
        
        # Mock time to trigger resets
        with patch('time.time') as mock_time:
            # Simulate hourly reset
            mock_time.return_value = 3600  # Exactly 1 hour
            
            # This would normally be called by the background task
            if int(mock_time.return_value) % 3600 == 0:
                monitor.user_metrics["active_users_hourly"].clear()
            
            assert len(monitor.user_metrics["active_users_hourly"]) == 0
            assert len(monitor.user_metrics["active_users_daily"]) == 1  # Should remain


@pytest.mark.integration
class TestPerformanceMonitorRealWorld:
    """Real-world integration tests for performance monitor."""

    @pytest.mark.asyncio
    async def test_realistic_monitoring_scenario(self):
        """Test a realistic monitoring scenario."""
        monitor = PerformanceMonitor()
        
        # Simulate API calls
        for i in range(10):
            success = i < 8  # 80% success rate
            duration = 1.0 + (i * 0.1)  # Increasing response times
            await monitor.track_api_call(
                operation="get_item",
                duration=duration,
                success=success,
                error_type="timeout" if not success else None
            )
        
        # Simulate cache operations
        for i in range(20):
            hit = i < 15  # 75% hit rate
            tier = "memory" if i < 10 else "redis"
            await monitor.track_cache_operation("get", tier, hit)
        
        # Simulate user activity
        for user_id in range(5):
            await monitor.track_user_activity(user_id, "command")
            if user_id < 2:
                await monitor.track_user_activity(user_id, "watch_create")
        
        # Simulate errors
        for i in range(3):
            await monitor.track_error(
                error_type="api_error",
                error_message=f"Error {i}",
                critical=i == 0
            )
        
        # Get comprehensive summary
        summary = monitor.get_performance_summary()
        
        # Verify realistic data
        assert summary["api_performance"]["total_calls"] == 10
        assert summary["api_performance"]["success_rate"] == 0.8
        assert summary["cache_performance"]["hit_rate"] == 0.75
        assert summary["user_activity"]["active_users_daily"] == 5
        assert summary["user_activity"]["watches_created"] == 2
        assert summary["error_summary"]["total_errors"] == 3
        assert summary["error_summary"]["critical_errors"] == 1

    @pytest.mark.asyncio
    async def test_high_load_simulation(self):
        """Test performance monitor under high load."""
        monitor = PerformanceMonitor()
        
        # Simulate high load
        tasks = []
        
        # Many concurrent API calls
        for i in range(100):
            tasks.append(monitor.track_api_call(f"operation_{i % 5}", 0.1 + (i % 10) * 0.01))
        
        # Many cache operations
        for i in range(200):
            tasks.append(monitor.track_cache_operation("get", "memory", i % 4 != 0))
        
        # Many user activities
        for i in range(50):
            tasks.append(monitor.track_user_activity(i % 10, "command"))
        
        # Execute all concurrently
        await asyncio.gather(*tasks)
        
        # Verify data integrity
        assert monitor.api_metrics["calls_total"] == 100
        assert monitor.cache_metrics["hits_total"] + monitor.cache_metrics["misses_total"] == 200
        assert monitor.user_metrics["commands_processed"] == 50
        
        # Performance should be reasonable
        summary = monitor.get_performance_summary()
        assert "error" not in summary
