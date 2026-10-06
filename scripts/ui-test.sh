#!/bin/sh
# Browser smoke test of the frontend. Starts a throwaway stack (compose project
# "herring-ui", port $HERRING_UI_TEST_PORT, default 18100), seeds sample data,
# and drives the UI in headless Chromium using Playwright's Docker image.
# Screenshots go to the directory given as $1 (default: ui-test-output/).
set -eu
cd "$(dirname "$0")/.."
OUT=${1:-ui-test-output}
PORT=${HERRING_UI_TEST_PORT:-18100}
PLAYWRIGHT_VERSION=1.62.0
PROJECT="docker compose -p herring-ui -f docker-compose.yml -f scripts/ui/compose.override.yml"
trap '$PROJECT down --volumes --remove-orphans >/dev/null 2>&1' EXIT

mkdir -p "$OUT"
HERRING_PORT=$PORT $PROJECT up --build -d
echo "Waiting for the web server on port $PORT..."
for _ in $(seq 120); do
    curl -sf -o /dev/null "http://localhost:$PORT/accounts/login/" && break
    sleep 1
done
$PROJECT exec -T project herring/manage.py shell < scripts/ui/seed.py

docker run --rm --network host --user "$(id -u):$(id -g)" -e HOME=/tmp \
    -v "$PWD/scripts/ui:/scripts:ro" -v "$PWD/$OUT:/out" \
    "mcr.microsoft.com/playwright/python:v$PLAYWRIGHT_VERSION-noble" \
    sh -c "pip install -q --user --break-system-packages --disable-pip-version-check playwright==$PLAYWRIGHT_VERSION 2>&1 | grep -v 'not on PATH\|no-warn-script-location' ;
           python /scripts/browse.py http://localhost:$PORT /out/ui"
