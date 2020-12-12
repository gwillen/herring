from django.contrib.auth.models import User
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from puzzles.tasks import create_puzzle_sheet_and_channel, post_answer, post_update, create_round_category
from puzzles.models import Puzzle, Round, UserProfile

@receiver(post_save, sender=Puzzle)
def on_puzzle_save(sender, instance, created, **kwargs):
    if created:
        create_puzzle_sheet_and_channel.delay(instance.slug)


@receiver(pre_save, sender=Puzzle)
def before_puzzle_save(sender, instance, **kwargs):
    if instance.answer:
        if instance.answer != instance.tracker.previous('answer'):
            post_answer.delay(instance.slug, instance.answer)

    if instance.tags != instance.tracker.previous('tags') and instance.tracker.previous('tags') is not None:
        post_update.delay(instance.slug, 'tags', instance.tags)

    if instance.note != instance.tracker.previous('note') and instance.tracker.previous('note') is not None:
        post_update.delay(instance.slug, 'notes', instance.note)


@receiver(post_save, sender=Round)
def on_round_save(sender, instance, created, **kwargs):
    if created:
        create_round_category.delay(instance.id)


@receiver(post_save, sender=User)
def on_user_save(sender, instance, created, **kwargs):
    if created or not hasattr(instance, 'profile'):
        UserProfile.objects.create(user=instance)
    instance.profile.save()
