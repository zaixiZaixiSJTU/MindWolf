import re
import logging
from typing import Optional

from ..models.enums import Phase
from ..models.schemas import GameAction

logger = logging.getLogger(__name__)

THINKING_RE = re.compile(r"<thinking>(.*?)</thinking>", re.DOTALL)
SPEAK_RE = re.compile(r"<speak>(.*?)</speak>", re.DOTALL)
VOTE_RE = re.compile(r"<vote>(.*?)</vote>", re.DOTALL)
ACTION_RE = re.compile(r"<action>(.*?)</action>", re.DOTALL)

# Fallback patterns to extract vote intent from speech
SPEECH_VOTE_PATTERNS = [
    re.compile(r"投票[放逐票]?\s*(\d+)\s*号"),
    re.compile(r"建议[放逐票]?\s*(\d+)\s*号"),
    re.compile(r"今天[先]?[出放逐票]+\s*(\d+)\s*号"),
    re.compile(r"(?:我)?[投放逐票]+\s*(?:给)?\s*(\d+)\s*号"),
    re.compile(r"集中[票放逐]+\s*(\d+)\s*号"),
]

class AgentOutputParseError(Exception):
    pass


def _extract_first(pattern: re.Pattern, text: str) -> Optional[str]:
    m = pattern.search(text)
    if m:
        return m.group(1).strip()
    return None


def _extract_vote_from_speech(speech: str) -> Optional[int]:
    """Fallback: extract vote target from speech when <vote> tag is missing."""
    for pattern in SPEECH_VOTE_PATTERNS:
        m = pattern.search(speech)
        if m:
            try:
                return int(m.group(1))
            except (ValueError, IndexError):
                continue
    return None


def parse_agent_output(raw: str, player_id: int, phase: Phase) -> GameAction:
    thinking = _extract_first(THINKING_RE, raw) or ""
    speech = _extract_first(SPEAK_RE, raw) or ""
    vote_str = _extract_first(VOTE_RE, raw)
    action_str = _extract_first(ACTION_RE, raw)

    vote_target = None
    if vote_str and vote_str.upper() != "NONE":
        try:
            vote_target = int(re.search(r"\d+", vote_str).group())
        except (ValueError, AttributeError):
            pass

    # Fallback: extract vote from speech text if <vote> tag missing
    if vote_target is None and phase in (Phase.DAY_VOTE,):
        vote_target = _extract_vote_from_speech(speech)

    skill_target: Optional[int] = None
    skill_name: Optional[str] = None
    if action_str and action_str.upper() != "NONE":
        parts = action_str.split(":")
        if len(parts) >= 2:
            skill_name = parts[0].strip().lower()
            try:
                skill_target = int(re.search(r"\d+", parts[1]).group())
            except (ValueError, AttributeError):
                pass

    if not thinking and not speech:
        raise AgentOutputParseError(f"Empty output from player {player_id}")

    return GameAction(
        player_id=player_id,
        phase=phase,
        thinking=thinking,
        speech=speech,
        vote_target=vote_target,
        skill_target=skill_target,
        skill_name=skill_name,
    )


def parse_with_retry(raw: str, player_id: int, phase: Phase, max_retries: int = 2) -> GameAction:
    for attempt in range(max_retries + 1):
        try:
            return parse_agent_output(raw, player_id, phase)
        except AgentOutputParseError as e:
            if attempt == max_retries:
                raise
            logger.warning(f"Parse attempt {attempt + 1} failed for player {player_id}: {e}")
    raise AgentOutputParseError(f"Failed to parse after {max_retries} retries for player {player_id}")
