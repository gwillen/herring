import asyncio
import collections
import concurrent.futures
import logging
import re
import threading
import typing
from datetime import timezone
from urllib.parse import urljoin
import aiohttp
from lazy_object_proxy import Proxy as lazy_object
import traceback
import sys

from typing import Optional, Any

import discord
from discord import app_commands
from asgiref.sync import async_to_sync, sync_to_async
from discord.ext import commands
from discord.utils import get
from django.db import transaction
from django.db.models import Q

from django.conf import settings
from puzzles.models import Round, Puzzle, UserProfile

# Discord limits a user to putting 20 emojis on a message, so if this is more than 19, the menu won't work
# also, an embed is limited to length 2048, which isn't really very long
MENU_REACTIONS = [
    "\N{REGIONAL INDICATOR SYMBOL LETTER A}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER B}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER C}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER D}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER E}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER F}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER G}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER H}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER I}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER J}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER K}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER L}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER M}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER N}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER O}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER P}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER Q}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER R}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER S}",
]
MENU_EXTRA_REACTION = "\N{DOWNWARDS BLACK ARROW}"
MENU_REACTION_LOOKUP = {reaction: index for index, reaction in enumerate(MENU_REACTIONS)}

# Discord also limits a category to 50 channels, so we can only put 25 puzzles in a category and then we
# have to make a new category for them
# making this less than 25 leaves a little elbow room for cleanup_channels if necessary
PUZZLES_PER_CATEGORY = 20

SIGNUP_EMOJI = "\N{RAISED HAND}"

# this is the most users we'll try to mention during an hb!who; more than this and you just get the number
MAX_USER_LIST = 10

# for safety's sake, we will only allow auto-assignment of roles below this role, to prevent bugs allowing
# auto-assignment of powerful roles.
AUTOROLE_MARKER = "-autoroles below-"

MAX_DISCORD_EMBED_LEN = 2048

GUILD_COMMANDS_FOR_TESTING = True

if settings.HERRING_DEBUG_DISCORD_VERBOSELY:
    discord.utils.setup_logging(level=logging.DEBUG)

class TestView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="button")
    async def test_button(self, interaction: discord.Interaction, button):
        logging.info("test button pressed! %s %s %s", self, interaction, button)
        await interaction.response.send_message("test button pressed!", view=TestView(), ephemeral=True)

    @discord.ui.select(custom_id="select_gwillen_testing_1", placeholder="select something maybe? I'm not your mom.", options=[
        discord.SelectOption(label="option 1", value="opt1", description="the first option probably", emoji="✴", default=True),
        discord.SelectOption(label="option 2", value="opt2", description="the second option allegedly", emoji="❤️", default=False)
    ])
    async def select_menu(self, interaction: discord.Interaction, select):
        logging.info("select interacted! %s %s %s", self, interaction, select)
        await interaction.response.defer()

class PuzzleChoiceList(discord.ui.Select):
    def __init__(self, herring_cog, puzzles, custom_id, placeholder, callback):
        super().__init__(custom_id=custom_id, placeholder=placeholder)
        for puzzle in puzzles:
            self.append_option(discord.SelectOption(
                label=puzzle.name,
                value=f'huntpuzzle_{puzzle.hunt_id}_{puzzle.parent_id}_{puzzle.slug}',
                description=herring_cog.puzzle_join_extra_info(puzzle)))
        self.provided_callback = {'c': callback}

    async def callback(self, interaction):
        return await self.provided_callback['c'](interaction, self)

class PuzzleChoiceView(discord.ui.View):
    def __init__(self, herring_cog, puzzles):
        super().__init__(timeout=None)
        self.herring_cog = herring_cog
        self.add_item(PuzzleChoiceList(herring_cog, puzzles, "PuzzleChoiceView", "Please choose a puzzle:", lambda i, s: self.item_callback(i, s)))

    async def item_callback(self, interaction: discord.Interaction, select):
        logging.info("puzzle selected! %s %s %s", self, interaction, select)
        logging.info("interaction details: %s %s %s %s %s",
                     interaction.extras,
                     interaction.message,
                     interaction.data,
                     interaction.namespace,
                     interaction.command)

        puzzle_option_value = interaction.data['values'][0]
        m = re.match("huntpuzzle_(.*)_(.*)_(.*)", puzzle_option_value)
        (hunt_id, round_id, puzzle_slug) = m.groups()
        puzzle_chosen = await sync_to_async(lambda: Puzzle.objects.get(hunt_id=hunt_id, parent=round_id, slug=puzzle_slug))()
        member = interaction.guild.get_member(interaction.user.id)
        logging.info(f"adding {interaction.user} to {puzzle_slug}")
        channel, _ = await self.herring_cog.add_user_to_puzzle(member, puzzle_slug)
        # the following appears in the channel, although we can mark it ephemeral, but we could DM it instead -- could make that optional.
        await interaction.response.send_message(f"Welcome to the puzzle `{puzzle_chosen.name}`! Click to go there: {channel.mention}! Happy solving!", ephemeral=True)
        await member.send(f"Welcome to the puzzle `{puzzle_chosen.name}`! Click to go there: {channel.mention}! Happy solving!")
        #await interaction.response.send_message(f'You selected: {interaction.data["values"]}')

class RoundChoiceList(discord.ui.Select):
    def __init__(self, rounds, custom_id, placeholder, callback):
        super().__init__(custom_id=custom_id, placeholder=placeholder)
        for round in rounds:
            self.append_option(discord.SelectOption(label=f'{round.number} - {round.name}', value=f'huntround_{round.hunt_id}_{round.id}'))
        self.provided_callback = {'c': callback}

    async def callback(self, interaction):
        return await self.provided_callback['c'](interaction, self)

class RoundChoiceView(discord.ui.View):
    def __init__(self, herring_cog, rounds):
        super().__init__(timeout=None)
        self.herring_cog = herring_cog
        self.add_item(RoundChoiceList(rounds, "RoundChoiceView", "Please choose a round:", lambda i, s: self.item_callback(i, s)))

    async def item_callback(self, interaction: discord.Interaction, select):
        logging.info("round selected! %s %s %s", self, interaction, select)
        logging.info("interaction details: %s %s %s %s %s",
                     interaction.extras,
                     interaction.message,
                     interaction.data,
                     interaction.namespace,
                     interaction.command)

        round_option_value = interaction.data['values'][0]
        m = re.match("huntround_(.*)_(.*)", round_option_value)
        (hunt_id, round_id) = m.groups()
        round_chosen = await sync_to_async(lambda: Round.objects.get(hunt_id=hunt_id, id=round_id))()

        puzzles = await sync_to_async(lambda: list(round_chosen.puzzle_set.all()))()
        if len(puzzles) == 0:
            await interaction.reply.send_message(f"Sorry, {round_chosen.name} has no puzzles at the moment.")
            return

        new_view = PuzzleChoiceView(self.herring_cog, puzzles)
        #interaction.client.add_view(new_view)  # XXX does this do anything at all
        await interaction.response.send_message(f'You selected: {interaction.data["values"]}', view=new_view, ephemeral=True)

