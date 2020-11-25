import asyncio
import collections
import logging
import threading

import discord
import typing
from asgiref.sync import sync_to_async
from discord.ext import commands
from discord.utils import get

from herring import settings
from puzzles.models import Round, Puzzle

# Discord limits a user to putting 20 emojis on a message, so if this is more than 19, the menu won't work
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
PUZZLES_PER_CATEGORY = 25

SIGNUP_EMOJI = "\N{RAISED HAND}"


class HerringCog(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
        self.guild = None
        self.announce_channel = None

    @commands.Cog.listener()
    async def on_ready(self):
        self.guild = self.bot.get_guild(settings.HERRING_DISCORD_GUILD_ID)
        self.announce_channel = get(self.guild.text_channels, name = settings.HERRING_DISCORD_PUZZLE_ANNOUNCEMENTS)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        # ignore myself
        if payload.user_id == self.bot.user.id:
            return
        if payload.channel_id == self.announce_channel.id and payload.emoji.name == SIGNUP_EMOJI:
            # add someone to the puzzle
            message: discord.Message = await self.announce_channel.fetch_message(payload.message_id)
            target_channel = message.channel_mentions[0]
            await self.add_user_to_puzzle(payload.member, target_channel.name)

    @commands.command()
    async def join(self, ctx:commands.Context, channel:typing.Optional[discord.TextChannel]):
        await self.delete_message_if_possible(ctx.message)
        # using fetch_member() here so we don't have to turn on the members intent
        member = await self.guild.fetch_member(ctx.author.id)

        if isinstance(channel, discord.TextChannel):
            # we were asked for a puzzle by name, let's just hand it over
            await self.add_user_to_puzzle(member, channel.name)
            return

        # this is the most ridiculous thing ever. i feel dirty for writing this
        rounds = await sync_to_async(lambda: list(Round.objects.all()))()
        if len(rounds) == 0:
            await ctx.author.send("Sorry, there are no rounds available!")
            return

        round_chosen: Round = await self.do_menu(
            ctx.author,
            rounds,
            "Which round contains the puzzle you want to join?",
            lambda round: round.name
        )

        puzzles = await sync_to_async(lambda: list(round_chosen.puzzle_set.all()))()
        if len(puzzles) == 0:
            await ctx.author.send(f"Sorry, {round_chosen.name} has no puzzles at the moment.")
            return

        puzzle_chosen: Puzzle = await self.do_menu(
            ctx.author,
            puzzles,
            "Which puzzle would you like to join?",
            lambda puzzle: f"{puzzle.name} (TODO presence data)"
        )

        logging.info(f"adding {member} to {puzzle_chosen.slug}")
        channel = await self.add_user_to_puzzle(member, puzzle_chosen.slug)
        await ctx.author.send(f"Welcome to the puzzle {puzzle_chosen.name} in {channel.mention}! Happy solving!")

    @commands.command(aliases=["part"])
    async def leave(self, ctx, channel:typing.Optional[discord.TextChannel]):
        await self.delete_message_if_possible(ctx.message)
        # using fetch_member() here so we don't have to turn on the members intent
        member = await self.guild.fetch_member(ctx.author.id)

        if not isinstance(channel, discord.TextChannel):
            channel = ctx.channel
        try:
            puzzle = await sync_to_async(lambda: Puzzle.objects.get(slug=channel.name))()
            await self.remove_user_from_puzzle(member, puzzle.slug)
        except Puzzle.DoesNotExist:
            # don't actually care
            pass

    @commands.command(aliases=["solve"])
    async def answer(self, ctx, *, answer):
        await self.delete_message_if_possible(ctx.message)
        def answer_puzzle(puzzle):
            puzzle.answer = answer
        await self._manipulate_puzzle(ctx.channel.name, answer_puzzle)

    @commands.command()
    async def tag(self, ctx, *, tag):
        await self.delete_message_if_possible(ctx.message)
        def tag_puzzle(puzzle):
            tags = self._parse_tags(puzzle)
            if tag not in tags:
                tags.append(tag)
            puzzle.tags = self._combine_tags(tags)
        await self._manipulate_puzzle(ctx.channel.name, tag_puzzle)

    @commands.command()
    async def untag(self, ctx, *, tag):
        await self.delete_message_if_possible(ctx.message)
        def untag_puzzle(puzzle):
            tags = self._parse_tags(puzzle)
            puzzle.tags = self._combine_tags([t for t in tags if t != tag])
        await self._manipulate_puzzle(ctx.channel.name, untag_puzzle)

    @staticmethod
    def _parse_tags(puzzle):
        return [t.strip() for t in puzzle.tags.split(',') if t.strip()]

    @staticmethod
    def _combine_tags(tags):
        return ", ".join(tags)

    @commands.command()
    async def note(self, ctx, *, note):
        await self.delete_message_if_possible(ctx.message)
        def note_puzzle(puzzle):
            puzzle.note = note
        await self._manipulate_puzzle(ctx.channel.name, note_puzzle)

    @staticmethod
    @sync_to_async
    def _manipulate_puzzle(puzzle_name, func):
        try:
            puzzle = Puzzle.objects.get(slug=puzzle_name)
            func(puzzle)
            puzzle.save()
        except Puzzle.DoesNotExist:
            return

    @commands.command()
    async def cleanup_channels(self, ctx):
        await self.delete_message_if_possible(ctx.message)

        really_do_it = await self.do_menu(
            ctx.author,
            [True, False],
            "This will rebuild all puzzle categories and channels, deleting any whose puzzles have been deleted!\n"
            "Are you sure you want to do this?",
            lambda b: "Yes" if b else "Dry Run"
        )

        @sync_to_async
        def get_rounds_and_puzzles():
            rounds = list(Round.objects.all())
            puzzles = list(Puzzle.objects.all())
            return rounds, puzzles

        rounds, puzzles = await get_rounds_and_puzzles()

        rounds_by_category = {int(category_id): round for round in rounds for category_id in round.discord_categories.split(",")}
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
                if channel.name not in puzzles_by_slug:
                    if really_do_it:
                        await channel.delete()
                    else:
                        await ctx.author.send(f"Deleting {channel.type} channel {channel.name} in {category.name}")

            if category.id not in rounds_by_category:
                if really_do_it:
                    await category.delete()
                else:
                    await ctx.author.send(f"Deleting category {category.name}")

        for round in rounds:
            # next, create any categories that don't seem to exist for whatever reason
            new_categories = []
            for idx, category_id in enumerate(round.discord_categories.split(",")):
                category = self.guild.get_channel(int(category_id))
                if category is None:
                    if really_do_it:
                        category = await _make_category_inner(self.guild, f"{round.name} {idx}" if idx > 0 else round.name)
                    else:
                        await ctx.author.send(f"creating new category for {round.name} {idx}")
                new_categories.append(category)

            while len(puzzles_by_round[round.id]) > len(new_categories) * PUZZLES_PER_CATEGORY:
                if really_do_it:
                    category = await _make_category_inner(self.guild, f"{round.name} {len(new_categories)}" if len(new_categories) > 0 else round.name)
                else:
                    await ctx.author.send(f"creating new category for {round.name} {len(new_categories)}")
                    category = None
                new_categories.append(category)

            @sync_to_async
            def save_categories(round, categories):
                round.discord_categories = categories
                round.save()

            new_categories_value = ",".join(str(category.id) for category in new_categories)
            if new_categories_value != round.discord_categories:
                if really_do_it:
                    await save_categories(round, new_categories_value)
                else:
                    await ctx.author.send(f"saving {new_categories_value} to round {round.name}")

            # now, rearrange puzzle channels into categories
            # first, stash metapuzzles somewhere else, to give us a little elbow room
            for puzzle in metapuzzles_by_round[round.id]:
                text_channel, voice_channel = self.get_channel_pair(puzzle.slug)
                if text_channel is None:
                    # we'll fix this later
                    continue
                if really_do_it:
                    await text_channel.edit(category=None)
                    await voice_channel.edit(category=None)
            # then, move and/or create the normal puzzles where they're supposed to be
            for idx, puzzle in enumerate(puzzles_by_round[round.id]):
                if puzzle.is_meta:
                    continue
                text_channel, voice_channel = self.get_channel_pair(puzzle.slug)
                intended_category_idx = idx // PUZZLES_PER_CATEGORY
                if text_channel is None:
                    if really_do_it:
                        await _make_puzzle_channels_inner(new_categories[intended_category_idx], puzzle)
                    else:
                        await ctx.author.send(f"creating channels for {puzzle.name} in {round.name} {intended_category_idx}")
                else:
                    if text_channel.category != new_categories[intended_category_idx]:
                        if really_do_it:
                            await text_channel.edit(category=new_categories[intended_category_idx])
                            await voice_channel.edit(category=new_categories[intended_category_idx])
                        else:
                            await ctx.author.send(f"Moving {puzzle.name} to category {round.name} {intended_category_idx}")
            # finally, put the metapuzzles back
            for puzzle in metapuzzles_by_round[round.id]:
                text_channel, voice_channel = self.get_channel_pair(puzzle.slug)
                if text_channel is None:
                    if really_do_it:
                        await _make_puzzle_channels_inner(new_categories[0], puzzle)
                    else:
                        await ctx.author.send(f"creating channels for meta {puzzle.name} in {round.name}")
                else:
                    if really_do_it:
                        await text_channel.edit(category=new_categories[0])
                        await voice_channel.edit(category=new_categories[0])
                    else:
                        await ctx.author.send(f"Moving meta {puzzle.name} to category {round.name}")

    @staticmethod
    async def delete_message_if_possible(request_message):
        # can't delete the other person's messages from DM channels
        if request_message.channel.type != discord.ChannelType.private:
            await request_message.delete()

    async def add_user_to_puzzle(self, member: discord.Member, puzzle_name: str):
        text_channel, voice_channel = self.get_channel_pair(puzzle_name)

        await text_channel.set_permissions(member, read_messages=True)
        await voice_channel.set_permissions(member, view_channel=True)
        return text_channel

    def get_channel_pair(self, puzzle_name):
        text_channel: discord.TextChannel = get(self.guild.text_channels, name=puzzle_name)
        voice_channel: discord.VoiceChannel = get(self.guild.voice_channels, name=puzzle_name)
        return text_channel, voice_channel

    async def remove_user_from_puzzle(self, member: discord.Member, puzzle_name: str):
        text_channel, voice_channel = self.get_channel_pair(puzzle_name)

        await text_channel.set_permissions(member, overwrite=None)
        await voice_channel.set_permissions(member, overwrite=None)

    async def do_menu(self, target, options, prompt, printerizer=(lambda x: x)):
        start = 0
        while start < len(options):
            description = prompt + "\n"
            description += "\n".join(f"{reaction} : {printerizer(option)}" for reaction, option in zip(MENU_REACTIONS, options[start:]))
            if len(options) > start + len(MENU_REACTIONS):
                description += f"\n{MENU_EXTRA_REACTION} : Something else"
            menu = await target.send("", embed = discord.Embed(description=description))
            for reaction, option in zip(MENU_REACTIONS, options[start:]):
                await menu.add_reaction(reaction)
            if len(options) > start + len(MENU_REACTIONS):
                await menu.add_reaction(MENU_EXTRA_REACTION)

            idx = None
            while idx is None:
                reaction, user = await self.bot.wait_for("reaction_add", check=lambda r, u: r.message.id == menu.id and u != self.bot.user)
                if reaction.emoji == MENU_EXTRA_REACTION:
                    idx = -1
                else:
                    idx = MENU_REACTION_LOOKUP[reaction.emoji]

            if idx != -1:
                return options[start + idx]

            # otherwise print the next page of the menu
            start += len(MENU_REACTIONS)
        # not sure how we would get here but print a log and bail
        logging.error(f"Ran out of options in a menu! {[printerizer(option) for option in options]}")
        return None

    @commands.command()
    async def test_positions(self, ctx: commands.Context):
        for category in self.guild.categories:
            channels_str = " ".join(f"{channel.name}: {channel.position}" for channel in category.channels)
            await ctx.author.send(f"{category.name}: {channels_str}")


def command_prefix(bot, message:discord.Message):
    if message.channel.type == discord.ChannelType.private:
        # allow unprefixed commands in DMs
        return ["hb!", ""]
    else:
        return "hb!"


class HerringListenerBot(commands.Bot):
    """
    The listener bot is run exactly once (alongside the Slack bot). It listens for things happening in Discord
    and makes appropriate changes in Django in response. It's critical that nothing in Celery or Django tries to
    access this bot directly, because it only exists in one of the worker processes.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(command_prefix, *args, **kwargs)
        self.add_cog(HerringCog(self))


class HerringAnnouncerBot(discord.Client):
    """
    The announcer bot is run in each Celery worker thread. Its job is to take actions in Discord in reaction to
    things happening in Django: creating categories and puzzles, announcing new puzzles, and announcing solved status.
    It's critical that this bot doesn't listen for anything happening in Discord, because there are multiple copies of it
    running at once, so each copy would react.
    """
    def __init__(self, *args, **kwargs):
        super(HerringAnnouncerBot, self).__init__(*args, **kwargs)
        self.guild = None
        self.announce_channel = None
        self._really_ready = asyncio.Event()

    async def on_ready(self):
        self.guild = self.get_guild(settings.HERRING_DISCORD_GUILD_ID)
        self.announce_channel = get(self.guild.text_channels, name = settings.HERRING_DISCORD_PUZZLE_ANNOUNCEMENTS)
        self._really_ready.set()

    def do_in_loop(self, coro):
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        try:
            return future.result(timeout=20)
        except TimeoutError as e:
            logging.error(f"Timed out running {coro.__name__} in bot", exc_info=True)
            return None

    async def make_category(self, name):
        await self._really_ready.wait()
        logging.info(f"making category called {name}")
        return await _make_category_inner(self.guild, name)

    async def make_puzzle_channels(self, puzzle: Puzzle):
        await self._really_ready.wait()
        logging.info(f"making puzzle channels for {puzzle.name}")

        @sync_to_async
        def get_round():
            round: Round = puzzle.parent
            num_puzzles = round.puzzle_set.count()
            return round, num_puzzles

        round, num_puzzles = await get_round()
        categories = [int(i) for i in round.discord_categories.split(",")]

        if num_puzzles > len(categories) * PUZZLES_PER_CATEGORY:
            # need to make a new category
            category = await self.make_category(f"{round.name} {len(categories)}")
            @sync_to_async
            def add_round_category(category):
                round.discord_categories += "," + str(category.id)
                round.save()
            await add_round_category(category)
        else:
            category = self.get_channel(categories[-1])
            if category is None:
                raise ValueError(f"category {categories[-1]} not found!")
            logging.debug(f"found category {category.name}")

        text_channel, voice_channel = await _make_puzzle_channels_inner(category, puzzle)
        announcement = await self.announce_channel.send(f"New puzzle {puzzle.name} opened! {SIGNUP_EMOJI} this message to join, then head to {text_channel.mention}.")
        await announcement.add_reaction(SIGNUP_EMOJI)

    async def post_local_and_global(self, puzzle_name, local_message, global_message:str):
        await self._really_ready.wait()
        channel: discord.TextChannel = get(self.guild.text_channels, name=puzzle_name)
        if channel is None:
            logging.error(f"Couldn't get Discord channel {puzzle_name} in post_local_and_global!")
            return

        await channel.send(local_message)
        global_message = global_message.replace(f"#{puzzle_name}", channel.mention)
        await self.announce_channel.send(global_message)


async def _make_puzzle_channels_inner(category: discord.CategoryChannel, puzzle: Puzzle):
    puzzle_name = puzzle.name
    if len(puzzle_name) >= 30:
        puzzle_name = puzzle_name[:29] + '\N{HORIZONTAL ELLIPSIS}'
    topic = f"{puzzle_name} - Sheet: {settings.HERRING_HOST}/s/{puzzle.id} - Puzzle: {puzzle.hunt_url}"
    # setting position=0 doesn't work
    position = 1 if puzzle.is_meta else puzzle.number + 10
    text_channel = await category.create_text_channel(puzzle.slug, topic=topic, position=position)
    voice_channel = await category.create_voice_channel(puzzle.slug, position=position)
    return text_channel, voice_channel


async def _make_category_inner(guild: discord.Guild, name: str):
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True)
    }

    return await guild.create_category(name, overwrites=overwrites)


def make_listener_bot(loop):
    return HerringListenerBot(loop=loop)


def make_announcer_bot(token):
    # create it in a new thread
    cond = threading.Condition()
    bot = None

    def start_bot_thread():
        async def start_bot():
            nonlocal bot
            with(cond):
                bot = HerringAnnouncerBot()
                cond.notify(1)
            await bot.start(token)

        asyncio.run(start_bot())

    with(cond):
        # make it a daemon thread so it doesn't keep the process alive
        bot_thread = threading.Thread(target=start_bot_thread, daemon=True)
        bot_thread.start()
        logging.info("about to wait for bot to be created")
        cond.wait()
        logging.info(f"got bot, it is a {type(bot)}")
        return bot

