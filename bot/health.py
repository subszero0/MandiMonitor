"""Flask health check and admin endpoints."""

import base64
from datetime import datetime, timedelta

from flask import Flask, jsonify, Response, request, abort, render_template_string
from sqlmodel import Session, select, func

from .cache_service import engine
from .config import settings
from .models import User, Watch, Click, Price

app = Flask(__name__)


def _check_auth() -> None:
    """Check HTTP Basic Auth credentials."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Basic "):
        abort(
            Response(
                "Auth required",
                401,
                {"WWW-Authenticate": 'Basic realm="Admin"'},
            )
        )

    # Decode base64 credentials
    try:
        encoded_creds = auth[6:]  # Remove "Basic "
        decoded_creds = base64.b64decode(encoded_creds).decode("utf-8")
        username, password = decoded_creds.split(":", 1)
    except (ValueError, UnicodeDecodeError):
        abort(401)

    # Check against settings
    if username != settings.ADMIN_USER or password != settings.ADMIN_PASS:
        abort(401)


@app.route("/health")
def health():
    """
    Basic health check endpoint for monitoring and load balancers.

    Returns
    -------
        JSON response with status indicator
    """
    return jsonify(status="ok")


@app.route("/health/ai")  
def ai_health():
    """
    Phase R5.2: Enhanced health check with AI performance monitoring.
    
    Returns
    -------
        JSON response with AI system health metrics
    """
    try:
        from .ai_performance_monitor import get_ai_monitor
        
        # Get AI performance statistics
        monitor = get_ai_monitor()
        stats = monitor.get_performance_stats()
        
        # Calculate health indicators
        health_status = "ok"
        warnings = []
        
        # Check model availability
        try:
            from .product_selection_models import get_selection_model
            test_model = get_selection_model("test query", 5)
            model_available = True
        except Exception as e:
            model_available = False
            health_status = "degraded"
            warnings.append(f"Model initialization failed: {str(e)[:100]}")
        
        # Check recent performance
        recent_failures = stats.get("recent_failures", 0)
        if recent_failures > 5:  # More than 5 failures in recent period
            health_status = "degraded" 
            warnings.append(f"High failure rate: {recent_failures} recent failures")
        
        # Check latency
        avg_latency = stats.get("average_latency_ms", 0)
        if avg_latency > 1000:  # More than 1 second average
            health_status = "degraded"
            warnings.append(f"High latency: {avg_latency:.1f}ms average")
        
        return jsonify({
            "status": health_status,
            "ai_system": {
                "model_available": model_available,
                "recent_selections": stats.get("total_selections", 0),
                "success_rate": stats.get("success_rate", 0),
                "average_latency_ms": avg_latency,
                "recent_failures": recent_failures,
                "model_distribution": stats.get("model_usage", {}),
            },
            "warnings": warnings,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": f"Health check failed: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@app.route("/admin/rollout")
def rollout_dashboard():
    """
    Phase R7: Rollout management dashboard for production deployment.
    """
    _check_auth()
    
    try:
        from .feature_rollout import get_rollout_manager
        
        manager = get_rollout_manager()
        rollout_status = manager.get_rollout_status()
        
        # Generate HTML dashboard
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>AI Feature Rollout Dashboard</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .feature { 
                    border: 1px solid #ddd; 
                    margin: 10px 0; 
                    padding: 15px; 
                    border-radius: 5px; 
                }
                .enabled { background-color: #d4edda; }
                .disabled { background-color: #f8d7da; }
                .percentage { font-weight: bold; font-size: 1.2em; }
                .controls { margin: 10px 0; }
                .controls input { margin: 5px; padding: 5px; }
                .emergency { background-color: #dc3545; color: white; }
            </style>
        </head>
        <body>
            <h1>🚀 AI Feature Rollout Dashboard</h1>
            <p><strong>Last Updated:</strong> {timestamp}</p>
            <p><strong>Rollback History:</strong> {rollback_count} events</p>
            
            <h2>🎯 Feature Status</h2>
        """.format(
            timestamp=datetime.fromtimestamp(rollout_status["timestamp"]).strftime("%Y-%m-%d %H:%M:%S"),
            rollback_count=rollout_status["rollback_history"]
        )
        
        # Add feature cards
        for feature_name, feature_info in rollout_status["features"].items():
            status_class = "enabled" if feature_info["enabled"] else "disabled"
            rollout_pct = feature_info["rollout_percentage"]
            
            html += f"""
            <div class="feature {status_class}">
                <h3>{feature_name.replace('_', ' ').title()}</h3>
                <div class="percentage">Rollout: {rollout_pct}%</div>
                <p><strong>Status:</strong> {"✅ Enabled" if feature_info["enabled"] else "❌ Disabled"}</p>
                <p><strong>Conditions:</strong> {"Yes" if feature_info["has_conditions"] else "None"}</p>
                <p><strong>Whitelist:</strong> {feature_info["whitelist_size"]} users</p>
                <p><strong>Blacklist:</strong> {feature_info["blacklist_size"]} users</p>
                
                <div class="controls">
                    <strong>Actions:</strong>
                    <button onclick="updateRollout('{feature_name}', 0)" class="emergency">Emergency Disable</button>
                    <button onclick="updateRollout('{feature_name}', 50)">50% Rollout</button>
                    <button onclick="updateRollout('{feature_name}', 75)">75% Rollout</button>
                    <button onclick="updateRollout('{feature_name}', 100)">Full Enable</button>
                </div>
            </div>
            """
        
        html += """
            <h2>📊 Quick Actions</h2>
            <div class="controls">
                <button onclick="emergencyDisableAll()" class="emergency">🚨 EMERGENCY: Disable All AI</button>
                <button onclick="location.reload()">🔄 Refresh Dashboard</button>
                <button onclick="showRollbackHistory()">📈 Rollback History</button>
            </div>
            
            <script>
                function updateRollout(feature, percentage) {
                    if (percentage === 0) {
                        const reason = prompt('Emergency disable reason:');
                        if (!reason) return;
                        if (!confirm(`Emergency disable ${feature}? Reason: ${reason}`)) return;
                    } else {
                        if (!confirm(`Update ${feature} to ${percentage}% rollout?`)) return;
                    }
                    
                    fetch('/admin/rollout/update', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ feature: feature, percentage: percentage })
                    }).then(() => location.reload());
                }
                
                function emergencyDisableAll() {
                    const reason = prompt('EMERGENCY: Disable all AI features. Reason:');
                    if (!reason) return;
                    if (!confirm('This will disable ALL AI features immediately!')) return;
                    
                    fetch('/admin/rollout/emergency-disable-all', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ reason: reason })
                    }).then(() => location.reload());
                }
            </script>
        </body>
        </html>
        """
        
        return html
        
    except Exception as e:
        return jsonify({
            "error": f"Rollout dashboard failed: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@app.route("/admin/rollout/update", methods=["POST"])
def update_rollout():
    """Update feature rollout percentage."""
    _check_auth()
    
    try:
        from .feature_rollout import get_rollout_manager
        
        data = request.get_json()
        feature_name = data.get("feature")
        percentage = data.get("percentage", 0)
        
        manager = get_rollout_manager()
        success = manager.update_rollout_percentage(feature_name, percentage)
        
        return jsonify({
            "success": success,
            "feature": feature_name,
            "new_percentage": percentage
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/admin/rollout/emergency-disable-all", methods=["POST"]) 
def emergency_disable_all():
    """Emergency disable all AI features."""
    _check_auth()
    
    try:
        from .feature_rollout import get_rollout_manager
        
        data = request.get_json()
        reason = data.get("reason", "Emergency disable")
        
        manager = get_rollout_manager()
        ai_features = [name for name in manager._flags.keys() if name.startswith("ai_")]
        
        results = {}
        for feature in ai_features:
            results[feature] = manager.emergency_disable_feature(feature, reason)
        
        return jsonify({
            "success": True,
            "disabled_features": results,
            "reason": reason
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/admin")
def admin_dashboard():
    """Return comprehensive admin dashboard."""
    _check_auth()
    
    try:
        with Session(engine) as s:
            # Get basic metrics
            explorers = s.exec(select(func.count(User.id))).one()
            watch_creators = s.exec(select(func.count(func.distinct(Watch.user_id)))).one()
            live_watches = s.exec(select(func.count(Watch.id))).one()
            click_outs = s.exec(select(func.count(Click.id))).one()
            scraper_fallbacks = s.exec(
                select(func.count(Price.id)).where(Price.source == "scraper")
            ).one()
            
            # Get recent activity (last 24 hours)
            yesterday = datetime.utcnow() - timedelta(days=1)
            
            recent_users = s.exec(
                select(func.count(User.id)).where(User.first_seen >= yesterday)
            ).one()
            
            recent_watches = s.exec(
                select(func.count(Watch.id)).where(Watch.created >= yesterday)
            ).one()
            
            recent_clicks = s.exec(
                select(func.count(Click.id)).where(Click.clicked_at >= yesterday)
            ).one()
            
            # Get recent watches with details - simplified query
            recent_watch_details = []
            try:
                recent_watch_results = s.exec(
                    select(Watch, User)
                    .join(User, Watch.user_id == User.id)
                    .where(Watch.created >= yesterday)
                    .order_by(Watch.created.desc())
                    .limit(10)
                ).all()
                recent_watch_details = recent_watch_results
            except Exception as e:
                print(f"Error fetching recent watches: {e}")
            
            # Get top brands being watched - simplified query
            brand_stats = []
            try:
                brand_results = s.exec(
                    select(Watch.brand, func.count(Watch.id).label("count"))
                    .where(Watch.brand.isnot(None))
                    .group_by(Watch.brand)
                    .order_by(func.count(Watch.id).desc())
                    .limit(10)
                ).all()
                brand_stats = brand_results
            except Exception as e:
                print(f"Error fetching brand stats: {e}")
            
            # Get price source stats
            paapi_prices = s.exec(
                select(func.count(Price.id)).where(Price.source == "paapi")
            ).one()
            
            total_prices = s.exec(select(func.count(Price.id))).one()
            
        return render_template_string(ADMIN_TEMPLATE, 
            explorers=explorers,
            watch_creators=watch_creators,
            live_watches=live_watches,
            click_outs=click_outs,
            scraper_fallbacks=scraper_fallbacks,
            recent_users=recent_users,
            recent_watches=recent_watches,
            recent_clicks=recent_clicks,
            recent_watch_details=recent_watch_details,
            brand_stats=brand_stats,
            paapi_prices=paapi_prices,
            total_prices=total_prices,
            conversion_rate=round((click_outs / live_watches * 100) if live_watches > 0 else 0, 2),
            paapi_success_rate=round((paapi_prices / total_prices * 100) if total_prices > 0 else 0, 2),
            datetime=datetime
        )
    except Exception as e:
        # Return simple error page for debugging
        return f"<h1>Admin Dashboard Error</h1><p>Error: {str(e)}</p><p>Please check logs for details.</p>", 500


@app.route("/admin/prices.csv")
def prices_csv():
    """Stream all price history as CSV."""
    _check_auth()

    def _generate():
        with Session(engine) as s:
            yield "id,watch_id,asin,price,source,fetched_at\n"
            for row in s.exec(select(Price)):
                yield f"{row.id},{row.watch_id},{row.asin},{row.price},{row.source},{row.fetched_at.isoformat()}\n"

    return Response(_generate(), mimetype="text/csv")


# HTML template for admin dashboard
ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>MandiMonitor Admin Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            margin: 0; 
            padding: 20px; 
            background: #f5f5f5; 
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .header h1 { margin: 0; display: flex; align-items: center; }
        .header .subtitle { opacity: 0.8; margin-top: 5px; }
        .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px; }
        .metric-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }
        .metric-number { font-size: 2em; font-weight: bold; color: #3498db; margin-bottom: 5px; }
        .metric-label { color: #666; font-size: 0.9em; }
        .section { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .section h2 { margin-top: 0; color: #2c3e50; border-bottom: 2px solid #ecf0f1; padding-bottom: 10px; }
        .activity-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; }
        .watch-item { border-left: 4px solid #3498db; padding: 15px; background: #f8f9fa; margin-bottom: 10px; border-radius: 0 4px 4px 0; }
        .watch-keywords { font-weight: bold; margin-bottom: 5px; }
        .watch-meta { font-size: 0.85em; color: #666; }
        .brand-stat { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #eee; }
        .brand-stat:last-child { border-bottom: none; }
        .badge { background: #3498db; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; }
        .success { color: #27ae60; }
        .warning { color: #f39c12; }
        .danger { color: #e74c3c; }
        .footer { text-align: center; margin-top: 30px; color: #666; font-size: 0.9em; }
        .refresh-btn { background: #3498db; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; float: right; }
        .refresh-btn:hover { background: #2980b9; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>
                🤖 MandiMonitor Admin Dashboard
                <button class="refresh-btn" onclick="location.reload()">🔄 Refresh</button>
            </h1>
            <div class="subtitle">Real-time monitoring and analytics for your price tracking bot</div>
        </div>

        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-number">{{ explorers }}</div>
                <div class="metric-label">Total Users</div>
            </div>
            <div class="metric-card">
                <div class="metric-number">{{ watch_creators }}</div>
                <div class="metric-label">Watch Creators</div>
            </div>
            <div class="metric-card">
                <div class="metric-number">{{ live_watches }}</div>
                <div class="metric-label">Active Watches</div>
            </div>
            <div class="metric-card">
                <div class="metric-number">{{ click_outs }}</div>
                <div class="metric-label">Affiliate Clicks</div>
            </div>
            <div class="metric-card">
                <div class="metric-number">{{ conversion_rate }}%</div>
                <div class="metric-label">Click Rate</div>
            </div>
            <div class="metric-card">
                <div class="metric-number">{{ paapi_success_rate }}%</div>
                <div class="metric-label">PA-API Success</div>
            </div>
        </div>

        <div class="activity-grid">
            <div class="section">
                <h2>📈 Recent Activity (24h)</h2>
                <div class="metric-card">
                    <div class="metric-number {{ 'success' if recent_users > 0 else 'warning' }}">{{ recent_users }}</div>
                    <div class="metric-label">New Users</div>
                </div>
                <div class="metric-card">
                    <div class="metric-number {{ 'success' if recent_watches > 0 else 'warning' }}">{{ recent_watches }}</div>
                    <div class="metric-label">New Watches</div>
                </div>
                <div class="metric-card">
                    <div class="metric-number {{ 'success' if recent_clicks > 0 else 'warning' }}">{{ recent_clicks }}</div>
                    <div class="metric-label">Recent Clicks</div>
                </div>
            </div>

            <div class="section">
                <h2>🔥 Top Brands</h2>
                {% for brand, count in brand_stats %}
                <div class="brand-stat">
                    <span>{{ brand.title() if brand else 'No Brand' }}</span>
                    <span class="badge">{{ count }}</span>
                </div>
                {% endfor %}
                {% if not brand_stats %}
                <p style="color: #666; text-align: center;">No brand data available yet</p>
                {% endif %}
            </div>
        </div>

        <div class="section">
            <h2>🕐 Recent Watches</h2>
            {% for watch, user in recent_watch_details %}
            <div class="watch-item">
                <div class="watch-keywords">{{ watch.keywords }}</div>
                <div class="watch-meta">
                    <strong>User:</strong> {{ user.tg_user_id }} | 
                    <strong>Brand:</strong> {{ watch.brand or 'Any' }} | 
                    <strong>Max Price:</strong> {{ '₹{:,}'.format(watch.max_price) if watch.max_price else 'Any' }} |
                    <strong>Min Discount:</strong> {{ '{}%'.format(watch.min_discount) if watch.min_discount else 'Any' }} |
                    <strong>Created:</strong> {{ watch.created.strftime('%Y-%m-%d %H:%M') }}
                </div>
            </div>
            {% endfor %}
            {% if not recent_watch_details %}
            <p style="color: #666; text-align: center;">No recent watches found</p>
            {% endif %}
        </div>

        <div class="section">
            <h2>⚙️ System Health</h2>
            <div class="activity-grid">
                <div>
                    <h3>Price Fetching</h3>
                    <p><strong>PA-API Fetches:</strong> <span class="success">{{ paapi_prices }}</span></p>
                    <p><strong>Scraper Fallbacks:</strong> <span class="{{ 'warning' if scraper_fallbacks > paapi_prices else 'success' }}">{{ scraper_fallbacks }}</span></p>
                    <p><strong>Total Price Checks:</strong> {{ total_prices }}</p>
                </div>
                <div>
                    <h3>Quick Actions</h3>
                    <p><a href="/admin/prices.csv" style="color: #3498db;">📥 Download Price History CSV</a></p>
                    <p><a href="/health" style="color: #3498db;">💚 Health Check Endpoint</a></p>
                </div>
            </div>
        </div>

        <div class="footer">
            <p>MandiMonitor Bot Admin Panel | Last updated: {{ datetime.now().strftime('%Y-%m-%d %H:%M:%S') }} IST</p>
        </div>
    </div>
    
    <script>
        // Auto-refresh every 5 minutes
        setTimeout(() => location.reload(), 5 * 60 * 1000);
    </script>
</body>
</html>
"""
