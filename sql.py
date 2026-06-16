import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import aiosqlite

from utils import TwitchBan, TwitchMessage, TwitchUser, TwitchWarning

db_dir = Path("databases")
db_path = db_dir / "mod_stuff.db"


async def init_db():

    if not db_dir.exists():
        db_dir.mkdir()
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(
            """CREATE TABLE IF NOT EXISTS bans
            (
                id INTEGER PRIMARY KEY,
                person_banned_display TEXT,
                person_banned_login TEXT,
                person_banned_id TEXT,
                reason TEXT,
                mod_responsible TEXT,
                time TEXT
            )"""
        )

        await conn.execute(
            """CREATE TABLE IF NOT EXISTS timeout
            (
                id INTEGER PRIMARY KEY,
                person_timedout_display TEXT,
                person_timedout_login TEXT,
                person_timedout_id TEXT,
                reason TEXT,
                mod_responsible TEXT,
                time TEXT,
                duration INTEGER
            )"""
        )

        await conn.execute(
            """CREATE TABLE IF NOT EXISTS warnings
            (
                id INTEGER PRIMARY KEY,
                person_warned_display TEXT,
                person_warned_login TEXT,
                person_warned_id TEXT,
                reason TEXT,
                rules_cited TEXT,
                time TEXT
            )"""
        )

        await conn.execute(
            """CREATE TABLE IF NOT EXISTS deleted_messages
            (
                id INTEGER PRIMARY KEY,
                message_id TEXT UNIQUE,
                message_content TEXT,
                author_display TEXT,
                author_login TEXT,
                author_id TEXT,
                when_sent TEXT,
                when_deleted TEXT
            )"""
        )

        await conn.execute(
            """CREATE TABLE IF NOT EXISTS messages_sent
            (
                message_id TEXT PRIMARY KEY,
                message_content TEXT,
                author_display TEXT,
                author_login TEXT,
                author_id TEXT,
                when_sent TEXT
            )"""
        )

        await conn.commit()


asyncio.run(init_db())


async def save_message(message: TwitchMessage):
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(
            """INSERT OR IGNORE INTO messages_sent
                (message_id, message_content, author_display, author_login, author_id, when_sent) VALUES
                (?, ?, ?, ?, ?, ?)""",
            (
                message.id,
                message.content,
                message.author.display,
                message.author.login,
                message.author.id,
                message.time_sent.strftime(r"%m-%d-%Y %H:%M:%S"),
            ),
        )
        await conn.commit()


