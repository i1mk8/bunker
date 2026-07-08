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

    card: CardName
    reasoning: str
    updated_notes: str | None = None


class VoteDecision(BaseModel):
    """Решение бота о том, за чьё исключение отдать голос."""

    target_id: int
    reasoning: str
    updated_notes: str | None = None
