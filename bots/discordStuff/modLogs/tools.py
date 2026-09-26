import asyncio
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import discord
from discord.ext import commands

from bots.discordStuff.modLogs.sql import get_deleted_messages
from bots.discordStuff.sharedBanLists.sql import add_to_ban_list
from utils import DiscordUser


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def send_images(self, ctx: commands.Context, image_paths: list[str | None]):
        images_found = False
        images: list[discord.File] = []
        for path in image_paths:
            if path is not None and not images_found:
                images_found = True
                await ctx.send("Here are the images that were deleted:")
            if path is not None:
                images.append(discord.File(Path(path)))
        if images_found:
            for i in range(0, len(images), 10):
                await ctx.send(files=images[i : i + 10])

    @commands.command(name="deleted")
    async def get_deleted_messages(self, ctx: commands.Context, *, username: str = ""):
        assert ctx.guild
        member = ctx.guild.get_member_named(username)
        if member is None:
            await ctx.reply(f"Coult not find a discord member with the name {username}")
            return

        messages = await get_deleted_messages(DiscordUser(member.name, member.id))
        image_paths: list[str | None] = []
        list_to_send: list[str] = []
        to_send = ""

        for message in messages:
            deleted_at = message.time_deleted.strftime(r"%Y-%m-%d %H:%M") if message.time_deleted else None

            if deleted_at and len(to_send) + len(message.content) + len(f"\nDeleted at: {deleted_at}") >= 200:
                list_to_send.append(to_send)
                to_send = message.content + f"\nDeleted at: {deleted_at}"

                if message.attachment_paths is not None:
                    image_paths.extend(message.attachment_paths)
                else:
                    image_paths.append(message.attachment_paths)

                continue

            if deleted_at:
                to_send += message.content + f"\nDeleted at: {deleted_at}"
            else:
                to_send += message.content + "Unknown when deleted."

            if message.attachment_paths is not None:
                image_paths.extend(message.attachment_paths)
            else:
                image_paths.append(message.attachment_paths)

        if to_send != "":
            list_to_send.append(to_send)

        await ctx.send("Here is all that you requested")

        for message in to_send:
            await ctx.send(message)
        await self.send_images(ctx, image_paths=image_paths)

    async def get_entry(
        self, guild: discord.Guild, action: discord.AuditLogAction, member: discord.Member
    ) -> discord.AuditLogEntry | None:
        async for entry in guild.audit_logs(limit=100, action=action):
            try:
                assert entry.target
            except AssertionError:
                continue
            if entry.target.id == member.id:
                return entry

    async def __send_ban_list_request(self, guild: discord.Guild, member: discord.Member, reason: str = ""):
        channel = self.bot.get_channel(1516090780173860914)
        assert isinstance(channel, discord.TextChannel)

        def check(m: discord.Message):
            return (m.content == "!confirm" or m.content == "!deny") and (m.channel == channel)

        await channel.send(
            f"Ban Found. Do you want to add user {member.name} to the shared ban list?\n"
            "(Respond with `!confirm` to add to the shared ban list or `!deny` to not add it to the shared ban list. "
            "Please reply within 48 hours!)"
        )
        try:
            trial: discord.Message = await self.bot.wait_for("message", check=check, timeout=2 * 24 * 60 * 60)
        except asyncio.TimeoutError:
            await channel.send("Timed out. Will not add user to the banlist.")
            return
        if trial.content == "!deny":
            await channel.send(f"User {member.name} will not be added to the shared ban list")
            return
        try:
            await add_to_ban_list(member, reason)
        except Exception as e:
            await channel.send(f"There was an error adding user to the ban list {e}")
            return
        await channel.send(f"User {member.name} has been added to the shared ban list")
        return

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.Member):
        channel = self.bot.get_channel(1516090780173860914)
        assert isinstance(channel, discord.TextChannel)

        ban_log: discord.AuditLogEntry | None = await self.get_entry(guild, discord.AuditLogAction.ban, user)

        if ban_log is None:
            await asyncio.sleep(1)
            for _ in range(5):
                ban_log: discord.AuditLogEntry | None = await self.get_entry(guild, discord.AuditLogAction.ban, user)
            await asyncio.sleep(1)
        if ban_log is None:
            return

        await channel.send(
            f"{user.name} has been banned on discord. Here are the details:\n"
            f"Person banned: {user.name} {f'(nickname: {user.nick})' if user.nick else ''}\n"
            f"Moderator responsible: {ban_log.user.name if ban_log.user else 'unknown moderator'}\n"
            f"Reason: {ban_log.reason if ban_log.reason else 'No reason was given.'}"
        )

        await self.__send_ban_list_request(guild, user, ban_log.reason if ban_log.reason else "No reason was given")

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.Member):
        channel = self.bot.get_channel(1516090780173860914)
        assert isinstance(channel, discord.TextChannel)
        unban_log = await self.get_entry(guild, discord.AuditLogAction.unban, user)

        if unban_log is None:
            await asyncio.sleep(1)
            for _ in range(5):
                unban_log = await self.get_entry(guild, discord.AuditLogAction.unban, user)
                if unban_log is not None:
                    break
                await asyncio.sleep(1)
            if unban_log is None:
                return

        await channel.send(
            f"{user.name} has been unbanned on discord. Here are the details:\n"
            f"Person unbanned: {user.name} {f'(nickname: {user.nick})' if user.nick else ''}\n"
            f"Moderator responsible: {unban_log.user.name if unban_log.user else 'unknown moderator'}\n"
            f"Reason: {unban_log.reason if unban_log.reason else 'No reason was given.'}"
        )

    @commands.Cog.listener()
    async def on_member_remove(self, user: discord.Member):
        channel = self.bot.get_channel(1516090780173860914)
        assert isinstance(channel, discord.TextChannel)

        kick_log = await self.get_entry(user.guild, discord.AuditLogAction.unban, user)

        if kick_log is None:
            await asyncio.sleep(1)
            for _ in range(5):
                kick_log = await self.get_entry(user.guild, discord.AuditLogAction.unban, user)
                if kick_log is not None:
                    break
                await asyncio.sleep(1)
            if kick_log is None:
                return

        await channel.send(
            f"{user.name} has been kicked from the discord. Here are the details:\n"
            f"Person kicked: {user.name} {f'(nickname: {user.nick})' if user.nick else ''}\n"
            f"Moderator responsible: {kick_log.user.name if kick_log.user else 'unknown moderator'}\n"
            f"Reason: {kick_log.reason if kick_log.reason else 'No reason was given.'}"
        )

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):

        channel = self.bot.get_channel(1516090780173860914)
        assert isinstance(channel, discord.TextChannel)

        if before.timed_out_until is None and after.timed_out_until is None:
            return
        if before.timed_out_until is None and after.timed_out_until is not None:
            try:
                timeout_length = after.timed_out_until - datetime.now(tz=ZoneInfo("UTC"))
            except Exception as e:
                print(e)
                return
            await channel.send(
                f"{after.name}{f' (nickname: {after.nick})' if after.nick else ''} was timedout on discord for"
                f"{timeout_length.seconds} seconds ({timeout_length.seconds / 60} minutes)"
            )
        elif before.timed_out_until is not None and after.timed_out_until is None:
            await channel.send(
                f"{after.name}{f' (nickname: {after.nick})' if after.nick else ''} has had their timeout removed"
                " (either ended or was manually removed.)"
            )
