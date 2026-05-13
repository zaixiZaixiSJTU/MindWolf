from __future__ import annotations

import asyncio
import json
import logging
import random
from typing import Optional

from ..config import LLMConfig
from ..models.enums import Role, Phase, WEREWOLF_ROLES
from ..models.schemas import Player, GameState, GameAction
from .prompt_builder import PromptBuilder
from .xml_parser import parse_with_retry, AgentOutputParseError
from .lying_engine import LyingEngine

logger = logging.getLogger(__name__)

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


class BaseAgent:
    def __init__(self, player: Player, state: GameState, llm_config: LLMConfig | None = None):
        self.player = player
        self.state = state
        self.llm_config = llm_config or LLMConfig()
        self.prompt_builder = PromptBuilder()
        self.lying_engine = LyingEngine()
        self._conversation_history: list[dict] = []

    async def act(
        self, phase: Phase, alive_ids: list[int], memory_text: str = "", extra_info: dict | None = None,
    ) -> GameAction:
        system_prompt = self.prompt_builder.build_system_prompt(
            self.player, self.state, memory_text,
        )

        user_context = self._build_user_context(phase, alive_ids, extra_info)

        lying_strategy = self.lying_engine.select_strategy(
            self.player.role,
            self._get_self_suspicion(),
        )
        strategy_hint = self.lying_engine.get_strategy_hint(lying_strategy)

        full_prompt = (
            f"{system_prompt}\n\n"
            f"# 本轮策略提示\n{strategy_hint or '诚实发言，根据你的身份做出合理决策。'}\n\n"
            f"# 当前任务\n{user_context}\n\n"
            f"请输出你的<thinking>、<speak>、<vote>和<action>。"
        )

        if not HAS_HTTPX or self.llm_config.api_key.startswith("sk-xxx"):
            action = self._mock_response(phase, alive_ids, lying_strategy)
        else:
            action = await self._call_llm(full_prompt, phase)

        self._conversation_history.append({
            "role": "user", "content": user_context,
        })
        self._conversation_history.append({
            "role": "assistant",
            "content": f"<thinking>{action.thinking}</thinking>\n<speak>{action.speech}</speak>",
        })

        if lying_strategy != "HONEST":
            action.lie_plan = {"type": lying_strategy}
            self.lying_engine.record_lie(self.player.id, self.state.round, action)

        return action

    async def _call_llm(self, prompt: str, phase: Phase) -> GameAction:
        for attempt in range(self.llm_config.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.llm_config.timeout) as client:
                    resp = await client.post(
                        f"{self.llm_config.base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.llm_config.api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": self.llm_config.model,
                            "messages": [{"role": "user", "content": prompt}],
                            "temperature": self.llm_config.temperature,
                            "max_tokens": self.llm_config.max_tokens,
                        },
                    )
                    data = resp.json()
                    raw = data["choices"][0]["message"]["content"]
                    return parse_with_retry(raw, self.player.id, phase, max_retries=1)
            except (AgentOutputParseError, Exception) as e:
                logger.warning(f"LLM call attempt {attempt + 1} failed for player {self.player.id}: {e}")
                if attempt == self.llm_config.max_retries:
                    return self._mock_response(phase, [])

        return self._mock_response(phase, [])

    def _mock_response(self, phase: Phase, alive_ids: list[int], strategy: str = "HONEST") -> GameAction:
        role = self.player.role
        pid = self.player.id

        if phase == Phase.NIGHT_WEREWOLF and role in WEREWOLF_ROLES:
            candidates = [i for i in alive_ids if i != pid]
            target = random.choice(candidates) if candidates else None
            return GameAction(
                player_id=pid, phase=phase,
                thinking=f"狼人协商击杀。可选目标: {candidates}。选择{target}号。",
                speech="",
                skill_target=target,
                skill_name="kill",
            )

        if phase == Phase.NIGHT_SEER and role == Role.SEER:
            candidates = [i for i in alive_ids if i != pid]
            target = random.choice(candidates) if candidates else None
            return GameAction(
                player_id=pid, phase=phase,
                thinking=f"查验{target}号的身份。",
                speech="",
                skill_target=target,
                skill_name="check",
            )

        if phase == Phase.NIGHT_WITCH and role == Role.WITCH:
            action = GameAction(
                player_id=pid, phase=phase,
                thinking="作为女巫，判断夜间死者是否需要救助。",
                speech="",
            )
            if self.player.skill_available.get("antidote"):
                action.skill_name = "antidote"
                action.skill_target = None  # save whoever was killed
            return action

        if phase in (Phase.DAY_DISCUSS, Phase.DAY_VOTE):
            suspects = [i for i in alive_ids if i != pid]
            vote_target = random.choice(suspects) if suspects else None
            return GameAction(
                player_id=pid, phase=phase,
                thinking=f"分析当前局面，怀疑{vote_target}号。",
                speech=f"我是{pid}号，我认为我们需要仔细分析每个人的发言。我目前比较怀疑{vote_target}号。",
                vote_target=vote_target,
            )

        return GameAction(player_id=pid, phase=phase, thinking="等待游戏推进。")

    def _build_user_context(
        self, phase: Phase, alive_ids: list[int], extra_info: dict | None,
    ) -> str:
        context = f"当前阶段: {phase.value}\n存活玩家: {alive_ids}"
        if extra_info:
            context += f"\n额外信息: {json.dumps(extra_info, ensure_ascii=False)}"
        return context

    def _get_self_suspicion(self) -> float:
        scores = self.player.suspicion_score
        if not scores:
            return 0.0
        total = sum(scores.values())
        return total / len(scores) if scores else 0.0


class MockAgent(BaseAgent):
    """Agent that always uses mock responses (no LLM calls)."""
    async def act(
        self, phase: Phase, alive_ids: list[int], memory_text: str = "", extra_info: dict | None = None,
    ) -> GameAction:
        return self._mock_response(phase, alive_ids)
