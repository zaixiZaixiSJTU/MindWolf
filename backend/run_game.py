"""
CLI driver for running Werewolf games with MockAgent (no real LLM needed).

Usage:
    cd WOLF && python -m backend.run_game --games 3 --verbose
"""
import asyncio
import argparse
import logging
import random

from .config import GameConfig
from .engine.game_master import GameMaster
from .models.enums import Role, Faction, Phase, WEREWOLF_ROLES
from .models.schemas import Player, GameAction
from .models.memory import BeliefState
from .memory.event_extractor import EventExtractor
from .memory.belief_updater import BeliefUpdater

logger = logging.getLogger(__name__)


def mock_action(player: Player, phase: Phase, alive_ids: list[int], extra: dict | None = None) -> GameAction:
    pid = player.id
    suspects = [i for i in alive_ids if i != pid]

    if phase == Phase.NIGHT_WEREWOLF and player.role in WEREWOLF_ROLES:
        target = random.choice(suspects) if suspects else None
        return GameAction(
            player_id=pid, phase=phase,
            thinking=f"狼人协商。目标: {target}号。",
            skill_target=target, skill_name="kill",
        )

    if phase == Phase.NIGHT_SEER and player.role == Role.SEER:
        target = random.choice(suspects) if suspects else None
        return GameAction(
            player_id=pid, phase=phase,
            thinking=f"查验{target}号。",
            skill_target=target, skill_name="check",
        )

    if phase == Phase.NIGHT_WITCH and player.role == Role.WITCH:
        action = GameAction(player_id=pid, phase=phase,
                            thinking="考虑是否用药。")
        killed = extra.get("night_killed") if extra else None
        if killed and player.skill_available.get("antidote", False):
            action.skill_name = "antidote"
            action.skill_target = None
        return action

    if phase in (Phase.DAY_DISCUSS, Phase.DAY_VOTE):
        target = random.choice(suspects) if suspects else None
        speeches = [
            f"我是{pid}号，我目前没有太多信息。听{target}号的发言有点奇怪。",
            f"{pid}号发言。我觉得{target}号可能是狼。大家投票注意。",
            f"作为一个好人，我认为需要仔细分析。怀疑{target}号。",
        ]
        return GameAction(
            player_id=pid, phase=phase,
            thinking=f"分析局面，怀疑{target}号。",
            speech=random.choice(speeches),
            vote_target=target,
        )

    return GameAction(player_id=pid, phase=phase, thinking="等待。")


