from django.db.models.signals import post_save
from django.dispatch import receiver
from puzzles.tasks import create_puzzle_sheet_and_channel
from puzzles.models import Puzzle


@receiver(post_save, sender=Puzzle)
def on_puzzle_save(sender, instance, created, **kwargs):
    if created:
        create_puzzle_sheet_and_channel.delay(instance.slug)

