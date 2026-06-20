import asyncio
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from twitchAPI.chat import Chat, ChatCommand, ChatMessage, EventData
from twitchAPI.eventsub.websocket import EventSubWebsocket
from twitchAPI.helper import first
from twitchAPI.oauth import UserAuthenticationStorageHelper
from twitchAPI.object.eventsub import (
    ChannelBanEvent,
    ChannelChatMessageDeleteEvent,
    ChannelUnbanEvent,
    ChannelWarningSendEvent,
    StreamOnlineEvent,
)
from twitchAPI.twitch import Twitch
from twitchAPI.type import AuthScope, ChatEvent

from bots.discord_bot import DavexDiscordBot
from sql import add_ban, add_timeout, add_warning, remove_ban, save_deleted_message, save_message
from utils import TwitchBan, TwitchMessage, TwitchUser, TwitchWarning

TARGET_CHANNELS = ["davex_gundyr"]


class DavexTwitchBot:
    def __init__(
        self, app_id: str, app_secret: str, bot_scope: list[AuthScope], dav_scope: list[AuthScope], discord_bot: DavexDiscordBot
    ):
        self.app_id = app_id
        self.app_secret = app_secret
        self.bot_scope = bot_scope
        self.dav_scope = dav_scope

        self.dav_eventsub: EventSubWebsocket | None = None
        self.bot_eventsub: EventSubWebsocket | None = None
        self.dav_twitch: Twitch | None = None
        self.bot_twitch: Twitch | None = None
        self.chat: Chat | None = None
        self.davex_id: str | None = None
        self.bot_id: str | None = None
        self.discord_bot: DavexDiscordBot = discord_bot

    async def setup(self):
        self.dav_twitch = await Twitch(self.app_id, self.app_secret)
        dav_twitch_helper = UserAuthenticationStorageHelper(self.dav_twitch, self.dav_scope, Path("tokens/davex.json"))
        await dav_twitch_helper.bind()

        self.bot_twitch = await Twitch(self.app_id, self.app_secret)
        bot_twitch_helper = UserAuthenticationStorageHelper(self.bot_twitch, self.bot_scope, Path("tokens/bot.json"))
        await bot_twitch_helper.bind()

        user = await first(self.bot_twitch.get_users(logins=["davex_gundyr"]))
        if user is None:
            raise ValueError("Could not find user: davex_gundyr")
        self.davex_id = user.id

        user_2 = await first(self.bot_twitch.get_users(logins=["chatbot_rotom"]))
        if user_2 is None:
            raise ValueError("Could not find user: chatbot_rotom")
        self.bot_id = user_2.id

        main_loop = asyncio.get_event_loop()

        self.dav_eventsub = EventSubWebsocket(self.dav_twitch, callback_loop=main_loop)
        self.dav_eventsub.start()
        self.bot_eventsub = EventSubWebsocket(self.bot_twitch, callback_loop=main_loop)
        self.bot_eventsub.start()

        self.chat = await Chat(self.bot_twitch)

    async def on_message(self, message: ChatMessage):
        _message = TwitchMessage(
            message.id,
            TwitchUser(message.user.display_name, message.user.name, message.user.id),
            datetime.fromtimestamp(message.sent_timestamp / 1000, ZoneInfo("America/Chicago")),
            message_content=message.text,
        )
        await save_message(_message)
        return

    async def on_ready(self, ready_event: EventData):
        print("Bot is ready for work, joining channels")
        await ready_event.chat.join_room(TARGET_CHANNELS)
        print("bot has joined the channels")

    async def on_ban(self, ban: ChannelBanEvent):
        assert self.discord_bot.twitch_moderation_loop
        ban_event = ban.event
        if ban_event.is_permanent:
            _ban = TwitchBan(
                TwitchUser(ban_event.user_name, ban_event.user_login, ban_event.user_id),
                ban_event.reason,
                ban_event.moderator_user_name,
                ban_event.banned_at,
            )
            await add_ban(_ban)
            await self.discord_bot.twitch_moderation_loop.send_ban_noti(_ban)
            return
        if ban_event.ends_at is None:
            return
        timeout = TwitchBan(
            TwitchUser(ban_event.user_name, ban_event.user_login, ban_event.user_id),
            ban_event.reason,
            ban_event.moderator_user_name,
            ban_event.banned_at,
            ban_event.ends_at - ban_event.banned_at,
        )
        await add_timeout(timeout)
        await self.discord_bot.twitch_moderation_loop.send_timeout_noti(timeout)

    async def on_unban(self, unban: ChannelUnbanEvent):
        assert self.discord_bot.twitch_moderation_loop
        unban_event = unban.event
        user = TwitchUser(unban_event.user_name, unban_event.user_login, unban_event.user_id)
        moderator = TwitchUser(unban_event.moderator_user_name, unban_event.moderator_user_login, unban_event.moderator_user_id)
        time = datetime.now(tz=ZoneInfo("America/Chicago"))
        await self.discord_bot.twitch_moderation_loop.unban_noti(user, moderator, time)
        await remove_ban(user)

    async def close_bot(self):
        if self.dav_eventsub:
            await self.dav_eventsub.stop()
        if self.chat:
            self.chat.stop()
        if self.dav_twitch:
            await self.dav_twitch.close()
        if self.bot_twitch:
            await self.bot_twitch.close()

    async def on_message_delete(self, DeletedEvent: ChannelChatMessageDeleteEvent):
        assert self.discord_bot.twitch_moderation_loop
        event = DeletedEvent.event
        message = TwitchMessage(
            event.message_id,
            TwitchUser(event.target_user_name, event.target_user_login, event.target_user_id),
            DeletedEvent.metadata.message_timestamp,
            datetime.now(),
        )
        await save_deleted_message(message)
        await self.discord_bot.twitch_moderation_loop.send_deleted_message(message)

    async def on_warning(self, warning_event: ChannelWarningSendEvent):
        assert self.discord_bot.twitch_moderation_loop
        event = warning_event.event
        warning = TwitchWarning(
            TwitchUser(event.user_name, event.user_login, event.user_id), event.reason, event.chat_rules_cited, datetime.now()
        )
        await add_warning(warning)
        await self.discord_bot.twitch_moderation_loop.send_warning_noti(warning)

    async def on_stream_start(self, stream_event: StreamOnlineEvent):
        assert self.bot_id
        assert self.bot_twitch

        event_data = stream_event.event
        message = "!intro"
        await self.bot_twitch.send_chat_message(
            broadcaster_id=event_data.broadcaster_user_id, sender_id=self.bot_id, message=message
        )

    async def appear_command(self, ChatCommand: ChatCommand):
        assert self.bot_twitch
        assert self.davex_id
        assert self.bot_id
        message = f"{ChatCommand.user.name}, I have appeared in the Graveyard! Thank you kind soul."
        await self.bot_twitch.send_chat_message(broadcaster_id=self.davex_id, sender_id=self.bot_id, message=message)

    async def run(self):
        try:
            await self.setup()
            assert self.chat, "Chat instance is None"
            assert self.bot_twitch, "Bot twitch instance is None"
            assert self.dav_twitch, "Dav twitch instance is None"
            assert self.dav_eventsub, "Event sub instance is None"
            assert self.bot_eventsub, "Event sub for the bot is None"
            assert self.davex_id, "Davexs ID is still None"
            assert self.bot_id, "Bots ID is still None"

            self.chat.register_event(ChatEvent.READY, self.on_ready)
            self.chat.register_event(ChatEvent.MESSAGE, self.on_message)
            self.chat.register_command("appear", self.appear_command)

            await self.dav_eventsub.listen_channel_ban(broadcaster_user_id=self.davex_id, callback=self.on_ban)
            await self.dav_eventsub.listen_channel_unban(broadcaster_user_id=self.davex_id, callback=self.on_unban)
            await self.bot_eventsub.listen_channel_warning_send(
                broadcaster_user_id=self.davex_id, moderator_user_id=self.bot_id, callback=self.on_warning
            )
            await self.bot_eventsub.listen_channel_chat_message_delete(
                broadcaster_user_id=self.davex_id, user_id=self.bot_id, callback=self.on_message_delete
            )
            await self.dav_eventsub.listen_stream_online(broadcaster_user_id=self.davex_id, callback=self.on_stream_start)

            self.chat.start()

            await asyncio.Event().wait()
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await self.close_bot()


# bot = DavexBot(APP_ID, APP_SECRET, BOT_SCOPES, DAVEX_SCOPES)
# asyncio.run(bot.run())
