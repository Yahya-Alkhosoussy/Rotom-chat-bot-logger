from asyncio import run
from datetime import datetime, timedelta
from pathlib import Path

from aiosqlite import connect

from utils import DiscordMessage, DiscordUser

db_path = Path("databases/discord mod stuff.db")


async def init_db():
    async with connect(db_path) as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS deleted
            (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                user_id BIGINT NOT NULL,
                message_content TEXT,
                image_path TEXT,
                deleted_at TEXT
            )
            """
        )
        await conn.commit()


async def check_for_username_changes(user: DiscordUser):
    async with connect(db_path) as conn:
        async with conn.execute("SELECT username FROM deleted WHERE user_id=?", (user.id,)) as cur:
            result = await cur.fetchone()
            if result is None:
                return
            username = result[0]
            if username != user.name:
                await conn.execute("UPDATE deleted SET username=? WHERE user_id=?", (user.name, user.id))


async def add_deleted_message(user: DiscordUser, message: DiscordMessage):
    await check_for_username_changes(user)

    async with connect(db_path) as conn:
        time_deleted = message.time_deleted.strftime(r"%Y-%m-%d %H:%M") if message.time_deleted else None
        await conn.execute(
            "INSERT OR IGNORE INTO deleted (username, user_id, message_content, deleted_at) VALUES (?, ?, ?, ?)",
            (user.name, user.id, message.content, time_deleted),
        )
        if message.attachment_paths is None:
            await conn.commit()
            return

        for attachment_path in message.attachment_paths:
            await conn.execute(
                "INSERT OR IGNORE INTO deleted (username, user_id, deleted_at, image_path) VALUES (?, ?, ?, ?, ?)",
                (user.name, user.id, time_deleted, attachment_path),
            )
        await conn.commit()


async def get_deleted_messages(user: DiscordUser) -> list[DiscordMessage]:
    async with connect(db_path) as conn:
        async with conn.execute(
            "SELECT message_content, image_path, deleted_at FROM deleted WHERE user_id=?", (user.id,)
        ) as cur:
            results = await cur.fetchall()
            messages: list[DiscordMessage] = []
            for result in results:
                deleted_at: str | None = result[2]
                if deleted_at is None:
                    messages.append(
                        DiscordMessage(
                            user,
                            content=result[0],
                            time_deleted=None,
                            attachment_paths=result[1],
                        )
                    )
                    continue

                if datetime.now() - datetime.strptime(deleted_at, r"%Y-%m-%d %H:%M") <= timedelta(7):
                    messages.append(
                        DiscordMessage(
                            user,
                            content=result[0],
                            time_deleted=datetime.strptime(deleted_at, r"%Y-%m-%d %H:%M"),
                            attachment_paths=result[1],
                        )
                    )
            return messages


run(init_db())
