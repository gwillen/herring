# Herring — global notes

- Django app (`herring/herring` = project, `herring/puzzles` = the one app) + Celery worker/beat on Redis + Postgres + a Discord bot (discord.py) + Google Drive/Sheets integration. React frontend in `herring/puzzles/static-src`, built to `herring/puzzles/static/{bundle.js,style.css}`, which are committed.
- Python deps via uv (`pyproject.toml`/`uv.lock`), frontend via pnpm. Production runs on Heroku (Procfile); Docker Compose is the local dev stack.
- The dev machine where Claude works is dev-only (user, 2026-10-05): the checkout and local ports are free to use; the live instance runs elsewhere (Heroku) and is still off-limits.
- Current hunt, its Discord server, and Discord/Sheets on/off are dashboard settings (`puzzles.site_settings`), not env vars (ACTIVATE_* remain hard switches).
- Admin dashboard app: `herring/dashboard` (`/dashboard/`: Settings, Logs, Discord servers / new-server setup). Dev helpers: `scripts/dev/`.
- Work on `master` (the user merged `claude-2026-oct` and switched the checkout, 2026-11-10).
- Tests: `scripts/test.sh` (Django tests in Docker), `scripts/ui-test.sh` (headless browser smoke test). Use separate compose project names (`-p ...`) and ports for manual runs so nothing collides.
- See `modernization.md` for the upgrade state, verified facts, deployment notes and gotchas.
