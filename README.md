# Herring

Herring is a web application for a puzzlehunt team's progress tracking and task management. It uses Django and React. It is inspired by the older puzzlehunt management tool `tsar`.

Members of teams Metropolitan Rage Warehouse and Death and Mayhem have contributed to Herring development!

## Local dev setup

First, when running as Metropolitan Rage Warehouse, get the file of stuff we can't commit to GitHub by downloading it from the pinned entry in https://ireproof.slack.com/messages/tech/. Save it as `.env` in this directory.

Now, you have a choice. If you have Docker (with Docker Compose) installed, or are comfortable installing it, see the [With Docker Compose](#user-content-with-docker-compose) section below. This frees you from having to manually manage database servers, worker processes, or Python virtual environments.

The alternative is to install the necessary software directly on your computer. If you choose this option, see the [Manually](#user-content-manually) section below.

Python dependencies are managed with [uv](https://docs.astral.sh/uv/) (`pyproject.toml`, `uv.lock`, and `.python-version` for the Python version). The frontend's are managed with [pnpm](https://pnpm.io/) (`herring/puzzles/static-src/package.json` and `pnpm-lock.yaml`). Heroku installs from `uv.lock` directly.

### With Docker Compose

Run `docker compose up --build` to build the image and start everything. When finished, run `docker compose stop` to stop running processes, or `docker compose down` to both stop and delete containers. The database lives in a named volume, so it survives `down`; `docker compose down --volumes` deletes it too.

The website will be accessible at http://localhost:8000, with an `admin` / `admin` superuser. To use another port, set `HERRING_PORT` (e.g. `HERRING_PORT=8001 docker compose up`). The container runs as UID/GID 1000 by default, so that files it creates in your checkout are owned by you; if your IDs differ, set `HERRING_UID` and `HERRING_GID`.

Python dependencies are baked into the image, so after changing `pyproject.toml` or `uv.lock`, rebuild with `docker compose build` (or `up --build`).

To run anything in the Python environment, use `docker compose exec project <command>`. For example, you can:
* open a Django-enabled Python REPL: `docker compose exec project herring/manage.py shell`
* create new database migration files: `docker compose exec project herring/manage.py makemigrations`
* inspect Celery workers: `docker compose exec project celery --app=herring --workdir=herring inspect stats`
* open a shell to run arbitrary commands: `docker compose exec project sh`

### Running the tests

`scripts/test.sh` runs the test suite in Docker. It uses a separate Compose project (`herring-test`) with its own database, so it doesn't interfere with a running dev stack, and it cleans up after itself. Arguments are passed to `manage.py test`, e.g. `scripts/test.sh puzzles.tests.test_views`.

Without Docker: `cd herring && uv run python manage.py test --settings=herring.settings_test`, with `DATABASE_URL` pointing at a Postgres server where you can create databases.

### Frontend

The React frontend lives in `herring/puzzles/static-src`. Its build (`build.mjs`, using esbuild and less) writes `herring/puzzles/static/bundle.js` and `herring/puzzles/static/style.css` (from `style.less`); both are committed. The frontend is built outside Docker:

```
cd herring/puzzles/static-src
pnpm install
pnpm watch      # or `pnpm build` for a one-off build
```

`scripts/ui-test.sh` is a browser smoke test: it starts a throwaway stack (Compose project `herring-ui`, port 18100), seeds sample puzzles, and drives the UI in headless Chromium (Playwright's Docker image), failing on browser console errors or failed requests. Screenshots go to `ui-test-output/`.

### Manually

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), [pnpm](https://pnpm.io/installation), Postgres, and Redis (e.g. `brew install uv pnpm postgresql redis`, or on Ubuntu, `apt-get install postgresql redis-server` plus the uv and pnpm installers).

Herring requires a `SECRET_KEY` setting, from the environment or `.env` (see `.env.example`). Generate one with `python3 -c 'import secrets; print(secrets.token_urlsafe(50))'` and add a `SECRET_KEY=...` line to `.env`. (Docker Compose sets a dev-only key itself.)

Install the Python dependencies (uv downloads the right Python version if needed, and creates `.venv`):

`uv sync`

Then either prefix commands with `uv run` (as below), or `source .venv/bin/activate` first.

Install the frontend dependencies:

`cd herring/puzzles/static-src && pnpm install && cd ../../../`

Set up your database:

(On Ubuntu before doing the next step: `sudo -u postgres createuser --createdb [your current username, under which you will be running herring]`)

`createdb herringdb`

Run:

`cd herring && uv run python manage.py migrate`

(OR, instead of createdb and migrate, you can restore from a prod backup. This is messy. If your prodbackup is named asdf.dump, do the following (NOTE: this is dangerous if your dump does not contain a specified database name, as it will overwrite the 'postgres' database!)

`sudo -u postgres pg_restore --no-owner --role=postgres -d postgres -Cc asdf.dump`
`sudo -u postgres psql -d postgres -c 'ALTER DATABASE whateverprodcalledit RENAME TO herringdb'`
`sudo -u postgres psql -d postgres -c 'ALTER USER myusername WITH SUPERUSER'`

Uh, obviously that last line should not be required. ?!

`uv run python manage.py runserver`

And in a second shell:

`uv run python manage.py collectstatic --noinput --clear --link`

`cd herring/puzzles/static-src && pnpm watch`

You can then view the website at `localhost:8000`.

Create a superuser so you can log into `localhost:8000/admin/` and make rounds and puzzles:

`uv run python manage.py createsuperuser`

To use the Discord and Google Drive integrations, you need to be running a worker process, so run this in yet another shell (from the top-level directory):

`uv run celery --workdir=herring --app=herring worker -E --beat`

## Deploying to Heroku

Heroku's Python buildpack installs from `uv.lock` (`uv sync --locked --no-default-groups`, so the `dev` group is skipped) using the Python version in `.python-version`, and runs `collectstatic` itself. The `Procfile` defines the `web` and `worker` processes.

Required configuration (config vars):
* `SECRET_KEY`: required; the app refuses to start without it.
* `SECRETS`: JSON object (see `.env.example`). The `/post_discord/` endpoint for scripts only works if it contains a `post-discord-token`, which callers must send as the `token` POST field.

Requirements of the current dependency versions:
* A supported stack: heroku-24 (the default) or heroku-26. heroku-22 is deprecated (supported through April 2027); heroku-20 is end-of-life. (Checked 2026-10.)
* Django 5.2 needs PostgreSQL 14 or newer.

Check them with (set the app name first):

```
HERRING_HEROKU_APP=rage-herring-staging
heroku stack -a $HERRING_HEROKU_APP
heroku pg:info -a $HERRING_HEROKU_APP
heroku buildpacks -a $HERRING_HEROKU_APP
heroku config -a $HERRING_HEROKU_APP | cut -d: -f1   # config var names only
```

## License

This software is licensed under the [MIT License (Expat)](https://www.debian.org/legal/licenses/mit).
