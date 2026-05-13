from typing import Optional

from ..models.enums import Role
from ..models.schemas import GameState, BeliefState


def judge_true_seer(
    state: GameState,
    belief_state: Optional[BeliefState] = None,
) -> Optional[int]:
    """Heuristically determine the most likely true Seer among claimants."""
    claimants: dict[int, list[dict]] = {}

    for event in state.game_history:
        if event.action.speech:
            if "我是预言家" in event.action.speech or "我为预言家" in event.action.speech:
                pid = event.actor_id
                if pid not in claimants:
                    claimants[pid] = []
                claimants[pid].append({
                    "round": event.round,
                    "speech": event.action.speech,
                })
            if "退水" in event.action.speech or "我不是预言家" in event.action.speech:
                claimants.pop(event.actor_id, None)

    alive_claimants = {
        pid: claims for pid, claims in claimants.items()
        if state.get_player(pid) and state.get_player(pid).is_alive
    }

    if not alive_claimants:
        return None
    if len(alive_claimants) == 1:
        return next(iter(alive_claimants))

    scores: dict[int, float] = {}
    for pid, claims in alive_claimants.items():
        score = 0.0
        for c in claims:
            speech = c.get("speech", "")
            if "金水" in speech:
                score += 1.0
            if "查杀" in speech:
                score += 0.8
            score += 0.2 * c.get("round", 1)
        scores[pid] = score

    if scores:
        return max(scores, key=scores.get)
    return None
