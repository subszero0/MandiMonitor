"""MandiMonitor Telegram Bot package."""

from bot.health import app as health_app
from .scheduler import scheduler, schedule_watch  # noqa: F401

__all__ = ["health_app"]
