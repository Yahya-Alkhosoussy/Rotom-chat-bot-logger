from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo

from pydantic import BaseModel


@dataclass()
class TwitchUser:
    display: str
    login: str
    id: str


@dataclass()
class TwitchMessage:
    id: str
    author: TwitchUser
    time_sent: datetime
    content: str | None = None
    time_deleted: datetime | None = None

    def __post_init__(self):
        self.time_sent = self.time_sent.astimezone(ZoneInfo("America/Chicago"))
        self.time_deleted = self.time_deleted.astimezone(ZoneInfo("America/Chicago")) if self.time_deleted else None


@dataclass()
class TwitchBan:
    person: TwitchUser
    reason: str
    mod_responsible: str
    time_banned: datetime
    duration: timedelta | float | None = None

    def __post_init__(self):
        self.time_banned = self.time_banned.astimezone(ZoneInfo("America/Chicago"))
        self.duration = self.duration.total_seconds() if isinstance(self.duration, timedelta) else self.duration


@dataclass()
class TwitchWarning:
    person: TwitchUser
    reason: str | None
    time_of_warning: datetime
    rules_cited: list[str] | str | None = None

    def __post_init__(self):

        self.reason = self.reason if self.reason else "No Reason Given"
        self.time_of_warning = self.time_of_warning.astimezone(ZoneInfo("America/Chicago"))

        if self.rules_cited is None:
            self.rules_cited = "No Rule Cited"
            return

        for rule in self.rules_cited:
            self.rules_cited += rule + "\n"


class CommandLevels(StrEnum):
    EVERYONE = "everyone"
    SUBSCRIBER = "subscriber"
    VIP = "vip"
    MOD = "moderator"
    STREAMER = "broadcaster"


class TwitchCommandFromWeb(BaseModel):
    name: str
    reply: str
    level: str
    active: bool


@dataclass()
class TwitchCommand:
    name: str
    reply: str
    level: CommandLevels
    active: bool

    def from_pydantic(self, command: TwitchCommandFromWeb):
        return TwitchCommand(
            command.name,
            command.reply,
            CommandLevels(command.level.lower()),
            command.active,
        )


@dataclass()
class DiscordUser:
    name: str
    id: int


@dataclass()
class DiscordMessage:
    author: DiscordUser
    content: str
    time_deleted: datetime | None
    attachment_paths: list[str | None] | None = None