class HerringCog(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
        self.guild: typing.Optional[discord.Guild] = None
        self.announce_channel = None
        self.debug_channel = None
        self.pronoun_roles = []
        self.timezone_roles = []
        bot.add_view(RoundChoiceView(self, [])) # XXX
        bot.add_view(PuzzleChoiceView(self, []))

    def get_pronoun_roles(self):
        result = []

        found_autoroles = False
        for role in reversed(self.guild.roles):
            if not found_autoroles and (role.name != AUTOROLE_MARKER):
                continue
            found_autoroles = True

            # You know what, it's close enough.
            if "/" in role.name:
                result.append(role)
        logging.info(f"Auto-detected pronoun roles: {result} (found autorole marker: {found_autoroles})")
        return result

    def get_timezone_roles(self):
        result = []

        found_autoroles = False
        for role in reversed(self.guild.roles):
            if not found_autoroles and role.name != AUTOROLE_MARKER:
                continue
            found_autoroles = True

            if "UTC" in role.name:
                result.append(role)
        logging.info(f"Auto-detected timezone roles: {result} (found autorole marker: {found_autoroles})")
        return result

    @commands.Cog.listener()
    async def on_ready(self):
        self.guild = self.bot.get_guild(settings.HERRING_DISCORD_GUILD_ID)
        self.announce_channel = get(self.guild.text_channels, name = settings.HERRING_DISCORD_PUZZLE_ANNOUNCEMENTS)
        self.debug_channel = get(self.guild.text_channels, name = settings.HERRING_DISCORD_DEBUG_CHANNEL)
        self.pronoun_roles = self.get_pronoun_roles()
        self.timezone_roles = self.get_timezone_roles()
        logging.info("listener bot cog is ready")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        logging.info("on_raw_reaction_add: %s", payload)
        # ignore myself
        if payload.user_id == self.bot.user.id:
            return
        if payload.channel_id == self.announce_channel.id and payload.emoji.name == SIGNUP_EMOJI:
            # add someone to the puzzle
            message: discord.Message = await self.announce_channel.fetch_message(payload.message_id)
            await message.remove_reaction(SIGNUP_EMOJI, payload.member)
            target_channel = message.channel_mentions[0]
            await self.add_user_to_puzzle(payload.member, target_channel.name)

        # TODO: Merge this with the above when not in ultra-conservative mode
        try:
            if payload.emoji.name == SIGNUP_EMOJI:
                member = self.guild.get_member(payload.user_id)
                if member is not None:
                    dm_channel = member.dm_channel
                    if dm_channel is None:
                        # This seems to be the case if the bot is restarted and
                        # an old message is reacted to.
                        dm_channel = await member.create_dm()
                    if dm_channel.id == payload.channel_id:
                        message: discord.Message = await dm_channel.fetch_message(payload.message_id)
                        if message.author.id == self.bot.user.id:
                            # Can't remove the user's reactions from a DM, apparently...

                            # message.channel_mentions is always an empty list in
                            # DMs, per the documentation, so we must do what we
                            # must do...
                            match = re.search('\(#([^)]*)\)', message.content)
                            if match is not None:
                                await self.add_user_to_puzzle(member, match[1])
        except Exception as e:
            logging.error(f"on_raw_reaction_add: error in subscription reaction handler", e)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        logging.info("on_message: %s", message)
        if message.author.id == self.bot.user.id:
            return

        if message.type != discord.MessageType.default:
            return

        context: commands.Context = await self.bot.get_context(message)
        if context.valid:
            # this is a command, not puzzle activity
            logging.info("ignoring raw message already processed as command message")
            return

        if message.channel.type == discord.ChannelType.private:
            await message.channel.send("Sorry, I didn't understand that.")
            return

        if not message.guild or message.guild.id != settings.HERRING_DISCORD_GUILD_ID:
            logging.info("Wrong-guild or no-guild non-DM message, this should never happen, ignoring...")
            # don't care about other-guild messages
            return

        def record_activity(puzzle: Puzzle):
            dt = message.created_at.replace(tzinfo=timezone.utc)
            puzzle.record_activity(dt)
            query = Q(user_id=str(message.author.id))
            row, created = puzzle.channelparticipation_set\
                .filter(query)\
                .get_or_create(defaults=dict(
                        user_id=str(message.author.id),
                        last_active=dt, is_member=True,
                        display_name=message.author.display_name,
                        channel_puzzle=puzzle,
                ))
            if not created and (row.last_active is None or row.last_active < dt):
                row.last_active = dt
                row.user_id = str(message.author.id)
                row.display_name = message.author.display_name
                row.is_member = True
                row.save(update_fields=['user_id', 'last_active', 'is_member', 'display_name'])

        try:
            puzzle = await _get_puzzle_by_slug(message.channel.name)
        except Puzzle.DoesNotExist as e:
            # This is fine -- we must have seen a non-command message in a non-puzzle channel. Ignore it.
            # Optionally, we could verify that it's in a non-puzzle category.
            return

        await _manipulate_puzzle(message.channel.name, record_activity)

        if puzzle is not None:
            need_mentions = []
            for member in message.mentions:
                # if someone got mentioned, invite them to the puzzle
                _, changed = await self.add_user_to_puzzle(member, puzzle.slug)
                if changed:
                    need_mentions.append(member)
            if len(need_mentions) > 0:
                all_mentions = ", ".join(member.mention for member in need_mentions)
                alert = await message.channel.send(f"Added {all_mentions} to puzzle by request")
                await alert.delete()

    #@app_commands.command(name="gwillen_test")
    #async def gwillen_test(self, interaction: discord.Interaction) -> None:
    #    await self.gwillen_test_inner(interaction)

    #@app_commands.command(name="gwillen_test_alias")
    #async def gwillen_test_alias(self, interaction: discord.Interaction) -> None:
    #    await self.gwillen_test_inner(interaction)

    #async def gwillen_test_inner(self, interaction: discord.Interaction) -> None:
    #    print("test", file=sys.stderr)
    #    await interaction.response.send_message("hello!", ephemeral=True)
    #    await interaction.followup.send("please consider:", view=TestView(), ephemeral=True)

    @commands.hybrid_command(brief="sync app command tree")
    async def synctree(self, ctx:commands.Context):
        """ sync command tree """
        logging.info("syncing command tree...")
        result_global = await ctx.bot.tree.sync()
        result_guild = await ctx.bot.tree.sync(guild=ctx.guild)
        logging.info("sync complete: global=%s guild=%s", result_global, result_guild)
        if ctx.interaction:
            await ctx.interaction.response.send_message("Synced command tree: global=%s guild=%s" % (result_global, result_guild), ephemeral=True)
        else:
            await ctx.author.send("Synced command tree: global=%s guild=%s" % (result_global, result_guild))

    async def round_autocomplete(self, interation: discord.Interaction, current: str):
        rounds: list[Round] = await sync_to_async(list)(Round.objects.filter(hunt_id = settings.HERRING_HUNT_ID))
        return [
            app_commands.Choice(name=f"{round.number} - {round.name}", value=f"huntround_{round.hunt_id}_{round.id}")
            for round in rounds if current.lower() in round.name.lower()
        ]

    async def puzzle_autocomplete(self, interaction: discord.Interaction, current: str):
        round = None
        logging.info("puzauto int data: %s", interaction.data)
        for arg in interaction.data['options']:
            if arg['name'] == "round":
                round = arg['value']
                m = re.match("huntround_(.*)_(.*)", round)
                (hunt_id, round_id) = m.groups()

        puzzles: list[Puzzle] = []
        if round is not None:
            puzzles: list[Puzzle] = await sync_to_async(list)(Puzzle.objects.filter(hunt_id = int(hunt_id), parent_id = int(round_id)))
        else:
            puzzles: list[Puzzle] = await sync_to_async(list)(Puzzle.objects.filter(hunt_id = settings.HERRING_HUNT_ID))

        return [
            app_commands.Choice(name=puzzle.name, value=f"huntpuzzle_{puzzle.hunt_id}_{puzzle.parent_id}_{puzzle.slug}")
            for puzzle in puzzles if current.lower() in puzzle.name.lower()
        ]

    @app_commands.command(name="join", description="Join a puzzle channel")
    @app_commands.autocomplete(round=round_autocomplete, puzzle=puzzle_autocomplete)
    async def slash_join(self, interaction: discord.Interaction, round: str = None, puzzle: str = None) -> None:
        if puzzle is not None:
            m = re.match("huntpuzzle_(.*)_(.*)_(.*)", puzzle)
            (hunt_id, round_id, puzzle_slug) = m.groups()
            puzzle_chosen = await sync_to_async(lambda: Puzzle.objects.get(hunt_id=hunt_id, parent=round_id, slug=puzzle_slug))()
            member = interaction.guild.get_member(interaction.user.id)
            logging.info(f"adding {interaction.user} to {puzzle_slug}")
            channel, _ = await self.add_user_to_puzzle(member, puzzle_slug)
            # the following appears in the channel, although we can mark it ephemeral, but we could DM it instead -- could make that optional.
            await interaction.response.send_message(f"Welcome to the puzzle `{puzzle_chosen.name}`! Click to go there: {channel.mention}! Happy solving!", ephemeral=True)
            await member.send(f"Welcome to the puzzle `{puzzle_chosen.name}`! Click to go there: {channel.mention}! Happy solving!")
            return
        elif round is not None:
            m = re.match("huntround_(.*)_(.*)", round)
            (hunt_id, round_id) = m.groups()
            round_chosen = await sync_to_async(Round.objects.get)(hunt_id=hunt_id, id=round_id)
            puzzles = await sync_to_async(list)(Puzzle.objects.filter(hunt_id=hunt_id, parent_id=round_id))
            if len(puzzles) == 0:
                await interaction.reply.send_message(f"Sorry, {round_chosen.name} has no puzzles at the moment.")
                return

            new_view = PuzzleChoiceView(self, puzzles)
            await interaction.response.send_message(f'Please choose a puzzle in {round_chosen.name} to join:', view=new_view, ephemeral=True)
            return

        rounds = await sync_to_async(list)(Round.objects.filter(hunt_id = settings.HERRING_HUNT_ID))
        if len(rounds) == 0:
            await interaction.response.send_message("Sorry, there are no rounds available!", ephemeral=True)
            return

        new_view = RoundChoiceView(self, rounds)
        await interaction.response.send_message(view=new_view, ephemeral=True)

    def puzzle_join_extra_info(self, puzzle):
        solved = "(SOLVED!) " if puzzle.answer else ""
        try:
            text_channel, voice_channel = self.get_channel_pair(puzzle.slug)
            # -2 for @everyone and the bot
            people_watching = len(text_channel.overwrites) - 2
            people_chatting = len(voice_channel.voice_states) if voice_channel else None
            voice_status = f", {people_chatting} in voice" if people_chatting else ""
            return f"{solved}({people_watching} watchers{voice_status})"
        except Exception as e:
            log_to_discord(f"Failed to printerize puzzle: {puzzle}", exn=e)
            return f"{solved}<problem with puzzle channels, admins have been notified>"

    def puzzle_join_printerizer(self, puzzle):
        return f"{_abbreviate_name(puzzle)} {self.puzzle_join_extra_info(puzzle)}"

    @commands.command(brief="Join a puzzle channel")
    async def join(self, ctx:commands.Context, channel:typing.Optional[discord.TextChannel]):
        """
        Join a puzzle channel. Including the exact name of the channel will just let you straight into it with
        no further fuss (this is what gets copied from the Herring UI). Otherwise, the bot will PM you with
        a menu interaction that will let you find the puzzle you're looking for.
        :param channel: (optional) A specific channel to join
        """
        await self.delete_message_if_possible(ctx)
        member = self.guild.get_member(ctx.author.id)

        if isinstance(channel, discord.TextChannel):
            # we were asked for a puzzle by name, let's just hand it over
            await self.add_user_to_puzzle(member, channel.name)
            return

        rounds = await sync_to_async(list)(Round.objects.filter(hunt_id = settings.HERRING_HUNT_ID))
        if len(rounds) == 0:
            await ctx.author.send("Sorry, there are no rounds available!")
            return

        round_chosen: Round = await self.do_menu(
            ctx.author,
            rounds,
            "Which round contains the puzzle you want to join?",
            lambda round: round.name
        )
        if round_chosen is None:
            # timed out, bail
            return

        puzzles = await sync_to_async(lambda: list(round_chosen.puzzle_set.all()))()
        if len(puzzles) == 0:
            await ctx.author.send(f"Sorry, {round_chosen.name} has no puzzles at the moment.")
            return

        puzzle_chosen: Puzzle = await self.do_menu(
            ctx.author,
            puzzles,
            "Which puzzle would you like to join?",
            self.puzzle_join_printerizer
        )

        if puzzle_chosen is None:
            # timed out, bail
            return

        logging.info(f"adding {member} to {puzzle_chosen.slug}")
        channel, _ = await self.add_user_to_puzzle(member, puzzle_chosen.slug)
        await ctx.author.send(f"Welcome to the puzzle `{puzzle_chosen.name}`! Click to go there: {channel.mention}! Happy solving!")

    @commands.hybrid_command(brief="Leave a puzzle channel")
    async def leave(self, ctx, channel:typing.Optional[discord.TextChannel]):
        await self.leave_inner(ctx, channel)

    @commands.hybrid_command(brief="Leave a puzzle channel")
    async def part(self, ctx, channel:typing.Optional[discord.TextChannel]):
        await self.leave_inner(ctx, channel)

    async def leave_inner(self, ctx, channel: typing.Optional[discord.TextChannel]):
        """
        Leave the puzzle channel in which you executed hb!leave, thus hiding it from you once more (once you click
        away). Technically you can also leave a channel by name from anywhere, because it was easy to write; I don't
        really see this capability as being very useful.
        :param channel: (optional) A specific channel to leave.
        """
        # app commands only:
        interaction: discord.Interaction = ctx.interaction
        if not interaction:
            await self.delete_message_if_possible(ctx)
        # using fetch_member() here so we don't have to turn on the members intent
        member = await self.guild.fetch_member(ctx.author.id)

        by_name = isinstance(channel, discord.TextChannel)
        if not by_name:
            channel = ctx.channel
        try:
            puzzle = await sync_to_async(lambda: Puzzle.objects.get(slug=channel.name))()
            await self.remove_user_from_puzzle(member, puzzle.slug)
        except Puzzle.DoesNotExist:
            # don't actually care
            if interaction:
                await interaction.response.send_message(f"{'That' if by_name else 'This'} channel doesn't seem to be a puzzle, so you can't leave it.", ephemeral=True)
            return

        if interaction:
            # No need to say anything, but satisfy the API that we did something.
            await interaction.response.send_message(f"You have left {'that' if by_name else 'this'} puzzle.{'' if by_name else ' Select another channel from the sidebar.'}", ephemeral=True)

    @commands.hybrid_command(aliases=["solve"], brief="You solved a puzzle!")
    async def answer(self, ctx, *, answer):
        """
        Register the answer to a puzzle in Herring. Must be called in a puzzle channel.
        :param answer: The puzzle answer; spaces are allowed
        """
        await self.delete_message_if_possible(ctx)
        def answer_puzzle(puzzle):
            puzzle.answer = answer
        await _manipulate_puzzle(ctx.channel.name, answer_puzzle)
        if ctx.interaction:
            ctx.interaction.response.defer()

    @commands.hybrid_command(brief="Add a tag to a puzzle")
    async def tag(self, ctx, *, tag):
        """
        Add a tag to a puzzle (for example, "konundrum"). Must be called in a puzzle channel. Puzzles can have
        as many tags as you like (within reason, please).
        :param tag: The tag to add
        """
        await self.delete_message_if_possible(ctx)
        def tag_puzzle(puzzle):
            tags = self._parse_tags(puzzle)
            if tag not in tags:
                tags.append(tag)
            puzzle.tags = self._combine_tags(tags)
        await _manipulate_puzzle(ctx.channel.name, tag_puzzle)
        if ctx.interaction:
            ctx.interaction.response.defer()

    @commands.hybrid_command(brief="Remove a tag from a puzzle")
    async def untag(self, ctx, *, tag):
        """
        Remove a tag from a puzzle. Must be called in a puzzle channel.
        :param tag: The tag to remove
        """
        await self.delete_message_if_possible(ctx)
        def untag_puzzle(puzzle):
            tags = self._parse_tags(puzzle)
            puzzle.tags = self._combine_tags([t for t in tags if t != tag])
        await _manipulate_puzzle(ctx.channel.name, untag_puzzle)
        if ctx.interaction:
            ctx.interaction.response.defer()

    @staticmethod
    def _parse_tags(puzzle):
        return [t.strip() for t in puzzle.tags.split(',') if t.strip()]

    @staticmethod
    def _combine_tags(tags):
        return ", ".join(tags)

    @commands.hybrid_command(brief="Set the note for a puzzle")
    async def note(self, ctx, *, note):
        """
        Set the note for a puzzle, as a suggestion for future solvers. Must be called in a puzzle channel.
        :param note: The note to set for future solvers
        """
        await self.delete_message_if_possible(ctx)
        def note_puzzle(puzzle):
            puzzle.note = note
        await _manipulate_puzzle(ctx.channel.name, note_puzzle)
        if ctx.interaction:
            ctx.interaction.response.defer()

    # not async! deals with database mostly; intended to be called from inside a _manipulate_puzzle
    def _update_channel_participation(self, puzzle):
        text_channel, _ = self.get_channel_pair(puzzle.slug)
        if text_channel is None:
            return
        membership = [member for member in text_channel.overwrites if member.id != self.guild.me.id and member.id != self.guild.default_role.id]
        _update_channel_participation_inner(puzzle, membership)

    @commands.hybrid_command(aliases=["status"], brief="Show stats about puzzles")
    async def who(self, ctx, puzzle_name:typing.Optional[discord.TextChannel]):
        """
        Reports status of puzzles, including who is currently in the voice chat (if anyone). Can take a puzzle
        channel name, in which case it only reports that puzzle; otherwise it PMs the user a menu to choose the round
        :param puzzle_name: (optional) A particular puzzle channel you're curious about
        """
        await self.delete_message_if_possible(ctx)
        interaction: discord.Interaction = ctx.interaction

        def puzzle_printerizer(puzzle):
            text_channel, voice_channel = self.get_channel_pair(puzzle.slug)
            membership: typing.Sequence[discord.Member] = [member for member in text_channel.overwrites if member.id != self.guild.me.id and member.id != self.guild.default_role.id]
            if len(membership) > MAX_USER_LIST:
                watching = len(membership)
            else:
                watching = ", ".join(member.display_name for member in membership) or "no one"

            if voice_channel is None:
                voice_status = ""
            elif len(voice_channel.members) > MAX_USER_LIST:
                in_voice = len(voice_channel.members)
                voice_status = f", {in_voice} in voice chat"
            else:
                in_voice = ", ".join(member.display_name for member in voice_channel.members) or "no one"
                voice_status = f", {in_voice} in voice chat"
            solved = " (SOLVED!)" if puzzle.answer else ""
            return f"{_abbreviate_name(puzzle)} ({text_channel.mention}){solved}: {watching} watching{voice_status}"

        if puzzle_name is not None:
            try:
                puzzle = await sync_to_async(Puzzle.objects.get(slug=puzzle_name.name))
                output = puzzle_printerizer(puzzle)
                if interaction:
                    await interaction.response.send_message(output, ephemeral=True)
                else:
                    await ctx.author.send(puzzle_printerizer(puzzle))
            except Puzzle.DoesNotExist:
                if interaction:
                    await interaction.response.send_message("Sorry, that puzzle doesn't exist.", ephemeral=True)
            return

        if interaction:
            await interaction.response.send_message("Sorry, this functionality doesn't work with slash commands at this time.", ephemeral=True)
            return

        rounds = await sync_to_async(list)(Round.objects.filter(hunt_id = settings.HERRING_HUNT_ID))
        if len(rounds) == 0:
            await ctx.author.send("Sorry, there are no rounds available!")
            return

        round_chosen: Round = await self.do_menu(
            ctx.author,
            rounds,
            "Which round are you curious about?",
            lambda round: round.name
        )
        if round_chosen is None:
            # timed out, bail
            return

        puzzles = await sync_to_async(list)(round_chosen.puzzle_set.all())
        if len(puzzles) == 0:
            await ctx.author.send("Sorry, that round contains no puzzles right now.")
            return

        description = puzzle_printerizer(puzzles[0])
        for puzzle in puzzles[1:]:
            puzzle_line = puzzle_printerizer(puzzle)
            if len(description) + len(puzzle_line) > 2000:
                await ctx.author.send("", embed=discord.Embed(description=description))
                description = puzzle_line
            else:
                description += "\n" + puzzle_line
        await ctx.author.send("", embed=discord.Embed(description=description))

    @commands.hybrid_command(brief="Set your pronoun and/or timezone roles")
    async def role(self, ctx):
        """
        Ask the bot to set your preferred pronoun and timezone roles, from the standard lists of choices. If you
        want something that isn't in the lists, please contact a czar directly and they can make it and assign it to you.
        """
        await self.delete_message_if_possible(ctx)
        interaction: discord.Interaction = ctx.interaction
        if interaction:
            # We never send a real interaction response, so just reply to the interaction immediately and continue.
            await interaction.response.send_message("Setting your roles! Please check your private messages for a message from HerringBot.", ephemeral=True)

        member:discord.Member = self.guild.get_member(ctx.author.id)
        if not member:
            await ctx.author.send("Sorry, it seems that you don't exist?? Please contact the admins for tech support.")
            return

        roles_to_add = []
        pronoun_role = await self.do_menu(
            ctx.author,
            self.pronoun_roles + ["Don't set"],
            "Which pronouns would you like to use? If your preference doesn't appear, just pick something and get a czar to fix it.",
            str
        )
        if not pronoun_role:
            return
        if isinstance(pronoun_role, discord.Role):
            roles_to_add.append(pronoun_role)

        timezone_role = await self.do_menu(
            ctx.author,
            self.timezone_roles + ["Don't set"],
            "Which time zone are you solving in? Again, if you don't like any of these, get a czar to fix it for you.",
            str
        )
        if not timezone_role:
            return
        if isinstance(timezone_role, discord.Role):
            roles_to_add.append(timezone_role)

        current_roles = member.roles
        roles_to_remove = []
        for role in self.pronoun_roles:
            if role in current_roles:
                roles_to_remove.append(role)

        for role in self.timezone_roles:
            if role in current_roles:
                roles_to_remove.append(role)

        await member.remove_roles(*roles_to_remove)
        await member.add_roles(*roles_to_add)
        await member.send(f"You've been set up! Please ensure that your roles are set the way you wanted them to be.")

    @commands.command(hidden=True)
    async def cleanup_channels(self, ctx):
        await self.delete_message_if_possible(ctx)

        if ctx.author.id != self.guild.owner_id:
            raise commands.NotOwner()

        run_modes = {
            "Full Rebuild": (True, True, True),
            "Create and Fix Only": (True, True, False),
            "Fix Only": (True, False, False),
            "Dry Run": (False, False, False)
        }

        run_mode = await self.do_menu(
            ctx.author,
            run_modes.keys(),
            "This will rebuild all puzzle categories and channels, deleting any whose puzzles have been deleted!\n"
            "Are you sure you want to do this?"
        )
        if run_mode is None:
            # timed out, bail
            raise commands.UserInputError("Command timed out!")

        fix, create, delete = run_modes[run_mode]

        @sync_to_async
        def get_rounds_and_puzzles():
            rounds = list(Round.objects.filter(hunt_id=settings.HERRING_HUNT_ID))
            puzzles = list(Puzzle.objects.filter(hunt_id=settings.HERRING_HUNT_ID))
            return rounds, puzzles

        rounds, puzzles = await get_rounds_and_puzzles()

        def split_categories(round):
            if round.discord_categories is None:
                return []
            categories = round.discord_categories.split(",")
            return [int(category_id) for category_id in categories if category_id]

        rounds_by_category = {category_id: round for round in rounds for category_id in split_categories(round)}
        puzzles_by_slug = {puzzle.slug: puzzle for puzzle in puzzles}
        puzzles_by_round = collections.defaultdict(list)
        metapuzzles_by_round = collections.defaultdict(list)
        for puzzle in puzzles:
            puzzles_by_round[puzzle.parent_id].append(puzzle)
            if puzzle.is_meta:
                metapuzzles_by_round[puzzle.parent_id].append(puzzle)

        # first delete anything that doesn't seem to be attached to an actual puzzle
        for category in self.guild.categories:
            if category.id in settings.HERRING_DISCORD_PROTECTED_CATEGORIES:
                # these aren't puzzle categories
                continue
            for channel in category.channels:
                if (channel.type in [discord.ChannelType.text, discord.ChannelType.voice]) and (channel.name not in puzzles_by_slug):
                    await ctx.author.send(f"Deleting {channel.type} channel {channel.name} in {category.name} (for real: {delete})")
                    if delete:
                        await channel.delete()

            if category.id not in rounds_by_category:
                await ctx.author.send(f"Deleting category {category.name} (for real: {delete})")
                if delete:
                    await category.delete()

        for channel in self.guild.channels:
            if (channel.type in [discord.ChannelType.text, discord.ChannelType.voice]) and (channel.category is None):
                await ctx.author.send(f"Deleting {channel.type} channel {channel.name} (which is in no category) (for real: {delete})")
                if delete:
                    await channel.delete()

        for round in rounds:
            # next, create any categories that don't seem to exist for whatever reason
            new_categories = []
            for idx, category_id in enumerate(split_categories(round)):
                category = self.guild.get_channel(category_id)
                if category is None:
                    await ctx.author.send(f"creating new category for {round.name} {idx} (for real: {create})")
                    if create:
                        category = await _make_category_inner(self.guild, f"{round.name} {idx}" if idx > 0 else round.name)
                new_categories.append(category)

            # pretend rounds with no puzzles have one puzzle, just in case
            while max(1, len(puzzles_by_round[round.id])) > len(new_categories) * PUZZLES_PER_CATEGORY:
                await ctx.author.send(f"creating new category for {round.name} {len(new_categories)} (for real: {create})")
                if create:
                    category = await _make_category_inner(self.guild, f"{round.name} {len(new_categories)}" if len(new_categories) > 0 else round.name)
                else:
                    category = None
                new_categories.append(category)

            @sync_to_async
            def save_categories(round, categories):
                round.discord_categories = categories
                round.save()

            new_categories_value = ",".join(str(category.id) for category in new_categories)
            if new_categories_value != round.discord_categories:
                await ctx.author.send(f"saving {new_categories_value} to round {round.name} (for real: {create})")
                if create:
                    await save_categories(round, new_categories_value)

            async def fixup_puzzle(puzzle, category_idx):
                text_channel, voice_channel = self.get_channel_pair(puzzle.slug)
                if text_channel is None:
                    await ctx.author.send(f"creating channels for {puzzle.name} in {round.name} {category_idx} (for real: {create})")
                    if create:
                        text_channel, voice_channel = await _make_puzzle_channels_inner(new_categories[category_idx], puzzle)
                if text_channel is not None and text_channel.category != new_categories[category_idx]:
                    await ctx.author.send(f"Moving {puzzle.name} (text) to category {round.name} {category_idx} (for real: {fix})")
                    if fix:
                        await text_channel.edit(category=new_categories[category_idx])
                if voice_channel is not None and voice_channel.category != new_categories[category_idx]:
                    await ctx.author.send(f"Moving {puzzle.name} (voice) to category {round.name} {category_idx} (for real: {fix})")
                    if fix:
                        await voice_channel.edit(category=new_categories[category_idx])

                new_topic = _build_topic(puzzle)
                if text_channel is not None and text_channel.topic != new_topic:
                    await ctx.author.send(f"Fixing topic of {puzzle.name} (for real: {fix})")
                    if fix:
                        await text_channel.edit(topic=new_topic)
                if fix and text_channel is not None:
                    await _manipulate_puzzle(puzzle, self._update_channel_participation)

            # now, rearrange puzzle channels into categories
            # first, stash metapuzzles somewhere else, to give us a little elbow room
            for puzzle in metapuzzles_by_round[round.id]:
                if fix:
                    # if either are None we'll fix it later
                    text_channel, voice_channel = self.get_channel_pair(puzzle.slug)
                    if text_channel is not None:
                        await text_channel.edit(category=None)
                    if voice_channel is not None:
                        await voice_channel.edit(category=None)

            # then, move and/or create the normal puzzles where they're supposed to be
            for idx, puzzle in enumerate(puzzles_by_round[round.id]):
                if puzzle.is_meta:
                    continue
                await fixup_puzzle(puzzle, idx // PUZZLES_PER_CATEGORY)

            # finally, put the metapuzzles back
            for puzzle in metapuzzles_by_round[round.id]:
                await fixup_puzzle(puzzle, 0)

        await ctx.author.send("cleanup_channels: Done.")

    @staticmethod
    async def delete_message_if_possible(request_context):
        if request_context.interaction:
            # this is a slash command, nothing to delete
            return
        request_message = request_context.message
        # can't delete the other person's messages from DM channels
        if request_message.channel.type != discord.ChannelType.private:
            await request_message.delete()

    async def add_user_to_puzzle(self, member: discord.Member, puzzle_name: str):
        text_channel, voice_channel = self.get_channel_pair(puzzle_name)

        changed = await _add_user_to_channels(member, text_channel, voice_channel)

        if changed:
            await _manipulate_puzzle(puzzle_name, self._update_channel_participation)
            await text_channel.send(f"{member.mention} joined the puzzle.")
        return text_channel, changed

    def get_channel_pair(self, puzzle_name):
        text_channel: discord.TextChannel = get(self.guild.text_channels, name=puzzle_name)
        voice_channel: discord.VoiceChannel = get(self.guild.voice_channels, name=puzzle_name)
        return text_channel, voice_channel

    async def remove_user_from_puzzle(self, member: discord.Member, puzzle_name: str):
        text_channel, voice_channel = self.get_channel_pair(puzzle_name)

        await text_channel.set_permissions(member, overwrite=None)
        if voice_channel is not None:
            await voice_channel.set_permissions(member, overwrite=None)
        await _manipulate_puzzle(puzzle_name, self._update_channel_participation)

    async def do_menu(self, target, options, prompt, printerizer=(lambda x: x)):
        start = 0
        options = list(options)  # cover for callers who pass something listlike that can't be subscripted
        while start < len(options):
            description = prompt + "\n"
            description += "\n".join(f"{reaction} : {printerizer(option)}" for reaction, option in zip(MENU_REACTIONS, options[start:]))
            if len(options) > start + len(MENU_REACTIONS):
                description += f"\n{MENU_EXTRA_REACTION} : Something else"
            menu = await target.send("", embed=discord.Embed(description=description))
            for reaction, option in zip(MENU_REACTIONS, options[start:]):
                await menu.add_reaction(reaction)
            if len(options) > start + len(MENU_REACTIONS):
                await menu.add_reaction(MENU_EXTRA_REACTION)

            idx = None
            while idx is None:
                try:
                    reaction, user = await self.bot.wait_for("reaction_add", check=lambda r, u: r.message.id == menu.id and u != self.bot.user, timeout=900)
                    if reaction.emoji == MENU_EXTRA_REACTION:
                        idx = -1
                    else:
                        idx = MENU_REACTION_LOOKUP[reaction.emoji]
                except asyncio.TimeoutError:
                    # we want to clean these up after a while so we don't leak tasks forever if people don't follow through
                    return None

            if idx != -1:
                return options[start + idx]

            # otherwise print the next page of the menu
            start += len(MENU_REACTIONS)
        # not sure how we would get here but print a log and bail
        logging.error(f"Ran out of options in a menu! {[printerizer(option) for option in options]}")
        return None

    @commands.command(hidden=True)
    async def test_positions(self, ctx: commands.Context):
        for category in self.guild.categories:
            channels_str = " ".join(f"{channel.name}: {channel.position}" for channel in category.channels)
            await ctx.author.send(f"{category.name}: {channels_str}")


class SolvertoolsCog(commands.Cog):

    def __init__(self, bot:commands.Bot, client:aiohttp.ClientSession):
        self.bot = bot
        self.client_session = client

    @commands.hybrid_command(name="anagram", with_app_command=True, brief="Retrieve anagrams")
    async def anagram(self, ctx, *, arg):
        """
        Returns a bunch of anagrams of the given letters, sorted by cromulence. You can use "+1" or "-3" to add positive
        or negative wildcards, but more than two positive wildcards is unlikely to produce useful results.
        :param arg: Some letters, optionally followed by + or - a number of wildcards
        """
        url = urljoin(settings.HERRING_SOLVERTOOLS_URL, "/api/anagram")
        await self.api_passthrough_command(ctx, url, arg)

    @commands.hybrid_command(brief="Solve crossword clues, maybe")
    async def clue(self, ctx, *, arg):
        """
        Ask solvertools to solve a crossword clue for you. This doesn't work all that well but sometimes it comes
        through for you. You can add an enumeration such as (10) or a pattern like /..s....to./ (or any other
        regular expression) to limit the responses.
        :param arg: A crossowrd clue, optionally followed by an enumeration in () or regular expression in //
        """
        url = urljoin(settings.HERRING_SOLVERTOOLS_URL, "/api/clue")
        await self.api_passthrough_command(ctx, url, arg)

    @commands.hybrid_command(brief="Retrieve words satisfying a pattern")
    async def pattern(self, ctx, *, arg):
        """
        Get a bunch of words that satisfy a regular expression, sorted by cromulence.
        :param arg: A regular expression, optionally enclosed in //
        """
        url = urljoin(settings.HERRING_SOLVERTOOLS_URL, "/api/pattern")
        await self.api_passthrough_command(ctx, url, arg)

    #@commands.command(brief="gwillen_test_cmd_cmd2")
    #async def gwillen_test_cmd_cmd2(self, ctx, *, arg):
    #    pass

    async def api_passthrough_command(self, ctx:commands.Context, url, args):
        # this might take a while
        async with ctx.typing():
            args = re.sub(r"`(.*)`", r"\1", args)
            try:
                async with self.client_session.get(url, params={"text": args}) as response:
                    result = await response.text()

                    embed = discord.Embed(description=discord.utils.escape_markdown(result[:1500]))
                    await ctx.send("", embed=embed)
            except aiohttp.ClientError:
                await ctx.send("Sorry, the connection to ireproof.org doesn't seem to be working today.")

# Copied from https://gist.github.com/EvieePy/7822af90858ef65012ea500bcecf1612
class CommandErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """The event triggered when an error is raised while invoking a command.
        Parameters
        ------------
        ctx: commands.Context
            The context used for command invocation.
        error: commands.CommandError
            The Exception raised.
        """

        # This prevents any commands with local handlers being handled here in on_command_error.
        if hasattr(ctx.command, 'on_error'):
            return

        # This prevents any cogs with an overwritten cog_command_error being handled here.
        cog = ctx.cog
        if cog:
            if cog._get_overridden_method(cog.cog_command_error) is not None:
                return

        ignored = (commands.CommandNotFound, )

        # Allows us to check for original exceptions raised and sent to CommandInvokeError.
        # If nothing is found. We keep the exception passed to on_command_error.
        error = getattr(error, 'original', error)

        # Anything in ignored will return and prevent anything happening.
        if isinstance(error, ignored):
            return

        if isinstance(error, commands.DisabledCommand):
            await ctx.author.send(f'{ctx.command} has been disabled.')
        elif isinstance(error, commands.NoPrivateMessage):
            try:
                await ctx.author.send(f'{ctx.command} can not be used in Private Messages.')
            except discord.HTTPException:
                pass
        elif isinstance(error, commands.NotOwner):
            await ctx.author.send(f'{ctx.command} can only be used by the bot owner.')
        elif isinstance(error, commands.UserInputError):
            await ctx.author.send(f'{ctx.command} failed: {error}')
        else:
            await ctx.author.send(f'{ctx.command} failed for some reason. The admins have been notified, probably.')
            # All other Errors not returned come here. And we can just print the default TraceBack.
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
            if settings.HERRING_ERRORS_TO_DISCORD:
                log_to_discord("on_command_error", exn=error)


def command_prefix(bot, message:discord.Message):
    if message.channel.type == discord.ChannelType.private:
        # allow unprefixed commands in DMs
        return commands.when_mentioned_or("hb!", "")(bot, message)
    else:
        return commands.when_mentioned_or("hb!")(bot, message)


class HerringListenerBot(commands.Bot):
    """
    The listener bot is run exactly once. It listens for things happening in Discord
    and makes appropriate changes in Django in response. It's critical that nothing in Celery or Django tries to
    access this bot directly, because it only exists in one of the worker processes.
    """
    def __init__(self, client, *args, **kwargs):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix, *args, intents=intents, **kwargs)
        self.client = client

    async def setup_hook(self) -> None:
        # The `guilds=` arg makes the slash commands load faster than if they are global, but then they won't work in DMs.
        if GUILD_COMMANDS_FOR_TESTING:
            guilds = [discord.Object(id=settings.HERRING_DISCORD_GUILD_ID)]
            await self.add_cog(HerringCog(self), guilds=guilds)
            await self.add_cog(SolvertoolsCog(self, self.client), guilds=guilds)
        else:
            await self.add_cog(HerringCog(self))
            await self.add_cog(SolvertoolsCog(self, self.client))
        await self.add_cog(CommandErrorHandler(self))

        @self.event
        async def on_error(event, *args, **kwargs):
            logging.error(f"Error in event: {event}, with args {args} and kwargs {kwargs}.", exc_info=True)

class HerringAnnouncerBot(discord.Client):
    """
    The announcer bot is run in each Celery worker thread. Its job is to take actions in Discord in reaction to
    things happening in Django: creating categories and puzzles, announcing new puzzles, and announcing solved status.
    It's critical that this bot doesn't listen for anything happening in Discord, because there are multiple copies of it
    running at once, so each copy would react.
    """
    def __init__(self, *args, **kwargs):
        intents = discord.Intents.default()
        intents.members = True
        # we don't want this bot to respond to messages; just don't ask for the intent
        intents.message_content = False
        super(HerringAnnouncerBot, self).__init__(*args, intents=intents, **kwargs)
        self.guild = None
        self.announce_channel = None
        self._really_ready = asyncio.Event()

    async def on_ready(self):
        self.guild = self.get_guild(settings.HERRING_DISCORD_GUILD_ID)
        if not self.guild:
            logging.info("couldn't find the right guild; are you sure you have the right bot token?")

        self.announce_channel = get(self.guild.text_channels, name = settings.HERRING_DISCORD_PUZZLE_ANNOUNCEMENTS)
        self._really_ready.set()
        logging.info("announcer bot is really ready")

    def do_in_loop(self, coro, timeout=20):
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            logging.error(f"Timed out running {coro} in bot from thread {threading.current_thread()}", exc_info=True)
            raise RuntimeError("seems like the announcer bot is dead")

    def do_in_loop_nonblocking(self, coro):
        def handle_future_result(f):
            # Retrieve and ignore result.
            # I don't think this actually does anything?
            # The goal was to suppress the warning that we ignored the result.
            future.result()

        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        future.add_done_callback(handle_future_result)

    async def wait_until_really_ready(self, timeout=None):
        try:
            await asyncio.wait_for(self._really_ready.wait(), timeout)
            return True
        except asyncio.TimeoutError:
            return False

    async def make_category(self, name):
        await self._really_ready.wait()
        logging.info(f"making category called {name}")
        return await _make_category_inner(self.guild, name)

    async def make_puzzle_channels(self, puzzle: Puzzle):
        await self._really_ready.wait()

        # don't get these swapped! they have to be in this order, with sync_to_async applying last (appearing first)
        @sync_to_async
        @transaction.atomic
        def ensure_category_ready():
            round: Round = Round.objects.select_for_update().get(id=puzzle.parent_id)
            if round.discord_categories is None or len(round.discord_categories) == 0:
                raise ValueError(f"round {round.name} has no categories yet, try again soon")

            num_puzzles = round.puzzle_set.count()
            categories = [int(i) for i in round.discord_categories.split(",")]
            if num_puzzles > len(categories) * PUZZLES_PER_CATEGORY:
                # need to make a new category, which means getting back to async-land
                @async_to_sync
                async def make_category():
                    return await self.make_category(f"{round.name} {len(categories)}")
                category = make_category()
                round.discord_categories += "," + str(category.id)
                round.save()
            else:
                category = self.get_channel(categories[-1])
                if category is None:
                    raise ValueError(f"category {categories[-1]} not found!")
                logging.debug(f"found category {category.name}")
            return round, category

        round, category = await ensure_category_ready()

        text_channel, voice_channel = await _make_puzzle_channels_inner(category, puzzle)
        announcement = await self.announce_channel.send(f"New puzzle {puzzle.name} opened! {SIGNUP_EMOJI} this message to join, then click here to jump to the channel: {text_channel.mention}.")
        await announcement.add_reaction(SIGNUP_EMOJI)

    async def post_message(self, channel_name, message, **kwargs):
        await self._really_ready.wait()
        channel: discord.TextChannel = get(self.guild.text_channels, name=channel_name)
        if channel is None:
            logging.error(f"Couldn't get Discord channel {channel_name} in post_local_and_global!")
            return
        await channel.send(message, **kwargs)

    async def post_local_and_global(self, puzzle_name, local_message, global_message:str):
        await self._really_ready.wait()
        channel: discord.TextChannel = get(self.guild.text_channels, name=puzzle_name)
        if channel is None:
            logging.error(f"Couldn't get Discord channel {puzzle_name} in post_local_and_global!")
            return

        await channel.send(local_message)
        global_message = global_message.replace(f"#{puzzle_name}", channel.mention)
        await self.announce_channel.send(global_message)

    async def add_user_to_puzzle(self, user_profile: UserProfile, puzzle_name):
        await self._really_ready.wait()
        text_channel, voice_channel = self.get_channel_pair(puzzle_name)
        if text_channel is None:
            return
        member = self.guild.get_member_named(user_profile.discord_identifier)
        if member is None:
            logging.warning(f"couldn't find member named {user_profile.discord_identifier}")
            return
        changed = await _add_user_to_channels(member, text_channel, voice_channel)
        membership = [member for member in text_channel.overwrites if member.id != self.guild.me.id and member.id != self.guild.default_role.id]
        await _manipulate_puzzle(puzzle_name, lambda puzzle: _update_channel_participation_inner(puzzle, membership))
        if changed:
            await text_channel.send(f"{member.mention} joined the puzzle.")
        return text_channel

    def get_channel_pair(self, puzzle_name):
        text_channel: discord.TextChannel = get(self.guild.text_channels, name=puzzle_name)
        voice_channel: discord.VoiceChannel = get(self.guild.voice_channels, name=puzzle_name)
        return text_channel, voice_channel

    async def send_subscription_messages(self, puzzle_name: str, discord_ids: list[str], message_text: str):
        await self._really_ready.wait()
        channel: discord.TextChannel = get(self.guild.text_channels, name=puzzle_name)
        if channel is None:
            logging.error(f"Couldn't get Discord channel {puzzle_name} in send_subscription_messages!")
            return
        message_text += f" {SIGNUP_EMOJI} this message to join, then click here to jump to the channel: {channel.mention}."
        for discord_identifier in discord_ids:
            member = self.guild.get_member_named(discord_identifier)
            if member is None:
                logging.warning(f"couldn't find member named {discord_identifier}")
                continue
            if member in channel.overwrites:
                continue
            message = await member.send(message_text)
            await message.add_reaction(SIGNUP_EMOJI)


@lazy_object
def DISCORD_ANNOUNCER() -> Optional[HerringAnnouncerBot]:
    if not settings.HERRING_ACTIVATE_DISCORD:
        logging.warning("Running without Discord integration!")
        return None
    bot = make_announcer_bot()
    if bot:
        # Absolutely must not use any other method to send this here, because they all directly or indirectly call DISCORD_ANNOUNCER and would explode.
        #bot.do_in_loop(bot.post_message(settings.HERRING_DISCORD_DEBUG_CHANNEL, f"Discord announcer bot created in app: {settings.HEROKU_APP_NAME} / dyno {settings.HEROKU_DYNO_NAME}"))
        return bot
    else:
        logging.info("Oh no, failed to create discord announcer bot :-(")
        return None  # whoever called us will fail to say things to discover forever after :-\

def do_in_discord(coro):
    try:
        return DISCORD_ANNOUNCER.do_in_loop(coro)
    except RuntimeError:
        # probably the discord bot is busted, try to make it rebuild
        logging.error("Invalidating discord announcer bot!")
        del DISCORD_ANNOUNCER.__target__
        raise

def do_in_discord_nonblocking(coro):
    DISCORD_ANNOUNCER.do_in_loop_nonblocking(coro)


def log_to_discord(message, exn=None, add_stacktrace=False):
    try:
        ct = threading.current_thread()
        thread_info = [ct.name, ct.ident, ct.native_id]
        if exn is None:
            stack_trace = "".join(traceback.format_stack(limit=5))
        else:
            stack_trace = "".join(traceback.format_exception(None, exn, exn.__traceback__, limit=5))
        if exn or add_stacktrace:
            stack = discord.Embed(description=discord.utils.escape_markdown(stack_trace)[:MAX_DISCORD_EMBED_LEN])
        else:
            stack = None
        do_in_discord_nonblocking(DISCORD_ANNOUNCER.post_message(settings.HERRING_DISCORD_DEBUG_CHANNEL, f"`log_to_discord`: `{message}` `({thread_info})`", embed=stack))
    except Exception as e:
        logging.error(f"Logging to Discord failed, ignoring it! message={message} exn={exn} (failed with: {e})")

# Shared utilities that both bots use

async def _make_puzzle_channels_inner(category: discord.CategoryChannel, puzzle: Puzzle):
    @async_to_sync
    async def do_make_channels(locked_puzzle):
        topic = _build_topic(locked_puzzle)
        # setting position=0 doesn't work
        position = 1 if locked_puzzle.is_meta else (locked_puzzle.number or locked_puzzle.id) + 10
        text_channel = get(category.guild.text_channels, name=locked_puzzle.slug) or \
                       await category.create_text_channel(locked_puzzle.slug, topic=topic, position=position)
        if settings.HERRING_CREATE_DISCORD_VOICE_CHANNELS:
            voice_channel = get(category.guild.voice_channels, name=locked_puzzle.slug) or \
                            await category.create_voice_channel(locked_puzzle.slug, position=position, bitrate=settings.HERRING_DISCORD_BITRATE)
        else:
            voice_channel = None
        return text_channel, voice_channel
    return await _manipulate_puzzle(puzzle, do_make_channels)


def _build_topic(puzzle):
    puzzle_name = _abbreviate_name(puzzle)
    topic = f"{puzzle_name} - Sheet: {settings.HERRING_HOST}/s/{puzzle.id} - Puzzle: {puzzle.hunt_url}"
    return topic


def _abbreviate_name(puzzle):
    puzzle_name = puzzle.name
    if len(puzzle_name) >= 30:
        puzzle_name = puzzle_name[:29] + '\N{HORIZONTAL ELLIPSIS}'
    return puzzle_name


async def _make_category_inner(guild: discord.Guild, name: str):
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True)
    }
    existing = get(guild.categories, name=name)
    return existing or await guild.create_category(name, overwrites=overwrites)


