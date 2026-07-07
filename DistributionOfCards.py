import json
import random 

def generate_bunker_card(num_players, file_path='roles.json'):
    titles = {
        "Profession": "Профессия",
        "Biology": "Биология",
        "Health": "Здоровье",
        "Hobby": "Хобби",
        "Baggage": "Багаж",
        "Fact": "Факт"
    }

    with open(file_path, 'r', encoding='utf-8') as f:
        roles_data = json.load(f)

    # Словарь для хранения карт по каждому игроку
    players_cards = {i: [] for i in range(1, num_players + 1)}

    # Проходимся по каждой категории
    for category, title in titles.items():
        # random.sample берет ровно num_players уникальных карт без повторений
        drawn_cards = random.sample(roles_data[category], num_players)
        
        # Распределяем вытянутые карты по игрокам
        for i, card in enumerate(drawn_cards):
            players_cards[i + 1].append(f"{title}: {card}")

    # Собираем красивый вывод
    result = ""
    for player_id, cards in players_cards.items():
        result += f"Игрок {player_id}:\n"
        result += "\n".join(cards) + "\n\n"

    return result.strip()

if __name__ == "__main__":
    players_count = 5
    print(generate_bunker_card(players_count))