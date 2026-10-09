"""
Which version of Herring is running, for logs. Computed at startup from the
deployment itself, never hardcoded, so it can't go stale.
"""
import logging
import os
import subprocess
from functools import cache

logger = logging.getLogger(__name__)

REPO_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _from_git():
    try:
        result = subprocess.run(['git', 'describe', '--always', '--dirty', '--tags'], cwd=REPO_DIR,
                                capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError) as e:
        logger.debug("version: git describe unavailable: %s", e)
        return None
    return result.stdout.strip() if result.returncode == 0 else None


@cache
def herring_version():
    """
    HERRING_VERSION (baked into prod images by scripts/prod.sh), else Heroku's
    slug commit (needs `heroku labs:enable runtime-dyno-metadata`), else git
    describe of the checkout, else 'unknown'.
    """
    return (os.environ.get('HERRING_VERSION')
            or os.environ.get('HEROKU_SLUG_COMMIT')
            or _from_git()
            or 'unknown')
