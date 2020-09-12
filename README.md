# Herring 

Herring is a web application for a puzzlehunt team's progress tracking and task management. It uses Django (with Python 3!) and ReactJS. It is inspired by the older puzzlehunt management tool `tsar`. 

Members of teams Metropolitan Rage Warehouse and Death and Mayhem have contributed to Herring development!

## Local dev setup

First, when running as Metropolitan Rage Warehouse, get the file of stuff we can't commit to GitHub by downloading it from the pinned entry in https://ireproof.slack.com/messages/tech/. Save it as `.env` in this directory.

Now, you have a choice. If you have Docker and Docker Compose installed, or are comfortable installing them, do so and then see the [With Docker Compose](#user-content-with-docker-compose) section below. This approach ensures you're running the same versions of software that we use on Heroku, and frees you from having to manually manage users, database servers, worker processes, or Python virtual environments. This comes at the expense of, well, running Docker, which is not always easy to manage on non-Linux platforms, and will generally use more disk space than installing the software natively.

The alternative is to install all the necessary software directly on your computer. If you choose this option, see the [Manually](#user-content-manually) section below.

### With Docker Compose

Run `docker-compose up` to create and start everything. When finished, run `docker-compose stop` to stop running processes, or `docker-compose down` to both stop and delete containers (which will result in a longer startup next time and an empty database).

The website will be accessible at http://localhost:8000.

To run anything in the Python environment, use `docker-compose exec project <command>`. For example, you can:
* open a Django-enabled Python REPL: `docker-compose exec project herring/manage.py shell`
* create new database migration files: `docker-compose exec project herring/manage.py makemigrations`
* inspect Celery workers: `docker-compose exec project celery --app=herring --workdir=herring inspect stats`
* open a shell to run arbitrary commands: `docker-compose exec project sh`

You can do work on the React frontend outside of the Docker environment:

```
cd herring/puzzles/static-src
npm install 
./node_modules/.bin/webpack --watch
```

### Manually

`brew install python3 postgres npm`

Install Redis, which is `apt-get install redis-server` or `brew install redis` for all I know.

Install node/JS dependencies:

`cd herring/puzzles/static-src && npm install && cd ../../../`

Make sure you have `virtualenv` installed. Then:

`virtualenv --python $(which python3) henv`

`source henv/bin/activate`

You'll see `(henv)` in front of your command line after doing this. If you open more terminals, you'll have to do the above step again for them.

Install Django and other Pythonic dependencies:

`pip3 install -r requirements.txt`

Set up your database:

`ln -sfv /usr/local/opt/postgresql/*.plist ~/Library/LaunchAgents`

`launchctl load ~/Library/LaunchAgents/homebrew.mxcl.postgresql.plist`

(On Ubuntu: it's already running after installation.)

(On Ubuntu before doing the next step: `sudo -u postgres createuser [your current username, under which you will be running herring]`)

`createdb herringdb`

Run:

`cd herring && python3 manage.py migrate`

(OR, instead of createdb and migrate, you can restore from a prod backup. This is messy. If your prodbackup is named asdf.dump, do the following (NOTE: this is dangerous if your dump does not contain a specified database name, as it will overwrite the 'postgres' database!)

`sudo -u postgres pg_restore --no-owner --role=postgres -d postgres -Cc asdf.dump`
`sudo -u postgres psql -d postgres -c 'ALTER DATABASE whateverprodcalledit RENAME TO herringdb'`
`sudo -u postgres psql -d postgres -c 'ALTER USER myusername WITH SUPERUSER'`

Uh, obviously that last line should not be required. ?!

`python3 manage.py runserver`

And in a second shell:

`python3 manage.py collectstatic --noinput --clear --link`

`cd herring/puzzles/static-src`

`./node_modules/.bin/webpack --watch`

You can then view the website at `localhost:8000`.

Create a superuser so you can log into `localhost:8000/admin/` and make rounds and puzzles:

`python3 manage.py createsuperuser`

To use the Slack and Google Drive integrations, you need to be running a worker process, so run this in yet another shell:

`python3 manage.py celery worker`

## License

This software is licensed under the [MIT License (Expat)](https://www.debian.org/legal/licenses/mit).
