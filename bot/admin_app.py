"""Secure admin interface with enhanced authentication and protection."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from typing import Dict, Optional, Tuple
from functools import wraps
from datetime import datetime, timedelta

from flask import Flask, Response, request, abort, session, redirect, url_for, make_response
from werkzeug.security import check_password_hash, generate_password_hash
from sqlmodel import Session, select, func

from .cache_service import engine
from .config import settings
from .models import User, Watch, Click, Price
from .api_rate_limiter import check_admin_access_rate_limit
from .logging_config import SecurityEventLogger

security_logger = SecurityEventLogger()

app = Flask(__name__)

# Security configuration
app.config.update(
    SECRET_KEY=secrets.token_hex(32),  # Generate secure secret key
    SESSION_COOKIE_SECURE=True,        # HTTPS only cookies
    SESSION_COOKIE_HTTPONLY=True,      # Prevent XSS attacks
    SESSION_COOKIE_SAMESITE='Strict',  # CSRF protection
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),  # Session timeout
)

# Security headers middleware
@app.after_request
def add_security_headers(response):
    """Add comprehensive security headers to all responses."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    return response


# --- Enhanced Authentication System -------------------------------------------

class AdminAuthManager:
    """Enhanced authentication manager with security features."""

    # In production, these should be stored securely (AWS Secrets Manager, etc.)
    _admin_credentials = {
        'username': settings.ADMIN_USER,
        'password_hash': generate_password_hash(settings.ADMIN_PASS, method='pbkdf2:sha256:100000')
    }

    _failed_attempts: Dict[str, list] = {}
    _blocked_ips: Dict[str, float] = {}

    @classmethod
    def authenticate(cls, username: str, password: str, ip_address: str) -> Tuple[bool, str]:
        """Authenticate admin user with enhanced security."""
        # Check if IP is blocked
        if ip_address in cls._blocked_ips:
            if time.time() < cls._blocked_ips[ip_address]:
                return False, "IP temporarily blocked due to failed attempts"
            else:
                del cls._blocked_ips[ip_address]
                cls._failed_attempts.pop(ip_address, None)

        # Rate limiting check
        rate_limit_result = check_admin_access_rate_limit(ip_address)
        if not rate_limit_result.allowed:
            cls._handle_failed_attempt(ip_address)
            return False, f"Rate limit exceeded. Try again in {rate_limit_result.retry_after:.0f} seconds"

        # Credential validation
        if username != cls._admin_credentials['username']:
            cls._handle_failed_attempt(ip_address)
            security_logger.log_auth_attempt(False, username, ip_address)
            return False, "Invalid credentials"

        if not check_password_hash(cls._admin_credentials['password_hash'], password):
            cls._handle_failed_attempt(ip_address)
            security_logger.log_auth_attempt(False, username, ip_address)
            return False, "Invalid credentials"

        # Successful authentication
        cls._clear_failed_attempts(ip_address)
        security_logger.log_auth_attempt(True, username, ip_address)
        return True, "Authentication successful"

    @classmethod
    def _handle_failed_attempt(cls, ip_address: str):
        """Handle failed authentication attempts."""
        if ip_address not in cls._failed_attempts:
            cls._failed_attempts[ip_address] = []

        cls._failed_attempts[ip_address].append(time.time())

        # Keep only attempts from last hour
        cutoff = time.time() - 3600
        cls._failed_attempts[ip_address] = [
            attempt for attempt in cls._failed_attempts[ip_address]
            if attempt > cutoff
        ]

        # Block IP after 5 failed attempts in an hour
        if len(cls._failed_attempts[ip_address]) >= 5:
            cls._blocked_ips[ip_address] = time.time() + 900  # Block for 15 minutes
            security_logger.log_security_event(
                "IP_BLOCKED",
                "high",
                {"ip_address": ip_address, "reason": "Too many failed attempts"},
                None,
                ip_address
            )

    @classmethod
    def _clear_failed_attempts(cls, ip_address: str):
        """Clear failed attempts for successful login."""
        cls._failed_attempts.pop(ip_address, None)
        cls._blocked_ips.pop(ip_address, None)

    @classmethod
    def get_client_ip(cls) -> str:
        """Get client IP address with proxy support."""
        # Check for X-Forwarded-For header (behind proxy)
        x_forwarded_for = request.headers.get('X-Forwarded-For')
        if x_forwarded_for:
            # Take the first IP if multiple
            return x_forwarded_for.split(',')[0].strip()

        # Check for X-Real-IP header
        x_real_ip = request.headers.get('X-Real-IP')
        if x_real_ip:
            return x_real_ip

        # Fallback to remote address
        return request.remote_addr or 'unknown'


