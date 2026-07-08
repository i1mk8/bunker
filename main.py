from graph import graph
from state import GameState
from langgraph.types import Command


def create_initial_state() -> dict:
    """Создание начального состояния игры"""
    players = [
        {
            "profession": "Врач", "biology": "Человек", "health": "100",
            "hobby": "Шахматы", "baggage": "Аптечка", "fact": "Не курит",
            "is_human": True, "is_alive": True, "revealed_cards": []
        },
        {
            "profession": "Инженер", "biology": "Человек", "health": "90",
            "hobby": "Рыбалка", "baggage": "Инструменты", "fact": "Знает 3 языка",
            "is_human": False, "is_alive": True, "revealed_cards": []
        },
        {
            "profession": "Повар", "biology": "Человек", "health": "85",
            "hobby": "Кулинария", "baggage": "Набор специй", "fact": "Вегетарианец",
            "is_human": False, "is_alive": True, "revealed_cards": []
        },
        {
            "profession": "Учитель", "biology": "Человек", "health": "95",
            "hobby": "Чтение", "baggage": "Книги", "fact": "Имеет 5 детей",
            "is_human": False, "is_alive": True, "revealed_cards": []
        },
        {
            "profession": "Фермер", "biology": "Человек", "health": "100",
            "hobby": "Садоводство", "baggage": "Семена", "fact": "Аллергия на пыль",
            "is_human": False, "is_alive": True, "revealed_cards": []
        },
        {
            "profession": "Психолог", "biology": "Человек", "health": "80",
            "hobby": "Медитация", "baggage": "Дневник", "fact": "Бывшая актриса",
            "is_human": False, "is_alive": True, "revealed_cards": []
        },
        {
            "profession": "Военный", "biology": "Человек", "health": "100",
            "hobby": "Стрельба", "baggage": "Оружие", "fact": "Пацифист",
            "is_human": False, "is_alive": True, "revealed_cards": []
        },
    ]
    return {
        "players": players,
        "current_player_index": 0,
        "count_round": 1,
        "capacity_bunker": 3,
        "count_player": 7,
        "message": "",
        "chosen_card": "",
        "votes": {},
        "round_started": False,
        "players_done_in_round": 0,  # ← НОВОЕ
    }


