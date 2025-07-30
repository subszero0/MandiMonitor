"""Sentry + health helpers."""

from __future__ import annotations

import sentry_sdk

from .config import settings

if settings.SENTRY_DSN:
    sentry_sdk.init(dsn=settings.SENTRY_DSN, traces_sample_rate=1.0)