def require_auth(f):
    """Decorator for routes requiring authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            # Try basic auth fallback
            auth = request.authorization
            if not auth:
                return Response(
                    "Authentication required",
                    401,
                    {"WWW-Authenticate": 'Basic realm="Admin"'}
                )

            success, message = AdminAuthManager.authenticate(
                auth.username,
                auth.password,
                AdminAuthManager.get_client_ip()
            )

            if not success:
                return Response(message, 401)

            # Set session for future requests
            session['authenticated'] = True
            session['username'] = auth.username
            session['login_time'] = time.time()
            session.permanent = True

        # Check session timeout
        if time.time() - session.get('login_time', 0) > 1800:  # 30 minutes
            session.clear()
            return Response("Session expired", 401)

        return f(*args, **kwargs)
    return decorated_function


def _check_auth() -> None:
    """Legacy authentication check for backward compatibility."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Basic "):
        abort(401, "Authentication required")

    try:
        user_pass = base64.b64decode(auth.split()[1]).decode()
    except Exception:
        abort(401, "Invalid authentication format")

    user, _, pwd = user_pass.partition(":")
    success, message = AdminAuthManager.authenticate(user, pwd, AdminAuthManager.get_client_ip())

    if not success:
        abort(401, message)


# --- Public routes (no auth required) -------------------------------------


@app.get("/health")
def health() -> str:
    """Health check endpoint for uptime monitoring."""
    return "ok", 200


@app.get("/login")
def login_page():
    """Simple login page for session-based authentication."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>MandiMonitor Admin Login</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 50px; }
            .login-form { max-width: 300px; margin: 0 auto; }
            input { width: 100%; padding: 10px; margin: 10px 0; }
            button { width: 100%; padding: 10px; background: #007bff; color: white; border: none; }
        </style>
    </head>
    <body>
        <div class="login-form">
            <h2>Admin Login</h2>
            <form method="POST" action="/login">
                <input type="text" name="username" placeholder="Username" required>
                <input type="password" name="password" placeholder="Password" required>
                <button type="submit">Login</button>
            </form>
        </div>
    </body>
    </html>
    """


@app.post("/login")
def login():
    """Handle login form submission."""
    username = request.form.get('username')
    password = request.form.get('password')
    ip_address = AdminAuthManager.get_client_ip()

    if not username or not password:
        return "Username and password required", 400

    success, message = AdminAuthManager.authenticate(username, password, ip_address)

    if success:
        session['authenticated'] = True
        session['username'] = username
        session['login_time'] = time.time()
        session.permanent = True
        return redirect(url_for('metrics'))
    else:
        return f"Login failed: {message}", 401


@app.post("/logout")
def logout():
    """Logout and clear session."""
    username = session.get('username')
    ip_address = AdminAuthManager.get_client_ip()

    if username:
        security_logger.log_security_event(
            "LOGOUT",
            "low",
            {"username": username},
            username,
            ip_address
        )

    session.clear()
    return "Logged out successfully", 200


# --- Protected routes (require authentication) -----------------------------


@app.get("/admin")
@require_auth
def metrics() -> Dict[str, int]:
    """Return high-level funnel metrics."""
    try:
        with Session(engine) as s:
            # Count total users (explorers)
            explorers = s.exec(select(func.count(User.id))).one()

            # Count users who have created at least one watch
            watch_creators = s.exec(select(func.count(func.distinct(Watch.user_id)))).one()

            # Count total watches
            live_watches = s.exec(select(func.count(Watch.id))).one()

            # Count total click-outs
            click_outs = s.exec(select(func.count(Click.id))).one()

            # Count scraper fallbacks
            scraper_fallbacks = s.exec(
                select(func.count(Price.id)).where(Price.source == "scraper")
            ).one()

            return {
                "explorers": explorers,
                "watch_creators": watch_creators,
                "live_watches": live_watches,
                "click_outs": click_outs,
                "scraper_fallbacks": scraper_fallbacks,
            }
    except Exception as e:
        security_logger.log_security_event(
            "ADMIN_ACCESS_ERROR",
            "medium",
            {"error": str(e), "endpoint": "/admin"},
            session.get('username'),
            AdminAuthManager.get_client_ip()
        )
        abort(500, "Internal server error")


