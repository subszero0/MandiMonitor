"""
Tests for AI Performance Monitor

This test suite validates the AI performance monitoring system that tracks:
- Model selection events and performance metrics
- Fallback patterns and success rates
- Health checks and alerting thresholds
- Performance summaries and export functionality
"""

import pytest
import time
from unittest.mock import patch

from bot.ai_performance_monitor import (
    AIPerformanceMonitor,
    get_ai_monitor,
    log_ai_selection,
    log_ai_fallback,
    get_ai_performance_summary,
    check_ai_health
)


class TestAIPerformanceMonitor:
    """Test the AIPerformanceMonitor class."""

    @pytest.fixture
    def monitor(self):
        """Create a fresh AIPerformanceMonitor instance."""
        return AIPerformanceMonitor()

    def test_monitor_initialization(self, monitor):
        """Test monitor initializes with correct defaults."""
        assert monitor.latency_threshold_ms == 500
        assert monitor.confidence_threshold == 0.7
        assert len(monitor._stats) == 0
        assert len(monitor._latencies) == 0
        assert len(monitor._selections) == 0

    def test_log_model_selection_success(self, monitor):
        """Test logging successful model selections."""
        selection_metadata = {
            "processing_time_ms": 150.5,
            "ai_confidence": 0.85,
            "matched_features": ["refresh_rate", "size"]
        }
        
        monitor.log_model_selection(
            model_name="FeatureMatchModel",
            user_query="gaming monitor 144hz 27 inch",
            product_count=10,
            selection_metadata=selection_metadata,
            success=True
        )
        
        # Check stats updated
        assert monitor._stats["FeatureMatchModel"]["total_selections"] == 1
        assert monitor._stats["FeatureMatchModel"]["successful_selections"] == 1
        assert monitor._stats["FeatureMatchModel"]["failed_selections"] == 0
        
        # Check latency recorded
        assert len(monitor._latencies["FeatureMatchModel"]) == 1
        assert monitor._latencies["FeatureMatchModel"][0] == 150.5
        
        # Check selection event recorded
        assert len(monitor._selections) == 1
        selection_event = monitor._selections[0]
        assert selection_event["model_name"] == "FeatureMatchModel"
        assert selection_event["success"] is True
        assert selection_event["latency_ms"] == 150.5
        assert selection_event["confidence"] == 0.85
        assert selection_event["matched_features"] == 2

    def test_log_model_selection_failure(self, monitor):
        """Test logging failed model selections."""
        selection_metadata = {"processing_time_ms": 50.0}
        
        monitor.log_model_selection(
            model_name="FeatureMatchModel",
            user_query="test query",
            product_count=5,
            selection_metadata=selection_metadata,
            success=False
        )
        
        assert monitor._stats["FeatureMatchModel"]["total_selections"] == 1
        assert monitor._stats["FeatureMatchModel"]["successful_selections"] == 0
        assert monitor._stats["FeatureMatchModel"]["failed_selections"] == 1

    def test_log_fallback_event(self, monitor):
        """Test logging fallback events."""
        monitor.log_fallback_event(
            primary_model="FeatureMatchModel",
            fallback_model="PopularityModel", 
            reason="Non-technical query"
        )
        
        assert monitor._stats["fallbacks"]["FeatureMatchModel_to_PopularityModel"] == 1
        assert monitor._stats["fallbacks"]["total_fallbacks"] == 1

    def test_performance_summary_empty(self, monitor):
        """Test performance summary with no data."""
        summary = monitor.get_performance_summary()
        
        assert summary["total_selections"] == 0
        assert summary["models"] == {}
        assert summary["latency_stats"] == {}
        assert summary["fallback_stats"] == {}

    def test_performance_summary_with_data(self, monitor):
        """Test performance summary with sample data."""
        # Add sample selections
        for i in range(5):
            monitor.log_model_selection(
                model_name="FeatureMatchModel",
                user_query=f"query {i}",
                product_count=10,
                selection_metadata={"processing_time_ms": 100 + i * 10},
                success=True
            )
        
        for i in range(3):
            monitor.log_model_selection(
                model_name="PopularityModel", 
                user_query=f"simple query {i}",
                product_count=5,
                selection_metadata={"processing_time_ms": 50 + i * 5},
                success=True
            )
        
        summary = monitor.get_performance_summary()
        
        assert summary["total_selections"] == 8
        assert len(summary["models"]) == 2
        
        # Check FeatureMatchModel stats
        fm_stats = summary["models"]["FeatureMatchModel"]
        assert fm_stats["total_selections"] == 5
        assert fm_stats["successful_selections"] == 5
        assert fm_stats["success_rate"] == 1.0
        assert fm_stats["usage_percentage"] == 62.5  # 5/8 * 100
        
        # Check latency stats
        fm_latency = summary["latency_stats"]["FeatureMatchModel"]
        assert fm_latency["count"] == 5
        assert fm_latency["avg_ms"] == 120.0  # (100+110+120+130+140)/5
        assert fm_latency["p50_ms"] == 120.0
        assert fm_latency["max_ms"] == 140.0

    def test_recent_performance(self, monitor):
        """Test recent performance calculation."""
        # Add selections with current timestamp
        current_time = time.time()
        
        with patch('time.time', return_value=current_time):
            for i in range(3):
                monitor.log_model_selection(
                    model_name="FeatureMatchModel",
                    user_query=f"query {i}",
                    product_count=10,
                    selection_metadata={
                        "processing_time_ms": 100,
                        "ai_confidence": 0.8
                    },
                    success=True
                )
        
        # Get recent performance (should include all selections)
        recent = monitor._get_recent_performance(minutes=60)
        
        assert recent["selections"] == 3
        assert recent["success_rate"] == 1.0
        assert recent["avg_latency_ms"] == 100.0
        assert recent["low_confidence_rate"] == 0.0  # All above threshold
        assert recent["selections_per_minute"] == 3/60

    def test_health_check_healthy(self, monitor):
        """Test health check with healthy system."""
        # Add good performance data
        for i in range(10):
            monitor.log_model_selection(
                model_name="FeatureMatchModel",
                user_query=f"gaming monitor {i}",
                product_count=10,
                selection_metadata={
                    "processing_time_ms": 100,
                    "ai_confidence": 0.85
                },
                success=True
            )
        
        health = monitor.check_health()
        
        assert health["status"] == "healthy"
        assert len(health["issues"]) == 0

    def test_health_check_low_ai_usage(self, monitor):
        """Test health check detects low AI usage."""
        # Add mostly non-AI selections
        for i in range(10):
            monitor.log_model_selection(
                model_name="PopularityModel",
                user_query=f"simple query {i}",
                product_count=5,
                selection_metadata={"processing_time_ms": 50},
                success=True
            )
        
        # Add one AI selection (10% usage)
        monitor.log_model_selection(
            model_name="FeatureMatchModel",
            user_query="gaming monitor",
            product_count=10,
            selection_metadata={"processing_time_ms": 100},
            success=True
        )
        
        health = monitor.check_health()
        
        assert health["status"] == "degraded"
        assert "Low AI model usage" in health["issues"]

    def test_health_check_high_latency(self, monitor):
        """Test health check detects high latency."""
        # Add selections with high latency
        for i in range(10):
            monitor.log_model_selection(
                model_name="FeatureMatchModel",
                user_query=f"query {i}",
                product_count=10,
                selection_metadata={"processing_time_ms": 600},  # Above threshold
                success=True
            )
        
        health = monitor.check_health()
        
        assert health["status"] in ["degraded", "unhealthy"]
        assert any("p95 latency high" in issue for issue in health["issues"])

    def test_health_check_low_success_rate(self, monitor):
        """Test health check detects low success rates."""
        # Add mostly failed selections
        for i in range(10):
            monitor.log_model_selection(
                model_name="FeatureMatchModel",
                user_query=f"query {i}",
                product_count=10,
                selection_metadata={"processing_time_ms": 100},
                success=False  # 0% success rate
            )
        
        health = monitor.check_health()
        
        assert health["status"] in ["degraded", "unhealthy"]
        assert any("low success rate" in issue for issue in health["issues"])

    def test_latency_deque_size_limit(self, monitor):
        """Test latency deque maintains size limit."""
        # Add more than 100 latency measurements
        for i in range(150):
            monitor.log_model_selection(
                model_name="FeatureMatchModel",
                user_query=f"query {i}",
                product_count=10,
                selection_metadata={"processing_time_ms": i},
                success=True
            )
        
        # Should only keep last 100
        assert len(monitor._latencies["FeatureMatchModel"]) == 100
        # Should have latest values (50-149)
        latencies = list(monitor._latencies["FeatureMatchModel"])
        assert min(latencies) == 50
        assert max(latencies) == 149

    def test_selections_deque_size_limit(self, monitor):
        """Test selections deque maintains size limit."""
        # Add more than 1000 selections
        for i in range(1200):
            monitor.log_model_selection(
                model_name="FeatureMatchModel",
                user_query=f"query {i}",
                product_count=10,
                selection_metadata={"processing_time_ms": 100},
                success=True
            )
        
        # Should only keep last 1000
        assert len(monitor._selections) == 1000

    def test_export_metrics(self, monitor):
        """Test metrics export functionality."""
        # Add some data
        monitor.log_model_selection(
            model_name="FeatureMatchModel",
            user_query="test query",
            product_count=10,
            selection_metadata={"processing_time_ms": 100},
            success=True
        )
        
        export_json = monitor.export_metrics()
        
        assert isinstance(export_json, str)
        # Should be valid JSON
        import json
        data = json.loads(export_json)
        
        assert "timestamp" in data
        assert "performance_summary" in data
        assert "health_check" in data
        assert "version" in data


