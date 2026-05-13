from __future__ import annotations

import random
from typing import Optional

from ..models.enums import Role, WEREWOLF_ROLES

LYING_STRATEGIES = [
    "SEER_CLAIM",
    "INFO_FABRICATION",
    "DEEP_COVER",
    "INSTIGATE",
    "SILENT_DEEP",
    "ROLE_CLAIM",
    "SILENT_OMISSION",
    "SELF_KILL",
]

STRATEGY_HINTS = {
    "SEER_CLAIM": "你正在伪装预言家。发布虚假查验结果，给狼队友发金水或给怀疑对象发查杀。保持查验逻辑连贯！",
    "INFO_FABRICATION": "编造虚假的夜间信息或扭曲其他玩家的发言来混淆视听。",
    "DEEP_COVER": "攻击自己的狼队友来洗白身份，表现得像一个激进的好人。",
    "INSTIGATE": "煽动好人之间互相怀疑，把焦点从自己身上移开。",
    "SILENT_DEEP": "保持低调发言，少说少错。说一些无关紧要的话，随大流投票。",
    "ROLE_CLAIM": "声称自己是女巫/猎人/守卫等神职来混淆好人视线。注意：如果真神职已明，不要穿帮。",
    "SILENT_OMISSION": "刻意不提及某些对狼队不利的关键事实，用模糊语言带过。",
    "SELF_KILL": "建议狼队自刀骗取女巫解药。",
}


class LieLedgerManager:
    def __init__(self):
        self._claims: dict[int, list[dict]] = {}

    def add_claim(self, player_id: int, round_num: int, claim: dict) -> None:
        if player_id not in self._claims:
            self._claims[player_id] = []
        claim["round"] = round_num
        self._claims[player_id].append(claim)

    def check_contradiction(self, player_id: int, new_claim: dict) -> list[str]:
        contradictions = []
        for old in self._claims.get(player_id, []):
            if old.get("claimed_role") and new_claim.get("claimed_role"):
                if old["claimed_role"] != new_claim["claimed_role"]:
                    contradictions.append(
                        f"曾声称是{old['claimed_role']}，现在声称是{new_claim['claimed_role']}"
                    )
            if old.get("target") == new_claim.get("target"):
                old_result = old.get("claimed_result")
                new_result = new_claim.get("claimed_result")
                if old_result and new_result and old_result != new_result:
                    contradictions.append(
                        f"对{old['target']}号的判断前后矛盾：曾说是{old_result}，现在说是{new_result}"
                    )
        return contradictions

    def generate_reconciliation(self, contradictions: list[str]) -> str:
        if not contradictions:
            return ""
        lines = ["检测到以下矛盾需要圆谎："]
        for i, c in enumerate(contradictions, 1):
            lines.append(f"  {i}. {c}")
        lines.append("建议：声称之前的判断因为新信息而修正，或承认自己之前可能被骗了。")
        return "\n".join(lines)

    def get_claimed_role(self, player_id: int) -> Optional[Role]:
        for claim in reversed(self._claims.get(player_id, [])):
            if "claimed_role" in claim:
                try:
                    return Role(claim["claimed_role"])
                except ValueError:
                    return None
        return None


class LyingEngine:
    def __init__(self):
        self.ledger = LieLedgerManager()

    def select_strategy(self, role: Role, suspicion_on_self: float) -> str:
        if role not in WEREWOLF_ROLES and suspicion_on_self < 0.6:
            return "HONEST"

        if role in WEREWOLF_ROLES:
            weights = {
                "SEER_CLAIM": 0.25,
                "INFO_FABRICATION": 0.15,
                "DEEP_COVER": 0.15,
                "INSTIGATE": 0.15,
                "SILENT_DEEP": 0.15,
                "ROLE_CLAIM": 0.10,
                "SILENT_OMISSION": 0.03,
                "SELF_KILL": 0.02,
            }
            strategies = list(weights.keys())
            probs = list(weights.values())
            return random.choices(strategies, weights=probs, k=1)[0]

        strategies = ["SILENT_OMISSION", "INFO_FABRICATION", "SILENT_DEEP"]
        return random.choice(strategies)

    def get_strategy_hint(self, strategy: str) -> str:
        return STRATEGY_HINTS.get(strategy, "")

    def record_lie(self, player_id: int, round_num: int, action) -> None:
        if not action.lie_plan:
            return
        claim = {
            "type": action.lie_plan.get("type", ""),
            "claimed_role": action.lie_plan.get("claimed_role"),
            "target": action.skill_target,
            "claimed_result": action.lie_plan.get("claimed_result"),
        }
        self.ledger.add_claim(player_id, round_num, claim)

    def check_before_speak(self, player_id: int, new_claim: dict) -> str:
        contradictions = self.ledger.check_contradiction(player_id, new_claim)
        if contradictions:
            return self.ledger.generate_reconciliation(contradictions)
        return ""
