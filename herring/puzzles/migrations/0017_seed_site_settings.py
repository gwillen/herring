from django.conf import settings
from django.db import migrations


def seed_from_environment(apps, schema_editor):
    """Copy DISCORD_GUILD, HUNT_ID and DISCORD_PROTECTED_CATEGORIES into the site settings, once."""
    SiteSettings = apps.get_model('puzzles', 'SiteSettings')
    SiteSettings.objects.get_or_create(id=1, defaults={
        'discord_guild_id': settings.HERRING_DISCORD_GUILD_ID or None,
        'hunt_id': settings.HERRING_HUNT_ID,
        'protected_category_ids': sorted(str(c) for c in settings.HERRING_DISCORD_PROTECTED_CATEGORIES),
    })


class Migration(migrations.Migration):
    dependencies = [('puzzles', '0016_site_settings')]
    operations = [migrations.RunPython(seed_from_environment, migrations.RunPython.noop)]
