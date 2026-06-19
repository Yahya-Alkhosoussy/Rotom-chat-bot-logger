import asyncio
from os import getenv

import discord
from discord.ext import commands
from dotenv import load_dotenv
from twitchAPI.type import AuthScope

from bots.discord_bot import DavexDiscordBot
from bots.twitch_bot import DavexTwitchBot, DavexTwitchModBot  # noqa

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.message_content = True
bot = DavexDiscordBot(intents=intents)

APP_ID = getenv("client_id")
APP_SECRET = getenv("client_secret")
assert APP_ID, "App ID is none"
assert APP_SECRET, "App secret is None"

DAVEX_SCOPES = [
    AuthScope.CHANNEL_BOT,
    AuthScope.CHANNEL_MODERATE,
    AuthScope.MODERATION_READ,
    AuthScope.MODERATOR_READ_BANNED_USERS,
    AuthScope.MODERATOR_READ_CHAT_MESSAGES,
    AuthScope.MODERATOR_READ_UNBAN_REQUESTS,
    AuthScope.MODERATOR_READ_WARNINGS,
]

BOT_SCOPES = [
    AuthScope.USER_BOT,
    AuthScope.USER_READ_CHAT,
    AuthScope.CHAT_READ,
    AuthScope.CHAT_EDIT,
    AuthScope.USER_WRITE_CHAT,
    AuthScope.MODERATION_READ,
    AuthScope.MODERATOR_READ_BANNED_USERS,
    AuthScope.MODERATOR_READ_CHAT_MESSAGES,
    AuthScope.MODERATOR_READ_UNBAN_REQUESTS,
    AuthScope.MODERATOR_READ_WARNINGS,
]

twitch_mod_bot = DavexTwitchModBot(APP_ID, APP_SECRET, BOT_SCOPES, DAVEX_SCOPES, bot)
twitch_bot = DavexTwitchBot(APP_ID, APP_SECRET, BOT_SCOPES, DAVEX_SCOPES)


@bot.group(name="get")
async def get(ctx: commands.Context):
    pass


@get.command(name="warnings")
async def get_warnings(ctx: commands.Context):
    assert bot.twitch_moderation_loop
    await bot.twitch_moderation_loop.warnings_requested(ctx=ctx)


@get.command(name="bans")
async def get_bans(ctx: commands.Context):
    assert bot.twitch_moderation_loop
    await bot.twitch_moderation_loop.bans_requested(ctx=ctx)


@get.command(name="timeouts")
async def get_timeouts(ctx: commands.Context):
    assert bot.twitch_moderation_loop
    await bot.twitch_moderation_loop.timeouts_requested(ctx=ctx)


@get.command(name="messages")
async def get_deleted_messages(ctx: commands.Context):
    assert bot.twitch_moderation_loop
    await bot.twitch_moderation_loop.deleted_messages_requested(ctx=ctx)


async def main():
    token = getenv("discord_token")
    assert token
    await asyncio.gather(bot.start(token=token), twitch_mod_bot.run(), twitch_bot.run(), return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())
