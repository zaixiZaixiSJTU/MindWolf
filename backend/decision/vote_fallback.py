import random
from typing import Optional

from ..models.schemas import Player, GameState, BeliefState


class VoteFallback:
    @staticmethod
    def fallback_if_invalid(
        vote_target: Optional[int],
        player_id: int,
        state: GameState,
        belief_state: Optional[BeliefState] = None,
    ) -> Optional[int]:
        alive_ids = state.get_alive_ids()

        if vote_target is not None and vote_target in alive_ids and vote_target != player_id:
            return vote_target

        return VoteFallback._weighted_vote(player_id, state, belief_state)

    @staticmethod
    def _weighted_vote(
        player_id: int, state: GameState, belief_state: Optional[BeliefState],
    ) -> Optional[int]:
        alive_ids = [i for i in state.get_alive_ids() if i != player_id]
        if not alive_ids:
            return None

        if belief_state:
            scores: dict[int, float] = {}
            for pid in alive_ids:
                probs = belief_state.role_probabilities.get(pid, {})
                wolf_prob = probs.get("WEREWOLF", 0.3)
                scores[pid] = wolf_prob
            if scores:
                return max(scores, key=scores.get)

        player = state.get_player(player_id)
        if player and player.suspicion_score:
            valid = {k: v for k, v in player.suspicion_score.items() if k in alive_ids}
            if valid:
                return max(valid, key=valid.get)

        return random.choice(alive_ids)


class VoteTally:
    @staticmethod
    def count(votes: dict[int, int]) -> dict[int, int]:
        tally: dict[int, int] = {}
        for target in votes.values():
            tally[target] = tally.get(target, 0) + 1
        return tally

    @staticmethod
    def resolve(tally: dict[int, int]) -> Optional[int]:
        if not tally:
            return None
        max_votes = max(tally.values())
        top = [pid for pid, c in tally.items() if c == max_votes]
        if len(top) == 1:
            return top[0]
        return None
