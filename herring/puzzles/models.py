from django.db import models

# **optional shortcut for optional fields
optional = {
    'blank': True,
    'null': True
}

class Round(models.Model):
    # shell model for defining rounds
    number = models.IntegerField(default=1)
    name = models.CharField(max_length=200)

    def __unicode__(self):
        return 'R' + str(self.number)

    class Meta:
        ordering = ['number']


class Puzzle(models.Model):
    # class for all puzzles, including metas
    parent = models.ForeignKey(Round)
    name = models.CharField(max_length=200)
    number = models.IntegerField(**optional)
    answer = models.CharField(max_length=200, default='', **optional)
    note = models.CharField(max_length=200, default='', **optional)
    tags = models.CharField(max_length=200, default='', **optional)
    is_meta = models.BooleanField(default=False)

    class Meta:
        ordering = ['parent', '-is_meta', 'number']

    def __unicode__(self):
        child_type = 'P'
        if self.is_meta:
            child_type = 'M'
        num = str(self.number) if self.number is not None else '?'
        return self.parent.__unicode__() + child_type + num + ': ' + self.name

    def is_answered(self):
        return bool(self.answer)