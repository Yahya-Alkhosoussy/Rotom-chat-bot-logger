import asyncio
from os import getenv
import os
import subprocess
import shutil
import sys

import discord
from discord.ext import commands
from dotenv import load_dotenv
from twitchAPI.type import AuthScope

from bots.discord_bot import DavexDiscordBot
from bots.twitch_bot import DavexTwitchBot

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
    AuthScope.CLIPS_EDIT,
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

twitch_mod_bot = DavexTwitchBot(APP_ID, APP_SECRET, BOT_SCOPES, DAVEX_SCOPES, bot)


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

def get_full_path():
    
    import winreg
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment") as key:
        system_path, _ = winreg.QueryValueEx(key, "Path")

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
        try:
            user_path, _ = winreg.QueryValueEx(key, "Path")
        except FileNotFoundError:
            user_path = ""

    separator = ";"

    # Combine registry paths with the bot's existing PATH, deduplicating
    all_paths = os.environ["PATH"].split(";") + system_path.split(";") + user_path.split(";")

    seen = set()
    deduped = []
    for p in all_paths:
        if p and p not in seen:
            seen.add(p)
            deduped.append(p)

    return separator.join(deduped)


@bot.command(name="restart")
async def restart(ctx: commands.Context, stash: bool):

    await ctx.send("Checking for updates...")

    # sync up python's PATH with window's PATH
    os.environ["PATH"] = get_full_path()

    git_path = shutil.which("git")

    try:
        assert git_path
        if stash:
            res_0 = await asyncio.to_thread(
                subprocess.run, [git_path, "stash"], capture_output=True, check=True, text=True, shell=True
            )
            await ctx.send("Stashed successfully")
            await ctx.send(res_0.stdout)
        res = await asyncio.to_thread(
            subprocess.run, [git_path, "pull"], capture_output=True, check=True, text=True, shell=True
        )
        await ctx.send("Pulled successfully")
        await ctx.send(res.stdout)
        res_2 = await asyncio.to_thread(
            subprocess.run, [sys.executable, "setup.py"], check=True, capture_output=True, text=True
        )
        await ctx.send("Successfully installed all dependencies")
        await ctx.send(res_2.stdout[-len(" Setup complete!") :])
    except subprocess.CalledProcessError as e:
        await ctx.send(f"failed: error {e.stderr}")
    except Exception as e:
        await ctx.send(f"Failed: Error {str(e)}")

    await ctx.send("Restarting now...")

    subprocess.Popen([sys.executable] + sys.argv)

    await bot.close()  # closes the bot normally

async def main():
    token = getenv("discord_token")
    assert token
    await asyncio.gather(bot.start(token=token), twitch_mod_bot.run(), return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())
