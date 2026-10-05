# Herring — global notes

- Django app (`herring/herring` = project, `herring/puzzles` = the one app) + Celery worker/beat on Redis + Postgres + a Discord bot (discord.py) + Google Drive/Sheets integration. React frontend in `herring/puzzles/static-src`, built to `herring/puzzles/static/bundle.js`, which is committed.
- Production historically ran on Heroku (Procfile). The dev machine where Claude works is dev-only (user, 2026-10-05): the checkout and local ports are free to use; the live instance runs elsewhere and is still off-limits.
- There are no automated tests (`puzzles/tests.py` is empty).
- Modernization is in progress as of 2026-10; see `modernization.md`.
