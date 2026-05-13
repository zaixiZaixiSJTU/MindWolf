from typing import Optional

from ..models.enums import Faction, Role
from ..models.schemas import GameState

WEREWOLF_ROLES = {Role.WEREWOLF, Role.WHITE_WOLF}
GOD_ROLES = {Role.SEER, Role.WITCH, Role.HUNTER, Role.IDIOT, Role.GUARD}


class VictoryChecker:

    @staticmethod
    def check(state: GameState) -> Optional[Faction]:
        """Returns the winning faction, or None if game continues."""
        alive_wolves = sum(
            1 for p in state.players if p.is_alive and p.role in WEREWOLF_ROLES
        )
        alive_gods = sum(
            1 for p in state.players if p.is_alive and p.role in GOD_ROLES
        )
        alive_plain_villagers = sum(
            1 for p in state.players if p.is_alive and p.role == Role.VILLAGER
        )

        if alive_wolves == 0:
            return Faction.VILLAGER

        if alive_gods == 0 or alive_plain_villagers == 0:
            return Faction.WEREWOLF

        alive_villagers = alive_gods + alive_plain_villagers
        if alive_wolves >= alive_villagers:
            return Faction.WEREWOLF

        return None

    @staticmethod
    def get_status(state: GameState) -> dict:
        """Return human-readable status for prompt context."""
        alive_wolves = sum(
            1 for p in state.players if p.is_alive and p.role in WEREWOLF_ROLES
        )
        alive_gods = sum(
            1 for p in state.players if p.is_alive and p.role in GOD_ROLES
        )
        alive_vills = sum(
            1 for p in state.players if p.is_alive and p.role == Role.VILLAGER
        )
        return {
            "alive_werewolves": alive_wolves,
            "alive_gods": alive_gods,
            "alive_villagers": alive_vills,
        }
