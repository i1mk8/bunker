"""Сборка JSON-данных партии для веб-фронтенда из состояния графа."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from bunker import prompts
from bunker.state import CARD_CATEGORIES, CATEGORY_LABELS, GameState, Player

if TYPE_CHECKING:
    from bunker.web.session import GameSession

_NOTE_PREFIX = re.compile(r"^\[Р(\d+)\]\s*(.*)$")


def _parse_notes(notes: str) -> list[tuple[int, str]]:
    """Разбирает накопленные заметки на пары (номер раунда, текст)."""
    entries: list[tuple[int, str]] = []
    for line in notes.splitlines():
        match = _NOTE_PREFIX.match(line)
        if match:
            entries.append((int(match.group(1)), match.group(2).strip()))
        elif entries:
            round_no, text = entries[-1]
            entries[-1] = (round_no, f"{text}\n{line}".strip())
    return entries


def notes_by_round(notes: str) -> list[dict]:
    """Группирует заметки игрока по раундам в порядке их появления."""
    grouped: dict[int, list[str]] = {}
    for round_no, text in _parse_notes(notes):
        if text:
            grouped.setdefault(round_no, []).append(text)
    return [{"round": round_no, "text": "\n".join(items)} for round_no, items in grouped.items()]


def round_notes(notes: str, round_no: int) -> str:
    """Возвращает заметки игрока только за указанный раунд."""
    texts = [text for note_round, text in _parse_notes(notes) if note_round == round_no and text]
    return "\n".join(texts)


def estimate_tokens(text: str) -> int:
    """Грубо оценивает число токенов — фолбэк, пока нет точного счёта от модели."""
    return max(1, round(len(text) / 4)) if text else 0


def serialize_player(state: GameState, player: Player) -> dict:
    """Собирает данные игрока: карты, статус, а для ботов — заметки и контекст."""
    data = {
        "id": player.id,
        "name": player.name,
        "is_human": player.is_human,
        "is_alive": player.is_alive,
        "cards": {
            CATEGORY_LABELS[category]: player.cards[category] for category in CARD_CATEGORIES
        },
        "revealed": [CATEGORY_LABELS[category] for category in player.revealed],
    }
    if player.is_human:
        return data

    context = f"{prompts.SYSTEM_RULES}\n\n{prompts.render_context(state, player)}"
    exact = player.memory.last_prompt_tokens > 0
    data.update(
        {
            "notes_by_round": notes_by_round(player.memory.notes),
            "round_notes": round_notes(player.memory.notes, state["round_no"]),
            "context": context,
            "context_chars": len(context),
            "context_tokens": player.memory.last_prompt_tokens
            if exact
            else estimate_tokens(context),
            "context_tokens_exact": exact,
        }
    )
    return data


def serialize_state(session: GameSession) -> dict:
    """Собирает полный снапшот партии для фронтенда."""
    values = session.values or {}
    players = values.get("players", [])
    alive_count = sum(1 for player in players if player.is_alive)
    event_log = values.get("event_log", [])
    return {
        "status": session.status,
        "error": session.error,
        "pending": session.pending,
        "round_no": values.get("round_no", 0),
        "capacity": values.get("capacity", 0),
        "catastrophe": values.get("catastrophe", ""),
        "alive_count": alive_count,
        "winner_message": values.get("winner_message", ""),
        "players": [serialize_player(values, player) for player in players],
        "event_log": [
            {
                "round_no": event.round_no,
                "phase": event.phase,
                "actor_id": event.actor_id,
                "text": event.text,
            }
            for event in event_log
        ],
    }
