import logging
import os

from django.apps import AppConfig


class PuzzlesConfig(AppConfig):
    name = 'puzzles'
    verbose_name = 'Puzzles'

    def ready(self):
        import puzzles.signals
        from herring.version import herring_version
        logging.info("Herring version %s starting (pid %d)", herring_version(), os.getpid())
