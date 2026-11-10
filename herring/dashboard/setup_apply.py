"""
Applying a setup plan's chosen operations (see dashboard.setup_plan): in plan
order, each only after the operations it depends on, re-checking its
preconditions against the live server first, and sending exactly the stored
request (with refs filled in from what earlier operations created). Every
outcome is recorded on the operation, including Discord's response.
"""
import logging

from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone

from . import discord_api
from .models import SetupPlan
from .setup_plan import refs_in, resolve

logger = logging.getLogger(__name__)


def queue_operations(plan, keys):
    """Queues the chosen operations plus any unapplied ones they depend on; returns the queued keys."""
    operations = {op.key: op for op in plan.operations.all()}
    wanted = dependency_closure(keys, operations)
    to_queue = sorted(k for k in wanted if operations[k].status != 'applied')
    plan.operations.filter(key__in=to_queue).update(status='queued', error='')
    return to_queue


def dependency_closure(keys, operations):
    wanted, todo = set(), [k for k in keys if k in operations]
    while todo:
        key = todo.pop()
        if key not in wanted:
            wanted.add(key)
            todo += operations[key].depends_on
    return wanted


@shared_task
def apply_setup_plan(plan_id, user_id):
    plan = SetupPlan.objects.get(id=plan_id)
    user = get_user_model().objects.filter(id=user_id).first()
    logger.info("Applying setup plan %s (%s) for %s", plan.id, plan.server_name, user)
    with discord_api.DiscordSession() as discord:
        for operation in plan.operations.filter(status='queued'):
            apply_operation(plan, operation, discord, user)
    logger.info("Finished applying setup plan %s", plan.id)


def apply_operation(plan, operation, discord, user):
    waiting = unapplied_dependencies(plan, operation)
    if waiting:
        return finish(operation, 'skipped', user, error=f"Not applied, because these weren't: {', '.join(waiting)}")
    try:
        problem = failed_precondition(plan, operation, discord)
        if problem:
            return finish(operation, 'failed', user, error=f"Not applied: {problem}")
        result = send(plan, operation, discord)
    except Exception as e:
        logger.error("Setup plan %s: %s failed", plan.id, operation.key, exc_info=True)
        return finish(operation, 'failed', user, error=f"{type(e).__name__}: {e}")
    record_created_id(plan, operation, result)
    finish(operation, 'applied', user, result=result)


def unapplied_dependencies(plan, operation):
    return sorted(plan.operations.filter(key__in=operation.depends_on).exclude(status='applied')
                  .values_list('key', flat=True))


def finish(operation, status, user, result=None, error=''):
    operation.status, operation.result, operation.error = status, result, error
    operation.applied_at, operation.applied_by = timezone.now(), user
    operation.save(update_fields=['status', 'result', 'error', 'applied_at', 'applied_by'])
    log = logger.info if status == 'applied' else logger.warning
    log("Setup plan %s: %s %s (%s)%s", operation.plan_id, operation.key, status, operation.description,
        f": {error}" if error else "")


def send(plan, operation, discord):
    path, body = resolve(operation.path, plan.id_map), resolve(operation.body, plan.id_map)
    if path is None or (operation.body is not None and body is None):
        missing = sorted(refs_in([operation.path, operation.body]) - set(plan.id_map))
        raise ValueError(f"no target IDs yet for {', '.join(missing)}")
    if operation.file:
        return discord.create_sticker(plan.target_guild_id, body, operation.file)
    return discord.request(operation.method, path, body)


def record_created_id(plan, operation, result):
    if operation.creates and isinstance(result, dict) and 'id' in result:
        plan.id_map[operation.creates] = result['id']
        plan.save(update_fields=['id_map'])


# --- Preconditions, checked against the live server ---------------------------

COLLECTION_PATHS = {'roles': '/roles', 'channels': '/channels', 'emojis': '/emojis', 'stickers': '/stickers',
                    'auto_moderation_rules': '/auto-moderation/rules'}


def failed_precondition(plan, operation, discord):
    """A description of the first precondition that no longer holds, or None."""
    for condition in operation.preconditions:
        problem = next(CHECKS[name](plan, condition, discord) for name in CHECKS if name in condition)
        if problem:
            return problem
    return None


def live(plan, discord, collection):
    return discord.request('GET', f"/guilds/{plan.target_guild_id}{COLLECTION_PATHS[collection]}")


def check_absent(plan, condition, discord):
    clash = [o for o in live(plan, discord, condition['absent'])
             if o['name'] == condition['name'] and condition.get('type', o.get('type')) == o.get('type')]
    return f"there's already one named {condition['name']!r}" if clash else None


def check_exists(plan, condition, discord):
    ids = {o['id'] for o in live(plan, discord, condition['exists'])}
    return None if condition['id'] in ids else "it no longer exists"


def check_no_messages(plan, condition, discord):
    messages = discord.request('GET', f"/channels/{condition['no_messages']}/messages", params={'limit': 1})
    return "it has messages" if messages else None


def check_empty_category(plan, condition, discord):
    children = [c for c in live(plan, discord, 'channels') if c.get('parent_id') == condition['empty_category']]
    return f"it still has {len(children)} channels" if children else None


def check_bot_role_on_top(plan, condition, discord):
    roles = live(plan, discord, 'roles')
    bot = discord.request('GET', f"/guilds/{plan.target_guild_id}/members/{discord.bot_user_id}")
    bot_top = max((r['position'] for r in roles if r['id'] in bot['roles']), default=0)
    return None if bot_top >= max(r['position'] for r in roles) else (
        "the bot's role isn't at the top of the role list (in Discord: Server Settings → Roles, drag it to the top)")


CHECKS = {'absent': check_absent, 'exists': check_exists, 'no_messages': check_no_messages,
          'empty_category': check_empty_category, 'bot_role_on_top': check_bot_role_on_top}