@sync_to_async
def _manipulate_puzzle(puzzle:typing.Union[Puzzle, str], func):
    try:
        with transaction.atomic():
            if isinstance(puzzle, str):
                locked_puzzle = Puzzle.objects.select_for_update().get(slug=puzzle, hunt_id=settings.HERRING_HUNT_ID)
            else:
                locked_puzzle = Puzzle.objects.select_for_update().get(id=puzzle.id)
            result = func(locked_puzzle)
            locked_puzzle.save()
            return result
    except Puzzle.DoesNotExist:
        return

@sync_to_async
def _get_puzzle_by_slug(slug):
    return Puzzle.objects.get(slug=slug, hunt_id=settings.HERRING_HUNT_ID)

async def _add_user_to_channels(member, text_channel:discord.TextChannel, voice_channel):
    current_perms = text_channel.overwrites
    if member not in current_perms:
        await text_channel.set_permissions(member, read_messages=True)
        if voice_channel is not None:
            await voice_channel.set_permissions(member, view_channel=True)
        return True
    return False


def _update_channel_participation_inner(puzzle, membership):
    n = len(membership)
    logging.info(f"updating membership for {puzzle.slug} to {membership}")
    puzzle.channel_count = n
    puzzle.channelparticipation_set \
        .exclude(user_id__in=[str(member.id) for member in membership]) \
        .update(is_member=False)
    for member in membership:
        query = Q(user_id=str(member.id))
        puzzle.channelparticipation_set\
            .filter(query)\
            .update_or_create(defaults=dict(
                    user_id=str(member.id),
                    is_member=True,
                    display_name=member.display_name,
                    channel_puzzle=puzzle,
            ))


