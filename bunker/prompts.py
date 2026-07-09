"""Русские промпты ведущего и сборка контекста памяти для игроков-ботов."""

from bunker.config import settings
from bunker.state import CARD_CATEGORIES, CATEGORY_LABELS, GameState, Player

SYSTEM_RULES = (
    "Ты — игрок социально-дедуктивной игры Бункер. Произошла катастрофа, в бункере "
    "ограниченное число мест. Каждый раунд игроки раскрывают по одной своей "
    "характеристике, обсуждают и анонимно голосуют за исключение одного участника. "
    "Твоя цель — убедить остальных в своей полезности и остаться в бункере. "
    "Отвечай кратко, по-русски и в характере своего персонажа. "
    "Не используй Markdown-разметку (звёздочки, решётки, списки) — пиши обычным текстом."
)


def _render_hand(player: Player) -> str:
    """Возвращает описание карт игрока с пометкой уже раскрытых."""
    lines = ["Твои карты:"]
    for category in CARD_CATEGORIES:
        mark = " — раскрыта всем" if category in player.revealed else ""
        lines.append(f"  {CATEGORY_LABELS[category]}: {player.cards[category]}{mark}")
    return "\n".join(lines)


def _render_alive(state: GameState) -> str:
    """Возвращает публичное состояние стола: раунд, места и раскрытые карты живых."""
    header = f"Раунд {state['round_no']}. Мест в бункере: {state['capacity']}."
    lines = [header, "Живые игроки и раскрытые ими карты:"]
    for player in state["players"]:
        if not player.is_alive:
            continue
        revealed = ", ".join(
            f"{CATEGORY_LABELS[category]}: {player.cards[category]}" for category in player.revealed
        )
        lines.append(f"  #{player.id} {player.name}: {revealed or 'пока ничего не раскрыл'}")
    return "\n".join(lines)


def _render_log(state: GameState) -> str:
    """Возвращает события последних memory_window раундов из публичного журнала."""
    min_round = state["round_no"] - settings.memory_window + 1
    events = [event for event in state["event_log"] if event.round_no >= min_round]
    if not events:
        return ""
    lines = ["Что происходило в недавних раундах:"]
    lines.extend(f"  [Р{event.round_no}] {event.text}" for event in events)
    return "\n".join(lines)


def render_context(state: GameState, player: Player) -> str:
    """Собирает контекст промпта: катастрофа, рука игрока, состояние стола и память."""
    catastrophe = f"Катастрофа этой партии: {state['catastrophe']}"
    blocks = [catastrophe, _render_hand(player), _render_alive(state), _render_log(state)]
    if player.memory.notes:
        blocks.append(f"Твои приватные заметки о партии:\n{player.memory.notes}")
    return "\n\n".join(block for block in blocks if block)


def reveal_messages(state: GameState, player: Player) -> tuple[str, str]:
    """Готовит системный и пользовательский промпты для фазы раскрытия карты."""
    system = (
        f"{SYSTEM_RULES} Сейчас фаза раскрытия карты. Сначала в new_notes запиши только "
        "новые наблюдения этого раунда (кратко); прошлые заметки уже сохранены и показаны "
        "выше — не повторяй их. Затем верни категорию карты для раскрытия."
    )
    hidden = ", ".join(
        f"{CATEGORY_LABELS[category]} ({category})" for category in player.hidden_categories()
    )
    user = (
        f"{render_context(state, player)}\n\n"
        f"Выбери одну из ещё не раскрытых карт, которую выгодно показать сейчас. "
        f"Ещё скрыты: {hidden}."
    )
    return system, user


def discuss_messages(state: GameState, player: Player) -> tuple[str, str]:
    """Готовит промпты для фазы общего обсуждения."""
    system = (
        f"{SYSTEM_RULES} Сейчас общее обсуждение. Говори только о своих уже раскрытых "
        "картах; не упоминай и не намекай на характеристики, которые ещё не раскрыл."
    )
    user = (
        f"{render_context(state, player)}\n\n"
        "Выступи в обсуждении в двух-трёх предложениях: защити своё место в бункере "
        "и по желанию укажи, кто из игроков кажется лишним."
    )
    return system, user


def vote_messages(state: GameState, player: Player, candidates: list[Player]) -> tuple[str, str]:
    """Готовит промпты для анонимного голосования за исключение."""
    system = (
        f"{SYSTEM_RULES} Сейчас анонимное голосование за исключение. Сначала в new_notes "
        "запиши только новые наблюдения этого раунда (кратко); прошлые заметки уже сохранены "
        "и показаны выше — не повторяй их. Затем верни id игрока для исключения."
    )
    listing_lines = []
    for candidate in candidates:
        revealed = ", ".join(
            f"{CATEGORY_LABELS[category]}: {candidate.cards[category]}"
            for category in candidate.revealed
        )
        summary = revealed or "ничего не раскрыл"
        listing_lines.append(f"  id={candidate.id} {candidate.name}: {summary}")
    listing = "\n".join(listing_lines)
    user = (
        f"{render_context(state, player)}\n\n"
        f"Проголосуй за исключение одного игрока. Кандидаты (кроме тебя):\n{listing}\n"
        "Верни id выбранного игрока."
    )
    return system, user


def last_word_messages(state: GameState, player: Player) -> tuple[str, str]:
    """Готовит промпты для последнего слова исключаемого игрока."""
    system = f"{SYSTEM_RULES} Тебя исключают из бункера по итогам голосования."
    user = (
        f"{render_context(state, player)}\n\n"
        "Скажи последнее слово в одном-двух предложениях перед уходом из бункера."
    )
    return system, user
