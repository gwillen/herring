import asyncio
import logging
import threading

import discord
from asgiref.sync import sync_to_async
from discord.ext import commands
from discord.utils import get

from herring.settings import HERRING_DISCORD_GUILD_ID
from puzzles.models import Round, Puzzle

menu_reactions = [
    "🇦",
    "🇧",
    "🇨"
]

reaction_lookup = {reaction: index for index, reaction in enumerate(menu_reactions)}

class HerringCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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
        round_menu_message = "Which round contains the puzzle you want to join?\n"

        round_menu_message += "\n".join(f"{reaction} : {round.name}" for reaction, round in zip(menu_reactions, rounds))

        round_menu = await ctx.send(round_menu_message)
        for reaction, round in zip(menu_reactions, rounds):
            await round_menu.add_reaction(reaction)

        reaction, user = await ctx.bot.wait_for("reaction_add", check=lambda r, u: r.message.id == round_menu.id and u != ctx.bot.user)
        idx = reaction_lookup[reaction.emoji]
        if idx is None:
            return
        round_chosen = rounds[idx]
        await ctx.author.send(f"You picked {round_chosen.name} but this next bit hasn't been implemented yet.")


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

    def do_in_loop(self, coro):
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        try:
            return future.result(timeout=10)
        except TimeoutError as e:
            logging.error("Timed out running %s in bot", coro.__name__, exc_info=True)
            return None

    async def make_category(self, name):
        await self.wait_until_ready()
        logging.info(f"making category called {name}")
        guild = self.get_guild(HERRING_DISCORD_GUILD_ID)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True)
        }

        category = await guild.create_category(name, overwrites=overwrites)
        return category


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

