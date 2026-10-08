# Modernization (2026-10)

Done on branch `claude-2026-oct` (2026-10-05/06): tests, uv/pnpm + Docker, Django 3.2 → 5.2, Python 3.10 → 3.14, all deps current, frontend on esbuild + React 19, security fixes, HTTPS hardening, self-hosted Compose option, /puzzles/ performance fixes. User has set SECRET_KEY on Heroku and moved the app to heroku-26 (2026-10-06).

## Decisions (user, 2026-10-05)

- Production stays on Heroku for now (don't mix a hosting change into this work). User is open to hosting recommendations later.
- Django 5.2 LTS (supported until April 2028; next LTS 6.2 ~April 2027).
- Keep committing the built `bundle.js` / `style.css`; building at deploy time is deferred.
- Security fixes in their own commits, as part of this work.

## Baseline as found (commit 8c31d25, last touched 2025-01)

Checked 2026-10-05 by running the unmodified repo: `docker compose up` (python:3.10.8-alpine, postgres 10.11, redis 4.0.14) worked; deps installed via apk + pip at every container start (~2 min). webpack 4.47 built fine on node 24. No tests existed.

## Tooling as set up

- Python: `pyproject.toml` (`[tool.uv] package = false`, `exclude-newer = "14 days"`), `uv.lock`, `.python-version` (3.14). `requirements.txt` / `runtime.txt` removed (Heroku requires a single package-manager file). `dev` group (honcho, watchdog) is skipped on Heroku (`uv sync --locked --no-default-groups`).
- **Upgrading: run `uv lock --upgrade`** (or `--upgrade-package X`). Raising a lower bound in pyproject only moves that package; uv keeps every other locked version that still satisfies constraints. That's how urllib3 stayed at 1.26.12 (from 2022) through the first upgrade pass until Dependabot flagged it.
- Relative `exclude-newer` checked with uv 0.12.19: lockfile stores `exclude-newer-span = "P14D"` plus a dummy absolute value for older uv; `uv sync --locked` accepts it.
- Docker (dev only): `Dockerfile` bakes the venv into `/opt/venv` (outside the `/opt/project` bind mount), `uv sync --locked --no-build` (no compiler in the image; every dep must have a wheel). `.dockerignore` only admits the manifests. Compose runs as `HERRING_UID`/`HERRING_GID` (default 1000, user also created in the image — without a passwd entry Celery assumed root). Named Postgres volume; Postgres 17 / Redis 7. `SECRET_KEY` is set to a dev-only value in compose.
- Tests: `scripts/test.sh` (compose project `herring-test`, torn down after; Django test runner with `herring.settings_test`: Celery eager, integrations off). `scripts/ui-test.sh` (project `herring-ui`, port 18100; seeds `scripts/ui/seed.py`, drives Chromium via `mcr.microsoft.com/playwright/python` + pip `playwright==` same version; fails on console errors/failed requests).
- Frontend: `herring/puzzles/static-src/build.mjs` (esbuild for `app.js` → `static/bundle.js`; less with `math: 'always'` for `style.less` → `static/style.css`). pnpm settings in `pnpm-workspace.yaml`: `minimumReleaseAge`, `blockExoticSubdeps`, `trustPolicy: no-downgrade`, `allowBuilds: {esbuild: false}` (pnpm 11 errors on unreviewed build scripts; esbuild's binary comes via optional deps anyway).
  - History: with Babel 7 / webpack-cli 3, `trustPolicy` blocked `semver@6.3.1` and `@5.7.2` (2023-07-10 ReDoS-fix backports by an npm CLI maintainer, no provenance). Gone with that tooling; if they reappear, that's why.
- Dev shutdown: watchmedo stops its child with SIGINT by default (Celery warm shutdown → waits for tasks); Procfile.dev passes `--signal SIGTERM` so dev matches prod (`REMAP_SIGTERM=SIGQUIT` → cold). `docker compose stop` ≈ 2s.

## Facts checked (2026-10-05)

- Heroku Python buildpack supports uv since 2025-05; needs `pyproject.toml` + `uv.lock` + `.python-version`, rejects multiple package-manager files. Python 3.10 deprecated there; 3.11–3.14 supported. Stacks: heroku-24 default, heroku-26 supported, heroku-22 deprecated (through 2027-04), heroku-20 EOL.
- Django 5.2 requires PostgreSQL 14+.
- google-api-python-client is in maintenance mode (critical/security fixes only), but Google says to keep using it for APIs without Cloud Client Libraries, which includes Drive.
- SECRET_KEY: came from `django-admin startproject` in the 2015 initial commit (startproject writes a random key into settings.py with a "keep it secret" warning; Django's deployment checklist says to load it from the environment). Impact of it being public was smaller than the commit message cbed0e5 claims: sessions use the DB backend, so the key didn't allow forging logins. It signs the messages cookie, password-reset tokens (which also need the user's password hash), and anything using django.core.signing.
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

## Deploy checklist (Heroku)

1. Check stack, Postgres ≥ 14, buildpacks (README "Deploying to Heroku"). Stack is now heroku-26; SECRET_KEY set (user, 2026-10-06).
2. **Open:** user believes an external script may call `/post_discord/`; they'll check. It now needs `token` = `SECRETS['post-discord-token']`. If the script exists, it probably belongs in this repo.
3. Deploy to staging (`rage-herring-staging`) first; watch for Celery broker / redbeat errors with `rediss://` URLs (kombu/redis-py/redbeat all upgraded) and for collectstatic (whitenoise replaced dj-static).

## Open issues / recommendations

- `ALLOWED_HOSTS = ['*']`.
- `tasks.optional_task` monkey-patches `apply_async` on tasks.
- discord.py 2.7 logs "PyNaCl / davey not installed, voice will NOT be supported" (voice channels are off by default).

## Later additions (2026-10-06)

- HTTPS hardening on by default (`HTTPS` env, default true; `HSTS_SECONDS` default 86400); Compose dev and tests turn it off. HSTS includeSubDomains/preload deliberately off (checks silenced in settings).
- Self-hosting: `docker-compose.prod.yml` + `scripts/prod.sh` + `deploy/` (Caddyfile, env template). Tested locally with bundled-db + caddy on localhost (ports 18080/18443). One `down` took the full 10s stop timeout once and didn't reproduce (likely the pre-fix image whose gunicorn control socket failed).
- gunicorn 26 opens a control socket under `$HOME/.gunicorn`; the prod image's user needs a home dir.
- Version: `herring/herring/version.py`, logged at startup by `PuzzlesConfig.ready()`. Not yet shown in the UI.
- Performance: `/puzzles/` query count is constant in hunt size (test_performance).
- Web process never connects to Discord (2026-10-06): status comes from Redis (`puzzles/redis_state.py`; workers' beat task `report_discord_status` + listener heartbeat, 30s interval, 90s TTL); channel links wait on `add_user_to_puzzle` via the Celery result backend (REDIS_URL, results only for that task, 10 min expiry); `/post_discord/`, ChatLogHandler and `log_to_discord` queue `post_discord_message` / `post_debug_message`. Not yet tested against a live Discord server.
- **Live-tested 2026-10-07** against the test server ("Herring Test Server For Claude", bot "HerringTestingClaude"; config in `.env`, which Claude doesn't read; user permitted any testing there). Worked: both bots connect only in a Celery worker (none in web); status → Redis → web shows connected; round → category; puzzles → channels with topics + announcements; answer/tags/notes via the web endpoint → channel and announcement posts; channel link (~35 ms round trip, correct channel ID; unknown username → explanatory 404); `post_discord_message` task; web warnings → debug channel via `post_debug_message`. Not testable without a human Discord user: prefix/slash commands, reactions, `on_message` activity tracking, permission overwrites for real members. Slash commands only register after `hb!synctree` (setup_hook doesn't sync the tree).
- `puzzles/management/commands/discord_inspect.py`: read-only dump of the configured server (categories, channels, overwrites count, `--messages N`). Use it to check what the bot did.
- ChatLogHandler ignores `discord.*` records below ERROR (routine rate-limit warnings; posting them could feed back into more rate limits) and labels posts with dyno/hostname + herring_version().
- Dev container logs "Herring version unknown": no git binary in the dev image, and HERRING_VERSION isn't set there.
- Channel links still use the old `discordapp.com` domain (redirects to discord.com).
- Discord test server: README "Using a test Discord server" (separate bot app; config in `.env`, which Claude must not read). `scripts/test.sh` and `scripts/ui-test.sh` force integrations off regardless of `.env`.
