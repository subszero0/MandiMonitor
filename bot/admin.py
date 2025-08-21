"""Flask admin interface for bot management with enhanced analytics."""

import asyncio
from datetime import datetime, timezone
from logging import getLogger

from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS

from .admin_analytics import AdminAnalytics
from .revenue_optimization import RevenueOptimizer

log = getLogger(__name__)


def create_admin_app():
    """Create Flask admin application with analytics dashboard.

    Returns
    -------
        Flask app instance with admin routes and analytics

    """
    app = Flask(__name__)
    CORS(app)

    # Initialize analytics components
    analytics = AdminAnalytics()
    revenue_optimizer = RevenueOptimizer()

    @app.route("/")
    def admin_dashboard():
        """Main admin dashboard with business metrics."""
        return render_template_string(DASHBOARD_TEMPLATE)

    @app.route("/api/dashboard/<period>")
    def api_dashboard(period: str = "30d"):
        """API endpoint for dashboard data.

        Args:
        ----
            period: Time period for analysis (7d, 30d, 90d)

        Returns:
        -------
            JSON response with dashboard metrics
        """
        try:
            # Run async function in event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            dashboard_data = loop.run_until_complete(
                analytics.generate_performance_dashboard(period)
            )

            loop.close()
            return jsonify(dashboard_data)

        except Exception as e:
            log.error("Failed to get dashboard data: %s", e)
            return jsonify({"error": str(e)}), 500

    @app.route("/api/user-segmentation")
    def api_user_segmentation():
        """API endpoint for user segmentation analysis."""
        try:
            detailed = request.args.get("detailed", "false").lower() == "true"

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            segmentation_data = loop.run_until_complete(
                analytics.analyze_user_segmentation(detailed)
            )

            loop.close()
            return jsonify(segmentation_data)

        except Exception as e:
            log.error("Failed to get user segmentation: %s", e)
            return jsonify({"error": str(e)}), 500

    @app.route("/api/product-performance")
    def api_product_performance():
        """API endpoint for product performance analysis."""
        try:
            category = request.args.get("category")

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            performance_data = loop.run_until_complete(
                analytics.analyze_product_performance(category)
            )

            loop.close()
            return jsonify(performance_data)

        except Exception as e:
            log.error("Failed to get product performance: %s", e)
            return jsonify({"error": str(e)}), 500

    @app.route("/api/revenue-insights")
    def api_revenue_insights():
        """API endpoint for revenue insights and forecasting."""
        try:
            include_forecasting = (
                request.args.get("forecast", "false").lower() == "true"
            )

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            revenue_data = loop.run_until_complete(
                analytics.generate_revenue_insights(include_forecasting)
            )

            loop.close()
            return jsonify(revenue_data)

        except Exception as e:
            log.error("Failed to get revenue insights: %s", e)
            return jsonify({"error": str(e)}), 500

    @app.route("/api/revenue-optimization/<int:user_id>")
    def api_revenue_optimization(user_id: int):
        """API endpoint for user-specific revenue optimization data."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            from .revenue_optimization import ConversionEvent

            funnel_data = loop.run_until_complete(
                revenue_optimizer.track_conversion_funnel(
                    user_id, ConversionEvent.SEARCH
                )
            )

            loop.close()
            return jsonify(funnel_data)

        except Exception as e:
            log.error("Failed to get revenue optimization data: %s", e)
            return jsonify({"error": str(e)}), 500

    @app.route("/health")
    def admin_health():
        """Health check endpoint for admin service."""
        return jsonify(
            {
                "status": "ok",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service": "admin_analytics",
            }
        )

    return app


# Simple HTML template for the admin dashboard
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MandiMonitor - Admin Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .dashboard { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .metric { font-size: 2em; font-weight: bold; color: #2196F3; }
        .label { color: #666; margin-top: 5px; }
        .header { text-align: center; margin-bottom: 30px; }
        .period-selector { margin: 20px 0; text-align: center; }
        .period-btn { margin: 0 5px; padding: 5px 15px; border: 1px solid #ddd; background: white; cursor: pointer; }
        .period-btn.active { background: #2196F3; color: white; }
        .loading { text-align: center; color: #666; }
        .error { color: #f44336; text-align: center; }
    </style>
</head>
<body>
    <div class="header">
        <h1>MandiMonitor Admin Dashboard</h1>
        <div class="period-selector">
            <button class="period-btn active" onclick="loadDashboard('7d')">7 Days</button>
            <button class="period-btn" onclick="loadDashboard('30d')">30 Days</button>
            <button class="period-btn" onclick="loadDashboard('90d')">90 Days</button>
        </div>
    </div>
    
    <div id="dashboard-content" class="loading">
        Loading dashboard...
    </div>

    <script>
        let currentPeriod = '30d';
        
        async function loadDashboard(period) {
            currentPeriod = period;
            
            // Update active button
            document.querySelectorAll('.period-btn').forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
            
            // Show loading
            document.getElementById('dashboard-content').innerHTML = '<div class="loading">Loading...</div>';
            
            try {
                const response = await fetch(`/api/dashboard/${period}`);
                const data = await response.json();
                
                if (data.error) {
                    throw new Error(data.error);
                }
                
                renderDashboard(data);
            } catch (error) {
                document.getElementById('dashboard-content').innerHTML = 
                    `<div class="error">Error loading dashboard: ${error.message}</div>`;
            }
        }
        
        function renderDashboard(data) {
            const html = `
                <div class="dashboard">
                    <div class="card">
                        <div class="metric">${data.user_metrics.total}</div>
                        <div class="label">Total Users</div>
                        <small>Active: ${data.user_metrics.active_monthly} | Growth: ${data.user_metrics.growth_rate.toFixed(1)}%</small>
                    </div>
                    
                    <div class="card">
                        <div class="metric">${data.product_metrics.total_watches}</div>
                        <div class="label">Total Watches</div>
                        <small>Active: ${data.product_metrics.active_watches} | Products: ${data.product_metrics.total_products}</small>
                    </div>
                    
                    <div class="card">
                        <div class="metric">$${data.revenue_metrics.estimated_revenue}</div>
                        <div class="label">Estimated Revenue</div>
                        <small>Clicks: ${data.revenue_metrics.total_clicks} | CTR: ${(data.revenue_metrics.click_through_rate * 100).toFixed(2)}%</small>
                    </div>
                    
                    <div class="card">
                        <div class="metric">${data.performance_metrics.total_api_calls}</div>
                        <div class="label">API Calls</div>
                        <small>Cache: ${(data.performance_metrics.cache_efficiency * 100).toFixed(1)}% | Uptime: ${data.performance_metrics.system_uptime}%</small>
                    </div>
                    
                    <div class="card">
                        <h3>Key Insights</h3>
                        <ul>
                            ${data.key_insights.map(insight => `<li>${insight}</li>`).join('')}
                        </ul>
                    </div>
                    
                    <div class="card">
                        <h3>Action Items</h3>
                        <ul>
                            ${data.action_items.map(action => `<li>${action}</li>`).join('')}
                        </ul>
                    </div>
                </div>
            `;
            
            document.getElementById('dashboard-content').innerHTML = html;
        }
        
        // Load initial dashboard
        loadDashboard('30d');
    </script>
</body>
</html>
"""