class TestGlobalFunctions:
    """Test global convenience functions."""

    def test_get_ai_monitor_singleton(self):
        """Test global monitor is singleton."""
        monitor1 = get_ai_monitor()
        monitor2 = get_ai_monitor()
        
        assert monitor1 is monitor2
        assert isinstance(monitor1, AIPerformanceMonitor)

    def test_log_ai_selection_convenience(self):
        """Test convenience function for logging selections."""
        selection_metadata = {
            "processing_time_ms": 100,
            "ai_confidence": 0.8
        }
        
        log_ai_selection(
            model_name="FeatureMatchModel",
            user_query="test query",
            product_count=5,
            selection_metadata=selection_metadata
        )
        
        # Should update global monitor
        monitor = get_ai_monitor()
        assert monitor._stats["FeatureMatchModel"]["total_selections"] >= 1

    def test_log_ai_fallback_convenience(self):
        """Test convenience function for logging fallbacks."""
        log_ai_fallback(
            primary_model="FeatureMatchModel",
            fallback_model="PopularityModel",
            reason="Test fallback"
        )
        
        # Should update global monitor
        monitor = get_ai_monitor()
        assert monitor._stats["fallbacks"]["total_fallbacks"] >= 1

    def test_get_ai_performance_summary_convenience(self):
        """Test convenience function for getting summary."""
        summary = get_ai_performance_summary()
        
        assert isinstance(summary, dict)
        assert "total_selections" in summary
        assert "models" in summary

    def test_check_ai_health_convenience(self):
        """Test convenience function for health check."""
        health = check_ai_health()
        
        assert isinstance(health, dict)
        assert "status" in health
        assert "issues" in health
        assert "recommendations" in health


