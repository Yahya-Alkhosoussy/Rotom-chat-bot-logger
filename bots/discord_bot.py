from datetime import datetime

import discord
from discord.ext import commands

from sql import get_bans, get_deleted_messages, get_timeouts, get_warnings
from utils import TwitchBan, TwitchMessage, TwitchUser, TwitchWarning


class DavexDiscordBot(commands.Bot):
    def __init__(self, intents: discord.Intents, **kwargs):
        super().__init__(command_prefix="!", intents=intents, **kwargs)
        self.twitch_moderation_loop: TwitchModerationLoop | None = None

    async def on_ready(self):
        assert self.user is not None
        self.twitch_moderation_loop = TwitchModerationLoop(self)
        print("")
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print("----------------------------------------------")

    async def on_message(self, message: discord.Message):
        await self.process_commands(message)


class TwitchModerationLoop:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.deleted_messages_channel = self.bot.get_channel(1516091306651287633)
        self.ban_timeout_warning_channel = self.bot.get_channel(1516090780173860914)
        self.guild = self.bot.get_guild(1017872414098608158)
        assert self.guild
        self.bot_maker = self.guild.get_member(604366329302220820)

    async def send_deleted_message(self, message: TwitchMessage):
        # The messaging logic
        try:
            assert isinstance(self.deleted_messages_channel, discord.TextChannel)
            assert isinstance(self.ban_timeout_warning_channel, discord.TextChannel)
            assert self.bot_maker
        except AssertionError as e:
            print(f"Got an error: {e}")
            return

        try:
            assert message.time_deleted is not None
            assert message.content is not None
        except AssertionError as e:
            await self.deleted_messages_channel.send(
                f"Got an error when trying to send a deleted message! Error: {e}. {self.bot_maker.mention} fix me!"
            )
            return

        time_deleted = message.time_deleted.strftime(r"%m-%d-%Y %H:%M:%S")
        message_to_send = f"""{message.author.display} has deleted a message at {time_deleted}.
Time the message was sent: {message.time_sent.strftime(r"%m-%d-%Y %H:%M:%S")}
Message content: {message.content}
Author's twitch login name: {message.author.login}
"""
        await self.deleted_messages_channel.send(message_to_send)
        return

    async def send_ban_noti(self, ban: TwitchBan):
        try:
            assert isinstance(self.deleted_messages_channel, discord.TextChannel)
            assert isinstance(self.ban_timeout_warning_channel, discord.TextChannel)
            assert self.bot_maker
        except AssertionError as e:
            print(f"Got an error: {e}")
            return

        message = f"""{ban.person.display} got banned on twitch. Here are the details:
Person banned: {ban.person.display}
Mod that banned them: {ban.mod_responsible}
Reason given for the ban: {ban.reason}
When they got banned: {ban.time_banned.strftime(r"%m-%d-%Y %H:%M:%S")}
"""
        await self.ban_timeout_warning_channel.send(message)

    async def send_timeout_noti(self, timeout: TwitchBan):
        try:
            assert isinstance(self.deleted_messages_channel, discord.TextChannel)
            assert isinstance(self.ban_timeout_warning_channel, discord.TextChannel)
            assert self.bot_maker
        except AssertionError as e:
            print(f"Got an error: {e}")
            return

        try:
            assert timeout.duration
        except AssertionError as e:
            await self.ban_timeout_warning_channel.send(f"{self.bot_maker.mention} I have reached an error! Error: {e}")
            return

        message = f"""{timeout.person.display} got a timeout on twitch. Here are the details:
Person timed out: {timeout.person.display}
Mod that timed them out: {timeout.mod_responsible}
Reason given for the timeout: {timeout.reason}
When they got timed out: {timeout.time_banned.strftime(r"%m-%d-%Y %H:%M:%S")}
How long the timeout is (seconds): {timeout.duration}
How long the timeout is (minutes): {timeout.duration / 60}
"""
        await self.ban_timeout_warning_channel.send(message)

    async def send_warning_noti(self, warning: TwitchWarning):
        try:
            assert isinstance(self.deleted_messages_channel, discord.TextChannel)
            assert isinstance(self.ban_timeout_warning_channel, discord.TextChannel)
            assert self.bot_maker
        except AssertionError as e:
            print(f"Got an error: {e}")
            return

        meessage = f"""{warning.person.display} got warned on twitch. Here are the details:
Person warned: {warning.person.display}
Reason for warning: {warning.reason}
Rules Cited: {warning.rules_cited}
When the warning happened: {warning.time_of_warning.strftime(r"%m-%d-%Y %H:%M:%S")}
"""
        await self.ban_timeout_warning_channel.send(meessage)

    async def warnings_requested(self, ctx: commands.Context):
        try:
            assert isinstance(self.ban_timeout_warning_channel, discord.TextChannel)
        except AssertionError as e:
            await ctx.reply(f"Got an error. Error: {e}")
            return

        warnings = await get_warnings()
        messages: list[str] = []
        message = "Here are the warnings: \n"
        for warning in warnings:
            to_add = f"""Person warned: {warning.person.display}
When warned: {warning.time_of_warning.strftime(r"%m-%d-%Y %H:%M:%S")}
Reason: {warning.reason}
Rules cited: {warning.rules_cited} \n"""
            if len(message) + len(to_add) >= 2000:
                messages.append(message)
                message = to_add
            else:
                message += to_add
                continue
        messages.append(message)

        if ctx.channel.id != self.ban_timeout_warning_channel.id:
            await ctx.reply("The messages are being sent in the appropriate channel")
            await self.ban_timeout_warning_channel.send(f"Warnings requested by {ctx.author.name}")
        else:
            await ctx.reply("Here you go!")
        for to_send in messages:
            await self.ban_timeout_warning_channel.send(to_send)

    async def bans_requested(self, ctx: commands.Context):
        try:
            assert isinstance(self.ban_timeout_warning_channel, discord.TextChannel)
        except AssertionError as e:
            await ctx.reply(f"Got an error. Error: {e}")
            return

        bans = await get_bans()
        messages: list[str] = []
        message = "Here are the bans: \n"
        for ban in bans:
            to_add = f"""Person banned: {ban.person.display}
When banned: {ban.time_banned.strftime(r"%m-%d-%Y %H:%M:%S")}
Reason: {ban.reason}
Mod responsible: {ban.mod_responsible}"""
            if len(message) + len(to_add) >= 2000:
                messages.append(message)
                message = to_add
            else:
                message += to_add
                continue
        messages.append(message)

        if ctx.channel.id != self.ban_timeout_warning_channel.id:
            await ctx.reply("The messages are being sent in the appropriate channel")
            await self.ban_timeout_warning_channel.send(f"Bans requested by {ctx.author.name}")
        else:
            await ctx.reply("Here you go!")
        for to_send in messages:
            await self.ban_timeout_warning_channel.send(to_send)

    async def timeouts_requested(self, ctx: commands.Context):
        try:
            assert isinstance(self.ban_timeout_warning_channel, discord.TextChannel)
        except AssertionError as e:
            await ctx.reply(f"Got an error. Error: {e}")
            return

        timeouts = await get_timeouts()
        messages: list[str] = []
        message = "Here are the timeouts: \n"
        for timeout in timeouts:
            to_add = f"""Person Banned: {timeout.person.display}
When warned: {timeout.time_banned.strftime(r"%m-%d-%Y %H:%M:%S")}
Reason: {timeout.reason}
Mod responsible: {timeout.mod_responsible}
Duration: {timeout.duration}"""
            if len(message) + len(to_add) >= 2000:
                messages.append(message)
                message = to_add
            else:
                message += to_add
                continue
        messages.append(message)

        if ctx.channel.id != self.ban_timeout_warning_channel.id:
            await ctx.reply("The messages are being sent in the appropriate channel")
            await self.ban_timeout_warning_channel.send(f"Timeouts requested by {ctx.author.name}")
        else:
            await ctx.reply("Here you go!")
        for to_send in messages:
            await self.ban_timeout_warning_channel.send(to_send)

    async def deleted_messages_requested(self, ctx: commands.Context):
        try:
            assert isinstance(self.deleted_messages_channel, discord.TextChannel)
        except AssertionError as e:
            await ctx.reply(f"Got an error. Error: {e}")
            return

        deleted_messages = await get_deleted_messages()
        messages: list[str] = []
        message = "Here are the messages deleted: \n"
        for deleted_message in deleted_messages:
            if deleted_message.time_deleted is None:
                continue
            to_add = f"""Author: {deleted_message.author.display}
When deleted: {deleted_message.time_deleted.strftime(r"%m-%d-%Y %H:%M:%S")}
When sent: {deleted_message.time_sent.strftime(r"%m-%d-%Y %H:%M:%S")}
Message content: {deleted_message.content}"""
            if len(message) + len(to_add) >= 2000:
                messages.append(message)
                message = to_add
            else:
                message += to_add
                continue
        messages.append(message)

        if ctx.channel.id != self.deleted_messages_channel.id:
            await ctx.reply("The messages are being sent in the appropriate channel")
            await self.deleted_messages_channel.send(f"Bans requested by {ctx.author.name}")
        else:
            await ctx.reply("Here you go!")
        for to_send in messages:
            await self.deleted_messages_channel.send(to_send)

    async def unban_noti(self, user: TwitchUser, moderator: TwitchUser, time: datetime):
        try:
            assert isinstance(self.deleted_messages_channel, discord.TextChannel)
            assert isinstance(self.ban_timeout_warning_channel, discord.TextChannel)
            assert self.bot_maker
        except AssertionError as e:
            print(f"Got an error: {e}")
            return

        time_str = time.strftime(r"%m-%d-%Y %H:%M:%S")
        await self.ban_timeout_warning_channel.send(f"User {user.display} got unbanned by {moderator.display} at {time_str}")