def get_human_input(state: GameState, node_name: str) -> dict:
    """Получение ввода от живого игрока с валидацией"""
    current_player = state["players"][state["current_player_index"]]
    
    print("\n" + "=" * 60)
    
    if node_name == "choice_card":
        print("🎴 ВАШ ХОД — ВЫБОР КАРТЫ")
        print("=" * 60)
        print(f"\nРаунд: {state['count_round']}")
        print("\nВаши карты:")
        for card in ["profession", "biology", "health", "hobby", "baggage", "fact"]:
            print(f"  • {card}: {current_player[card]}")
        
        valid_cards = ["profession", "biology", "health", "hobby", "baggage", "fact"]
        while True:
            choice = input("\nВаш выбор (profession/biology/health/hobby/baggage/fact): ").strip().lower()
            if choice in valid_cards:
                break
            print(f"❌ Некорректный ввод. Допустимые значения: {', '.join(valid_cards)}")
        
        return {"card_choice": choice, "chosen_card": choice}

    elif node_name == "discuss":
        print("💬 ВАШ ХОД — ОБСУЖДЕНИЕ")
        print("=" * 60)
        revealed_info = "\n".join(
            f"Игрок {i+1}: {', '.join(p['revealed_cards']) if p['revealed_cards'] else 'пока ничего не раскрыл'}"
            for i, p in enumerate(state["players"])
            if p["is_alive"]
        )
        print(f"\nРаскрытые карты:\n{revealed_info}")
        alive_count = sum(1 for p in state["players"] if p["is_alive"])
        print(f"Живых игроков: {alive_count}")
        print(f"Мест в бункере: {state['capacity_bunker']}")
        
        while True:
            discussion = input("\nВаше выступление: ").strip()
            if discussion:
                break
            print("❌ Введите текст выступления (не может быть пустым)")
        
        next_idx = state["current_player_index"] + 1
        while next_idx < len(state["players"]) and not state["players"][next_idx]["is_alive"]:
            next_idx += 1
        if next_idx >= len(state["players"]):
            next_idx = 0
            while next_idx < len(state["players"]) and not state["players"][next_idx]["is_alive"]:
                next_idx += 1
        
        return {
            "discussion": discussion,
            "message": discussion,
            "current_player_index": next_idx
        }

    elif node_name == "vote":
        print("🗳️ ВАШ ХОД — ГОЛОСОВАНИЕ")
        print("=" * 60)
        alive_indices = [
            i for i, p in enumerate(state["players"])
            if p["is_alive"] and i != state["current_player_index"]
        ]
        print("\nЖивые игроки:")
        for i in alive_indices:
            print(f"  • Игрок {i+1} ({state['players'][i]['profession']})")
        revealed_info = "\n".join(
            f"Игрок {i+1}: {', '.join(p['revealed_cards'])}"
            for i, p in enumerate(state["players"])
            if p["is_alive"]
        )
        print(f"\nРаскрытые карты:\n{revealed_info}")
        
        while True:
            target = input(f"\nНомер игрока для выгона (1-7, кроме {state['current_player_index'] + 1}): ").strip()
            if not target:
                print("❌ Введите номер игрока")
                continue
            try:
                target_num = int(target)
                if 1 <= target_num <= 7 and (target_num - 1) in alive_indices:
                    break
                print(f"❌ Некорректный номер. Допустимые: {[i+1 for i in alive_indices]}")
            except ValueError:
                print("❌ Введите число от 1 до 7")
        
        votes = state.get("votes", {})
        target_idx = target_num - 1
        votes[target_idx] = votes.get(target_idx, 0) + 1
        
        return {"votes": votes, "target_player": target_num}

    return {}


def main():
    config = {"configurable": {"thread_id": "game-1"}}
    initial_state = create_initial_state()

    print("🚀 Игра 'Бункер' начинается!")
    print(f"Игроков: {initial_state['count_player']}")
    print(f"Мест в бункере: {initial_state['capacity_bunker']}")
    print("=" * 60)

    # Первый запуск
    result = graph.invoke(initial_state, config)
    
    # Цикл обработки остановок
    while True:
        state_snapshot = graph.get_state(config)
        
        print(f"\n[ОТЛАДКА] Состояние графа:")
        print(f"  next: {state_snapshot.next}")
        
        # Если граф завершён
        if not state_snapshot.next:
            print("\n[ОТЛАДКА] Граф завершён")
            break
        
        next_node = state_snapshot.next[0]
        current_state = state_snapshot.values
        
        print(f"[ОТЛАДКА] Следующая нода: {next_node}")
        
        # Проверяем, живой ли текущий игрок
        current_player = current_state["players"][current_state["current_player_index"]]
        
        if current_player["is_human"] and next_node in ["choice_card", "discuss", "vote"]:
            # Живой игрок — получаем ввод
            print(f"\n[ОТЛАДКА] Живой игрок, нода {next_node} — ждём ввод")
            updates = get_human_input(current_state, next_node)
            
            # ⚠️ КЛЮЧЕВОЕ: используем Command(resume=...) для возобновления
            print(f"[ОТЛАДКА] Возобновляем граф с данными: {updates}")
            result = graph.invoke(Command(resume=updates), config)
        else:
            # LLM-бот или другая нода — просто продолжаем
            print(f"[ОТЛАДКА] LLM-бот или служебная нода — продолжаем")
            result = graph.invoke(None, config)

    # Финальное состояние
    final_state = graph.get_state(config).values
    print("\n" + "=" * 60)
    print("🏁 ИГРА ЗАВЕРШЕНА")
    print("=" * 60)
    print(f"\n{final_state.get('message', '')}")
    print(f"Раундов сыграно: {final_state.get('count_round', 0)}")


if __name__ == "__main__":
    main()