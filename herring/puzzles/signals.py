import re
from django.contrib.auth.models import User
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.db import transaction
from puzzles.tasks import create_puzzle_sheet_and_channel, post_answer, post_update, create_round_category, notify_subscribers
from puzzles.models import Puzzle, Round, UserProfile

@receiver(post_save, sender=Puzzle)
def on_puzzle_save(sender, instance, created, **kwargs):
    if created:
        transaction.on_commit(lambda: create_puzzle_sheet_and_channel.delay(instance.slug))


@receiver(pre_save, sender=Puzzle)
def before_puzzle_save(sender, instance, **kwargs):
    if instance.answer:
        if instance.answer != instance.tracker.previous('answer'):
            post_answer.delay(instance.slug, instance.answer)

    old_keywords = set()
    new_keywords = set()

    if instance.tags != instance.tracker.previous('tags') and instance.tracker.previous('tags') is not None:
        post_update.delay(instance.slug, 'tags', instance.tags)
        old_keywords.update(re.findall('\w+', instance.tracker.previous('tags').lower()))
        new_keywords.update(re.findall('\w+', instance.tags.lower()))

    if instance.note != instance.tracker.previous('note') and instance.tracker.previous('note') is not None:
        post_update.delay(instance.slug, 'notes', instance.note)
        old_keywords.update(re.findall('\w+', instance.tracker.previous('note').lower()))
        new_keywords.update(re.findall('\w+', instance.note.lower()))

    new_keywords.difference_update(old_keywords)
    if len(new_keywords) > 0 and instance.answer == '':
        notify_subscribers.delay(instance.slug, '|'.join(new_keywords))


@receiver(post_save, sender=Round)
def on_round_save(sender, instance, created, **kwargs):
    if created:
        transaction.on_commit(lambda: create_round_category.delay(instance.id))


@receiver(post_save, sender=User)
def on_user_save(sender, instance, created, **kwargs):
    if created or not hasattr(instance, 'profile'):
        UserProfile.objects.create(user=instance)
    instance.profile.save()
