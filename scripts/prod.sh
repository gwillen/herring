#!/bin/sh
# Runs docker compose for the self-hosted production stack
# (docker-compose.prod.yml + .env.prod), stamping the image with the git
# version of this checkout. Arguments are passed to docker compose, e.g.:
#   scripts/prod.sh up -d --build
#   scripts/prod.sh logs -f worker
#   scripts/prod.sh exec web python herring/manage.py createsuperuser
set -eu
cd "$(dirname "$0")/.."
# HERRING_PROD_ENV_FILE selects another env file (e.g. for a test instance).
ENV_FILE=${HERRING_PROD_ENV_FILE:-.env.prod}
[ -f "$ENV_FILE" ] || { echo "Missing $ENV_FILE; start from deploy/env.prod.example" >&2; exit 1; }
export HERRING_PROD_ENV_FILE="$ENV_FILE"
HERRING_VERSION=$(git describe --always --dirty --tags 2>/dev/null || echo unknown)
export HERRING_VERSION
exec docker compose -p "${HERRING_PROD_PROJECT:-herring-prod}" -f docker-compose.prod.yml --env-file "$ENV_FILE" "$@"
