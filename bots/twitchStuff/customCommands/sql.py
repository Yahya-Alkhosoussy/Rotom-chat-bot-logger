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
                active bool,
                streamer TEXT DEFAULT 'davex_gundyr'
            )
            """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS standard_commands
            (
                id INTEGER PRIMARY KEY,
                name TEXT,
                reply TEXT,
                user_level TEXT,
                active BOOL,
                streamer TEXT DEFAULT 'davex_gundyr'
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
                    TwitchCommand(
                        name=result[0], reply=result[1], level=CommandLevels.parse(result[2].lower()), active=result[3]
                    )
                )

    return commands


async def add_standard_command(command: TwitchCommand):
    async with connect(db_path) as conn:
        await conn.execute(
            "INSERT OR IGNORE INTO standard_commands (name, reply, user_level, active) VALUES (?, ?, ?, ?)",
            (command.name, command.reply, command.level.value, command.active),
        )
        await conn.commit()


async def get_standard_command_by_name(name: str) -> TwitchCommand:
    async with connect(db_path) as conn:
        cur = await conn.execute("SELECT reply, user_level, active FROM standard_commands WHERE name=?", (name,))
        result = await cur.fetchone()
        if result is None:
            raise LookupError(f"Could not find the standard command {name}")
        return TwitchCommand(name=name, reply=result[0], level=CommandLevels.parse(result[1].lower()), active=bool(result[2]))


run(init_db())
