"""Доменные модели игры и структура состояния графа LangGraph."""

from typing import Annotated, Literal, TypedDict

from pydantic import BaseModel, Field

CARD_CATEGORIES: tuple[str, ...] = (
    "profession",
    "biology",
    "health",
    "hobby",
    "baggage",
    "fact",
)

CATEGORY_LABELS: dict[str, str] = {
    "profession": "Профессия",
    "biology": "Биология",
    "health": "Здоровье",
    "hobby": "Хобби",
    "baggage": "Багаж",
    "fact": "Факт",
}


class PlayerMemory(BaseModel):
    """Приватная память игрока, недоступная другим участникам."""

    notes: str = ""
    rolling_summary: str = ""
    last_prompt_tokens: int = 0


class Player(BaseModel):
    """Игрок партии: набор карт, статус и приватная память."""

    id: int
    name: str
    cards: dict[str, str]
    revealed: list[str] = Field(default_factory=list)
    is_human: bool = False
    is_alive: bool = True
    memory: PlayerMemory = Field(default_factory=PlayerMemory)

    def hidden_categories(self) -> list[str]:
        """Возвращает категории карт, которые игрок ещё не раскрыл."""
        return [category for category in CARD_CATEGORIES if category not in self.revealed]


class GameEvent(BaseModel):
    """Событие публичного журнала партии, видимое всем игрокам."""

    round_no: int
    phase: Literal["reveal", "discuss", "vote_result", "last_word"]
    actor_id: int | None
    text: str


def append_events(old: list[GameEvent], new: list[GameEvent]) -> list[GameEvent]:
    """Reducer публичного журнала: дописывает новые события к уже накопленным."""
    return old + new


class GameState(TypedDict):
    """Состояние игрового графа, сохраняемое чекпоинтером между раундами."""

    players: list[Player]
    catastrophe: str
    event_log: Annotated[list[GameEvent], append_events]
    round_no: int
    capacity: int
    current_index: int
    phase_done: int
    votes: dict[int, int]
    pending_last_word: int | None
    winner_message: str