async def run_one_game(game_id: int, verbose: bool = False) -> GameMaster:
    config = GameConfig()
    gm = GameMaster(config)
    gm.init_game()
    extractor = EventExtractor()

    if verbose:
        print(f"\n=== Game {game_id} ===")
        for p in gm.state.players:
            print(f"  Player {p.id}: {p.role.value}")

    while gm.state.phase != Phase.GAME_OVER:
        phase = gm.state.phase
        alive_ids = gm.state.get_alive_ids()

        if verbose:
            print(f"\n--- Round {gm.state.round} | {phase.value} | Alive: {alive_ids} ---")

        if phase == Phase.PRE_GAME:
            gm.state.phase = Phase.NIGHT_WEREWOLF
            gm.state.round = 1
            continue

        elif phase == Phase.NIGHT_WEREWOLF:
            wolves = [p for p in gm.state.players if p.is_alive and p.role in WEREWOLF_ROLES]
            actions = []
            for w in wolves:
                act = mock_action(w, phase, alive_ids)
                actions.append(act)
                gm._record_event(w.id, act)
            kill = gm._resolve_wolf_kill(actions)
            gm._last_wolf_kill = kill
            gm.state.phase = Phase.NIGHT_SEER

        elif phase == Phase.NIGHT_SEER:
            seers = [p for p in gm.state.players if p.is_alive and p.role == Role.SEER]
            for s in seers:
                act = mock_action(s, phase, alive_ids)
                gm._record_event(s.id, act)
                if act.skill_target:
                    target = gm.state.get_player(act.skill_target)
                    gm._last_seer_result = (act.skill_target, target.faction if target else None)
            gm.state.phase = Phase.NIGHT_WITCH

        elif phase == Phase.NIGHT_WITCH:
            witches = [p for p in gm.state.players if p.is_alive and p.role == Role.WITCH]
            for w in witches:
                extra = {"night_killed": getattr(gm, "_last_wolf_kill", None)}
                act = mock_action(w, phase, alive_ids, extra)
                gm._record_event(w.id, act)
                if act.skill_name == "antidote" and w.skill_available.get("antidote"):
                    w.skill_available["antidote"] = False
                    gm._last_witch_save = getattr(gm, "_last_wolf_kill", None)
                elif act.skill_name == "poison" and w.skill_available.get("poison"):
                    w.skill_available["poison"] = False
                    gm._last_witch_poison = act.skill_target
            gm.state.phase = Phase.NIGHT_HUNTER

        elif phase == Phase.NIGHT_HUNTER:
            gm.state.phase = Phase.DAY_ANNOUNCE

        elif phase == Phase.DAY_ANNOUNCE:
            killed = getattr(gm, "_last_wolf_kill", None)
            saved = getattr(gm, "_last_witch_save", None)
            poisoned = getattr(gm, "_last_witch_poison", None)
            deaths = []
            if killed and killed != saved:
                p = gm.state.get_player(killed)
                if p:
                    p.mark_dead()
                deaths.append((killed, "wolf_kill"))
            if poisoned:
                p = gm.state.get_player(poisoned)
                if p:
                    if p.role == Role.HUNTER:
                        p.skill_available["shoot"] = False
                    p.mark_dead()
                deaths.append((poisoned, "poison"))
            gm._update_alive_counts()

            if verbose and deaths:
                print(f"  Deaths: {deaths}")
            elif verbose and not deaths:
                print(f"  Peaceful night (平安夜)")

            gm._last_wolf_kill = None
            gm._last_witch_save = None
            gm._last_witch_poison = None

            winner = gm._check_victory()
            if gm.state.phase == Phase.GAME_OVER:
                break
            gm.state.phase = Phase.DAY_DISCUSS

        elif phase == Phase.DAY_DISCUSS:
            alive = gm.state.get_alive_players()
            for p in alive:
                act = mock_action(p, phase, alive_ids)
                gm._record_event(p.id, act)
                if act.speech:
                    units = extractor.extract(p.id, gm.state.round, act.speech)
                    for u in units:
                        gm.memory_pool.add_unit(u)
                if verbose:
                    print(f"  [{p.id}] {act.speech[:80]}...")
            gm.state.phase = Phase.DAY_VOTE

        elif phase == Phase.DAY_VOTE:
            alive = gm.state.get_alive_players()
            votes: dict[int, int] = {}
            for p in alive:
                act = mock_action(p, phase, alive_ids)
                gm._record_event(p.id, act)
                if act.vote_target and act.vote_target in alive_ids:
                    votes[p.id] = act.vote_target
            eliminated = gm._tally_votes(votes)
            if eliminated is not None:
                victim = gm.state.get_player(eliminated)
                if victim:
                    if victim.role == Role.IDIOT:
                        victim.can_vote = False
                        victim.revealed_role = Role.IDIOT
                    else:
                        if victim.role == Role.HUNTER and victim.skill_available.get("shoot"):
                            shoot_target = random.choice([i for i in alive_ids if i != victim.id])
                            t = gm.state.get_player(shoot_target)
                            if t:
                                t.mark_dead()
                            victim.skill_available["shoot"] = False
                        victim.mark_dead()
                if verbose:
                    print(f"  Eliminated: Player {eliminated} ({victim.role.value if victim else '?'})")
            elif verbose:
                print(f"  Vote tied — no elimination")
            gm._update_alive_counts()

            gm.memory_pool.decay_all(gm.state.round)
            for pid in gm.belief_states:
                BeliefUpdater.update(gm.belief_states[pid], gm.memory_pool)

            winner = gm._check_victory()
            if gm.state.phase == Phase.GAME_OVER:
                break
            gm.state.round += 1
            gm.state.phase = Phase.NIGHT_WEREWOLF

    gm.state.winner = gm._check_victory() or gm.state.winner
    gm._write_logs()
    if verbose:
        print(f"\n  Winner: {gm.state.winner.value if gm.state.winner else '?'} "
              f"| Rounds: {gm.state.round} | Memories: {len(gm.memory_pool.units)}")
    return gm


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=int, default=1)
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    wins: dict[str, int] = {Faction.VILLAGER.value: 0, Faction.WEREWOLF.value: 0}

    for i in range(args.games):
        gm = await run_one_game(i + 1, verbose=args.verbose)
        if gm.state.winner:
            wins[gm.state.winner.value] += 1
        print(f"Game {i + 1}: {gm.state.winner.value if gm.state.winner else '?'} "
              f"({gm.state.round} rounds)")

    if args.games > 1:
        total = args.games
        print(f"\nSummary ({total} games):")
        for f, c in wins.items():
            print(f"  {f}: {c} ({c/total*100:.0f}%)")


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    asyncio.run(main())
