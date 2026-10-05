# Modernization (started 2026-10)

## Baseline as found (commit 8c31d25, last touched 2025-01)

Checked 2026-10-05 by running the unmodified repo:
- `docker compose up` (python:3.10.8-alpine, postgres 10.11, redis 4.0.14) **works**: deps install (apk + pip at every container start, ~2 min), migrations apply, `makemigrations` reports no model drift, gunicorn serves, login as admin/admin works, `/puzzles/` JSON works, celery worker+beat connect to redis.
- Dev annoyance: the `discordbot` Procfile.dev entry exits immediately when Discord is disabled, and `watchmedo auto-restart` respawns it about once a second forever.
- Frontend: `pnpm install` + `webpack` (4.47) builds fine on node 24 as-is (webpack 4.47 has the Node 17+ md4 fix).
- compose's `version:` key is obsolete (warning only).

## Dependency census (2026-10-05, grep of imports in herring/)

- Declared but never imported: Whoosh, natsort, Unidecode, pyOpenSSL, yarl, urllib3, static3 (only via dj-static).
- Imported only by dead code: `websockets` (imported in tasks.py, unused), `bs4` + `requests` (only the disabled `scrape_activity_log` string block).
- Imported but not declared (arrive transitively): `cachetools` (via google-auth), `asgiref` (via Django), `kombu` (via celery).
- Frontend CSS/JS from CDNs in templates: Bootstrap 3.3.2, jQuery 1.11.2, less.js 2.2.0 compiling `style.less` in the browser.

Latest versions at that date: Django 6.1.1 (needs py>=3.12; 5.2 is the current LTS), celery 5.6.3, redis-py 8.1, celery-redbeat 2.4.2, discord.py 2.7.1, psycopg 3.3, React 19.3, webpack 5.111.

## Decisions (user, 2026-10-05)

- Production stays on Heroku for now (don't mix a hosting change into this work).
- Target Django 5.2 LTS.
- Keep committing the built `bundle.js`; building at deploy time is deferred.
- Fix the security issues as part of this work, in their own commits.

## Tooling as set up (step 2)

- Python: `pyproject.toml` (`[tool.uv] package = false`, `exclude-newer = "14 days"`), `uv.lock`, `.python-version`. `requirements.txt` and `runtime.txt` were removed (Heroku requires a single package-manager file). The `dev` dependency group (honcho, watchdog) is skipped on Heroku (`--no-default-groups`).
- Relative `exclude-newer` checked with uv 0.12.19: the lockfile stores `exclude-newer-span = "P14D"` plus a dummy absolute value for older uv versions, and `uv sync --locked` accepts it.
- Docker: `Dockerfile` bakes the venv into `/opt/venv` (outside the `/opt/project` bind mount); `.dockerignore` only admits the manifests. Compose runs as `HERRING_UID`/`HERRING_GID` (default 1000, created in the image too; without a passwd entry Celery assumed it was root). Postgres data is in a named volume. `scripts/test.sh` uses compose project `herring-test` and tears it down after.
- Frontend: pnpm settings live in `herring/puzzles/static-src/pnpm-workspace.yaml` (`minimumReleaseAge`, `blockExoticSubdeps`, `trustPolicy: no-downgrade`).
  - `trustPolicyExclude` entries, checked 2026-10-05: `semver@6.3.1` and `semver@5.7.2` were both published 2023-07-10 by lukekarrys (npm CLI team) as backports of the ReDoS fix (CVE-2022-25883), without provenance, after 7.x releases had it. Pulled in by Babel 7 / webpack-cli 3; should become unnecessary once that tooling is replaced.
- Dev shutdown: watchmedo stops its child with SIGINT by default, which gives Celery a warm shutdown that waits for running tasks; Procfile.dev now passes `--signal SIGTERM` so dev matches production (`REMAP_SIGTERM=SIGQUIT` → cold shutdown). `docker compose stop` takes ~2s.

## Constraints / facts checked

- Heroku Python buildpack supports uv (since 2025-05): needs `pyproject.toml` + `uv.lock` + `.python-version`, and **rejects apps with more than one package-manager file** — so `requirements.txt` must go when `uv.lock` arrives (`runtime.txt` is superseded by `.python-version`). Heroku: Python 3.10 is deprecated (upstream EOL 2026-10); 3.11–3.14 supported.
- django-environ `get_value('DEBUG', default=False)` infers bool cast from the default, so `DEBUG=0` → False (checked with 0.9.0). Not a bug.

## Issues noticed (not yet fixed)

- lazy-object-proxy: `del proxy.__target__` (used by `discordbot.do_in_discord` to rebuild a dead announcer bot) is implementation-dependent: works with the 1.8.0 manylinux wheel, raises AttributeError with the Alpine 1.8.0 build and with 1.12.0. Replace with an explicit holder.
- `LOGIN_REDIRECT_URL` unset: logging in without `?next=` lands on the nonexistent `/accounts/profile/`.
- `UserEditForm.email` is a required (disabled) field, so users without an email can never save their profile.
- The puzzle URL editor in the React UI is unreachable (`showPuzzleUrlModal` is never called), and would send `url` rather than `hunt_url`.

- `SECRET_KEY` is hardcoded in settings.py and committed.
- `/post_discord/` is `csrf_exempt` with no login check: anyone who can reach the site can make the bot post to any channel.
- `update_puzzle` does `setattr` for every key in the request JSON (any logged-in user can set any field, e.g. `hunt_id`, `sheet_id`).
- `datetime.utcnow()` (deprecated) in views.py.
- Templates use protocol-relative CDN URLs (`//code.jquery.com/...`).
