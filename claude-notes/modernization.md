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

## Constraints / facts checked

- Heroku Python buildpack supports uv (since 2025-05): needs `pyproject.toml` + `uv.lock` + `.python-version`, and **rejects apps with more than one package-manager file** — so `requirements.txt` must go when `uv.lock` arrives (`runtime.txt` is superseded by `.python-version`). Heroku: Python 3.10 is deprecated (upstream EOL 2026-10); 3.11–3.14 supported.
- django-environ `get_value('DEBUG', default=False)` infers bool cast from the default, so `DEBUG=0` → False (checked with 0.9.0). Not a bug.

## Issues noticed (not yet fixed)

- `SECRET_KEY` is hardcoded in settings.py and committed.
- `/post_discord/` is `csrf_exempt` with no login check: anyone who can reach the site can make the bot post to any channel.
- `update_puzzle` does `setattr` for every key in the request JSON (any logged-in user can set any field, e.g. `hunt_id`, `sheet_id`).
- `datetime.utcnow()` (deprecated) in views.py.
- Templates use protocol-relative CDN URLs (`//code.jquery.com/...`).
