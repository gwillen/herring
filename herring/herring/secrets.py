# load secrets from the environment

import os
import json
import environ
env = environ.Env()
environ.Env.read_env()

SECRETS = json.loads(env.get_value('SECRETS', default='{}'))
FUCK_OAUTH = json.loads(env.get_value('FUCK_OAUTH', default='{}'))
