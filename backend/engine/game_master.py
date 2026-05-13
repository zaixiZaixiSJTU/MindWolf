from __future__ import annotations

import asyncio
import json
import logging
import os
import random
from datetime import datetime
from typing import Optional

from ..models.enums import Role, Faction, Phase, get_faction, WEREWOLF_ROLES
from ..models.schemas import (
    Player, GameAction, GameEvent, NightResult, GameState, VoteResult,
    GameModelConfig, PlayerModelConfig,
)
from ..models.memory import MemoryPool, BeliefState
from ..memory.event_extractor import EventExtractor
from .role_registry import role_registry
from .victory_checker import VictoryChecker
from ..config import GameConfig, LLMConfig, generate_game_id

logger = logging.getLogger(__name__)

ROLE_POOL_12 = [
    Role.WEREWOLF, Role.WEREWOLF, Role.WEREWOLF, Role.WEREWOLF,
    Role.SEER, Role.WITCH, Role.HUNTER, Role.IDIOT,
    Role.VILLAGER, Role.VILLAGER, Role.VILLAGER, Role.VILLAGER,
]


class GameMaster:
    def __init__(self, config: GameConfig | None = None):
        self.config = config or GameConfig()
        self.state = GameState(phase=Phase.PRE_GAME)
        self.memory_pool = MemoryPool()
        self.belief_states: dict[int, BeliefState] = {}
        self._subscribers: list[asyncio.Queue[dict]] = []
        self._action_queues: dict[int, asyncio.Queue[GameAction]] = {}
        self.game_id: str = ""
        self._human_player_ids: set[int] = set()
        self._llm_call_log: list[dict] = []
        self._model_config: GameModelConfig | None = None
        self._provider_keys: dict[str, str] = {}
        self._agent_cache: dict[int, object] = {}
        self._last_transcript: list[str] = []
        self._extractor = EventExtractor()

    def init_game(
        self,
        agent_names: list[str] | None = None,
        human_ids: list[int] | None = None,
    ) -> None:
        n = self.config.player_count
        if agent_names is None:
            agent_names = [f"Player_{i}" for i in range(1, n + 1)]
        roles = random.sample(ROLE_POOL_12, n)
        random.shuffle(roles)

        self.game_id = generate_game_id()
        self.state = GameState(phase=Phase.PRE_GAME, round=0)
        self.memory_pool = MemoryPool()
        self.belief_states.clear()
        self._subscribers = []
        self._action_queues = {}
        self._human_player_ids = set(human_ids or [])
        self._llm_call_log = []
        self._agent_cache = {}

        for i, (name, role) in enumerate(zip(agent_names, roles), start=1):
            faction = get_faction(role)
            skill_available = {}
            if role == Role.WITCH:
                skill_available = {"antidote": True, "poison": True}
            elif role == Role.HUNTER:
                skill_available = {"shoot": True}
            elif role == Role.GUARD:
                skill_available = {"guard": True}

            is_human = i in self._human_player_ids
            player = Player(
                id=i, name=name, role=role, faction=faction,
                skill_available=skill_available,
            )
            self.state.players.append(player)
            self._action_queues[i] = asyncio.Queue()
            belief = BeliefState(player_id=i)
            belief.init_uniform(
                list(range(1, n + 1)),
                ["WEREWOLF", "VILLAGER", "SEER", "WITCH", "HUNTER", "IDIOT"],
            )
            self.belief_states[i] = belief

        self.state.alive_werewolves = sum(
            1 for p in self.state.players if p.role in WEREWOLF_ROLES
        )
        self.state.alive_villagers = self.config.player_count - self.state.alive_werewolves

        self._write_meta()

    def is_human(self, player_id: int) -> bool:
        return player_id in self._human_player_ids

    def set_model_config(self, cfg: GameModelConfig) -> None:
        self._model_config = cfg
        self._provider_keys = {}
        for provider_key, pk in cfg.providers.items():
            if pk.api_key:
                self._provider_keys[provider_key] = pk.api_key

    def get_player_model(self, player_id: int) -> dict:
        if self._model_config:
            for pc in self._model_config.players:
                if pc.player_id == player_id:
                    d = pc.model_dump()
                    d["api_key"] = self._provider_keys.get(pc.provider, "")
                    return d
        return {"model": "mock", "temperature": 0.8, "base_url": "", "api_key": ""}

    def get_provider_base_url(self, provider: str) -> str:
        known = {
            "deepseek": "https://api.deepseek.com/v1",
            "openai": "https://api.openai.com/v1",
            "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "doubao": "https://ark.cn-beijing.volces.com/api/v3",
        }
        return known.get(provider, "")

    async def run(self) -> GameState:
        logger.info(f"Game {self.game_id} started. Human players: {self._human_player_ids}")
        await self._broadcast({"type": "PHASE_CHANGE", "payload": {
            "phase": self.state.phase.value, "round": self.state.round,
            "game_id": self.game_id,
        }})

        while self.state.phase != Phase.GAME_OVER:
            await self._run_phase()

        winner = VictoryChecker.check(self.state)
        self.state.winner = winner
        await self._broadcast({"type": "GAME_OVER", "payload": {
            "winner": winner.value if winner else None,
            "game_id": self.game_id,
            "players": [
                {"id": p.id, "name": p.name, "role": p.role.value, "faction": p.faction.value}
                for p in self.state.players
            ],
        }})
        self._write_logs()
        logger.info(f"Game {self.game_id} over. Winner: {winner}")
        return self.state

    async def _run_phase(self) -> None:
        phase = self.state.phase
        if phase == Phase.PRE_GAME:
            self.state.phase = Phase.NIGHT_WEREWOLF
            self.state.round = 1
            await self._notify_roles()
        elif phase == Phase.NIGHT_WEREWOLF:
            await self._night_werewolf()
        elif phase == Phase.NIGHT_SEER:
            await self._night_seer()
        elif phase == Phase.NIGHT_WITCH:
            await self._night_witch()
        elif phase == Phase.NIGHT_HUNTER:
            self.state.phase = Phase.DAY_ANNOUNCE
        elif phase == Phase.DAY_ANNOUNCE:
            await self._day_announce()
        elif phase == Phase.DAY_DISCUSS:
            await self._day_discuss()
        elif phase == Phase.DAY_VOTE:
            await self._day_vote()

        if self.state.phase != Phase.GAME_OVER:
            self._check_victory()

    def _check_victory(self) -> None:
        winner = VictoryChecker.check(self.state)
        if winner is not None:
            self.state.winner = winner
            self.state.phase = Phase.GAME_OVER

    async def _notify_roles(self) -> None:
        for player in self.state.players:
            extra = {}
            is_human = self.is_human(player.id)
            if player.role in WEREWOLF_ROLES:
                wolves = [p.id for p in self.state.players
                          if p.role in WEREWOLF_ROLES and p.id != player.id]
                extra["wolf_teammates"] = wolves
            await self._broadcast({
                "type": "ROLE_ASSIGN",
                "payload": {
                    "player_id": player.id,
                    "role": player.role.value,
                    "faction": player.faction.value,
                    "is_human": is_human,
                    **extra,
                },
            })

    # ---- Night phases ----

    async def _night_werewolf(self) -> None:
        wolves = [p for p in self.state.players if p.is_alive and p.role in WEREWOLF_ROLES]
        alive_ids = self.state.get_alive_ids()
        wolf_team_ids = [w.id for w in wolves]

        await self._broadcast({
            "type": "PHASE_CHANGE",
            "payload": {"phase": self.state.phase.value, "round": self.state.round},
        })

        actions: list[GameAction] = []
        for wolf in wolves:
            # Wolves must not kill teammates — exclude wolf_ids from targets
            valid_targets = [i for i in alive_ids if i not in wolf_team_ids]
            extra = {
                "wolf_teammates": [i for i in wolf_team_ids if i != wolf.id],
                "valid_targets": valid_targets,
                "hint": "你是狼人。夜间与队友协商击杀目标。不能刀自己的狼队友。",
            }
            action = await self._request_action(wolf.id, alive_ids, extra_info=extra)
            actions.append(action)
            self._record_event(wolf.id, action)

        kill_target = self._resolve_wolf_kill(actions)
        self._last_wolf_kill = kill_target
        self.state.phase = Phase.NIGHT_SEER

    async def _night_seer(self) -> None:
        seers = [p for p in self.state.players if p.is_alive and p.role == Role.SEER]
        alive_ids = self.state.get_alive_ids()
        for seer in seers:
            action = await self._request_action(seer.id, alive_ids)
            self._record_event(seer.id, action)
            if action.skill_target:
                target = self.state.get_player(action.skill_target)
                result = target.faction if target else None
                self._last_seer_result = (action.skill_target, result)
        self.state.phase = Phase.NIGHT_WITCH

    async def _night_witch(self) -> None:
        witches = [p for p in self.state.players if p.is_alive and p.role == Role.WITCH]
        alive_ids = self.state.get_alive_ids()
        killed = self._last_wolf_kill

        for witch in witches:
            action = await self._request_action(
                witch.id, alive_ids,
                extra_info={
                    "night_killed": killed,
                    "your_skills": witch.skill_available,
                },
            )
            self._record_event(witch.id, action)

            if action.skill_name == "antidote" and witch.skill_available.get("antidote"):
                witch.skill_available["antidote"] = False
                self._last_witch_save = killed
            elif action.skill_name == "poison" and witch.skill_available.get("poison"):
                witch.skill_available["poison"] = False
                self._last_witch_poison = action.skill_target

        self.state.phase = Phase.NIGHT_HUNTER

    async def _day_announce(self) -> None:
        killed = self._last_wolf_kill
        saved = getattr(self, "_last_witch_save", None)
        poisoned = getattr(self, "_last_witch_poison", None)

        deaths: list[tuple[int, str]] = []

        if killed and killed != saved:
            deaths.append((killed, "wolf_kill"))
        if poisoned:
            deaths.append((poisoned, "poison"))

        for pid, cause in deaths:
            player = self.state.get_player(pid)
            if player:
                player.mark_dead()
                if cause == "poison" and player.role == Role.HUNTER:
                    player.skill_available["shoot"] = False

        self._update_alive_counts()

        night_result = NightResult(
            killed_player=killed,
            saved_player=saved,
            poisoned_player=poisoned,
        )
        self.state.night_results.append(night_result)

        self._last_wolf_kill = None
        self._last_witch_save = None
        self._last_witch_poison = None

        await self._broadcast({
            "type": "NIGHT_RESULT",
            "payload": {
                "deaths": deaths,
                "death_info": self._format_death_info(deaths),
            },
        })

        self._check_victory()
        if self.state.phase == Phase.GAME_OVER:
            return

        self.state.phase = Phase.DAY_DISCUSS

    async def _day_discuss(self) -> None:
        alive = self.state.get_alive_players()
        alive_ids = [p.id for p in alive]

        await self._broadcast({
            "type": "PHASE_CHANGE",
            "payload": {"phase": self.state.phase.value, "round": self.state.round},
        })

        transcript: list[str] = []
        for player in alive:
            context = self._build_discuss_context(player, transcript)
            action = await self._request_action(player.id, alive_ids, extra_info=context)
            self._record_event(player.id, action)
            transcript.append(f"Player {player.id}: {action.speech}")
            if action.speech:
                units = self._extractor.extract(player.id, self.state.round, action.speech)
                for u in units:
                    self.memory_pool.add_unit(u)
            await self._broadcast({
                "type": "PLAYER_SPEECH",
                "payload": {
                    "player_id": player.id,
                    "speech": action.speech,
                    "is_human": self.is_human(player.id),
                },
            })

        self._last_transcript = transcript
        self.state.phase = Phase.DAY_VOTE

    async def _day_vote(self) -> None:
        alive = self.state.get_alive_players()
        alive_ids = [p.id for p in alive]

        await self._broadcast({
            "type": "PHASE_CHANGE",
            "payload": {"phase": "DAY_VOTE", "round": self.state.round},
        })

        votes: dict[int, int] = {}
        discuss_ctx = self._build_discuss_context(alive[0]) if alive else {}
        discuss_ctx["round_transcript"] = "\n".join(self._last_transcript)
        for player in alive:
            action = await self._request_action(player.id, alive_ids, extra_info=discuss_ctx)
            self._record_event(player.id, action)
            if action.vote_target and action.vote_target in alive_ids:
                votes[player.id] = action.vote_target

        eliminated = self._tally_votes(votes)
        if eliminated is not None:
            victim = self.state.get_player(eliminated)
            if victim:
                if victim.role == Role.IDIOT:
                    victim.can_vote = False
                    victim.revealed_role = Role.IDIOT
                else:
                    victim.mark_dead()
                    if victim.role == Role.HUNTER and victim.skill_available.get("shoot"):
                        hunter_action = await self._request_action(
                            victim.id, alive_ids,
                            extra_info={"death_cause": "vote", "can_shoot": True},
                        )
                        if hunter_action.skill_target and hunter_action.skill_name == "shoot":
                            target = self.state.get_player(hunter_action.skill_target)
                            if target:
                                target.mark_dead()

            self._update_alive_counts()

        self._check_victory()
        if self.state.phase == Phase.GAME_OVER:
            return

        self.state.round += 1
        self.state.phase = Phase.NIGHT_WEREWOLF

        self.memory_pool.decay_all(self.state.round, self.config.decay_factor)
        from ..memory.belief_updater import BeliefUpdater
        for pid in self.belief_states:
            BeliefUpdater.update(self.belief_states[pid], self.memory_pool)

    # ---- Helpers ----

    async def _request_action(
        self, player_id: int, alive_ids: list[int], extra_info: dict | None = None,
    ) -> GameAction:
        is_human_flag = self.is_human(player_id)

        await self._broadcast({
            "type": "ACTION_REQUIRED",
            "payload": {
                "player_id": player_id,
                "phase": self.state.phase.value,
                "round": self.state.round,
                "alive_players": alive_ids,
                "extra": extra_info or {},
                "is_human": is_human_flag,
            },
        })

        if is_human_flag:
            try:
                return await asyncio.wait_for(
                    self._action_queues[player_id].get(), timeout=300.0,
                )
            except asyncio.TimeoutError:
                logger.warning(f"Human player {player_id} timed out, using fallback")

        return await self._agent_action(player_id, alive_ids, extra_info)

    async def _agent_action(
        self, player_id: int, alive_ids: list[int], extra_info: dict | None = None,
    ) -> GameAction:
        """Drive AI agent via BaseAgent — auto-detects mock vs real LLM."""
        import time as _time
        from ..agent.base_agent import BaseAgent

        player = self.state.get_player(player_id)
        if player is None:
            return GameAction(player_id=player_id, phase=self.state.phase)

        # Build LLM config from model config
        if player_id not in self._agent_cache:
            model_cfg = self.get_player_model(player_id)
            api_key = model_cfg.get("api_key", "")
            base_url = model_cfg.get("base_url", "")
            if not base_url or base_url == "":
                base_url = self.get_provider_base_url(model_cfg.get("provider", "mock"))

            llm_cfg = LLMConfig(
                api_key=api_key if api_key else "sk-xxx",
                base_url=base_url if base_url else "https://api.deepseek.com/v1",
                model=model_cfg.get("model", "deepseek-chat"),
                temperature=model_cfg.get("temperature", 0.8),
                timeout=30.0,
                max_retries=2,
            )
            self._agent_cache[player_id] = BaseAgent(player, self.state, llm_cfg)

        agent = self._agent_cache[player_id]
        # Update agent's reference to current game state
        agent.player = player
        agent.state = self.state

        memory_text = self.memory_pool.format_for_prompt()

        t0 = _time.time()
        try:
            action = await asyncio.wait_for(
                agent.act(
                    self.state.phase, alive_ids,
                    memory_text=memory_text,
                    extra_info=extra_info,
                ),
                timeout=45.0,
            )
        except asyncio.TimeoutError:
            logger.warning(f"AI agent {player_id} timed out, using mock fallback")
            action = agent._mock_response(self.state.phase, alive_ids)

        # Broadcast thinking stream to spectators
        if action.thinking:
            await self._broadcast({
                "type": "THINKING_CHUNK",
                "payload": {
                    "player_id": player_id,
                    "chunk": action.thinking,
                    "done": True,
                },
            })

        elapsed = _time.time() - t0
        model_name = self.get_player_model(player_id).get("model", "mock")
        thinking_preview = action.thinking[:100] if action.thinking else ""
        logger.info(f"Agent {player_id}({player.role.value}) [{model_name}] → "
                    f"{len(action.thinking)}chars thinking, {len(action.speech)}chars speech "
                    f"({elapsed:.1f}s)")

        self.log_llm_call(player_id,
            prompt=f"[phase={self.state.phase.value} round={self.state.round}]",
            response=thinking_preview,
            elapsed=elapsed,
            model=model_name,
        )

        return action

    def subscribe(self) -> asyncio.Queue[dict]:
        q: asyncio.Queue[dict] = asyncio.Queue()
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[dict]) -> None:
        try:
            self._subscribers.remove(q)
        except ValueError:
            pass

    async def _broadcast(self, msg: dict) -> None:
        for q in self._subscribers:
            await q.put(msg)

    def _record_event(self, player_id: int, action: GameAction) -> None:
        event = GameEvent(
            round=self.state.round,
            phase=self.state.phase,
            actor_id=player_id,
            action=action,
        )
        self.state.game_history.append(event)

    def _resolve_wolf_kill(self, actions: list[GameAction]) -> Optional[int]:
        votes: dict[int, int] = {}
        for a in actions:
            if a.skill_target:
                votes[a.skill_target] = votes.get(a.skill_target, 0) + 1
        if not votes:
            return None
        return max(votes, key=votes.get)

    def _tally_votes(self, votes: dict[int, int]) -> Optional[int]:
        tally: dict[int, int] = {}
        for target in votes.values():
            tally[target] = tally.get(target, 0) + 1
        if not tally:
            return None
        max_votes = max(tally.values())
        top = [pid for pid, c in tally.items() if c == max_votes]
        if len(top) == 1:
            return top[0]
        return None

    def _update_alive_counts(self) -> None:
        self.state.alive_werewolves = sum(
            1 for p in self.state.players if p.is_alive and p.role in WEREWOLF_ROLES
        )
        self.state.alive_villagers = sum(
            1 for p in self.state.players if p.is_alive and p.role not in WEREWOLF_ROLES
        )

    def _build_discuss_context(self, player: Player, transcript: list[str] | None = None) -> dict:
        memory_text = self.memory_pool.format_for_prompt()
        ctx: dict = {
            "memory_snapshot": memory_text,
            "alive_count": len(self.state.get_alive_players()),
        }
        if transcript:
            ctx["round_transcript"] = "\n".join(transcript)
        return ctx

    @staticmethod
    def _format_death_info(deaths: list[tuple[int, str]]) -> str:
        if not deaths:
            return "昨夜是平安夜，无人死亡。"
        parts = []
        for pid, cause in deaths:
            if cause == "wolf_kill":
                parts.append(f"{pid}号玩家被狼人杀害")
            elif cause == "poison":
                parts.append(f"{pid}号玩家被毒杀")
        return "；".join(parts)

    # ---- Structured logging ----

    def _get_log_path(self) -> str:
        path = os.path.join(self.config.log_dir, self.game_id)
        os.makedirs(path, exist_ok=True)
        return path

    def _write_meta(self) -> None:
        meta = {
            "game_id": self.game_id,
            "players": [
                {"id": p.id, "name": p.name, "role": p.role.value, "faction": p.faction.value,
                 "is_human": self.is_human(p.id)}
                for p in self.state.players
            ],
            "config": {
                "player_count": self.config.player_count,
                "use_sheriff": self.config.use_sheriff,
                "decay_factor": self.config.decay_factor,
            },
        }
        out = os.path.join(self._get_log_path(), "meta.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

    def _write_logs(self) -> None:
        path = self._get_log_path()

        events_path = os.path.join(path, "events.jsonl")
        with open(events_path, "w", encoding="utf-8") as f:
            for e in self.state.game_history:
                f.write(e.model_dump_json() + "\n")

        beliefs_path = os.path.join(path, "beliefs.jsonl")
        with open(beliefs_path, "w", encoding="utf-8") as f:
            for pid, belief in self.belief_states.items():
                belief.round = self.state.round
                f.write(belief.model_dump_json() + "\n")

        lies_path = os.path.join(path, "lies.json")
        with open(lies_path, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)

        if self._llm_call_log:
            llm_path = os.path.join(path, "llm_calls.jsonl")
            with open(llm_path, "w", encoding="utf-8") as f:
                for call in self._llm_call_log:
                    f.write(json.dumps(call, ensure_ascii=False) + "\n")

        logger.info(f"Logs written to {path}")

    def log_llm_call(self, player_id: int, prompt: str, response: str, elapsed: float, model: str = "") -> None:
        entry = {
            "player_id": player_id,
            "model": model,
            "round": self.state.round,
            "phase": self.state.phase.value,
            "prompt": prompt,
            "response": response,
            "elapsed_sec": round(elapsed, 3),
            "api_key": "***",
        }
        self._llm_call_log.append(entry)
        for q in self._subscribers:
            q.put_nowait({"type": "LLM_CALL", "payload": entry})

    # ---- Streaming ----

    def event_stream(self):
        q = self.subscribe()

        async def _stream():
            try:
                while True:
                    msg = await q.get()
                    yield msg
                    if msg.get("type") == "GAME_OVER":
                        break
            finally:
                self.unsubscribe(q)

        return _stream()

    def get_agent_action_queue(self, player_id: int) -> asyncio.Queue:
        return self._action_queues[player_id]

    def submit_action(self, player_id: int, action: GameAction) -> None:
        if player_id in self._action_queues:
            self._action_queues[player_id].put_nowait(action)
