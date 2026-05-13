import re
import uuid
from typing import List, Optional

from ..models.memory import MemoryUnit

STATEMENT_PATTERNS = [
    ("claim_role", re.compile(r"(我是|我为)\s*(\d+)?\s*号?\s*(预言家|女巫|猎人|守卫|村民|狼|白痴)"), 1.0),
    ("check_result", re.compile(r"(验|查)\s*(\d+)\s*(号|是)\s*(好人|狼|金水|查杀)"), 1.0),
    ("accuse", re.compile(r"(我认为|觉得|怀疑|听)\s*(\d+)\s*(号|是|像)\s*(狼|坏人|有问题)"), 0.8),
    ("defend", re.compile(r"(我觉得|认为|保)\s*(\d+)\s*(号|是)\s*(好人|金水|村民|真预言家)"), 0.6),
    ("retract", re.compile(r"(退水|我不是\s*(预言家|神|女巫|猎人|守卫))"), 0.9),
    ("self_claim", re.compile(r"(我是|我为)\s*(\d+)?\s*号?\s*(好人|村民|平民)"), 0.5),
]


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

                target_id = self._extract_target(m, event_type)
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
    def _extract_target(match: re.Match, event_type: str) -> Optional[int]:
        groups = match.groups()
        if event_type == "claim_role":
            for g in groups:
                if g and g.isdigit():
                    return int(g)
            return None
        if event_type in ("check_result", "accuse", "defend"):
            for g in groups:
                if g and g.isdigit():
                    return int(g)
        return None

    @staticmethod
    def _build_content(event_type: str, match: re.Match) -> str:
        raw = match.group(0).strip()
        type_labels = {
            "claim_role": "声称身份",
            "check_result": "查验结果",
            "accuse": "指控",
            "defend": "辩护",
            "retract": "退水",
            "self_claim": "自认",
        }
        label = type_labels.get(event_type, event_type)
        return f"[{label}] {raw}"
