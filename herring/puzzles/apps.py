from django.apps import AppConfig


class PuzzlesConfig(AppConfig):
    name = 'puzzles'
    verbose_name = 'Puzzles'

    def ready(self):
        import puzzles.signals
