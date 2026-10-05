#!/bin/sh
# Run the test suite in Docker, in a compose project ("herring-test") separate
# from the dev stack, so it never touches the dev database or ports.
# Extra arguments go to `manage.py test`, e.g. `scripts/test.sh puzzles.tests.test_views`.
set -eu
cd "$(dirname "$0")/.."
PROJECT="docker compose -p herring-test"
trap '$PROJECT down --volumes --remove-orphans >/dev/null 2>&1' EXIT
$PROJECT run --rm --build -T -w /opt/project/herring project python manage.py test --settings=herring.settings_test "$@"
