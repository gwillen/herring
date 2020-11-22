from datetime import datetime
from django.conf import settings
from django.db import models
from autoslug import AutoSlugField
from puzzles.slugtools import puzzle_to_slug
from model_utils import FieldTracker


# **optional shortcut for optional fields
optional = {
    'blank': True,
    'null': True
}


# A mixin class which adds a to_json method to a model
class JSONMixin(object):
    def to_json(self):
        retval = {}
        for fieldName in self.Json.include_fields:
            field = getattr(self, fieldName)
            value = to_json_value(field)
            retval[fieldName] = value
        return retval


def to_json_value(field):
    if isinstance(field, str):
        return field
    if isinstance(field, int):
        return field
    if isinstance(field, dict):
        return { key: to_json_value(value) for key, value in field.items() }
    if isinstance(field, (list, models.query.QuerySet)):
        return [to_json_value(item) for item in field]
    if isinstance(field, models.manager.Manager):
        return [to_json_value(item) for item in field.all()]
    if isinstance(field, JSONMixin):
        return field.to_json()
    if isinstance(field, datetime):
        return field.isoformat()


class Round(models.Model,JSONMixin):
    # shell model for defining rounds
    hunt_id = models.IntegerField(default=settings.HERRING_HUNT_ID)  # which hunt is this for? Will turn into a foreign key later.
    number = models.IntegerField(default=1)
    name = models.CharField(max_length=200)
    hunt_url = models.CharField(max_length=1000, default='', **optional)
    discord_categories = models.CharField(max_length=1000, editable=False, **optional)

    def __str__(self):
        return 'R' + str(self.number)

    class Meta:
        ordering = ['number', 'id']
    class Json:
        include_fields = ['id', 'name', 'number', 'puzzle_set', 'hunt_url']


class Puzzle(models.Model,JSONMixin):
    # class for all puzzles, including metas
    hunt_id = models.IntegerField(default=settings.HERRING_HUNT_ID)  # which hunt is this for? Will turn into a foreign key later.
    parent = models.ForeignKey(Round, on_delete=models.PROTECT)
    name = models.CharField(max_length=200)
    slug = AutoSlugField(
        populate_from=puzzle_to_slug,
        unique=True,
        db_index=True
    )
    number = models.IntegerField(**optional)
    answer = models.CharField(max_length=200, default='', **optional)
    note = models.CharField(max_length=200, default='', **optional)
    tags = models.CharField(max_length=200, default='', **optional)
    is_meta = models.BooleanField(default=False)
    sheet_id = models.CharField(max_length=1000, default=None, unique=True, db_index=True, null=True)
    hunt_url = models.CharField(max_length=1000, default='', **optional)

    last_active = models.DateTimeField(auto_now_add=True, editable=False)
    channel_count = models.PositiveIntegerField(default=0, editable=False)
    activity_tracker = models.BigIntegerField(default=0, editable=False)

    tracker = FieldTracker()

    class Meta:
        ordering = ['parent', '-is_meta', 'number', 'id']

    class Json:
        include_fields = ['id', 'name', 'number', 'answer', 'note', 'tags', 'is_meta', 'hunt_url', 'slug', 'channel_count', 'activity_histo', 'last_active']

    # XXX: This is arguably misnamed now that it no longer includes the puzzle number. It's just a prefix.
    def identifier(self):
        meta_marker = ''
        if self.is_meta:
            meta_marker = 'M'
        return str(self.parent) + meta_marker

    def __str__(self):
        return '#%s %s' % (self.slug, self.name)

    def is_answered(self):
        return bool(self.answer)

    def record_activity(self, dt):
        """
        Updates the last_active and activity_tracker fields to be consistent
        with activity seen at the given time. Returns a boolean indicating
        whether this model was changed as a consequence.
        """

        # Let time be divided into a fixed set of observation periods of size
        # P. activity_tracker is a bitset where each bit represents whether
        # there was or was not activity during a certain period. Bit 0 always
        # corresponds to the period containing the last_active datetime, and
        # a total of N periods are tracked. For now,
        P = 120  # = two minutes
        N = 60   # for a total window of two hours
        # record_activity needs to do two things: ensure last_active is equal
        # to or later than dt (bitshifting activity_tracker in the process if
        # necessary), and set the bit corresponding to the period of dt in
        # activity_tracker.

        dt0 = self.last_active
        shift_distance = int(dt.timestamp()) // P - int(dt0.timestamp()) // P

        changed = False
        bits = self.activity_tracker

        if dt > dt0:
            changed = True
            self.last_active = dt

            if shift_distance < N:
                # Note: we're in Python, so this is not as efficient as it
                # looks. Probably doesn't matter, but if it ever does, bring in
                # numpy or something.
                bits <<= shift_distance
                bits &= (1 << N) - 1
            else:
                bits = 0
            bits |= 1
        else:
            shift_distance = -shift_distance
            if shift_distance < N:
                bits |= 1 << shift_distance
                changed = bits != self.activity_tracker

        self.activity_tracker = bits
        return changed

    @property
    def activity_histo(self):
        """
        This is a slightly friendlier representation of activity_tracker,
        intended for JSON transport.
        """
        return f"{self.activity_tracker:015x}"

    @classmethod
    def batch_save_activity(cls, objs):
        cls.objects.bulk_update(objs, ['last_active', 'activity_tracker'], batch_size=50)


class UserProfile(models.Model):
    user = models.OneToOneField(
            settings.AUTH_USER_MODEL,
            on_delete=models.CASCADE,
            related_name='profile',
    )
    avatar_url = models.CharField(max_length=200)
    discord_identifier = models.CharField(max_length=200, **optional)

    def __str__(self):
        return "profile for " + self.user.__str__()


class ChannelParticipation(models.Model):
    channel_puzzle = models.ForeignKey(
        Puzzle,
        to_field='slug',
        db_column='channel_name',
        on_delete=models.CASCADE)
    user_id = models.CharField(max_length=30)
    last_active = models.DateTimeField(null=True)
    is_member = models.BooleanField()

    class Meta:
        indexes = [models.Index(fields=['channel_puzzle', 'user_id'])]
