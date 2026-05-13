from enum import Enum


class Faction(str, Enum):
    VILLAGER = "VILLAGER"
    WEREWOLF = "WEREWOLF"
    THIRD_PARTY = "THIRD_PARTY"


class Role(str, Enum):
    WEREWOLF = "WEREWOLF"
    VILLAGER = "VILLAGER"
    SEER = "SEER"
    WITCH = "WITCH"
    HUNTER = "HUNTER"
    IDIOT = "IDIOT"
    GUARD = "GUARD"
    WHITE_WOLF = "WHITE_WOLF"


class Phase(str, Enum):
    PRE_GAME = "PRE_GAME"
    NIGHT_WEREWOLF = "NIGHT_WEREWOLF"
    NIGHT_SEER = "NIGHT_SEER"
    NIGHT_WITCH = "NIGHT_WITCH"
    NIGHT_HUNTER = "NIGHT_HUNTER"
    DAY_ANNOUNCE = "DAY_ANNOUNCE"
    DAY_DISCUSS = "DAY_DISCUSS"
    DAY_VOTE = "DAY_VOTE"
    GAME_OVER = "GAME_OVER"


WEREWOLF_ROLES = {Role.WEREWOLF, Role.WHITE_WOLF}
VILLAGER_ROLES = {Role.VILLAGER}
SEER_ROLES = {Role.SEER}
WITCH_ROLES = {Role.WITCH}
HUNTER_ROLES = {Role.HUNTER}
NIGHT_ACTIVE_ROLES = {Role.WEREWOLF, Role.WHITE_WOLF, Role.SEER, Role.WITCH, Role.GUARD}


def get_faction(role: Role) -> Faction:
    if role in WEREWOLF_ROLES:
        return Faction.WEREWOLF
    return Faction.VILLAGER


PHASE_ORDER: list[Phase] = [
    Phase.PRE_GAME,
    Phase.NIGHT_WEREWOLF,
    Phase.NIGHT_SEER,
    Phase.NIGHT_WITCH,
    Phase.NIGHT_HUNTER,
    Phase.DAY_ANNOUNCE,
    Phase.DAY_DISCUSS,
    Phase.DAY_VOTE,
]
