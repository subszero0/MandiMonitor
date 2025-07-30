"""Flask health check and admin endpoints."""

import base64

from flask import Flask, jsonify, Response, request, abort
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
    """Health check endpoint for monitoring and load balancers.

    Returns
    -------
        JSON response with status indicator

    """
    return jsonify(status="ok")


@app.route("/admin")
def metrics():
    """Return high-level funnel metrics."""
    _check_auth()
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

        return jsonify(
            {
                "explorers": explorers,
                "watch_creators": watch_creators,
                "live_watches": live_watches,
                "click_outs": click_outs,
                "scraper_fallbacks": scraper_fallbacks,
            }
        )


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
