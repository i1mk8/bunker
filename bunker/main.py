"""Точка входа: запуск консольной партии Бункер."""

import logging

from langgraph.types import Command

from bunker import console
from bunker.cards import create_initial_state
from bunker.config import settings
from bunker.graph import build_graph

RECURSION_LIMIT = 1000


def _narrate_new(values: dict, printed: int) -> int:
    """Печатает события журнала, появившиеся после предыдущего вывода."""
    events = values.get("event_log", [])
    for event in events[printed:]:
        console.narrate(event.text)
    return len(events)


def main() -> None:
    """Раздаёт карты, ведёт цикл графа с прерываниями для человека, печатает финал."""
    logging.basicConfig(level=logging.WARNING, format="[%(levelname)s] %(message)s")
    console.setup_console()

    graph = build_graph()
    state = create_initial_state(
        players_count=settings.players_count,
        capacity=settings.capacity,
        seed=settings.deal_seed,
    )
    config = {
        "configurable": {"thread_id": settings.thread_id},
        "recursion_limit": RECURSION_LIMIT,
    }

    console.narrate("Игра Бункер началась.")
    console.narrate(f"Игроков: {settings.players_count}, мест в бункере: {settings.capacity}.")
    console.narrate(f"Катастрофа: {state['catastrophe']}")

    printed = 0
    values = graph.invoke(state, config)
    while True:
        printed = _narrate_new(values, printed)
        if "__interrupt__" not in values:
            break
        answer = console.read_answer(values["__interrupt__"][0].value)
        values = graph.invoke(Command(resume=answer), config)

    console.narrate("")
    console.narrate(values["winner_message"])


if __name__ == "__main__":
    main()
