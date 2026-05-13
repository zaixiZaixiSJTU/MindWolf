from typing import Optional
from ..models.enums import Role, Phase
from ..models.schemas import Player, GameState, BeliefState


class SkillSuggestions:

    @staticmethod
    def witch_antidote_suggestion(
        player: Player, state: GameState, killed_player: Optional[int],
    ) -> str:
        if not player.skill_available.get("antidote"):
            return "[系统] 解药已使用"
        if state.round == 1:
            return "[系统提示] 首夜建议使用解药救人，避免好人减员。"
        if killed_player is not None:
            return f"[系统提示] 解药可用，昨夜 {killed_player} 号被狼刀。建议根据局势判断是否救人。"
        return "[系统提示] 解药可用，无人被刀。"

    @staticmethod
    def witch_poison_suggestion(
        player: Player, state: GameState, belief_state: Optional[BeliefState] = None,
    ) -> str:
        if not player.skill_available.get("poison"):
            return "[系统] 毒药已使用"
        if belief_state is None:
            return "[系统提示] 毒药可用。建议毒杀明确的狼人，不要毒预言家。"
        candidates = []
        for pid, probs in belief_state.role_probabilities.items():
            if probs.get("WEREWOLF", 0) > 0.6:
                target = state.get_player(pid)
                if target and target.is_alive:
                    candidates.append(pid)
        if candidates:
            return f"[系统提示] 毒药可用。高概率狼人候选: {candidates}"
        return "[系统提示] 毒药可用。目前没有高置信度的狼人目标。"

    @staticmethod
    def seer_check_suggestion(
        player: Player, state: GameState, belief_state: Optional[BeliefState] = None,
    ) -> str:
        if belief_state is None:
            return "[系统提示] 建议查验发言矛盾或行为可疑的玩家。"
        candidates = []
        for pid, probs in belief_state.role_probabilities.items():
            confidence = max(probs.values()) if probs else 1.0
            if confidence < 0.5:
                target = state.get_player(pid)
                if target and target.is_alive:
                    candidates.append(pid)
        if candidates:
            return f"[系统提示] 建议查验不确定性高的玩家: {candidates}"
        return "[系统提示] 建议查验尚未确认身份的存活玩家。"
