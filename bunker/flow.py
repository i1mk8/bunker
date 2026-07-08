"""Маршрутизация графа и служебные ноды смены раундов."""

from bunker.state import GameState, Player


def first_alive(players: list[Player]) -> int:
    """Возвращает индекс первого живого игрока."""
    return next(player.id for player in players if player.is_alive)


def next_alive(players: list[Player], index: int) -> int:
    """Возвращает индекс следующего живого игрока после index по кругу."""
    count = len(players)
    for step in range(1, count + 1):
        candidate = (index + step) % count
        if players[candidate].is_alive:
            return candidate
    return index


def _alive_count(state: GameState) -> int:
    return sum(1 for player in state["players"] if player.is_alive)


def check_end(state: GameState) -> str:
    """Определяет, помещаются ли все выжившие в бункер (конец игры)."""
    return "end" if _alive_count(state) <= state["capacity"] else "play"


def advance_phase(state: GameState) -> str:
    """Сообщает, все ли живые игроки уже отработали текущую фазу."""
    return "next" if state["phase_done"] >= _alive_count(state) else "continue"


def next_round(state: GameState) -> dict:
    """Начинает новый раунд: сбрасывает счётчик фазы, голоса и указатель хода."""
    return {
        "round_no": state["round_no"] + 1,
        "votes": {},
        "pending_last_word": None,
        "phase_done": 0,
        "current_index": first_alive(state["players"]),
    }


def end_game(state: GameState) -> dict:
    """Формирует итоговое сообщение о выживших."""
    survivors = [player.name for player in state["players"] if player.is_alive]
    return {"winner_message": f"Игра окончена. В бункере остались: {', '.join(survivors)}."}
