from typing import TypedDict


class PlayerState(TypedDict):
    profession: str
    biology: str
    health: str
    hobby: str
    baggage: str
    fact: str
    is_human: bool
    is_alive: bool
    revealed_cards: list[str]


class GameState(TypedDict):
    players: list[PlayerState]
    current_player_index: int
    count_round: int
    capacity_bunker: int
    count_player: int
    message: str
    chosen_card: str
    votes: dict  # {index_игрока: количество_голосов}