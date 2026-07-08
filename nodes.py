import requests
import time
from langgraph.types import interrupt
from state import GameState


def call_lm_studio(prompt: str, max_tokens: int = 200, retries: int = 3) -> str:
    """Прямой HTTP-запрос к LM Studio с retry"""
    url = "http://localhost:1234/v1/chat/completions"
    
    payload = {
        "model": "meta-llama-3.1-8b-instruct",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": max_tokens,
        "stream": False
    }
    
    for attempt in range(retries):
        try:
            print(f"  → Отправляем запрос в LM Studio (попытка {attempt + 1}/{retries})...")
            response = requests.post(url, json=payload, timeout=60)
            
            print(f"  → Статус: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if "choices" in data and len(data["choices"]) > 0:
                    content = data["choices"][0]["message"]["content"]
                    print(f"  → Успех! Ответ: {content[:80]}")
                    return content
                else:
                    print(f"  → Ответ без choices: {data}")
                    return ""
            else:
                print(f"  → Ошибка {response.status_code}: {response.text[:100]}")
                return ""
                
        except Exception as e:
            print(f"  → Ошибка запроса (попытка {attempt + 1}): {e}")
            if attempt < retries - 1:
                print(f"  → Ждём 3 секунды перед повторной попыткой...")
                time.sleep(3)
    
    print(f"  → Все {retries} попыток не удались")
    return ""


# ============================================================
# ПРОВЕРОЧНЫЕ ФУНКЦИИ
# ============================================================

def check_condition(state: GameState) -> str:
    alive_count = sum(1 for p in state["players"] if p["is_alive"])
    capacity = state["capacity_bunker"]
    
    print(f"\n[ОТЛАДКА] check_condition:")
    print(f"  Живых игроков: {alive_count}, Мест: {capacity}")
    
    if alive_count <= capacity:
        print("  → Игра окончена")
        return "Игра окончена"
    print("  → Игра продолжается")
    return "Игра продолжается"


def check_all_players_done(state: GameState) -> str:
    """Проверка, прошли ли все игроки ход"""
    alive_count = sum(1 for p in state["players"] if p["is_alive"])
    done_count = state.get("players_done_in_round", 0)
    
    print(f"\n[ОТЛАДКА] check_all_players_done:")
    print(f"  Живых игроков: {alive_count}")
    print(f"  Прошло ход: {done_count}")
    
    if done_count >= alive_count:
        print("  → Раунд окончен")
        return "Раунд окончен"
    
    print("  → Продолжаем")
    return "Продолжаем"


def check_all_voted(state: GameState) -> str:
    alive_count = sum(1 for p in state["players"] if p["is_alive"])
    voted_count = sum(state.get("votes", {}).values())
    
    print(f"\n[ОТЛАДКА] check_all_voted: живых={alive_count}, голосов={voted_count}")
    
    if voted_count >= alive_count:
        print("  → Все проголосовали")
        return "Все проголосовали"
    print("  → Продолжаем голосование")
    return "Продолжаем голосование"


# ============================================================
# СЧЁТЧИКИ И СООБЩЕНИЯ
# ============================================================

def increment_round(state: GameState) -> dict:
    new_round = state["count_round"] + 1
    
    first_alive = 0
    while first_alive < len(state["players"]) and not state["players"][first_alive]["is_alive"]:
        first_alive += 1
    
    print(f"\n[ОТЛАДКА] increment_round: {state['count_round']} → {new_round}, index → {first_alive}")
    
    return {
        "count_round": new_round,
        "current_player_index": first_alive,
        "round_started": False,
        "players_done_in_round": 0,  # ← сброс счётчика
    }


def generate_end_game_message(state: GameState) -> dict:
    alive_players = [
        f"Игрок {i+1} ({p['profession']})"
        for i, p in enumerate(state["players"])
        if p["is_alive"]
    ]
    print(f"\n[ОТЛАДКА] generate_end_game_message: выжили {len(alive_players)}")
    return {"message": f"Игра окончена! Выжили: {', '.join(alive_players)}"}


def next_voter(state: GameState) -> dict:
    next_index = state["current_player_index"] + 1
    while next_index < len(state["players"]) and not state["players"][next_index]["is_alive"]:
        next_index += 1
    if next_index >= len(state["players"]):
        next_index = 0
        while next_index < len(state["players"]) and not state["players"][next_index]["is_alive"]:
            next_index += 1
    
    print(f"\n[ОТЛАДКА] next_voter: {state['current_player_index']} → {next_index}")
    return {"current_player_index": next_index}


# ============================================================
# ФАЗА 1: ВЫБОР КАРТЫ
# ============================================================

def ChoiceCard(state: GameState) -> dict:
    current_player = state["players"][state["current_player_index"]]
    print(f"\n[ОТЛАДКА] ChoiceCard: игрок {state['current_player_index'] + 1}, is_human={current_player['is_human']}")
    
    # Увеличиваем счётчик игроков, прошедших ход
    current_done = state.get("players_done_in_round", 0)
    updates = {
        "round_started": True,
        "players_done_in_round": current_done + 1
    }
    
    if current_player["is_human"]:
        print("  → interrupt: ждём ввод от живого игрока")
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
        
        print(f"  → Получены данные от пользователя: {user_input}")
        chosen = user_input.get("card_choice", user_input.get("chosen_card", "profession"))
        
        return {
            **updates,
            "chosen_card": chosen,
            "message": f"Вы выбрали карту: {chosen}"
        }
    
    print("  → вызов LLM для выбора карты")
    prompt = (
        f"Ты игрок в Бункер. Твои характеристики:\n"
        f"Профессия - {current_player['profession']}, "
        f"Биология - {current_player['biology']}, "
        f"Здоровье - {current_player['health']}, "
        f"Хобби - {current_player['hobby']}, "
        f"Багаж - {current_player['baggage']}, "
        f"Факт - {current_player['fact']}.\n"
        f"Раунд {state['count_round']}. Выбери ОДНУ карту для раскрытия.\n"
        "Ответь ТОЛЬКО одним словом из списка: profession, biology, health, hobby, baggage, fact"
    )
    
    answer = call_lm_studio(prompt)
    if not answer:
        answer = "profession"
    
    answer = answer.lower().strip()
    valid_cards = ["profession", "biology", "health", "hobby", "baggage", "fact"]
    card = "profession"
    for c in valid_cards:
        if c in answer:
            card = c
            break
    
    print(f"  → Выбранная карта: {card}")
    return {
        **updates,
        "chosen_card": card,
        "message": f"Игрок {state['current_player_index'] + 1} выбрал: {card}"
    }


# ============================================================
# ФАЗА 2: РАСКРЫТИЕ КАРТЫ
# ============================================================

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
    
    print(f"\n[ОТЛАДКА] DisclosureCard: игрок {state['current_player_index'] + 1} раскрыл {chosen_card} = {card_value}")
    
    return {
        "players": updated_players,
        "message": f"Игрок {state['current_player_index'] + 1} раскрыл: {chosen_card} - {card_value}"
    }


# ============================================================
# ФАЗА 3: ОБСУЖДЕНИЕ
# ============================================================

def discuss(state: GameState) -> dict:
    current_player = state["players"][state["current_player_index"]]
    print(f"\n[ОТЛАДКА] discuss: игрок {state['current_player_index'] + 1}, is_human={current_player['is_human']}")
    
    revealed_info = "\n".join(
        f"Игрок {i+1}: {', '.join(p['revealed_cards']) if p['revealed_cards'] else 'пока ничего не раскрыл'}"
        for i, p in enumerate(state["players"])
        if p["is_alive"]
    )
    alive_count = sum(1 for p in state["players"] if p["is_alive"])
    
    if current_player["is_human"]:
        print("  → interrupt: ждём выступление от живого игрока")
        user_input = interrupt({
            "type": "discuss",
            "question": "Ваше выступление на обсуждении",
            "revealed_cards": revealed_info,
            "alive_count": alive_count,
            "capacity_bunker": state["capacity_bunker"]
        })
        
        print(f"  → Получены данные: {user_input}")
        discussion_text = user_input.get("discussion", user_input.get("message", ""))
        
        next_idx = state["current_player_index"] + 1
        while next_idx < len(state["players"]) and not state["players"][next_idx]["is_alive"]:
            next_idx += 1
        if next_idx >= len(state["players"]):
            next_idx = 0
            while next_idx < len(state["players"]) and not state["players"][next_idx]["is_alive"]:
                next_idx += 1
        
        return {
            "message": discussion_text,
            "current_player_index": next_idx
        }
    
    print("  → вызов LLM для обсуждения")
    prompt = (
        f"Ты игрок в Бункер. Твои характеристики:\n"
        f"Профессия - {current_player['profession']}, "
        f"Биология - {current_player['biology']}, "
        f"Факт - {current_player['fact']}.\n"
        f"Раунд {state['count_round']}. Мест: {state['capacity_bunker']}. "
        f"Игроков осталось: {alive_count}.\n"
        f"Раскрытые карты:\n{revealed_info}\n"
        "Выступите на обсуждении (2-3 предложения): защитите себя и предложите, кого выгнать."
    )
    
    message = call_lm_studio(prompt, max_tokens=300)
    if not message:
        message = "Я считаю, что все игроки полезны."
    
    next_idx = state["current_player_index"] + 1
    while next_idx < len(state["players"]) and not state["players"][next_idx]["is_alive"]:
        next_idx += 1
    if next_idx >= len(state["players"]):
        next_idx = 0
        while next_idx < len(state["players"]) and not state["players"][next_idx]["is_alive"]:
            next_idx += 1
    
    return {
        "message": message,
        "current_player_index": next_idx
    }


# ============================================================
# ФАЗА 4: ГОЛОСОВАНИЕ
# ============================================================

def vote(state: GameState) -> dict:
    current_player = state["players"][state["current_player_index"]]
    votes = state.get("votes", {}).copy()
    alive_indices = [
        i for i, p in enumerate(state["players"])
        if p["is_alive"] and i != state["current_player_index"]
    ]
    
    print(f"\n[ОТЛАДКА] vote: игрок {state['current_player_index'] + 1}, is_human={current_player['is_human']}")
    
    revealed_info = "\n".join(
        f"Игрок {i+1}: {', '.join(p['revealed_cards'])}"
        for i, p in enumerate(state["players"])
        if p["is_alive"]
    )
    
    if current_player["is_human"]:
        print("  → interrupt: ждём голос от живого игрока")
        user_input = interrupt({
            "type": "vote",
            "question": "Кого вы хотите выгнать?",
            "alive_players": [f"Игрок {i+1}" for i in alive_indices],
            "revealed_cards": revealed_info
        })
        
        print(f"  → Получены данные: {user_input}")
        target = user_input.get("target_player", 1) - 1
        votes[target] = votes.get(target, 0) + 1
        return {
            "votes": votes,
            "message": f"Вы проголосовали за игрока {target + 1}"
        }
    
    print("  → вызов LLM для голосования")
    alive_list = ", ".join(f"Игрок {i+1}" for i in alive_indices)
    prompt = (
        f"Голосование в Бункере. Раскрытые карты:\n{revealed_info}\n"
        f"Живые игроки (кроме тебя): {alive_list}\n"
        "Выбери ОДНОГО игрока для выгона. Ответь ТОЛЬКО номером (1-7)."
    )
    
    answer = call_lm_studio(prompt, max_tokens=50)
    
    target = None
    for i in alive_indices:
        if str(i + 1) in answer:
            target = i
            break
    
    if target is None:
        target = alive_indices[0]
    
    votes[target] = votes.get(target, 0) + 1
    print(f"  → Голос за игрока {target + 1}")
    
    return {
        "votes": votes,
        "message": f"Игрок {state['current_player_index'] + 1} проголосовал за игрока {target + 1}"
    }


# ============================================================
# ФАЗА 5: ИСКЛЮЧЕНИЕ ИГРОКА
# ============================================================

def eliminate_player(state: GameState) -> dict:
    votes = state.get("votes", {})
    print(f"\n[ОТЛАДКА] eliminate_player: голоса = {votes}")
    
    if not votes:
        return {"message": "Нет голосов"}
    
    eliminated_index = max(votes, key=votes.get)
    updated_players = [p.copy() for p in state["players"]]
    updated_players[eliminated_index]["is_alive"] = False
    
    new_index = state["current_player_index"]
    if not updated_players[new_index]["is_alive"]:
        new_index += 1
        while new_index < len(updated_players) and not updated_players[new_index]["is_alive"]:
            new_index += 1
        if new_index >= len(updated_players):
            new_index = 0
    
    print(f"  → Исключён игрок {eliminated_index + 1} ({updated_players[eliminated_index]['profession']})")
    
    return {
        "players": updated_players,
        "votes": {},
        "current_player_index": new_index,
        "round_started": False,
        "players_done_in_round": 0,
        "message": (
            f"Игрок {eliminated_index + 1} ({updated_players[eliminated_index]['profession']}) "
            f"исключён с {votes[eliminated_index]} голосами!"
        )
    }