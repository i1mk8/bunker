import os
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langgraph.types import interrupt
from state import GameState

# LM Studio предоставляет OpenAI-совместимый API
llm = ChatOpenAI(
    model="llama-3.1-8b",       # любое имя, LM Studio его проигнорирует
    base_url="http://localhost:1234/v1",
    api_key="lm-studio",         # любое значение, LM Studio не проверяет
    temperature=0.7
)


class CardChoice(BaseModel):
    card: str = Field(description="Название карты: profession, biology, health, hobby, baggage, fact")
    reason: str = Field(description="Краткое обоснование выбора")


class VoteChoice(BaseModel):
    target_player: int = Field(description="Номер игрока для голосования (1-7)")
    reason: str = Field(description="Краткое обоснование")


def check_condition(state: GameState) -> str:
    alive_count = sum(1 for p in state["players"] if p["is_alive"])
    if alive_count <= state["capacity_bunker"]:
        return "Игра окончена"
    return "Игра продолжается"


def check_all_players_done(state: GameState) -> str:
    if state["current_player_index"] == 0:
        return "Раунд окончен"
    return "Продолжаем"


def check_all_voted(state: GameState) -> str:
    alive_count = sum(1 for p in state["players"] if p["is_alive"])
    voted_count = sum(state.get("votes", {}).values())
    if voted_count >= alive_count:
        return "Все проголосовали"
    return "Продолжаем голосование"


def increment_round(state: GameState) -> dict:
    return {"count_round": state["count_round"] + 1}


def generate_end_game_message(state: GameState) -> dict:
    alive_players = [
        f"Игрок {i+1} ({p['profession']})"
        for i, p in enumerate(state["players"])
        if p["is_alive"]
    ]
    return {"message": f"Игра окончена! Выжили: {', '.join(alive_players)}"}


def next_player(state: GameState) -> dict:
    next_index = state["current_player_index"] + 1
    while next_index < len(state["players"]) and not state["players"][next_index]["is_alive"]:
        next_index += 1
    if next_index >= len(state["players"]):
        next_index = 0
        while next_index < len(state["players"]) and not state["players"][next_index]["is_alive"]:
            next_index += 1
    return {"current_player_index": next_index}


def next_voter(state: GameState) -> dict:
    next_index = state["current_player_index"] + 1
    while next_index < len(state["players"]) and not state["players"][next_index]["is_alive"]:
        next_index += 1
    if next_index >= len(state["players"]):
        next_index = 0
        while next_index < len(state["players"]) and not state["players"][next_index]["is_alive"]:
            next_index += 1
    return {"current_player_index": next_index}


def ChoiceCard(state: GameState) -> dict:
    current_player = state["players"][state["current_player_index"]]
    
    if current_player["is_human"]:
        user_input = interrupt({
            "type": "choice_card",
            "question": "Какую карту хотите раскрыть?",
            "your_cards": {
                "profession": current_player["profession"],
                "biology": current_player["biology"],
                "health": current_player["health"],
                "hobby": current_player["hobby"],
                "baggage": current_player["baggage"],
                "fact": current_player["fact"]
            },
            "round": state["count_round"]
        })
        return {
            "chosen_card": user_input["card_choice"],
            "message": f"Вы выбрали карту: {user_input['card_choice']}"
        }
    
    prompt = (
        f"Ты игрок в Бункер. Твои характеристики:\n"
        f"Профессия - {current_player['profession']}, "
        f"Биология - {current_player['biology']}, "
        f"Здоровье - {current_player['health']}, "
        f"Хобби - {current_player['hobby']}, "
        f"Багаж - {current_player['baggage']}, "
        f"Факт - {current_player['fact']}.\n"
        f"Раунд {state['count_round']}. Выбери ОДНУ карту для раскрытия.\n"
        "Ответь СТРОГО в формате: profession/biology/health/hobby/baggage/fact"
    )
    
    # Для локальных моделей structured output может не работать
    # Используем обычный invoke и парсим ответ
    response = llm.invoke(prompt)
    
    # Простой парсинг ответа
    answer = response.content.lower()
    if "profession" in answer or "профессия" in answer:
        card = "profession"
    elif "biology" in answer or "биология" in answer:
        card = "biology"
    elif "health" in answer or "здоровье" in answer:
        card = "health"
    elif "hobby" in answer or "хобби" in answer:
        card = "hobby"
    elif "baggage" in answer or "багаж" in answer:
        card = "baggage"
    elif "fact" in answer or "факт" in answer:
        card = "fact"
    else:
        card = "profession"  # дефолт
    
    return {
        "chosen_card": card,
        "message": f"Игрок {state['current_player_index'] + 1} выбрал: {card}"
    }


