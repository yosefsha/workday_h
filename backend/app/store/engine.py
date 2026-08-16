"""The database engine, created once at import time."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine

from app.config import settings

# pool_pre_ping costs one round trip per checkout and buys immunity to
# connections killed underneath us by a restart or an idle timeout.
engine: Engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
