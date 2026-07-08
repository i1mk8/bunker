"""Загрузка пулов карт из JSON и раздача их игрокам в начале партии."""

import json
import logging
import random
from pathlib import Path

from bunker.state import CARD_CATEGORIES, GameState, Player

logger = logging.getLogger(__name__)

CARDS_DIR = Path(__file__).resolve().parent.parent / "data" / "cards"


def load_pools(cards_dir: Path) -> dict[str, list[str]]:
    """Читает пулы значений категорий карт из JSON-файлов каталога."""
    pools: dict[str, list[str]] = {}
    for category in CARD_CATEGORIES:
        path = cards_dir / f"{category}.json"
        if not path.is_file():
            raise FileNotFoundError(f"Не найден файл пула карт: {path}")
        values = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
            raise ValueError(f"Пул {path} должен быть списком строк")
        if not values:
            raise ValueError(f"Пул {path} пуст")
        pools[category] = values
    return pools


def _deal_category(values: list[str], count: int, rng: random.Random) -> list[str]:
    """Выбирает count значений категории без повторов, если хватает уникальных."""
    unique = list(dict.fromkeys(values))
    if len(unique) >= count:
        return rng.sample(unique, count)
    logger.warning(
        "В пуле недостаточно уникальных значений (%d < %d) — допускаю повторы",
        len(unique),
        count,
    )
    return rng.choices(unique, k=count)


def deal_players(
    pools: dict[str, list[str]],
    count: int,
    human_seat: int,
    rng: random.Random,
) -> list[Player]:
    """Раздаёт count игрокам по одной случайной карте из каждой категории.

    Игрок с индексом human_seat становится живым; при индексе вне диапазона
    партия состоит только из ботов.
    """
    dealt = {category: _deal_category(values, count, rng) for category, values in pools.items()}
    players: list[Player] = []
    for index in range(count):
        cards = {category: dealt[category][index] for category in CARD_CATEGORIES}
        players.append(
            Player(
                id=index,
                name=f"Игрок {index + 1}",
                cards=cards,
                is_human=(index == human_seat),
            )
        )
    return players


def create_initial_state(
    *,
    players_count: int,
    capacity: int,
    human_seat: int,
    cards_dir: Path = CARDS_DIR,
    seed: int | None = None,
) -> GameState:
    """Собирает стартовое состояние партии с розданными картами."""
    rng = random.Random(seed)
    pools = load_pools(cards_dir)
    players = deal_players(pools, players_count, human_seat, rng)
    return GameState(
        players=players,
        event_log=[],
        round_no=1,
        capacity=capacity,
        current_index=0,
        phase_done=0,
        votes={},
        pending_last_word=None,
        winner_message="",
    )