async def save_deleted_message(message: TwitchMessage):
    async with aiosqlite.connect(db_path) as conn:
        async with conn.execute("SELECT message_content FROM messages_sent WHERE message_id=?", (message.id,)) as cur:
            result = await cur.fetchone()
            if result is None:
                raise Exception("Message content not found!")
            message.content = result[0]
        if message.time_deleted is None:
            return None

        await conn.execute(
            """INSERT OR IGNORE INTO deleted_messages
            (message_id, message_content, author_display, author_login, author_id, when_sent, when_deleted)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                message.id,
                message.content,
                message.author.display,
                message.author.login,
                message.author.id,
                message.time_sent,
                message.time_deleted.strftime(r"%m-%d-%Y %H:%M:%S"),
            ),
        )
        await conn.commit()


async def add_warning(warning: TwitchWarning):
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(
            """INSERT OR IGNORE INTO warnings
            (person_warned_display, person_warned_login, person_warned_id, reason, rules_cited, time) VALUES (?, ?, ?, ?, ?, ?)""",
            (
                warning.person.display,
                warning.person.login,
                warning.person.id,
                warning.reason,
                warning.rules_cited,
                warning.time_of_warning.strftime(r"%m-%d-%Y %H:%M:%S"),
            ),
        )
        await conn.commit()


async def add_timeout(timeout: TwitchBan):
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(
            """INSERT OR IGNORE INTO timeout
            (person_timedout_display, person_timedout_login, person_timedout_id, reason, mod_responsible, time, duration) VALUES
            (?, ?, ?, ?, ?, ?, ?)""",
            (
                timeout.person.display,
                timeout.person.login,
                timeout.person.id,
                timeout.reason,
                timeout.mod_responsible,
                timeout.time_banned.strftime(r"%m-%d-%Y %H:%M:%S"),
                timeout.duration,
            ),
        )
        await conn.commit()


async def add_ban(ban: TwitchBan):
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(
            """INSERT OR IGNORE INTO bans
            (person_banned_display, person_banned_login, person_banned_id, reason, mod_responsible, time) VALUES (?, ?, ?, ?, ?, ?)""",
            (
                ban.person.display,
                ban.person.login,
                ban.person.display,
                ban.reason,
                ban.mod_responsible,
                ban.time_banned.strftime(r"%m-%d-%Y %H:%M:%S"),
            ),
        )
        await conn.commit()


async def get_deleted_messages() -> list[TwitchMessage]:
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT * FROM deleted_messages ORDER BY id DESC") as cur:
            results = await cur.fetchall()
            messages: list[TwitchMessage] = []
            for result in results:
                if datetime.now().astimezone(ZoneInfo("America/Chicago")) - datetime.strptime(
                    result["when_deleted"], r"%m-%d-%Y %H:%M:%S"
                ).replace(tzinfo=ZoneInfo("America/Chicago")) > timedelta(30):
                    break
                message = TwitchMessage(
                    result["message_id"],
                    TwitchUser(result["author_display"], result["author_login"], result["author_id"]),
                    datetime.strptime(result["when_sent"], r"%m-%d-%Y %H:%M:%S"),
                    datetime.strptime(result["when_deleted"], r"%m-%d-%Y %H:%M:%S"),
                    result["message_content"],
                )
                messages.append(message)
    return messages


async def get_warnings() -> list[TwitchWarning]:
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT * FROM warnings ORDER BY id DESC") as cur:
            results = await cur.fetchall()
            warns: list[TwitchWarning] = []
            for result in results:
                time = datetime.strptime(result["time"], r"%m-%d-%Y %H:%M:%S").replace(tzinfo=ZoneInfo("America/Chicago"))
                if datetime.now().astimezone(ZoneInfo("America/Chicago")) - time > timedelta(30):
                    break
                rules: str = result["rules_cited"]

                warn = TwitchWarning(
                    TwitchUser(result["person_warned_display"], result["person_warned_login"], result["person_warned_id"]),
                    result["reason"],
                    rules.splitlines(),
                    time,
                )
                warns.append(warn)
    return warns


async def get_timeouts() -> list[TwitchBan]:
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT * FROM timeout ORDER BY id DESC") as cur:
            results = await cur.fetchall()
            bans: list[TwitchBan] = []
            for result in results:
                time = datetime.strptime(result["time"], r"%m-%d-%Y %H:%M:%S").replace(tzinfo=ZoneInfo("America/Chicago"))
                if datetime.now().astimezone(ZoneInfo("America/Chicago")) - time > timedelta(30):
                    break
                ban = TwitchBan(
                    TwitchUser(
                        result["person_timedout_display"], result["person_timedout_login"], result["person_timedout_id"]
                    ),
                    result["reason"],
                    result["mod_responsible"],
                    time,
                    timedelta(seconds=float(result["duration"])),
                )
                bans.append(ban)
    return bans


async def get_bans() -> list[TwitchBan]:
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT * FROM bans ORDER BY id DESC") as cur:
            results = await cur.fetchall()
            bans: list[TwitchBan] = []
            for result in results:
                time = datetime.strptime(result["time"], r"%m-%d-%Y %H:%M:%S").replace(tzinfo=ZoneInfo("America/Chicago"))
                if datetime.now().astimezone(ZoneInfo("America/Chicago")) - time > timedelta(30):
                    break
                ban = TwitchBan(
                    TwitchUser(result["person_banned_display"], result["person_banned_login"], result["person_banned_id"]),
                    result["reason"],
                    result["mod_responsible"],
                    datetime.strptime(result["time"], r"%m-%d-%Y %H:%M:%S"),
                )
                bans.append(ban)
    return bans


async def remove_ban(user: TwitchUser):
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute("DELETE FROM bans WHERE person_banned_id=?", (user.id,))
        await conn.commit()
