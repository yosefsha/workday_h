#!/bin/sh
# Migrate, then run whatever was asked for.
#
# The schema is applied by the thing that owns it, at the moment it starts, so
# `docker compose up` on an empty volume produces a working service without a
# separate manual step. `exec` hands PID 1 to the real process so signals reach
# it and the container stops promptly.
set -eu

echo "applying database migrations"
alembic upgrade head

exec "$@"
