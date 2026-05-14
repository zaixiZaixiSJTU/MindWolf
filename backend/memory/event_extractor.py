import re
import uuid
from typing import List, Optional

from ..models.memory import MemoryUnit

STATEMENT_PATTERNS = [
    # (event_type, regex, base_weight)
    (
        "claim_role",
        re.compile(
            r"(?:我是|我为|我跳|我(?:就|可)是|身份[是为])\s*"
            r"(?:(\d+)\s*号\s*)?"
            r"(预言家|女巫|猎人|守卫|村民|狼人?|白痴|丘比特|混血儿)",
        ),
        1.0,
    ),
    (
        "check_result",
        re.compile(
            r"(?:查验|验|查)\s*(?:了|过|的)?\s*"
            r"(\d+)\s*号?\s*(?:玩家|是|为)?\s*"
            r"(?:结果(?:是|为)\s*)?"
            r"(好人|狼人?|金水|查杀|坏人)",
        ),
        1.0,
    ),
    (
        "accuse",
        re.compile(
            r"(?:我认为|我觉得|我怀疑|怀疑|听|感觉|看)\s*"
            r"(\d+)\s*号?\s*"
            r"(?:玩家|发言)?\s*"
            r"(?:很|非常|有点|比较|最)?\s*"
            r"(?:可疑|像是?狼|是狼|有问题|不对劲|像坏人|带节奏|奇怪|有问题)",
        ),
        0.8,
    ),
    (
        "defend",
        re.compile(
            r"(?:我认为|我觉得|我?相信|保)\s*"
            r"(\d+)\s*号?\s*"
            r"(?:玩家|发言|是|为)?\s*"
            r"(?:好人|金水|村民|真预言家|真女巫|真猎人|可信|没问题|好人面)",
        ),
        0.7,
    ),
    (
        "retract",
        re.compile(
            r"(?:退水|我不是\s*(?:预言家|神|女巫|猎人|守卫)|"
            r"(?:收回|撤销)\s*(?:之前|前面|刚才)?\s*(?:的)?\s*(?:发言|身份|跳|声称))",
        ),
        0.9,
    ),
    (
        "self_claim",
        re.compile(
            r"(?:我是|我为)\s*"
            r"(?:(\d+)\s*号\s*)?"
            r"(?:一个|普通|平民)?\s*"
            r"(?:好人|村民|平民|普通村民)",
        ),
        0.5,
    ),
    (
        "vote_intent",
        re.compile(
            r"(?:投票|建议|今天|出|放逐|票)\s*"
            r"(?:放逐|出|投|票)?\s*"
            r"(\d+)\s*号",
        ),
        0.4,
    ),
]

# Role name to uppercase key mapping
ROLE_ALIASES = {
    "预言家": "SEER", "女巫": "WITCH", "猎人": "HUNTER",
    "守卫": "GUARD", "村民": "VILLAGER", "平民": "VILLAGER",
    "狼": "WEREWOLF", "狼人": "WEREWOLF", "白痴": "IDIOT",
    "好人": "VILLAGER", "坏人": "WEREWOLF",
    "金水": "VILLAGER", "查杀": "WEREWOLF",
}


def _role_label(role_name: str) -> str:
    return ROLE_ALIASES.get(role_name, role_name.upper())


class EventExtractor:
    def __init__(self, patterns: list | None = None):
        self.patterns = patterns or STATEMENT_PATTERNS

    def extract(
        self, speaker_id: int, round_num: int, text: str,
    ) -> list[MemoryUnit]:
        units: list[MemoryUnit] = []
        seen_spans: set[tuple[int, int]] = set()

        for event_type, pattern, base_weight in self.patterns:
            for m in pattern.finditer(text):
                span = (m.start(), m.end())
                if span in seen_spans:
                    continue
                seen_spans.add(span)

                target_id = self._extract_target(m, event_type, speaker_id)
                content = self._build_content(event_type, m)

                unit = MemoryUnit(
                    id=uuid.uuid4().hex[:8],
                    round=round_num,
                    speaker_id=speaker_id,
                    target_id=target_id,
                    event_type=event_type,
                    content=content,
                    base_weight=base_weight,
                    current_weight=base_weight,
                )
                units.append(unit)

        return units

    @staticmethod
    def _extract_target(
        match: re.Match, event_type: str, speaker_id: int,
    ) -> Optional[int]:
        """Extract target player ID from matched groups.
        For self-claims (claim_role, self_claim), falls back to speaker_id.
        """
        groups = match.groups()
        # First try: find a numeric group
        for g in groups:
            if g and g.isdigit():
                return int(g)
        # Fallback: self-claims target the speaker
        if event_type in ("claim_role", "self_claim"):
            return speaker_id
        return None

    @staticmethod
    def _build_content(event_type: str, match: re.Match) -> str:
        raw = match.group(0).strip()
        groups = match.groups()

        if event_type == "claim_role":
            role = groups[-1] if groups[-1] else "?"
            return f"声称是{role}"

        if event_type == "check_result":
            pid = next((g for g in groups if g and g.isdigit()), "?")
            result = groups[-1] if groups[-1] else "?"
            return f"查验{pid}号为{result}"

        if event_type == "accuse":
            pid = next((g for g in groups if g and g.isdigit()), "?")
            return f"指控{pid}号为狼人"

        if event_type == "defend":
            pid = next((g for g in groups if g and g.isdigit()), "?")
            return f"认为{pid}号是好人"

        if event_type == "retract":
            return "退水"

        if event_type == "self_claim":
            return "声称自己是平民"

        if event_type == "vote_intent":
            pid = next((g for g in groups if g and g.isdigit()), "?")
            return f"意图投票{pid}号"

        return raw[:60]
