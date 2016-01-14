# load secrets from the environment

import os
import json

SECRETS = json.load(os.environ['SECRETS'])
FUCK_OAUTH = json.load(os.environ['FUCK_OAUTH'])
