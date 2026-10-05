# Herring — global notes

- Django app (`herring/herring` = project, `herring/puzzles` = the one app) + Celery worker/beat on Redis + Postgres + a Discord bot (discord.py) + Google Drive/Sheets integration. React frontend in `herring/puzzles/static-src`, built to `herring/puzzles/static/{bundle.js,style.css}`, which are committed.
- Python deps via uv (`pyproject.toml`/`uv.lock`), frontend via pnpm. Production runs on Heroku (Procfile); Docker Compose is the local dev stack.
- The dev machine where Claude works is dev-only (user, 2026-10-05): the checkout and local ports are free to use; the live instance runs elsewhere (Heroku) and is still off-limits.
- Tests: `scripts/test.sh` (Django tests in Docker), `scripts/ui-test.sh` (headless browser smoke test). Use separate compose project names (`-p ...`) and ports for manual runs so nothing collides.
- See `modernization.md` for the 2026-10 upgrade state, verified facts, and the pending Heroku deploy checklist.
