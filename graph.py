from langgraph.graph import StateGraph, START,END
from user import UserPlayer

graph = StateGraph(UserPlayer)

def SaveCard(state: UserPlayer):
    return {"profession": state["profession"]}

graph.add_node("SaveCard", SaveCard)

graph.add_edge(START,"SaveCard")
graph.add_edge("SaveCard",END)

app = graph.compile()


result = app.invoke({"profession": "1",
                     "biology": "?"
                     })
print(result)