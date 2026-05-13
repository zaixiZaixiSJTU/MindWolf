import logging
from typing import Dict

from ..models.memory import BeliefState, MemoryUnit

logger = logging.getLogger(__name__)


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
                    "WEREWOLF": 1/6, "VILLAGER": 1/6,
                    "SEER": 1/6, "WITCH": 1/6,
                    "HUNTER": 1/6, "IDIOT": 1/6,
                }

            delta = 0.05 * unit.current_weight

            if unit.event_type == "accuse":
                belief_state.role_probabilities[target]["WEREWOLF"] = min(
                    0.95, belief_state.role_probabilities[target].get("WEREWOLF", 0) + delta
                )
            elif unit.event_type == "check_result":
                if any(w in unit.content for w in ("狼", "查杀")):
                    belief_state.role_probabilities[target]["WEREWOLF"] = 0.95
                elif any(g in unit.content for g in ("好人", "金水")):
                    belief_state.role_probabilities[target]["VILLAGER"] = 0.90
            elif unit.event_type == "defend":
                belief_state.role_probabilities[target]["VILLAGER"] = min(
                    0.90, belief_state.role_probabilities[target].get("VILLAGER", 0) + delta * 2
                )
            elif unit.event_type == "claim_role":
                for r in ("SEER", "WITCH", "HUNTER", "IDIOT"):
                    if r in unit.content:
                        belief_state.role_probabilities[target][r] = min(
                            0.80, belief_state.role_probabilities[target].get(r, 0) + 0.3
                        )

        belief_state.normalize()
        belief_state.confidence = min(0.95, belief_state.confidence + 0.1)
        belief_state.update_reason = f"Updated from {len(memory_pool.get_active_memories())} active memories"

    @staticmethod
    def init_from_role(player_id: int, known_roles: dict[int, str], alive_ids: list[int]) -> BeliefState:
        """Initialize belief with known roles (e.g., werewolves know each other)."""
        belief = BeliefState(player_id=player_id)
        all_roles = ["WEREWOLF", "VILLAGER", "SEER", "WITCH", "HUNTER", "IDIOT"]
        for pid in alive_ids:
            if pid == player_id:
                continue
            if pid in known_roles:
                role = known_roles[pid]
                belief.role_probabilities[pid] = {
                    r: (0.9 if r == role else 0.02) for r in all_roles
                }
            else:
                belief.role_probabilities[pid] = {
                    r: 1.0 / len(all_roles) for r in all_roles
                }
        belief.normalize()
        return belief
