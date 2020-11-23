import asyncio
import logging
import threading

import discord
from asgiref.sync import sync_to_async
from discord.ext import commands
from discord.utils import get

from herring import settings
from puzzles.models import Round, Puzzle

# Discord has a limit of 50 channels per category, so if this is more than 25 things Discord will break
menu_reactions = [
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
    "\N{REGIONAL INDICATOR SYMBOL LETTER T}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER U}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER V}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER W}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER X}",
    "\N{REGIONAL INDICATOR SYMBOL LETTER Y}",
]
menu_extra_reaction = "\N{REGIONAL INDICATOR SYMBOL LETTER Z}"
menu_reaction_lookup = {reaction: index for index, reaction in enumerate(menu_reactions)}


signup_emoji = "\N{RAISED HAND}"


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
        if payload.channel_id == self.announce_channel.id and payload.emoji.name == signup_emoji:
            # add someone to the puzzle
            message: discord.Message = await self.announce_channel.fetch_message(payload.message_id)
            target_channel = message.channel_mentions[0]
            await self.add_user_to_puzzle(payload.member, target_channel.name)

    @commands.command()
    async def echo(self, ctx, * , arg):
        await ctx.send("echo " + arg)

    @commands.command()
    async def link(self, ctx:commands.Context):
        if ctx.channel.type != discord.ChannelType.private:
            # can't delete the other fellow's messages from DM channels, don't know why
            await ctx.message.delete()
        embed = discord.Embed(description="Choose [wisely](https://www.google.com/)")
        menu = await ctx.author.send("", embed=embed)
        await menu.add_reaction("🇦")
        await menu.add_reaction("🇧")
        await menu.add_reaction("🇨")
        reaction, user = await ctx.bot.wait_for("reaction_add", check=lambda r, u: r.message.id == menu.id and u != ctx.bot.user)
        await ctx.author.send(user.mention + " chose " + str(reaction.emoji))

    @commands.command()
    async def join(self, ctx:commands.Context):
        if ctx.channel.type != discord.ChannelType.private:
            # can't delete the other fellow's messages from DM channels, don't know why
            await ctx.message.delete()

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

        # using fetch_member here so we don't have to turn on the members intent
        member = await self.guild.fetch_member(ctx.author.id)
        logging.info(f"adding {member} to {puzzle_chosen.slug}")
        channel = await self.add_user_to_puzzle(member, puzzle_chosen.slug)
        await ctx.author.send(f"Welcome to the puzzle {puzzle_chosen.name} in {channel.mention}! Happy solving!")

    async def add_user_to_puzzle(self, member: discord.Member, puzzle_name: str):
        text_channel: discord.TextChannel = get(self.guild.text_channels, name=puzzle_name)
        voice_channel: discord.VoiceChannel = get(self.guild.voice_channels, name=puzzle_name)

        await text_channel.set_permissions(member, read_messages=True)
        await voice_channel.set_permissions(member, view_channel=True)
        return text_channel

    async def do_menu(self, target, options, prompt, printerizer):
        start = 0
        while start < len(options):
            description = prompt + "\n"
            description += "\n".join(f"{reaction} : {printerizer(option)}" for reaction, option in zip(menu_reactions, options[start:]))
            if len(options) > start + len(menu_reactions):
                description += f"\n{menu_extra_reaction} : Something else"
            menu = await target.send("", embed = discord.Embed(description=description))
            for reaction, option in zip(menu_reactions, options[start:]):
                await menu.add_reaction(reaction)
            if len(options) > start + len(menu_reactions):
                await menu.add_reaction(menu_extra_reaction)

            idx = None
            while idx is None:
                reaction, user = await self.bot.wait_for("reaction_add", check=lambda r, u: r.message.id == menu.id and u != self.bot.user)
                if reaction.emoji == menu_extra_reaction:
                    idx = -1
                else:
                    idx = menu_reaction_lookup[reaction.emoji]

            if idx != -1:
                return options[start + idx]

            # otherwise print the next page of the menu
            start += len(menu_reactions)
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

    async def on_ready(self):
        self.guild = self.get_guild(settings.HERRING_DISCORD_GUILD_ID)
        self.announce_channel = get(self.guild.text_channels, name = settings.HERRING_DISCORD_PUZZLE_ANNOUNCEMENTS)

    def do_in_loop(self, coro):
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        try:
            return future.result(timeout=20)
        except TimeoutError as e:
            logging.error(f"Timed out running {coro.__name__} in bot", exc_info=True)
            return None

    async def make_category(self, name):
        await self.wait_until_ready()
        logging.info(f"making category called {name}")
        overwrites = {
            self.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            self.guild.me: discord.PermissionOverwrite(read_messages=True)
        }

        category = await self.guild.create_category(name, overwrites=overwrites)
        return category

    async def make_puzzle_channels(self, puzzle: Puzzle):
        await self.wait_until_ready()
        logging.info(f"making puzzle channels for {puzzle.name}")

        @sync_to_async
        def get_round():
            round: Round = puzzle.parent
            num_puzzles = round.puzzle_set.count()
            return round, num_puzzles

        round, num_puzzles = await get_round()
        categories = [int(i) for i in round.discord_categories.split(",")]

        if num_puzzles > len(categories) * len(menu_reactions):
            # need to make a new category
            category = await self.make_category(f"{round.name} {len(categories)}")
            @sync_to_async
            def add_round_category(category):
                round.discord_categories += "," + str(category.id)
                round.save()
            await add_round_category()
        else:
            category = self.get_channel(categories[-1])
            if category is None:
                raise ValueError(f"category {categories[-1]} not found!")
            logging.debug(f"found category {category.name}")

        puzzle_name = puzzle.name
        if len(puzzle_name) >= 30:
            puzzle_name = puzzle_name[:29] + '\N{HORIZONTAL ELLIPSIS}'
        topic = f"{puzzle_name} - Sheet: {settings.HERRING_HOST}/s/{puzzle.id} - Puzzle: {puzzle.hunt_url}"
        # setting position=0 doesn't work
        position = 1 if puzzle.is_meta else puzzle.number + 10
        text_channel = await category.create_text_channel(puzzle.slug, topic=topic, position=position)
        voice_channel = await category.create_voice_channel(puzzle.slug, position=position)

        announcement = await self.announce_channel.send(f"New puzzle {puzzle.name} opened! {signup_emoji} this message to join, then head to {text_channel.mention}.")
        await announcement.add_reaction(signup_emoji)


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

