import logging
from typing import Dict

from ..models.memory import BeliefState, MemoryUnit

logger = logging.getLogger(__name__)

# Role detection keywords in Chinese content
ROLE_KEYWORDS: dict[str, list[str]] = {
    "WEREWOLF": ["狼", "查杀", "坏人"],
    "VILLAGER": ["村民", "平民", "好人", "金水"],
    "SEER": ["预言家"],
    "WITCH": ["女巫"],
    "HUNTER": ["猎人"],
    "IDIOT": ["白痴"],
    "GUARD": ["守卫"],
}


def _detect_role(content: str) -> str | None:
    """Detect which role is being claimed/mentioned in content text."""
    for role, keywords in ROLE_KEYWORDS.items():
        for kw in keywords:
            if kw in content:
                return role
    return None


class BeliefUpdater:
    @staticmethod
    def update(belief_state: BeliefState, memory_pool, player_role=None) -> None:
        """Update belief_state based on active memory units. Mutates in place."""
        for unit in memory_pool.get_active_memories():
            target = unit.target_id
            if target is None or target == belief_state.player_id:
                continue

            if target not in belief_state.role_probabilities:
                belief_state.role_probabilities[target] = {
                    r: 1.0 / 6 for r in ["WEREWOLF", "VILLAGER", "SEER", "WITCH", "HUNTER", "IDIOT"]
                }

            delta = 0.08 * unit.current_weight

            if unit.event_type == "claim_role":
                detected = _detect_role(unit.content)
                if detected:
                    belief_state.role_probabilities[target][detected] = min(
                        0.85,
                        belief_state.role_probabilities[target].get(detected, 0) + 0.35,
                    )
                    # Reduce probability of competing roles
                    for r in belief_state.role_probabilities[target]:
                        if r != detected:
                            belief_state.role_probabilities[target][r] = max(
                                0.02, belief_state.role_probabilities[target].get(r, 0.16) - 0.05,
                            )

            elif unit.event_type == "check_result":
                detected = _detect_role(unit.content)
                if detected:
                    # Check results are strong evidence
                    belief_state.role_probabilities[target][detected] = 0.90
                    for r in belief_state.role_probabilities[target]:
                        if r != detected:
                            belief_state.role_probabilities[target][r] = max(
                                0.01, (1.0 - 0.90) / 5,
                            )

            elif unit.event_type == "accuse":
                belief_state.role_probabilities[target]["WEREWOLF"] = min(
                    0.90, belief_state.role_probabilities[target].get("WEREWOLF", 0.16) + delta
                )

            elif unit.event_type == "defend":
                belief_state.role_probabilities[target]["VILLAGER"] = min(
                    0.85, belief_state.role_probabilities[target].get("VILLAGER", 0.16) + delta * 1.5
                )

            elif unit.event_type == "retract":
                # Lower all non-VILLAGER probabilities
                for r in ("SEER", "WITCH", "HUNTER", "IDIOT", "WEREWOLF"):
                    if r in belief_state.role_probabilities[target]:
                        belief_state.role_probabilities[target][r] = max(
                            0.05, belief_state.role_probabilities[target][r] - 0.2,
                        )

        belief_state.normalize()
        belief_state.confidence = min(0.95, belief_state.confidence + 0.05)
        n = len(memory_pool.get_active_memories())
        belief_state.update_reason = f"Updated from {n} active memories"

    @staticmethod
    def init_from_role(
        player_id: int, known_roles: dict[int, str], alive_ids: list[int],
    ) -> BeliefState:
        """Initialize belief with known roles (e.g., werewolves know each other)."""
        belief = BeliefState(player_id=player_id)
        all_roles = ["WEREWOLF", "VILLAGER", "SEER", "WITCH", "HUNTER", "IDIOT"]
        n = len(all_roles)
        for pid in alive_ids:
            if pid == player_id:
                continue
            if pid in known_roles:
                role = known_roles[pid]
                belief.role_probabilities[pid] = {
                    r: (0.85 if r == role else 0.03) for r in all_roles
                }
            else:
                belief.role_probabilities[pid] = {r: 1.0 / n for r in all_roles}
        belief.normalize()
        return belief
