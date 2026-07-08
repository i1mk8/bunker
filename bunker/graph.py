"""Сборка графа игры на LangGraph."""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from bunker.flow import advance_phase, check_end, end_game, next_round
from bunker.nodes import discuss, eliminate, last_word, reveal, vote
from bunker.state import GameState


def build_graph() -> CompiledStateGraph:
    """Собирает и компилирует граф игры с чекпоинтером в памяти."""
    graph = StateGraph(GameState)
    graph.add_node("reveal", reveal)
    graph.add_node("discuss", discuss)
    graph.add_node("vote", vote)
    graph.add_node("eliminate", eliminate)
    graph.add_node("last_word", last_word)
    graph.add_node("next_round", next_round)
    graph.add_node("end_game", end_game)

    graph.add_conditional_edges(START, check_end, {"end": "end_game", "play": "reveal"})
    graph.add_conditional_edges("reveal", advance_phase, {"continue": "reveal", "next": "discuss"})
    graph.add_conditional_edges("discuss", advance_phase, {"continue": "discuss", "next": "vote"})
    graph.add_conditional_edges("vote", advance_phase, {"continue": "vote", "next": "eliminate"})
    graph.add_edge("eliminate", "last_word")
    graph.add_edge("last_word", "next_round")
    graph.add_conditional_edges("next_round", check_end, {"end": "end_game", "play": "reveal"})
    graph.add_edge("end_game", END)

    # MemorySaver держит состояние в памяти процесса; для веба заменяется на SqliteSaver.
    return graph.compile(checkpointer=MemorySaver())
