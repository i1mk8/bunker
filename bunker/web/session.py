"""Игровая сессия: гоняет граф в фоновом потоке и хранит состояние для веба."""

import logging
import threading

from langgraph.types import Command

from bunker.cards import create_initial_state
from bunker.config import settings
from bunker.graph import build_graph
from bunker.state import GameState

logger = logging.getLogger(__name__)

RECURSION_LIMIT = 1000  # столько же, сколько в консольном main.py


class GameSession:
    """Одна партия Бункер: продвигает граф до хода человека и хранит снапшот.

    Статусы: ``idle`` (партия не начата), ``advancing`` (ходят боты/граф считает),
    ``awaiting_human`` (ждём ответ человека, см. ``pending``), ``finished`` (игра
    окончена), ``error`` (сбой графа, см. ``error``).
    """

    def __init__(self) -> None:
        """Готовит граф и пустое состояние; партия начинается в start()."""
        self._graph = build_graph()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._counter = 0
        self.values: GameState | None = None
        self.pending: dict | None = None
        self.status = "idle"
        self.error: str | None = None
        self._config = self._new_config()

    def _new_config(self) -> dict:
        """Возвращает конфиг графа с уникальным thread_id для новой партии."""
        self._counter += 1
        thread_id = f"{settings.thread_id}-{self._counter}"
        return {"configurable": {"thread_id": thread_id}, "recursion_limit": RECURSION_LIMIT}

    def start(self) -> None:
        """Создаёт новую партию из настроек и запускает первый ход."""
        state = create_initial_state(
            players_count=settings.players_count,
            capacity=settings.capacity,
            seed=settings.deal_seed,
        )
        with self._lock:
            self.values = state
            self._begin_locked()
        self._spawn(state)

    def restart(self) -> None:
        """Начинает партию заново с новой раздачей."""
        with self._lock:
            self._config = self._new_config()
        self.start()

    def submit(self, answer: dict | str) -> bool:
        """Принимает ответ человека и продолжает партию; False, если сейчас не его ход."""
        with self._lock:
            if self.status != "awaiting_human":
                return False
            self._begin_locked()
        self._spawn(Command(resume=answer))
        return True

    def _begin_locked(self) -> None:
        """Переводит сессию в состояние счёта (вызывать под удержанным локом)."""
        self.status = "advancing"
        self.pending = None
        self.error = None

    def _spawn(self, graph_input: object) -> None:
        """Запускает продвижение графа в фоновом потоке-демоне."""
        thread = threading.Thread(target=self._advance, args=(graph_input,), daemon=True)
        self._thread = thread
        thread.start()

    def _advance(self, graph_input: object) -> None:
        """Гоняет граф до ближайшего прерывания человека или до конца партии."""
        try:
            for chunk in self._graph.stream(graph_input, self._config, stream_mode="values"):
                with self._lock:
                    self.values = chunk
            snapshot = self._graph.get_state(self._config)
            interrupts = getattr(snapshot, "interrupts", ())
            with self._lock:
                self.values = snapshot.values
                if interrupts:
                    self.pending = interrupts[0].value
                    self.status = "awaiting_human"
                else:
                    self.pending = None
                    self.status = "finished"
        except Exception as error:
            logger.exception("Сбой продвижения графа")
            with self._lock:
                self.error = str(error)
                self.status = "error"
