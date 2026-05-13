import asyncio
import logging
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect

from ..engine.game_master import GameMaster
from ..models.schemas import GameAction

logger = logging.getLogger(__name__)


class Broadcaster:
    def __init__(self):
        self._spectators: list[WebSocket] = []
        self._player_sockets: dict[int, WebSocket] = {}
        self._human_sockets: dict[int, WebSocket] = {}

    def register_spectator(self, ws: WebSocket) -> None:
        self._spectators.append(ws)

    def unregister_spectator(self, ws: WebSocket) -> None:
        if ws in self._spectators:
            self._spectators.remove(ws)

    def register_player(self, player_id: int, ws: WebSocket) -> None:
        self._player_sockets[player_id] = ws

    def unregister_player(self, player_id: int) -> None:
        self._player_sockets.pop(player_id, None)

    def register_human(self, player_id: int, ws: WebSocket) -> None:
        self._human_sockets[player_id] = ws

    def unregister_human(self, player_id: int) -> None:
        self._human_sockets.pop(player_id, None)

    async def broadcast(self, msg: dict) -> None:
        dead: list[WebSocket] = []
        for ws in self._spectators:
            try:
                await ws.send_json(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._spectators.remove(ws)

    async def send_to_player(self, player_id: int, msg: dict) -> None:
        ws = self._player_sockets.get(player_id) or self._human_sockets.get(player_id)
        if ws:
            try:
                await ws.send_json(msg)
            except Exception:
                self._player_sockets.pop(player_id, None)
                self._human_sockets.pop(player_id, None)


_HUMAN_COUNTER: int = 0


def _next_human_id(gm: GameMaster) -> int:
    global _HUMAN_COUNTER
    used = set(p.id for p in gm.state.players)
    _HUMAN_COUNTER += 1
    return _HUMAN_COUNTER


async def _gm_event_forwarder(gm: GameMaster, broadcaster: Broadcaster, player_id: int):
    async for msg in gm.event_stream():
        if msg.get("type") == "ACTION_REQUIRED" and msg.get("payload", {}).get("player_id") != player_id:
            continue
        await broadcaster.send_to_player(player_id, msg)


def create_ws_router(gm: GameMaster, broadcaster: Broadcaster):

    async def player_ws(websocket: WebSocket, player_id: int):
        await websocket.accept()
        broadcaster.register_player(player_id, websocket)
        logger.info(f"Player {player_id} connected")

        try:
            event_task = asyncio.create_task(
                _gm_event_forwarder(gm, broadcaster, player_id)
            )

            while gm.state.phase.value != "GAME_OVER":
                try:
                    data = await asyncio.wait_for(
                        websocket.receive_json(), timeout=120.0,
                    )
                    if data.get("type") == "SUBMIT_ACTION":
                        payload = data.get("payload", {})
                        action = GameAction(
                            player_id=player_id,
                            phase=gm.state.phase,
                            **{k: v for k, v in payload.items()
                               if k in GameAction.model_fields},
                        )
                        gm.submit_action(player_id, action)
                except asyncio.TimeoutError:
                    logger.warning(f"Player {player_id} WebSocket timeout")
                    gm.submit_action(player_id, GameAction(
                        player_id=player_id, phase=gm.state.phase,
                    ))
                    break

            await event_task
        except WebSocketDisconnect:
            logger.info(f"Player {player_id} disconnected")
        finally:
            broadcaster.unregister_player(player_id)

    # ---- Human player WS (Section 14) ----

    async def human_ws(websocket: WebSocket):
        await websocket.accept()

        if gm.state.phase.value in ("PRE_GAME", "GAME_OVER"):
            await websocket.send_json({
                "type": "INFO",
                "payload": {"message": "Waiting for game to start..."},
            })

        while gm.state.phase.value in ("PRE_GAME", "GAME_OVER"):
            try:
                data = await asyncio.wait_for(
                    websocket.receive_json(), timeout=3600.0,
                )
                if data.get("type") == "JOIN_GAME":
                    break
            except asyncio.TimeoutError:
                await websocket.send_json({
                    "type": "ERROR",
                    "payload": {"message": "Game not started, rejoin later."},
                })
                return

        human_id = _next_human_id(gm)
        broadcaster.register_human(human_id, websocket)
        logger.info(f"Human player {human_id} connected")

        try:
            event_task = asyncio.create_task(
                _gm_event_forwarder(gm, broadcaster, human_id)
            )

            while gm.state.phase.value != "GAME_OVER":
                try:
                    data = await asyncio.wait_for(
                        websocket.receive_json(), timeout=300.0,
                    )
                    if data.get("type") == "SUBMIT_ACTION":
                        payload = data.get("payload", {})
                        action = GameAction(
                            player_id=human_id,
                            phase=gm.state.phase,
                            **{k: v for k, v in payload.items()
                               if k in GameAction.model_fields},
                        )
                        gm.submit_action(human_id, action)
                except asyncio.TimeoutError:
                    logger.warning(f"Human player {human_id} timeout")
                    gm.submit_action(human_id, GameAction(
                        player_id=human_id, phase=gm.state.phase,
                        thinking="[HUMAN] idle",
                    ))
                    break

            await event_task
        except WebSocketDisconnect:
            logger.info(f"Human player {human_id} disconnected")
        finally:
            broadcaster.unregister_human(human_id)

    async def spectator_ws(websocket: WebSocket):
        await websocket.accept()
        broadcaster.register_spectator(websocket)
        logger.info("Spectator connected")
        try:
            async for msg in gm.event_stream():
                await websocket.send_json(msg)
        except WebSocketDisconnect:
            logger.info("Spectator disconnected")
        finally:
            broadcaster.unregister_spectator(websocket)

    return player_ws, human_ws, spectator_ws
