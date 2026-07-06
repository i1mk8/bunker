from langgraph.graph import StateGraph, START,END
from count_game import Count


graph_capacity_bk = StateGraph(Count)

def check_capacity(state: Count) -> None:
    return None 

def check_condition(state: Count) -> str:
    if state["capacity_bunker"] >= state["count_player"]:
        return "Игра окончена"
    else:
        return "Игра продолжается"

def generate_end_game_message(state: Count) -> dict:
    return {
        "message": f"Игра окончена"
    }
def generate_continue_game_message(state: Count) -> dict:
    return {
        "message": f"Игра продолжается"
    }

graph_capacity_bk.add_node("check_capacity", check_capacity)
graph_capacity_bk.add_node("generate_end_game_message", generate_end_game_message)
graph_capacity_bk.add_node("generate_continue_game_message", generate_continue_game_message)

graph_capacity_bk.add_edge(START,"check_capacity")

graph_capacity_bk.add_conditional_edges(
    "check_capacity",
    check_condition,
    {
        "Игра окончена": "generate_end_game_message",
        "Игра продолжается": "generate_continue_game_message"
    }
)

graph_capacity_bk.add_edge("generate_end_game_message",END)
graph_capacity_bk.add_edge("generate_continue_game_message",END)

app = graph_capacity_bk.compile()

result = app.invoke({"count_player": 5,
                    "capacity_bunker": 3
})
print(result)