# Public factory methods

async def run_listener_bot():
    logging.info("Starting Discord listener bot")
    log_to_discord("Starting Discord listener bot")
    async with aiohttp.ClientSession() as client:
        async with HerringListenerBot(client) as bot:
            await bot.start(settings.HERRING_SECRETS['discord-bot-token'])


def make_announcer_bot():
    # create it in a new thread
    evt = threading.Event()
    bot = None

    def start_bot_thread():
        nonlocal bot
        try:
            logging.info("Trying to start announcer bot in thread...")
            # Hack hack: prevent discord from emitting a warning during startup, which would wreck our day
            discord.VoiceClient.warn_nacl = False
            async def run_bot():
                nonlocal bot
                async with HerringAnnouncerBot() as bot:
                    logging.info("Created announcer bot object, signalling Event.")
                    evt.set()
                    await bot.start(settings.HERRING_SECRETS['discord-bot-token'])

            asyncio.run(run_bot())
        except Exception as e:
            # This is at info because I don't want to risk problems (this code can be called from logs at WARNING and higher)
            logging.info("Oh no, announcer bot thread exception! {e}")

    # make it a daemon thread so it doesn't keep the process alive
    bot_thread = threading.Thread(target=start_bot_thread, daemon=True)
    bot_thread.start()
    result = evt.wait(timeout=5)
    if result:
        logging.info(f"got bot, it is a {type(bot)}")
        return bot
    else:
        logging.error(f"failed to create discord announcer bot (timed out trying). Is bot thread alive: {bot_thread.is_alive()}. bot_thread: {bot_thread}")
        return None
