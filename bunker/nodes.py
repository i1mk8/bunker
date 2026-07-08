"""Ноды фаз игрового раунда: раскрытие, обсуждение, голосование, исключение."""

import random

from langgraph.types import interrupt

from bunker import llm, prompts
from bunker.config import settings
from bunker.flow import first_alive, next_alive
from bunker.schemas import CardChoice, CardName, VoteDecision
from bunker.state import CATEGORY_LABELS, GameEvent, GameState


def _phase_position(state: GameState) -> tuple[int, int]:
    """Возвращает индекс ходящего игрока и число уже отходивших в фазе.

    При свежем входе в фазу (счётчик достиг числа живых) сбрасывает указатель
    на первого живого игрока и счётчик в ноль.
    """
    players = state["players"]
    alive = sum(1 for player in players if player.is_alive)
    if state["phase_done"] >= alive:
        return first_alive(players), 0
    index = state["current_index"]
    if not players[index].is_alive:
        index = first_alive(players)
    return index, state["phase_done"]


def reveal(state: GameState) -> dict:
    """Фаза раскрытия: текущий игрок раскрывает одну из скрытых карт."""
    index, done = _phase_position(state)
    players = [player.model_copy(deep=True) for player in state["players"]]
    player = players[index]
    hidden = player.hidden_categories()
    if not hidden:
        return {"current_index": next_alive(players, index), "phase_done": done + 1}

    system, user = prompts.reveal_messages(state, player)
    if player.is_human:
        payload = {
            "type": "reveal",
            "round": state["round_no"],
            "hand": {CATEGORY_LABELS[c]: player.cards[c] for c in player.cards},
            "hidden": [(CATEGORY_LABELS[c], c) for c in hidden],
        }
        choice = CardChoice.model_validate(interrupt(payload))
    else:
        choice = llm.decide(CardChoice, system, user, CardChoice(card=CardName(hidden[0])))

    category = str(choice.card)
    if category not in player.cards or category in player.revealed:
        category = hidden[0]
    player.revealed.append(category)
    if choice.updated_notes:
        player.memory.notes = choice.updated_notes

    text = f"{player.name} раскрыл: {CATEGORY_LABELS[category]} — {player.cards[category]}"
    event = GameEvent(round_no=state["round_no"], phase="reveal", actor_id=player.id, text=text)
    return {
        "players": players,
        "event_log": [event],
        "current_index": next_alive(players, index),
        "phase_done": done + 1,
    }


def discuss(state: GameState) -> dict:
    """Фаза обсуждения: текущий игрок выступает с репликой."""
    index, done = _phase_position(state)
    player = state["players"][index]
    system, user = prompts.discuss_messages(state, player)
    if player.is_human:
        payload = {"type": "discuss", "round": state["round_no"], "capacity": state["capacity"]}
        speech = str(interrupt(payload))
    else:
        speech = llm.free_text(system, user)

    event = GameEvent(
        round_no=state["round_no"],
        phase="discuss",
        actor_id=player.id,
        text=f"{player.name}: {speech}",
    )
    return {
        "event_log": [event],
        "current_index": next_alive(state["players"], index),
        "phase_done": done + 1,
    }


def vote(state: GameState) -> dict:
    """Фаза голосования: текущий игрок анонимно голосует за исключение."""
    index, done = _phase_position(state)
    players = [player.model_copy(deep=True) for player in state["players"]]
    voter = players[index]
    candidates = [player for player in players if player.is_alive and player.id != voter.id]

    system, user = prompts.vote_messages(state, voter, candidates)
    if voter.is_human:
        payload = {
            "type": "vote",
            "candidates": [{"id": player.id, "name": player.name} for player in candidates],
        }
        decision = VoteDecision.model_validate(interrupt(payload))
    else:
        decision = llm.decide(VoteDecision, system, user, VoteDecision(target_id=candidates[0].id))

    target = decision.target_id
    if target not in {player.id for player in candidates}:
        target = candidates[0].id
    if decision.updated_notes:
        voter.memory.notes = decision.updated_notes

    votes = dict(state["votes"])
    votes[target] = votes.get(target, 0) + 1
    return {
        "players": players,
        "votes": votes,
        "current_index": next_alive(players, index),
        "phase_done": done + 1,
    }


def eliminate(state: GameState) -> dict:
    """Определяет исключённого по итогам голосования со случайным тай-брейком."""
    votes = state["votes"]
    if not votes:
        return {"pending_last_word": None}

    players = [player.model_copy(deep=True) for player in state["players"]]
    top = max(votes.values())
    leaders = [player_id for player_id, count in votes.items() if count == top]
    eliminated_id = random.Random(settings.deal_seed).choice(leaders)
    players[eliminated_id].is_alive = False

    text = f"{players[eliminated_id].name} исключён — голосов: {votes[eliminated_id]}"
    event = GameEvent(round_no=state["round_no"], phase="vote_result", actor_id=None, text=text)
    return {"players": players, "pending_last_word": eliminated_id, "event_log": [event]}


def last_word(state: GameState) -> dict:
    """Последнее слово исключённого игрока перед уходом из бункера."""
    eliminated_id = state["pending_last_word"]
    if eliminated_id is None:
        return {}

    player = state["players"][eliminated_id]
    system, user = prompts.last_word_messages(state, player)
    if player.is_human:
        speech = str(interrupt({"type": "last_word", "name": player.name}))
    else:
        speech = llm.free_text(system, user)

    event = GameEvent(
        round_no=state["round_no"],
        phase="last_word",
        actor_id=eliminated_id,
        text=f"Последнее слово {player.name}: {speech}",
    )
    return {"event_log": [event], "pending_last_word": None}