class TestConcurrentAccess:
    """Test thread safety and concurrent access."""

    def test_concurrent_logging(self, monitor):
        """Test concurrent logging doesn't cause race conditions."""
        import threading
        
        def log_selections():
            for i in range(50):
                monitor.log_model_selection(
                    model_name="FeatureMatchModel",
                    user_query=f"query {i}",
                    product_count=10,
                    selection_metadata={"processing_time_ms": 100},
                    success=True
                )
        
        # Run concurrent logging
        threads = []
        for _ in range(4):
            thread = threading.Thread(target=log_selections)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Should have all selections recorded
        assert monitor._stats["FeatureMatchModel"]["total_selections"] == 200
        assert len(monitor._latencies["FeatureMatchModel"]) == 100  # Deque limit
        assert len(monitor._selections) == 200


class TestPerformanceThresholds:
    """Test performance threshold detection."""

    def test_latency_warning_threshold(self, monitor):
        """Test latency warning is logged when threshold exceeded."""
        with patch('bot.ai_performance_monitor.log') as mock_log:
            monitor.log_model_selection(
                model_name="FeatureMatchModel",
                user_query="test",
                product_count=10,
                selection_metadata={"processing_time_ms": 600},  # Above 500ms threshold
                success=True
            )
            
            # Should log warning
            mock_log.warning.assert_called_once()
            warning_call = mock_log.warning.call_args[0][0]
            assert "High latency detected" in warning_call

    def test_confidence_warning_threshold(self, monitor):
        """Test confidence warning is logged when threshold not met."""
        with patch('bot.ai_performance_monitor.log') as mock_log:
            monitor.log_model_selection(
                model_name="FeatureMatchModel",
                user_query="test",
                product_count=10,
                selection_metadata={
                    "processing_time_ms": 100,
                    "ai_confidence": 0.5  # Below 0.7 threshold
                },
                success=True
            )
            
            # Should log warning
            mock_log.warning.assert_called_once()
            warning_call = mock_log.warning.call_args[0][0]
            assert "Low confidence selection" in warning_call


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
