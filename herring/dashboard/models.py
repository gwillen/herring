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
    # 'bot' (read by the bot from the server itself) or 'template' (from a server template link; its
    # sections come from server_structure.sections_from_template).
    origin = models.CharField(max_length=20, default='bot')

    class Meta:
        ordering = ['-taken_at']

    def __str__(self):
        return f"{self.guild_name} ({self.guild_id}) at {self.taken_at:%Y-%m-%d %H:%M}"


class SetupPlan(models.Model):
    """
    A plan for setting up a Discord server (the target) like an old one (the
    source snapshot): its operations, and the IDs of things it has created.
    Built by dashboard.setup_plan; applied by dashboard.setup_apply.
    """
    source = models.ForeignKey(DiscordServerSnapshot, on_delete=models.PROTECT, related_name='+')
    target = models.ForeignKey(DiscordServerSnapshot, on_delete=models.PROTECT, related_name='+',
                               help_text="The target server as it was when the plan was made")
    target_guild_id = models.BigIntegerField()
    server_name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+')
    usage = models.JSONField(default=dict)  # how used the target looked: age_days, human_members, human_messages
    warnings = models.JSONField(default=list)  # why it might not be a new server; applying requires acknowledging
    notices = models.JSONField(default=list)  # things to fix first (e.g. the bot's role position)
    notes = models.JSONField(default=list)  # what was left out, etc.
    id_map = models.JSONField(default=dict)  # {ref: target ID}: matched at planning time, plus everything created since
    acknowledged_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                        related_name='+')

    class Meta:
        ordering = ['-created_at']


class SetupOperation(models.Model):
    """One Discord API request in a SetupPlan, stored exactly as it will be sent (refs aside)."""
    # 'existing': a create found the object already there and used it as is.
    STATUSES = ['pending', 'queued', 'applied', 'existing', 'failed', 'skipped']
    DONE = ('applied', 'existing')

    plan = models.ForeignKey(SetupPlan, on_delete=models.CASCADE, related_name='operations')
    seq = models.IntegerField()
    key = models.CharField(max_length=100)
    stage = models.CharField(max_length=40)
    description = models.TextField()
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=300)
    body = models.JSONField(null=True)
    file = models.JSONField(null=True)
    creates = models.CharField(max_length=100, blank=True)
    preconditions = models.JSONField(default=list)
    depends_on = models.JSONField(default=list)  # keys of operations that must be applied first
    default_selected = models.BooleanField(default=True)
    partial = models.BooleanField(default=False)  # see setup_plan.Operation.partial
    status = models.CharField(max_length=10, default='pending', choices=[(s, s) for s in STATUSES])
    result = models.JSONField(null=True)  # Discord's response, kept as-is
    error = models.TextField(blank=True)
    applied_at = models.DateTimeField(null=True)
    applied_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+')

    class Meta:
        ordering = ['seq']
        constraints = [models.UniqueConstraint(fields=['plan', 'key'], name='unique_operation_key_per_plan')]
