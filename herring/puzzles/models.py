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


class Round(models.Model,JSONMixin):
    # shell model for defining rounds
    number = models.IntegerField(default=1)
    name = models.CharField(max_length=200)
    hunt_url = models.CharField(max_length=1000, default='', **optional)

    def __str__(self):
        return 'R' + str(self.number)

    class Meta:
        ordering = ['number', 'id']
    class Json:
        include_fields = ['id', 'name', 'number', 'puzzle_set', 'hunt_url']


class Puzzle(models.Model,JSONMixin):
    # class for all puzzles, including metas
    parent = models.ForeignKey(Round)
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
    url = models.CharField(max_length=1000, default='', **optional)
    hunt_url = models.CharField(max_length=1000, default='', **optional)

    tracker = FieldTracker()

    class Meta:
        ordering = ['parent', '-is_meta', 'number', 'id']

    class Json:
        include_fields = ['id', 'name', 'number', 'answer', 'note', 'tags', 'is_meta', 'url', 'hunt_url', 'slug']

    def identifier(self):
        child_type = 'P'
        if self.is_meta:
            child_type = 'M'
        num = str(self.number) if self.number is not None else 'x'
        return str(self.parent) + child_type + num
    
    def __str__(self):
        return '#%s %s' % (self.slug, self.name)

    def is_answered(self):
        return bool(self.answer)


class UserProfile(models.Model):
    user = models.OneToOneField(
            settings.AUTH_USER_MODEL,
            on_delete=models.CASCADE,
            related_name='profile',
    )
    avatar_url = models.CharField(max_length=200)

    def __str__(self):
        return "profile for " + self.user.__str__()
