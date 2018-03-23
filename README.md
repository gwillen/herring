# Herring 

Herring is a web application for a puzzlehunt team's progress tracking and task management. It uses Django (with Python 3!) and ReactJS. It is inspired by the older puzzlehunt management tool `tsar`. 

Members of teams Metropolitan Rage Warehouse and Death and Mayhem have contributed to Herring development!

## Local dev setup

`brew install python3 postgres npm`

`brew upgrade python` to bump it to python 3, which has been mapped to `python` by homebrew but doesn't install by default.

Install Redis, which might be `apt-get install redis-server` or maybe `brew install redis`.

Install JS dependencies:

`cd herring/puzzles/static-src && npm install && cd ../../../`

Make sure you have `virtualenv` installed. Then:

`virtualenv --python $(which python3) henv`

`source henv/bin/activate`

You'll see `(henv)` in front of your command line after doing this. If you open more terminal windows, you'll have to do the above step again for them.

Install Django and other Pythonic dependencies:

`pip3 install -r requirements.txt`

Set up your database:

`ln -sfv /usr/local/opt/postgresql/*.plist ~/Library/LaunchAgents`

`launchctl load ~/Library/LaunchAgents/homebrew.mxcl.postgresql.plist`

`createdb herringdb`

When running as Rage for the Galaxy, get the Python module of stuff we can't commit to GitHub by downloading it from the pinned entry in https://ireproof.slack.com/messages/tech/. Save it as `herring/herring/secrets.py` (that is, in the same directory that settings.py is in).

Run:

`cd herring && python3 manage.py migrate`

`python3 manage.py runserver`

And in a second shell:

`cd herring/puzzles/static-src`

`./node_modules/.bin/webpack --watch`

You can then view the website at `localhost:8000`.

Create a superuser so you can log into `localhost:8000/admin/` and make rounds and puzzles:

`python3 manage.py createsuperuser`

To use the Slack and Google Drive integrations, you need to be running a worker process, so run this in yet another shell:

`python3 manage.py celery worker`

## License

This software is licensed under the [MIT License (Expat)](https://www.debian.org/legal/licenses/mit).
