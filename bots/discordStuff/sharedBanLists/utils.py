from dataclasses import dataclass
from enum import StrEnum


class Servers(StrEnum):
    SHARKOCALYPSE = "shark's cult"
    DAVEX = "davex's graveyard"
    SHARKTROCITY = "The nocturnal cavern"


class Statuses(StrEnum):
    BANNED = "banned"
    UNBANNED = "unbanned"


@dataclass()
class BannedMember:
    name: str
    id: int
    reason: str
    status: Statuses
    initial_server_ban: Servers
