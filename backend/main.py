import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse

from .config import config
from .engine.game_master import GameMaster
from .ws.router import Broadcaster, create_ws_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

gm = GameMaster(config.game)
broadcaster = Broadcaster()
player_ws_handler, human_ws_handler, spectator_ws_handler = create_ws_router(gm, broadcaster)
_game_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Server starting...")
    yield
    logger.info("Server shutting down...")


app = FastAPI(title="SJM-Werewolf", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- Health ----

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "game_id": gm.game_id or "not_started",
        "game_phase": gm.state.phase.value,
        "game_round": gm.state.round,
    }


# ---- Game control ----

@app.post("/game/start")
async def start_game(human_count: int = 0):
    global _game_task
    if gm.state.phase.value not in ("PRE_GAME", "GAME_OVER"):
        return {"error": "Game already in progress"}
    if _game_task and not _game_task.done():
        _game_task.cancel()
    human_ids = list(range(1, human_count + 1)) if human_count > 0 else []
    gm.init_game(human_ids=human_ids)
    _game_task = asyncio.create_task(gm.run())
    return {
        "status": "game_started",
        "game_id": gm.game_id,
        "phase": gm.state.phase.value,
        "human_players": human_ids,
    }


# ---- Model configuration (Section 16) ----

PROVIDERS: dict[str, dict] = {
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "models": ["deepseek-chat", "deepseek-reasoner"],
    },
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-4o", "gpt-4o-mini", "o4-mini"],
    },
    "qwen": {
        "name": "阿里 Qwen",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": ["qwen-plus", "qwen-max", "qwen-turbo"],
    },
    "doubao": {
        "name": "豆包 Doubao",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "models": ["doubao-lite-128k", "doubao-pro-128k"],
    },
    "mock": {
        "name": "Mock (无 API 本地模拟)",
        "base_url": "",
        "models": ["mock"],
    },
}


@app.get("/providers")
async def list_providers():
    return {"providers": PROVIDERS}


@app.get("/game/config")
async def get_game_config():
    if gm._model_config is None:
        return {"configured": False}
    cfg = gm._model_config.model_dump()
    for p in cfg.get("providers", {}):
        if cfg["providers"][p].get("api_key"):
            cfg["providers"][p]["api_key"] = "sk-***"
    return {"configured": True, "config": cfg}


@app.post("/game/config")
async def set_game_config(cfg: dict):
    from .models.schemas import GameModelConfig
    model_cfg = GameModelConfig(**cfg)
    gm.set_model_config(model_cfg)
    return {"status": "ok", "players_configured": len(model_cfg.players)}


@app.get("/game/state")
async def get_game_state():
    return {
        "game_id": gm.game_id,
        "phase": gm.state.phase.value,
        "round": gm.state.round,
        "players": [
            {
                "id": p.id, "name": p.name, "is_alive": p.is_alive,
                "is_human": gm.is_human(p.id),
                "revealed_role": p.revealed_role.value if p.revealed_role else None,
            }
            for p in gm.state.players
        ],
        "winner": gm.state.winner.value if gm.state.winner else None,
    }


# ---- Observability endpoints (Section 13) ----

@app.get("/game/events")
async def get_events(round_num: int | None = Query(None, alias="round")):
    events = gm.state.game_history
    if round_num is not None:
        events = [e for e in events if e.round == round_num]
    return {
        "game_id": gm.game_id,
        "count": len(events),
        "events": [e.model_dump(mode="json") for e in events],
    }


@app.get("/game/beliefs")
async def get_beliefs():
    return {
        "game_id": gm.game_id,
        "round": gm.state.round,
        "beliefs": {
            str(pid): b.model_dump(mode="json")
            for pid, b in gm.belief_states.items()
        },
    }


@app.get("/game/replay")
async def get_replay():
    return {
        "game_id": gm.game_id,
        "meta": {
            "phase": gm.state.phase.value,
            "round": gm.state.round,
            "winner": gm.state.winner.value if gm.state.winner else None,
            "players": [
                {"id": p.id, "name": p.name, "role": p.role.value, "faction": p.faction.value,
                 "is_alive": p.is_alive, "is_human": gm.is_human(p.id)}
                for p in gm.state.players
            ],
        },
        "events": [e.model_dump(mode="json") for e in gm.state.game_history],
        "beliefs": {str(pid): b.model_dump(mode="json") for pid, b in gm.belief_states.items()},
    }


@app.get("/game/logs")
async def list_logs():
    base = config.game.log_dir
    if not os.path.isdir(base):
        return {"games": []}
    games = sorted(os.listdir(base), reverse=True)[:20]
    return {"games": games}


@app.get("/game/logs/{game_id}/{filename}")
async def get_log_file(game_id: str, filename: str):
    filepath = os.path.join(config.game.log_dir, game_id, filename)
    if not os.path.isfile(filepath):
        return PlainTextResponse("Not found", status_code=404)
    if filename.endswith(".jsonl"):
        lines = []
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                lines.append(json.loads(line))
        return {"game_id": game_id, "file": filename, "lines": lines}
    return FileResponse(filepath, media_type="application/json")


# ---- WebSocket endpoints ----

@app.websocket("/ws/player/{player_id}")
async def ws_player(websocket: WebSocket, player_id: int):
    await player_ws_handler(websocket, player_id)


@app.websocket("/ws/human")
async def ws_human(websocket: WebSocket):
    await human_ws_handler(websocket)


@app.websocket("/ws/spectator")
async def ws_spectator(websocket: WebSocket):
    await spectator_ws_handler(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)
