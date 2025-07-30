#!/usr/bin/env python3
"""Launch Monitoring Script for MandiMonitorBot

This script monitors key metrics during the public soft-launch phase
and provides real-time insights into system performance and user engagement.

Usage:
    python scripts/launch_monitoring.py
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict

import psutil
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("launch_monitoring.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class LaunchMonitor:
    """Monitor system performance and user metrics during launch."""

    def __init__(self):
        self.health_url = os.getenv("HEALTH_URL", "http://localhost:8000/health")
        self.admin_url = os.getenv("ADMIN_URL", "http://localhost:5000/admin")
        self.admin_user = os.getenv("ADMIN_USER", "admin")
        self.admin_pass = os.getenv("ADMIN_PASS", "changeme")
        self.check_interval = int(os.getenv("CHECK_INTERVAL", "60"))  # seconds

        self.metrics_history = []
        self.alerts_sent = set()

        # Performance thresholds
        self.thresholds = {
            "response_time_warning": 2.0,  # seconds
            "response_time_critical": 5.0,  # seconds
            "error_rate_warning": 1.0,  # percentage
            "error_rate_critical": 5.0,  # percentage
            "memory_warning": 512,  # MB
            "memory_critical": 1024,  # MB
            "cpu_warning": 70.0,  # percentage
            "cpu_critical": 90.0,  # percentage
        }

    async def check_health(self) -> Dict[str, Any]:
        """Check bot health endpoint."""
        try:
            start_time = time.time()
            response = requests.get(self.health_url, timeout=10)
            response_time = time.time() - start_time

            return {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "response_time": response_time,
                "status_code": response.status_code,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "response_time": None,
                "status_code": None,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def get_admin_metrics(self) -> Dict[str, Any]:
        """Fetch metrics from admin interface."""
        try:
            response = requests.get(
                self.admin_url,
                auth=(self.admin_user, self.admin_pass),
                timeout=10,
            )

            if response.status_code == 200:
                # Parse metrics from admin interface
                # This would need to be adapted based on actual admin interface format
                return {
                    "total_users": 0,  # Parse from admin response
                    "total_watches": 0,
                    "total_clicks": 0,
                    "last_24h_users": 0,
                    "timestamp": datetime.now().isoformat(),
                }
            else:
                logger.warning(f"Admin metrics unavailable: {response.status_code}")
                return {}

        except Exception as e:
            logger.error(f"Failed to get admin metrics: {e}")
            return {}

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system resource usage metrics."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used_mb": memory.used / (1024 * 1024),
                "memory_available_mb": memory.available / (1024 * 1024),
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free / (1024 * 1024 * 1024),
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return {}

    def analyze_metrics(
        self, health: Dict, admin: Dict, system: Dict
    ) -> Dict[str, str]:
        """Analyze metrics and determine alert levels."""
        alerts = {}

        # Response time analysis
        if health.get("response_time"):
            rt = health["response_time"]
            if rt > self.thresholds["response_time_critical"]:
                alerts["response_time"] = (
                    f"CRITICAL: Response time {rt:.2f}s > {self.thresholds['response_time_critical']}s"
                )
            elif rt > self.thresholds["response_time_warning"]:
                alerts["response_time"] = (
                    f"WARNING: Response time {rt:.2f}s > {self.thresholds['response_time_warning']}s"
                )

        # Memory analysis
        memory_mb = system.get("memory_used_mb", 0)
        if memory_mb > self.thresholds["memory_critical"]:
            alerts["memory"] = (
                f"CRITICAL: Memory usage {memory_mb:.0f}MB > {self.thresholds['memory_critical']}MB"
            )
        elif memory_mb > self.thresholds["memory_warning"]:
            alerts["memory"] = (
                f"WARNING: Memory usage {memory_mb:.0f}MB > {self.thresholds['memory_warning']}MB"
            )

        # CPU analysis
        cpu_percent = system.get("cpu_percent", 0)
        if cpu_percent > self.thresholds["cpu_critical"]:
            alerts["cpu"] = (
                f"CRITICAL: CPU usage {cpu_percent:.1f}% > {self.thresholds['cpu_critical']}%"
            )
        elif cpu_percent > self.thresholds["cpu_warning"]:
            alerts["cpu"] = (
                f"WARNING: CPU usage {cpu_percent:.1f}% > {self.thresholds['cpu_warning']}%"
            )

        # Health status
        if health.get("status") != "healthy":
            alerts["health"] = (
                f"CRITICAL: Health check failed - {health.get('error', 'Unknown error')}"
            )

        return alerts

    def log_metrics_summary(
        self, health: Dict, admin: Dict, system: Dict, alerts: Dict
    ):
        """Log comprehensive metrics summary."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # System performance summary
        logger.info(f"=== LAUNCH METRICS SUMMARY - {timestamp} ===")
        logger.info(f"Health Status: {health.get('status', 'unknown')}")
        logger.info(
            f"Response Time: {health.get('response_time', 'N/A'):.2f}s"
            if health.get("response_time")
            else "Response Time: N/A"
        )
        logger.info(f"CPU Usage: {system.get('cpu_percent', 0):.1f}%")
        logger.info(
            f"Memory Usage: {system.get('memory_used_mb', 0):.0f}MB ({system.get('memory_percent', 0):.1f}%)"
        )
        logger.info(f"Disk Free: {system.get('disk_free_gb', 0):.1f}GB")

        # User metrics summary
        if admin:
            logger.info(f"Total Users: {admin.get('total_users', 'N/A')}")
            logger.info(f"Total Watches: {admin.get('total_watches', 'N/A')}")
            logger.info(f"Total Clicks: {admin.get('total_clicks', 'N/A')}")
            logger.info(f"New Users (24h): {admin.get('last_24h_users', 'N/A')}")
        else:
            logger.info("User Metrics: Admin interface unavailable")

        # Alerts summary
        if alerts:
            logger.warning(f"ACTIVE ALERTS ({len(alerts)}):")
            for alert_type, message in alerts.items():
                logger.warning(f"  {alert_type.upper()}: {message}")
        else:
            logger.info("No active alerts - all systems green! ✅")

        logger.info("=" * 50)

    def save_metrics_to_file(
        self, health: Dict, admin: Dict, system: Dict, alerts: Dict
    ):
        """Save metrics to JSON file for historical analysis."""
        metrics_record = {
            "timestamp": datetime.now().isoformat(),
            "health": health,
            "admin": admin,
            "system": system,
            "alerts": alerts,
        }

        self.metrics_history.append(metrics_record)

        # Save to file
        try:
            with open("launch_metrics.json", "w") as f:
                json.dump(self.metrics_history, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save metrics to file: {e}")

    def send_alert_notifications(self, alerts: Dict):
        """Send notifications for critical alerts (placeholder)."""
        for alert_type, message in alerts.items():
            alert_key = f"{alert_type}_{datetime.now().strftime('%Y%m%d_%H')}"

            if alert_key not in self.alerts_sent:
                if "CRITICAL" in message:
                    logger.critical(f"🚨 ALERT: {message}")
                    # Here you could add actual notification logic:
                    # - Send to Slack webhook
                    # - Send email alert
                    # - Send Telegram notification
                    # - Trigger PagerDuty incident
                    self.alerts_sent.add(alert_key)
                elif "WARNING" in message:
                    logger.warning(f"⚠️  WARNING: {message}")

    def generate_hourly_report(self):
        """Generate hourly summary report."""
        if not self.metrics_history:
            return

        # Get metrics from the last hour
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_metrics = [
            m
            for m in self.metrics_history
            if datetime.fromisoformat(m["timestamp"]) > one_hour_ago
        ]

        if not recent_metrics:
            return

        # Calculate averages
        avg_response_time = sum(
            m["health"].get("response_time", 0)
            for m in recent_metrics
            if m["health"].get("response_time")
        ) / len([m for m in recent_metrics if m["health"].get("response_time")])

        avg_cpu = sum(m["system"].get("cpu_percent", 0) for m in recent_metrics) / len(
            recent_metrics
        )
        avg_memory = sum(
            m["system"].get("memory_used_mb", 0) for m in recent_metrics
        ) / len(recent_metrics)

        alert_count = sum(len(m["alerts"]) for m in recent_metrics)

        logger.info("📊 HOURLY REPORT")
        logger.info(f"Average Response Time: {avg_response_time:.2f}s")
        logger.info(f"Average CPU Usage: {avg_cpu:.1f}%")
        logger.info(f"Average Memory Usage: {avg_memory:.0f}MB")
        logger.info(f"Total Alerts: {alert_count}")

    async def monitor_loop(self):
        """Main monitoring loop."""
        logger.info("🚀 Starting MandiMonitorBot launch monitoring...")
        logger.info(f"Health URL: {self.health_url}")
        logger.info(f"Check interval: {self.check_interval} seconds")

        last_hourly_report = datetime.now()

        while True:
            try:
                # Collect metrics
                health = await self.check_health()
                admin = await self.get_admin_metrics()
                system = self.get_system_metrics()

                # Analyze for alerts
                alerts = self.analyze_metrics(health, admin, system)

                # Log summary
                self.log_metrics_summary(health, admin, system, alerts)

                # Save metrics
                self.save_metrics_to_file(health, admin, system, alerts)

                # Send alerts if needed
                if alerts:
                    self.send_alert_notifications(alerts)

                # Generate hourly report
                if datetime.now() - last_hourly_report >= timedelta(hours=1):
                    self.generate_hourly_report()
                    last_hourly_report = datetime.now()

                # Wait for next check
                await asyncio.sleep(self.check_interval)

            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(30)  # Wait 30 seconds before retrying


async def main():
    """Main function to run the launch monitor."""
    monitor = LaunchMonitor()
    await monitor.monitor_loop()


if __name__ == "__main__":
    asyncio.run(main())
