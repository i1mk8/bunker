"""Консольный ввод-вывод: единственное место с print и input."""

import sys


def setup_console() -> None:
    """Переключает стандартные потоки на UTF-8 для корректного вывода кириллицы."""
    for stream in (sys.stdout, sys.stdin):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")


def narrate(text: str) -> None:
    """Печатает строку повествования ведущего."""
    print(text)


def read_answer(payload: dict) -> dict | str:
    """Отрисовывает вопрос человека по типу interrupt-payload и возвращает ответ."""
    kind = payload["type"]
    if kind == "reveal":
        return _ask_reveal(payload)
    if kind == "discuss":
        return _ask_speech("Ваше выступление в обсуждении: ")
    if kind == "vote":
        return _ask_vote(payload)
    if kind == "last_word":
        return _ask_speech("Ваше последнее слово: ")
    raise ValueError(f"Неизвестный тип запроса: {kind}")


def _ask_reveal(payload: dict) -> dict:
    print(f"\n=== Раунд {payload['round']}. Ваш ход: раскрытие карты ===")
    print("Ваши карты:")
    for label, value in payload["hand"].items():
        print(f"  {label}: {value}")
    options = payload["hidden"]
    print("Доступно для раскрытия:")
    for number, option in enumerate(options, start=1):
        print(f"  {number}. {option[0]}")
    choice = _read_index("Номер карты для раскрытия: ", len(options))
    return {"card": options[choice - 1][1], "new_notes": ""}


def _ask_vote(payload: dict) -> dict:
    print("\n=== Ваш ход: анонимное голосование за исключение ===")
    candidates = payload["candidates"]
    for number, candidate in enumerate(candidates, start=1):
        print(f"  {number}. {candidate['name']}")
    choice = _read_index("Номер игрока для исключения: ", len(candidates))
    return {"target_id": candidates[choice - 1]["id"], "new_notes": ""}


def _ask_speech(prompt: str) -> str:
    while True:
        text = input(prompt).strip()
        if text:
            return text
        print("Ответ не может быть пустым.")


def _read_index(prompt: str, count: int) -> int:
    while True:
        raw = input(prompt).strip()
        if raw.isdigit() and 1 <= int(raw) <= count:
            return int(raw)
        print(f"Введите число от 1 до {count}.")
