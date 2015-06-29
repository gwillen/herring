# Herring

Herring is a web application for a puzzlehunt team's progress tracking and task management. It uses Django (with Python 3!) and ReactJS. It is inspired by the older puzzlehunt management tool `tsar`. 

Members of teams Metropolitan Rage Warehouse and Death and Mayhem have contributed to Herring development!

## Local dev setup

`brew install python3 postgres`

Make sure you have `virtualenv` installed. Then:

`virtualenv --python $(which python3) henv`

`source henv/bin/activate`

You'll see `(henv)` in front of your command line after doing this. If you open more terminals, you'll have to do the above step again for them.

`pip3 install -r requirements.txt`

This software is licensed under the [MIT License (Expat)](https://www.debian.org/legal/licenses/mit).
