"""Runtime configuration, read from the environment at import time.

Every value has a default that works on a laptop, so `python -m app report`
runs against a local Postgres with no environment set up. The one deliberate
exception is INGEST_TOKEN: it has no default, and its absence disables the
ingest endpoint entirely rather than leaving it open with a placeholder secret.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

RESUME_FEED_URL = (
    "https://recruiting-test-resume-data.hiredscore.com/"
    "allcands-full-api_hub_b1f6-acde48001122.json"
)
LINKEDIN_FEED_URL = (
    "https://recruiting-test-resume-data.hiredscore.com/"
    "linkedin_source_b1f6-acde48001122.csv"
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Points at the port docker-compose.yml publishes, so the CLI works from
    # the host against the compose stack with no environment set up. The API
    # container overrides it to reach the database over the compose network.
    database_url: str = "postgresql+psycopg://app:app@localhost:5433/app"

    resume_feed_url: str = RESUME_FEED_URL
    linkedin_feed_url: str = LINKEDIN_FEED_URL

    # A gap shorter than this is month-boundary noise, not time out of work.
    # A policy knob, not a constant: gaps are derived on read, so changing it
    # re-evaluates every snapshot already in the database.
    gap_threshold_days: int = 30

    feed_connect_timeout_seconds: float = 5.0
    feed_read_timeout_seconds: float = 10.0
    feed_retries: int = 1

    # Unset means POST /ingest is not registered at all.
    ingest_token: str | None = None

    # A fresh database has no snapshot to serve, so the first boot fills it.
    # Once a successful run exists, startup never touches the network again.
    ingest_on_startup_when_empty: bool = True


settings = Settings()
