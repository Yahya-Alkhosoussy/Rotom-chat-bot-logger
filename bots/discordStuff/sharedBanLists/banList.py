import asyncio

import discord
from discord.ext import commands, tasks

from bots.discordStuff.sharedBanLists.sql import get_banned_members
from bots.discordStuff.sharedBanLists.utils import BannedMember, Statuses


class BanListChecker:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.membersLookedAt: dict[BannedMember, Statuses] = {}
        self._loop: tasks.Loop | None = None

    def is_running(self) -> bool:
        return bool(self._loop)

    async def handle_ban_request(self, member: BannedMember, guild: discord.Guild):
        user = guild.get_member(member.id)

        if not isinstance(user, discord.Member):
            return

        channel = guild.get_channel(1516090780173860914)

        if not isinstance(channel, discord.TextChannel):
            return

        await channel.send(
            f"Ban Detected: {member.name} had been banned from {member.initial_server_ban} for {member.reason}\n"
            "Should I go ahead and ban them? Reply with `!confirm` to ban them or `!deny` to not ban them."
            " You have 2 days to reply"
        )

        def check(m: discord.Message):
            return (m.content == "!confirm" or m.content == "!deny") and (m.channel == channel)

        try:
            reply = await self.bot.wait_for("message", check=check, timeout=2 * 24 * 60 * 60)  # 2 days
        except asyncio.TimeoutError:
            await channel.send(f"I got no reply. {member.name} will not be banned.")
            return

        if reply.content == "!deny":
            await channel.send(f"Request denied successfully. {member.name} will not be banned.")
            return
        await channel.send(f"Request to ban {member.name} acknowledged. Starting ban process...")
        await user.ban(reason=member.reason)
        await channel.send(f"{member.name} successfully banned.")

    async def handle_unban_request(self, member: BannedMember, guild: discord.Guild):
        channel = guild.get_channel(1516090780173860914)

        if not isinstance(channel, discord.TextChannel):
            return

        await channel.send(
            f"User {member.name} was unbanned from the original server they were banned in. "
            "Should I attempt to unban them? (Within the next 2 days reply with `!confirm` to allow me to try to unban them"
            f" or `!deny` to keep them banned.) As a reminder the reason they were banned is: {member.reason}",
        )

        def check(m: discord.Message):
            return (m.content == "!confirm" or m.content == "!deny") and (m.channel == channel)

        try:
            reply = await self.bot.wait_for("message", check=check, timeout=2 * 24 * 60 * 60)  # 48 hours
        except asyncio.TimeoutError:
            await channel.send(f"Got no reply. {member.name} will not be unbanned.")
            return
        if reply.content == "!deny":
            await channel.send(f"Request denied successfully. {member.name} will not be unbanned.")
            return
        await channel.send(f"Request to ban {member.name} acknowledged. Starting unban process...")
        try:
            await guild.unban(member)
        except discord.NotFound as e:
            await channel.send(f"Unban failed. Could not find user {member.name}. Error: {str(e)}")
        except discord.Forbidden:
            await channel.send("Unban failed. I do not have the proper permissions.")
        except discord.HTTPException:
            await channel.send("Something went wrong while unbanning, could not complete.")

    def start(self):
        async def _tick():
            banned_members = await get_banned_members()
            for member in banned_members:
                if member in self.membersLookedAt and self.membersLookedAt[member] == member.status:
                    continue

                guild = self.bot.get_guild(1017872414098608158)
                if not guild:
                    return
                bans = [ban async for ban in guild.bans()]
                banned_user_ids = [ban.user.id for ban in bans]
                if member.status == Statuses.UNBANNED and member.id in banned_user_ids:
                    await self.handle_unban_request(member, guild)

                guild_member = await guild.query_members(user_ids=[member.id])
                # check if the person is in the guild
                # no use in sending a ban request if the person isn't in the guild to begin with.

                if member.id not in banned_user_ids and member.status == Statuses.BANNED and guild_member:
                    await self.handle_ban_request(member, guild)
                self.membersLookedAt[member] = member.status

        loop = tasks.loop(hours=8, reconnect=True)(_tick)

        @loop.before_loop
        async def _before():
            await self.bot.wait_until_ready()

        @loop.after_loop
        async def _after():
            pass

        @loop.error
        async def _error(something, error):
            pass

        loop.start()
