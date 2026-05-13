from typing import Dict, Set, Callable, Optional

from ..models.enums import Role, Faction, Phase
from ..models.schemas import Player, GameState, GameAction


class RoleConfig:
    def __init__(
        self,
        role: Role,
        faction: Faction,
        night_action_order: int = 0,
        can_night_action: bool = False,
        night_phase: Optional[Phase] = None,
    ):
        self.role = role
        self.faction = faction
        self.night_action_order = night_action_order
        self.can_night_action = can_night_action
        self.night_phase = night_phase


BUILTIN_ROLES: dict[Role, RoleConfig] = {
    Role.WEREWOLF: RoleConfig(Role.WEREWOLF, Faction.WEREWOLF, 1, True, Phase.NIGHT_WEREWOLF),
    Role.VILLAGER: RoleConfig(Role.VILLAGER, Faction.VILLAGER, 0, False),
    Role.SEER: RoleConfig(Role.SEER, Faction.VILLAGER, 3, True, Phase.NIGHT_SEER),
    Role.WITCH: RoleConfig(Role.WITCH, Faction.VILLAGER, 2, True, Phase.NIGHT_WITCH),
    Role.HUNTER: RoleConfig(Role.HUNTER, Faction.VILLAGER, 4, True, Phase.NIGHT_HUNTER),
    Role.IDIOT: RoleConfig(Role.IDIOT, Faction.VILLAGER, 0, False),
    Role.GUARD: RoleConfig(Role.GUARD, Faction.VILLAGER, 0, True, Phase.NIGHT_WEREWOLF),
    Role.WHITE_WOLF: RoleConfig(Role.WHITE_WOLF, Faction.WEREWOLF, 1, True, Phase.NIGHT_WEREWOLF),
}


class RoleRegistry:
    def __init__(self):
        self._configs: dict[Role, RoleConfig] = dict(BUILTIN_ROLES)

    def get(self, role: Role) -> RoleConfig:
        if role not in self._configs:
            raise KeyError(f"Unknown role: {role}")
        return self._configs[role]

    def register(self, config: RoleConfig) -> None:
        self._configs[config.role] = config

    def get_night_roles(self) -> list[Role]:
        return sorted(
            [r for r, c in self._configs.items() if c.can_night_action],
            key=lambda r: self._configs[r].night_action_order,
        )

    def is_valid_action(self, player: Player, action: GameAction, state: GameState) -> tuple[bool, str]:
        """Validate action legality. Returns (valid, error_message)."""
        if not player.is_alive:
            return False, f"Player {player.id} is dead"

        cfg = self.get(player.role)

        if action.phase != state.phase:
            return False, f"Action phase {action.phase} != current phase {state.phase}"

        if action.phase.value.startswith("NIGHT_") and not cfg.can_night_action:
            return False, f"Role {player.role} cannot act at night"

        if action.vote_target is not None:
            if action.vote_target == player.id:
                return False, "Cannot vote for self"
            target = state.get_player(action.vote_target)
            if target is None or not target.is_alive:
                return False, f"Vote target {action.vote_target} is not a valid alive player"

        if action.skill_target is not None:
            if player.role == Role.WITCH:
                if action.skill_name not in ("antidote", "poison"):
                    return False, f"Invalid witch skill: {action.skill_name}"
                if action.skill_name == "antidote" and (
                    not player.skill_available.get("antidote", False)
                ):
                    return False, "Antidote already used"
                if action.skill_name == "poison" and (
                    not player.skill_available.get("poison", False)
                ):
                    return False, "Poison already used"

            if player.role == Role.GUARD and action.skill_target == player.id:
                return False, "Guard cannot protect self"

        return True, ""


role_registry = RoleRegistry()
