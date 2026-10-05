# Modernization (2026-10)

Done on branch `claude-2026-oct` (2026-10-05): tests, uv/pnpm + Docker, Django 3.2 → 5.2, Python 3.10 → 3.14, all deps current, frontend on esbuild + React 19, security fixes. **Not yet deployed to Heroku** — see "Deploy checklist".

## Decisions (user, 2026-10-05)

- Production stays on Heroku for now (don't mix a hosting change into this work). User is open to hosting recommendations later.
- Django 5.2 LTS (supported until April 2028; next LTS 6.2 ~April 2027).
- Keep committing the built `bundle.js` / `style.css`; building at deploy time is deferred.
- Security fixes in their own commits, as part of this work.

## Baseline as found (commit 8c31d25, last touched 2025-01)

Checked 2026-10-05 by running the unmodified repo: `docker compose up` (python:3.10.8-alpine, postgres 10.11, redis 4.0.14) worked; deps installed via apk + pip at every container start (~2 min). webpack 4.47 built fine on node 24. No tests existed.

## Tooling as set up

- Python: `pyproject.toml` (`[tool.uv] package = false`, `exclude-newer = "14 days"`), `uv.lock`, `.python-version` (3.14). `requirements.txt` / `runtime.txt` removed (Heroku requires a single package-manager file). `dev` group (honcho, watchdog) is skipped on Heroku (`uv sync --locked --no-default-groups`).
- Relative `exclude-newer` checked with uv 0.12.19: lockfile stores `exclude-newer-span = "P14D"` plus a dummy absolute value for older uv; `uv sync --locked` accepts it.
- Docker (dev only): `Dockerfile` bakes the venv into `/opt/venv` (outside the `/opt/project` bind mount), `uv sync --locked --no-build` (no compiler in the image; every dep must have a wheel). `.dockerignore` only admits the manifests. Compose runs as `HERRING_UID`/`HERRING_GID` (default 1000, user also created in the image — without a passwd entry Celery assumed root). Named Postgres volume; Postgres 17 / Redis 7. `SECRET_KEY` is set to a dev-only value in compose.
- Tests: `scripts/test.sh` (compose project `herring-test`, torn down after; Django test runner with `herring.settings_test`: Celery eager, integrations off). `scripts/ui-test.sh` (project `herring-ui`, port 18100; seeds `scripts/ui/seed.py`, drives Chromium via `mcr.microsoft.com/playwright/python` + pip `playwright==` same version; fails on console errors/failed requests).
- Frontend: `herring/puzzles/static-src/build.mjs` (esbuild for `app.js` → `static/bundle.js`; less with `math: 'always'` for `style.less` → `static/style.css`). pnpm settings in `pnpm-workspace.yaml`: `minimumReleaseAge`, `blockExoticSubdeps`, `trustPolicy: no-downgrade`, `allowBuilds: {esbuild: false}` (pnpm 11 errors on unreviewed build scripts; esbuild's binary comes via optional deps anyway).
  - History: with Babel 7 / webpack-cli 3, `trustPolicy` blocked `semver@6.3.1` and `@5.7.2` (2023-07-10 ReDoS-fix backports by an npm CLI maintainer, no provenance). Gone with that tooling; if they reappear, that's why.
- Dev shutdown: watchmedo stops its child with SIGINT by default (Celery warm shutdown → waits for tasks); Procfile.dev passes `--signal SIGTERM` so dev matches prod (`REMAP_SIGTERM=SIGQUIT` → cold). `docker compose stop` ≈ 2s.

## Facts checked (2026-10-05)

- Heroku Python buildpack supports uv since 2025-05; needs `pyproject.toml` + `uv.lock` + `.python-version`, rejects multiple package-manager files. Python 3.10 deprecated there; 3.11–3.14 supported. Stacks: heroku-24 default, heroku-26 supported, heroku-22 deprecated (through 2027-04), heroku-20 EOL.
- Django 5.2 requires PostgreSQL 14+.
- redis-py 6.4: `ssl_cert_reqs=None` still means `CERT_NONE` (used by `tasks.redis_client()` for `rediss://`).
- celery-redbeat 2.4 warns "will stop falling back to broker_url/broker_transport_options in 2.5.0" even though `CELERY_REDBEAT_REDIS_URL` is set: its `is_key_in_conf` checks `app.conf.keys()`, which doesn't list Django-namespaced custom keys. The value actually used is correct. Re-check before upgrading redbeat to 2.5.
- django-environ `get_value('DEBUG', default=False)` infers bool from the default, so `DEBUG=0` → False. Not a bug.
- Old (`static/style.less` via less.js 2.2.0 in browser) vs new compiled CSS: identical to lessc 2.7.3 output except `.5`/`0.5` (lessc 2.2.0 CLI outputs nothing on node 24). UI screenshots old vs new: pixel-identical except the open Bootstrap dropdown (3.3.2 → 3.4.1).
- store.js v2 (old UI-settings storage) used the plain key with JSON values, so `loadStored('uiSettings')` reads existing settings.

## Fixed along the way (details in commit messages)

- `check_connection_to_messaging` held a worker + Redis mutex forever even when the listener bot doesn't run under Celery.
- `del DISCORD_ANNOUNCER.__target__` (lazy-object-proxy) didn't reset the bot on newer/some builds → replaced by `discordbot.LazyAnnouncer`. `check_spreadsheet_service` tested a proxy `is not None` (always true) → `drive_service()` function.
- Security: SECRET_KEY from env (no default); `/post_discord/` requires `token` = `SECRETS['post-discord-token']`; puzzle update endpoint accepts only answer/note/tags strings; signup secret compared in constant time and refused if unconfigured.
- `LOGIN_REDIRECT_URL = '/'`; profile edit works for users without email.

## Deploy checklist (Heroku; not yet done)

1. Check stack, Postgres ≥ 14, buildpacks (README "Deploying to Heroku").
2. Set `SECRET_KEY` config var (logs everyone out once).
3. If anything calls `/post_discord/`, add `post-discord-token` to `SECRETS` and update the caller to send `token`.
4. Deploy to staging (`rage-herring-staging`) first; watch for Celery broker / redbeat errors with `rediss://` URLs (kombu/redis-py/redbeat all upgraded) and for collectstatic (whitenoise replaced dj-static).

## Open issues / recommendations

- `manage.py check --deploy`: SECURE_HSTS_SECONDS, SECURE_SSL_REDIRECT, SESSION_COOKIE_SECURE, CSRF_COOKIE_SECURE unset. Reasonable for an HTTPS-only Heroku app, but would break plain-http local dev unless env-controlled.
- `ALLOWED_HOSTS = ['*']`.
- The puzzle URL editor in the React UI is unreachable (`showPuzzleUrlModal` never called) and would send `url`, which the update endpoint now rejects.
- `tasks.optional_task` monkey-patches `apply_async` on tasks.
- discord.py 2.7 logs "PyNaCl / davey not installed, voice will NOT be supported" (voice channels are off by default).
