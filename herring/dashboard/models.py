from django.conf import settings
from django.db import models


class DiscordServerSnapshot(models.Model):
    """
    A saved copy of a Discord server's structure: Discord's raw API responses
    for its roles, channels, onboarding, etc. (see discord_api.SNAPSHOT_SECTIONS).
    Used as the source when setting up a new hunt's server, and as a record.
    """
    guild_id = models.BigIntegerField(db_index=True)
    guild_name = models.CharField(max_length=200)
    taken_at = models.DateTimeField(auto_now_add=True)
    taken_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    herring_version = models.CharField(max_length=200)
    sections = models.JSONField()  # {section name: raw JSON from Discord}
    errors = models.JSONField(default=dict)  # {section name: error} for sections that couldn't be read

    class Meta:
        ordering = ['-taken_at']

    def __str__(self):
        return f"{self.guild_name} ({self.guild_id}) at {self.taken_at:%Y-%m-%d %H:%M}"
