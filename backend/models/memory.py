from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class MemoryUnit(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    round: int
    speaker_id: int
    target_id: Optional[int] = None
    event_type: str = ""
    content: str = ""
    base_weight: float = 0.5
    current_weight: float = 0.5
    is_contradicted: bool = False


class MemoryPool:
    def __init__(self):
        self.units: list[MemoryUnit] = []

    def add_unit(self, unit: MemoryUnit) -> None:
        unit.current_weight = unit.base_weight
        self.units.append(unit)

    def decay_all(self, current_round: int, decay_factor: float = 0.85) -> None:
        for u in self.units:
            age = current_round - u.round
            if age >= 0:
                u.current_weight = u.base_weight * (decay_factor ** age)
            if u.is_contradicted:
                u.current_weight = 0.0

    def mark_contradiction(self, event_id: str) -> None:
        for u in self.units:
            if u.id == event_id:
                u.is_contradicted = True
                u.current_weight = 0.0

    def get_active_memories(self, min_weight: float = 0.15) -> list[MemoryUnit]:
        return sorted(
            [u for u in self.units if u.current_weight >= min_weight and not u.is_contradicted],
            key=lambda u: u.current_weight,
            reverse=True,
        )

    def get_by_speaker(self, speaker_id: int) -> list[MemoryUnit]:
        return [u for u in self.units if u.speaker_id == speaker_id]

    def format_for_prompt(self, min_weight: float = 0.2) -> str:
        active = self.get_active_memories(min_weight)
        if not active:
            return "[无重要记忆]"
        lines = ["[重要记忆]"]
        for u in active:
            lines.append(f"- 第{u.round}轮，{u.speaker_id}号：{u.content} (权重{u.current_weight:.2f})")
        return "\n".join(lines)


class BeliefState(BaseModel):
    player_id: int
    round: int = 0
    role_probabilities: dict[int, dict[str, float]] = Field(default_factory=dict)
    confidence: float = 0.5
    update_reason: str = ""

    def init_uniform(self, alive_ids: list[int], roles: list[str]) -> None:
        base = {r: 1.0 / len(roles) for r in roles}
        for pid in alive_ids:
            if pid != self.player_id:
                self.role_probabilities[pid] = base.copy()

    def normalize(self) -> None:
        for pid in self.role_probabilities:
            total = sum(self.role_probabilities[pid].values())
            if total > 0:
                self.role_probabilities[pid] = {
                    k: v / total for k, v in self.role_probabilities[pid].items()
                }


class TheoryOfMind(BaseModel):
    perceived_by_others: dict[int, dict[str, float]] = Field(default_factory=dict)
    second_order_beliefs: dict[int, dict[int, dict[str, float]]] = Field(default_factory=dict)