# --- CSV download ----------------------------------------------------------


@app.get("/admin/prices.csv")
@require_auth
def prices_csv() -> Response:
    """Stream all price history as CSV with security controls."""
    try:
        username = session.get('username')
        ip_address = AdminAuthManager.get_client_ip()

        # Log admin action
        security_logger.log_security_event(
            "ADMIN_CSV_EXPORT",
            "medium",
            {"action": "price_history_export"},
            username,
            ip_address
        )

        def _generate():
            try:
                with Session(engine) as s:
                    yield "id,watch_id,asin,price,source,fetched_at\n"
                    for row in s.exec(select(Price)):
                        yield f"{row.id},{row.watch_id},{row.asin},{row.price},{row.source},{row.fetched_at.isoformat()}\n"
            except Exception as e:
                security_logger.log_security_event(
                    "ADMIN_CSV_EXPORT_ERROR",
                    "high",
                    {"error": str(e)},
                    username,
                    ip_address
                )
                yield "Error generating CSV\n"

        response = Response(_generate(), mimetype="text/csv")
        response.headers['Content-Disposition'] = 'attachment; filename=price_history.csv'
        response.headers['X-Content-Type-Options'] = 'nosniff'

        return response

    except Exception as e:
        security_logger.log_security_event(
            "ADMIN_CSV_ACCESS_ERROR",
            "high",
            {"error": str(e)},
            session.get('username'),
            AdminAuthManager.get_client_ip()
        )
        abort(500, "Access denied")


# --- Admin dashboard page --------------------------------------------------


@app.get("/admin/dashboard")
@require_auth
def admin_dashboard():
    """HTML dashboard for admin interface."""
    username = session.get('username', 'Unknown')
    login_time = datetime.fromtimestamp(session.get('login_time', time.time())).strftime('%Y-%m-%d %H:%M:%S')

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>MandiMonitor Admin Dashboard</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .header {{ background: #f8f9fa; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
            .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }}
            .metric {{ background: #e9ecef; padding: 20px; border-radius: 5px; text-align: center; }}
            .metric h3 {{ margin: 0; color: #495057; }}
            .metric p {{ font-size: 24px; font-weight: bold; margin: 10px 0 0 0; }}
            .actions {{ margin-top: 30px; }}
            .btn {{ display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 5px; }}
            .btn:hover {{ background: #0056b3; }}
            .logout {{ background: #dc3545; }}
            .logout:hover {{ background: #c82333; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>MandiMonitor Admin Dashboard</h1>
            <p>Welcome, {username} | Login time: {login_time}</p>
        </div>

        <div class="metrics" id="metrics">
            <div class="metric">
                <h3>Explorers</h3>
                <p id="explorers">Loading...</p>
            </div>
            <div class="metric">
                <h3>Watch Creators</h3>
                <p id="watch-creators">Loading...</p>
            </div>
            <div class="metric">
                <h3>Live Watches</h3>
                <p id="live-watches">Loading...</p>
            </div>
            <div class="metric">
                <h3>Click Outs</h3>
                <p id="click-outs">Loading...</p>
            </div>
        </div>

        <div class="actions">
            <a href="/admin" class="btn">View JSON Metrics</a>
            <a href="/admin/prices.csv" class="btn">Download Price History</a>
            <form method="POST" action="/logout" style="display: inline;">
                <button type="submit" class="btn logout">Logout</button>
            </form>
        </div>

        <script>
            // Load metrics via AJAX
            fetch('/admin')
                .then(response => response.json())
                .then(data => {{
                    document.getElementById('explorers').textContent = data.explorers;
                    document.getElementById('watch-creators').textContent = data.watch_creators;
                    document.getElementById('live-watches').textContent = data.live_watches;
                    document.getElementById('click-outs').textContent = data.click_outs;
                }})
                .catch(error => {{
                    console.error('Error loading metrics:', error);
                    document.getElementById('metrics').innerHTML = '<p>Error loading metrics</p>';
                }});
        </script>
    </body>
    </html>
    """


if __name__ == "__main__":
    # For development only - use proper WSGI server in production
    app.run(
        host="0.0.0.0",
        port=8000,
        debug=False,  # Never enable debug in production
        ssl_context=None  # Use proper SSL/TLS in production
    )
