import os
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class LLMConfig:
    api_key: str = os.getenv("LLM_API_KEY", "sk-xxx")
    base_url: str = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
    model: str = os.getenv("LLM_MODEL", "deepseek-chat")
    temperature: float = 0.8
    max_tokens: int = 1024
    timeout: float = 30.0
    max_retries: int = 3


@dataclass
class GameConfig:
    player_count: int = 12
    human_player_count: int = 0
    werewolf_count: int = 4
    villager_count: int = 4
    roles: list[str] = field(default_factory=lambda: [
        "WEREWOLF", "WEREWOLF", "WEREWOLF", "WEREWOLF",
        "SEER", "WITCH", "HUNTER", "IDIOT",
        "VILLAGER", "VILLAGER", "VILLAGER", "VILLAGER",
    ])
    use_guard: bool = False
    use_sheriff: bool = False
    witch_can_self_save: bool = False
    decay_factor: float = 0.85
    min_memory_weight: float = 0.15
    speech_order: str = "sequential"
    log_dir: str = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")

    def __post_init__(self):
        if len(self.roles) != self.player_count:
            raise ValueError(
                f"Role count {len(self.roles)} != player_count {self.player_count}"
            )


@dataclass
class Config:
    llm: LLMConfig = field(default_factory=LLMConfig)
    game: GameConfig = field(default_factory=GameConfig)


def generate_game_id() -> str:
    return datetime.utcnow().strftime("game_%Y%m%d_%H%M%S")


config = Config()
