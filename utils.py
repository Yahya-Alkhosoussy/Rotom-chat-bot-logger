from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


class TwitchUser:
    def __init__(self, display: str, login: str, id: str):
        self.display = display
        self.login = login
        self.id = id


class TwitchMessage:
    def __init__(
        self,
        message_id: str,
        author: TwitchUser,
        when_sent: datetime,
        when_deleted: datetime | None = None,
        message_content: str | None = None,
    ):
        self.id = message_id
        self.content = message_content
        self.author = author
        self.time_sent = when_sent.astimezone(ZoneInfo("America/Chicago"))
        self.time_deleted = when_deleted.astimezone(ZoneInfo("America/Chicago")) if when_deleted else None


class TwitchBan:
    def __init__(
        self,
        banned_person: TwitchUser,
        reason_for_ban: str,
        mod_responsible: str,
        time_banned: datetime,
        duration: timedelta | None = None,
    ):
        self.person = banned_person
        self.reason = reason_for_ban
        self.mod_responsible = mod_responsible
        self.time_banned = time_banned.astimezone(ZoneInfo("America/Chicago"))
        self.duration = duration.total_seconds() if duration else None


class TwitchWarning:
    def __init__(
        self,
        person_warned: TwitchUser,
        reason_for_warning: str | None,
        rules_cited: list[str] | None,
        time_of_warning: datetime,
    ):
        self.person = person_warned
        self.reason = reason_for_warning if reason_for_warning else "No Reason given"
        self.rules_cited: str = ""
        self.time_of_warning = time_of_warning.astimezone(ZoneInfo("America/Chicago"))

        if rules_cited is None:
            self.rules_cited = "No Rule Cited"
            return

        for rule in rules_cited:
            self.rules_cited += rule + "\n"
