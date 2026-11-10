"""
Making a server setup plan: snapshot the target server, check that it looks
new, build the operations (dashboard.setup_plan) and store them.
"""
import logging
from datetime import datetime, timezone

from django.db import transaction

from herring.version import herring_version
from puzzles.models import Round
from . import discord_api, setup_plan
from .models import DiscordServerSnapshot, SetupOperation, SetupPlan

logger = logging.getLogger(__name__)

# Setup refuses (unless acknowledged) a server that looks used: older than this, or with more than this
# many non-bot members, or more than this many messages from non-bot users. (User's rule, 2026-11-10.)
MAX_AGE_DAYS = 30
MAX_HUMAN_MEMBERS = 5
MAX_HUMAN_MESSAGES = 50
DISCORD_EPOCH_MS = 1420070400000


def snowflake_time(snowflake):
    return datetime.fromtimestamp(((int(snowflake) >> 22) + DISCORD_EPOCH_MS) / 1000, tz=timezone.utc)


def usage_warnings(usage):
    """Why the server might not be a brand-new one (empty if it looks new)."""
    checks = [(usage['age_days'] > MAX_AGE_DAYS, f"it was created {usage['age_days']} days ago"),
              (usage['human_members'] > MAX_HUMAN_MEMBERS, f"it has {usage['human_members']} non-bot members"),
              (usage['human_messages'] > MAX_HUMAN_MESSAGES,
               f"it has more than {MAX_HUMAN_MESSAGES} messages from non-bot users")]
    return [reason for failed, reason in checks if failed]


def bot_role_notices(target_sections, bot_user_id, roles_to_arrange):
    """
    Discord only lets the bot arrange roles below its own role's position number, and doesn't renumber
    roles as they're created, so a person has to drag the bot's role to the top (see check_bot_role_on_top).
    """
    roles = target_sections.get('roles', [])
    bot_top = max((r['position'] for r in roles if (r.get('tags') or {}).get('bot_id') == bot_user_id), default=0)
    if bot_top > roles_to_arrange and bot_top >= max((r['position'] for r in roles), default=0):
        return []
    return ["Arranging the roles needs a hand from you: once the roles have been created (apply the plan), go to "
            "Server Settings → Roles in Discord and drag the bot's role to the very top of the list. That renumbers "
            "the roles so the bot may arrange them; then apply the 'Arrange the roles' step again."]


def puzzle_category_ids():
    """Every Discord category Herring has made for a round, in any hunt."""
    return frozenset(c for r in Round.objects.exclude(discord_categories=None) for c in r.discord_categories.split(',') if c)


def create_plan(source, target_guild_id, server_name, user):
    sections, errors, usage, bot_user_id = discord_api.run(
        discord_api.fetch_setup_inputs(target_guild_id, MAX_HUMAN_MESSAGES))
    usage['age_days'] = (datetime.now(timezone.utc) - snowflake_time(target_guild_id)).days
    target = save_snapshot(target_guild_id, sections, errors, user)
    setup = setup_plan.SetupInput(source.sections, sections, server_name, bot_user_id, puzzle_category_ids())
    plan = save_plan(source, target, setup, usage, user)
    logger.info("Created setup plan %s: %s -> %s (%s), %d operations, warnings: %s",
                plan.id, source, target, server_name, plan.operations.count(), plan.warnings or 'none')
    return plan


def save_snapshot(guild_id, sections, errors, user):
    return DiscordServerSnapshot.objects.create(
        guild_id=guild_id, guild_name=sections.get('guild', {}).get('name', '(unknown)'), taken_by=user,
        herring_version=herring_version(), sections=sections, errors=errors)


@transaction.atomic
def save_plan(source, target, setup, usage, user):
    draft = setup_plan.build_plan(setup)
    plan = SetupPlan.objects.create(
        source=source, target=target, target_guild_id=target.guild_id, server_name=setup.server_name,
        created_by=user, usage=usage, warnings=usage_warnings(usage), notes=draft.notes, id_map=draft.id_map,
        notices=bot_role_notices(setup.target, setup.bot_id, len(setup_plan.copyable_roles(setup.source))))
    depends_on = setup_plan.dependencies(draft.operations, draft.id_map)
    SetupOperation.objects.bulk_create(operation_row(plan, seq, op, depends_on[op.key])
                                       for seq, op in enumerate(draft.operations))
    return plan


def operation_row(plan, seq, op, depends_on):
    return SetupOperation(plan=plan, seq=seq, key=op.key, stage=op.stage, description=op.description,
                          method=op.method, path=op.path, body=op.body, file=op.file, creates=op.creates or '',
                          preconditions=list(op.preconditions), depends_on=depends_on, default_selected=op.selected,
                          partial=op.partial)