def DisclosureCard(state: GameState) -> dict:
    current_player = state["players"][state["current_player_index"]]
    chosen_card = state.get("chosen_card", "profession")
    if state["count_round"] == 1:
        chosen_card = "profession"
    card_value = current_player[chosen_card]
    updated_players = [p.copy() for p in state["players"]]
    updated_players[state["current_player_index"]]["revealed_cards"].append(
        f"{chosen_card}: {card_value}"
    )
    return {
        "players": updated_players,
        "message": f"Игрок {state['current_player_index'] + 1} раскрыл: {chosen_card} - {card_value}"
    }


def discuss(state: GameState) -> dict:
    current_player = state["players"][state["current_player_index"]]
    revealed_info = "\n".join(
        f"Игрок {i+1}: {', '.join(p['revealed_cards']) if p['revealed_cards'] else 'пока ничего не раскрыл'}"
        for i, p in enumerate(state["players"])
        if p["is_alive"]
    )
    alive_count = sum(1 for p in state["players"] if p["is_alive"])
    
    if current_player["is_human"]:
        user_input = interrupt({
            "type": "discuss",
            "question": "Ваше выступление на обсуждении",
            "revealed_cards": revealed_info,
            "alive_count": alive_count,
            "capacity_bunker": state["capacity_bunker"]
        })
        return {
            "message": user_input["discussion"],
            "current_player_index": next_player(state)["current_player_index"]
        }
    
    prompt = (
        f"Ты игрок в Бункер. Твои характеристики:\n"
        f"Профессия - {current_player['profession']}, "
        f"Биология - {current_player['biology']}, "
        f"Факт - {current_player['fact']}.\n"
        f"Раунд {state['count_round']}. Мест в бункере: {state['capacity_bunker']}. "
        f"Игроков осталось: {alive_count}.\n"
        f"Раскрытые карты:\n{revealed_info}\n"
        "Выступите на обсуждении: защитите себя и предложите, кого выгнать."
    )
    response = llm.invoke(prompt)
    return {
        "message": response.content,
        "current_player_index": next_player(state)["current_player_index"]
    }


def vote(state: GameState) -> dict:
    current_player = state["players"][state["current_player_index"]]
    votes = state.get("votes", {}).copy()
    alive_indices = [
        i for i, p in enumerate(state["players"])
        if p["is_alive"] and i != state["current_player_index"]
    ]
    revealed_info = "\n".join(
        f"Игрок {i+1}: {', '.join(p['revealed_cards'])}"
        for i, p in enumerate(state["players"])
        if p["is_alive"]
    )
    
    if current_player["is_human"]:
        user_input = interrupt({
            "type": "vote",
            "question": "Кого вы хотите выгнать?",
            "alive_players": [f"Игрок {i+1}" for i in alive_indices],
            "revealed_cards": revealed_info
        })
        target = user_input["target_player"] - 1
        votes[target] = votes.get(target, 0) + 1
        return {
            "votes": votes,
            "message": f"Вы проголосовали за игрока {user_input['target_player']}"
        }
    
    alive_list = ", ".join(f"Игрок {i+1}" for i in alive_indices)
    prompt = (
        f"Голосование в Бункере. Раскрытые карты:\n{revealed_info}\n"
        f"Живые игроки (кроме тебя): {alive_list}\n"
        "Выбери ОДНОГО игрока для выгона. Ответь ТОЛЬКО номером игрока (1-7)."
    )
    
    response = llm.invoke(prompt)
    
    # Парсим номер игрока из ответа
    answer = response.content
    target = None
    for i in alive_indices:
        if str(i + 1) in answer:
            target = i
            break
    
    if target is None:
        target = alive_indices[0]  # дефолт
    
    votes[target] = votes.get(target, 0) + 1
    return {
        "votes": votes,
        "message": f"Игрок {state['current_player_index'] + 1} проголосовал за игрока {target + 1}"
    }


def eliminate_player(state: GameState) -> dict:
    votes = state.get("votes", {})
    if not votes:
        return {"message": "Нет голосов"}
    eliminated_index = max(votes, key=votes.get)
    updated_players = [p.copy() for p in state["players"]]
    updated_players[eliminated_index]["is_alive"] = False
    return {
        "players": updated_players,
        "votes": {},
        "message": (
            f"Игрок {eliminated_index + 1} ({updated_players[eliminated_index]['profession']}) "
            f"исключён с {votes[eliminated_index]} голосами!"
        )
    }