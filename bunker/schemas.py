"""Схемы структурированных решений языковой модели."""

from enum import StrEnum

from pydantic import BaseModel


class CardName(StrEnum):
    """Категория карты, которую игрок выбирает для раскрытия."""

    profession = "profession"
    biology = "biology"
    health = "health"
    hobby = "hobby"
    baggage = "baggage"
    fact = "fact"


class CardChoice(BaseModel):
    """Решение бота о том, какую карту раскрыть в текущем раунде."""

    new_notes: str
    card: CardName


class VoteDecision(BaseModel):
    """Решение бота о том, за чьё исключение отдать голос."""

    new_notes: str
    target_id: int
