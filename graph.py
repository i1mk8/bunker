from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from state import GameState
from nodes import (
    ChoiceCard,
    DisclosureCard,
    discuss,
    vote,
    next_voter,
    eliminate_player,
    increment_round,
    generate_end_game_message,
    check_condition,
    check_all_players_done,
    check_all_voted,
)


def build_graph():
    graph = StateGraph(GameState)

    graph.add_node("check_end", lambda state: None)
    graph.add_node("choice_card", ChoiceCard)
    graph.add_node("disclosure_card", DisclosureCard)
    graph.add_node("discuss", discuss)
    graph.add_node("vote", vote)
    graph.add_node("next_voter", next_voter)
    graph.add_node("eliminate_player", eliminate_player)
    graph.add_node("increment_round", increment_round)
    graph.add_node("end_game", generate_end_game_message)

    graph.add_edge(START, "check_end")

    graph.add_conditional_edges(
        "check_end",
        check_condition,
        {
            "Игра окончена": "end_game",
            "Игра продолжается": "choice_card",
        },
    )

    graph.add_edge("choice_card", "disclosure_card")
    graph.add_edge("disclosure_card", "discuss")

    graph.add_conditional_edges(
        "discuss",
        check_all_players_done,
        {
            "Раунд окончен": "vote",
            "Продолжаем": "choice_card",
        },
    )

    graph.add_edge("vote", "next_voter")

    graph.add_conditional_edges(
        "next_voter",
        check_all_voted,
        {
            "Все проголосовали": "eliminate_player",
            "Продолжаем голосование": "vote",
        },
    )

    graph.add_edge("eliminate_player", "increment_round")
    graph.add_edge("increment_round", "check_end")
    graph.add_edge("end_game", END)

    memory = MemorySaver()
    return graph.compile(checkpointer=memory)


app = build_graph()