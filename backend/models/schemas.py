from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field

from .enums import Role, Faction, Phase


class Player(BaseModel):
    id: int
    name: str
    role: Role
    faction: Faction
    is_alive: bool = True
    can_vote: bool = True
    has_used_skill: bool = False
    skill_available: dict[str, bool] = Field(default_factory=dict)
    suspicion_score: dict[int, float] = Field(default_factory=dict)
    revealed_role: Optional[Role] = None
    guarded_last_round: bool = False

    def mark_dead(self) -> None:
        self.is_alive = False
        self.can_vote = False

    def mark_revealed(self) -> None:
        if self.role in (Role.IDIOT, Role.HUNTER):
            self.revealed_role = self.role


class GameAction(BaseModel):
    player_id: int
    phase: Phase
    thinking: str = ""
    speech: str = ""
    vote_target: Optional[int] = None
    skill_target: Optional[int] = None
    skill_name: Optional[str] = None
    lie_plan: Optional[dict] = None
    belief_state: Optional[dict[int, dict[str, float]]] = None


class GameEvent(BaseModel):
    round: int
    phase: Phase
    actor_id: int
    action: GameAction
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class NightResult(BaseModel):
    killed_player: Optional[int] = None
    saved_player: Optional[int] = None
    poisoned_player: Optional[int] = None
    guarded_player: Optional[int] = None
    checked_player: Optional[int] = None
    check_result: Optional[Faction] = None


class VoteResult(BaseModel):
    voter_id: int
    target_id: Optional[int]


class GameState(BaseModel):
    phase: Phase
    round: int = 0
    players: list[Player] = Field(default_factory=list)
    alive_werewolves: int = 0
    alive_villagers: int = 0
    night_results: list[NightResult] = Field(default_factory=list)
    sheriff_id: Optional[int] = None
    game_history: list[GameEvent] = Field(default_factory=list)
    winner: Optional[Faction] = None

    def get_alive_players(self) -> list[Player]:
        return [p for p in self.players if p.is_alive]

    def get_player(self, player_id: int) -> Optional[Player]:
        for p in self.players:
            if p.id == player_id:
                return p
        return None

    def get_alive_ids(self) -> list[int]:
        return [p.id for p in self.players if p.is_alive]

    def count_alive_by_faction(self, faction: Faction) -> int:
        return sum(1 for p in self.players if p.is_alive and p.faction == faction)

    def count_alive_by_role_type(self) -> tuple[int, int]:
        """Returns (alive_gods, alive_plain_villagers)."""
        from .enums import VILLAGER_ROLES, WEREWOLF_ROLES
        gods = sum(
            1 for p in self.players
            if p.is_alive and p.role not in VILLAGER_ROLES and p.role not in WEREWOLF_ROLES
        )
        plain = sum(1 for p in self.players if p.is_alive and p.role == Role.VILLAGER)
        return gods, plain


class ProviderKey(BaseModel):
    api_key: str = ""


class PlayerModelConfig(BaseModel):
    player_id: int
    provider: str = "deepseek"
    model: str = "deepseek-chat"
    temperature: float = 0.8
    system_prompt_extra: str = ""


class GameModelConfig(BaseModel):
    default_provider: str = "deepseek"
    default_model: str = "deepseek-chat"
    default_temperature: float = 0.8
    providers: dict[str, ProviderKey] = Field(default_factory=dict)
    players: list[PlayerModelConfig] = []
