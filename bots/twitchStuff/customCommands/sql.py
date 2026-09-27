from asyncio import run
from pathlib import Path

from aiosqlite import connect

from utils import CommandLevels, TwitchCommand

db_path = Path("databases/custom commands.db")


async def init_db():
    async with connect(db_path) as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS commands
            (
                id INTEGER PRIMARY KEY,
                name TEXT,
                reply TEXT,
                user_level TEXT,
                active bool
            )
            """
        )
        await conn.commit()


async def get_commands() -> list[TwitchCommand]:
    async with connect(db_path) as conn:
        async with conn.execute("SELECT name, reply, user_level, active FROM commands") as cur:
            results = await cur.fetchall()
            commands: list[TwitchCommand] = []
            for result in results:
                commands.append(
                    TwitchCommand(name=result[0], reply=result[1], level=CommandLevels(result[2]), active=result[3])
                )

    return commands


run(init_db())
