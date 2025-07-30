"""Minimal /admin interface with basic-auth and CSV export."""

from __future__ import annotations

import base64
from typing import Dict

from flask import Flask, Response, request, abort
from sqlmodel import Session, select, func

from .cache_service import engine
from .config import settings
from .models import User, Watch, Click, Price

app = Flask(__name__)


# --- Auth helper -----------------------------------------------------------


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
    try:
        user_pass = base64.b64decode(auth.split()[1]).decode()
    except Exception:
        abort(401)
    user, _, pwd = user_pass.partition(":")
    if user != settings.ADMIN_USER or pwd != settings.ADMIN_PASS:
        abort(401)


# --- Health route (no auth) -----------------------------------------------


@app.get("/health")
def health() -> str:  # nosec B701
    """Health check endpoint for uptime monitoring."""
    return "ok", 200


# --- Metrics route ---------------------------------------------------------


@app.get("/admin")
def metrics() -> Dict[str, int]:
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

        return {
            "explorers": explorers,
            "watch_creators": watch_creators,
            "live_watches": live_watches,
            "click_outs": click_outs,
            "scraper_fallbacks": scraper_fallbacks,
        }


# --- CSV download ----------------------------------------------------------


@app.get("/admin/prices.csv")
def prices_csv() -> Response:
    """Stream all price history as CSV."""
    _check_auth()

    def _generate():
        with Session(engine) as s:
            yield "id,watch_id,asin,price,source,fetched_at\n"
            for row in s.exec(select(Price)):
                yield f"{row.id},{row.watch_id},{row.asin},{row.price},{row.source},{row.fetched_at.isoformat()}\n"

    return Response(_generate(), mimetype="text/csv")


if __name__ == "__main__":
    app.run(port=8000)
