from graph import app
from langgraph.types import Command


def create_initial_state() -> dict:
    """Создание начального состояния игры: 1 живой + 6 LLM-ботов"""
    players = [
        {
            "profession": "Врач",
            "biology": "Человек",
            "health": "100",
            "hobby": "Шахматы",
            "baggage": "Аптечка",
            "fact": "Не курит",
            "is_human": True,   # живой игрок
            "is_alive": True,
            "revealed_cards": []
        },
        {
            "profession": "Инженер",
            "biology": "Человек",
            "health": "90",
            "hobby": "Рыбалка",
            "baggage": "Инструменты",
            "fact": "Знает 3 языка",
            "is_human": False,
            "is_alive": True,
            "revealed_cards": []
        },
        {
            "profession": "Повар",
            "biology": "Человек",
            "health": "85",
            "hobby": "Кулинария",
            "baggage": "Набор специй",
            "fact": "Вегетарианец",
            "is_human": False,
            "is_alive": True,
            "revealed_cards": []
        },
        {
            "profession": "Учитель",
            "biology": "Человек",
            "health": "95",
            "hobby": "Чтение",
            "baggage": "Книги",
            "fact": "Имеет 5 детей",
            "is_human": False,
            "is_alive": True,
            "revealed_cards": []
        },
        {
            "profession": "Фермер",
            "biology": "Человек",
            "health": "100",
            "hobby": "Садоводство",
            "baggage": "Семена",
            "fact": "Аллергия на пыль",
            "is_human": False,
            "is_alive": True,
            "revealed_cards": []
        },
        {
            "profession": "Психолог",
            "biology": "Человек",
            "health": "80",
            "hobby": "Медитация",
            "baggage": "Дневник",
            "fact": "Бывшая актриса",
            "is_human": False,
            "is_alive": True,
            "revealed_cards": []
        },
        {
            "profession": "Военный",
            "biology": "Человек",
            "health": "100",
            "hobby": "Стрельба",
            "baggage": "Оружие",
            "fact": "Пацифист",
            "is_human": False,
            "is_alive": True,
            "revealed_cards": []
        },
    ]

    return {
        "players": players,
        "current_player_index": 0,
        "count_round": 1,
        "capacity_bunker": 6,
        "count_player": 7,
        "message": "",
        "chosen_card": "",
        "votes": {},
    }


def handle_interrupt(result, config):
    """Обработка interrupt — когда граф ждёт ввод от пользователя"""
    if "__interrupt__" not in result:
        return result

    interrupt_info = result["__interrupt__"][0]
    data = interrupt_info.value

    print("\n" + "=" * 60)

    # Выбор карты
    if data.get("type") == "choice_card":
        print("🎴 ВАШ ХОД — ВЫБОР КАРТЫ")
        print("=" * 60)
        print(f"\n{data['question']}")
        print(f"Раунд: {data['round']}")
        print("\nВаши карты:")
        for card, value in data["your_cards"].items():
            print(f"  • {card}: {value}")

        choice = input("\nВаш выбор (profession/biology/health/hobby/baggage/fact): ").strip()
        return app.invoke(Command(resume={"card_choice": choice}), config)

    # Обсуждение
    elif data.get("type") == "discuss":
        print("💬 ВАШ ХОД — ОБСУЖДЕНИЕ")
        print("=" * 60)
        print(f"\n{data['question']}")
        print(f"\nРаскрытые карты:\n{data['revealed_cards']}")
        print(f"Живых игроков: {data['alive_count']}")
        print(f"Мест в бункере: {data['capacity_bunker']}")

        discussion = input("\nВаше выступление: ")
        return app.invoke(Command(resume={"discussion": discussion}), config)

    # Голосование
    elif data.get("type") == "vote":
        print("🗳️ ВАШ ХОД — ГОЛОСОВАНИЕ")
        print("=" * 60)
        print(f"\n{data['question']}")
        print("\nЖивые игроки:")
        for p in data["alive_players"]:
            print(f"  • {p}")
        print(f"\nРаскрытые карты:\n{data['revealed_cards']}")

        target = input("\nНомер игрока для выгона (1-7): ").strip()
        return app.invoke(Command(resume={"target_player": int(target)}), config)

    return result


def main():
    # Конфигурация сессии
    config = {"configurable": {"thread_id": "game-1"}}

    # Начальное состояние
    initial_state = create_initial_state()

    print("🚀 Игра 'Бункер' начинается!")
    print(f"Игроков: {initial_state['count_player']}")
    print(f"Мест в бункере: {initial_state['capacity_bunker']}")
    print("=" * 60)

    # Запускаем граф
    result = app.invoke(initial_state, config)

    # Обрабатываем interrupt'ы в цикле
    while "__interrupt__" in result:
        result = handle_interrupt(result, config)

    # Финальное состояние
    print("\n" + "=" * 60)
    print("🏁 ИГРА ЗАВЕРШЕНА")
    print("=" * 60)
    print(f"\n{result.get('message', '')}")
    print(f"Раундов сыграно: {result.get('count_round', 0)}")


if __name__ == "__main__":
    main()