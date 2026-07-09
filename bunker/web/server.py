"""HTTP-сервер веб-интерфейса: отдаёт статику и продвигает партию по ответам."""

import logging
import threading
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from bunker.web import serialize
from bunker.web.session import GameSession

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"

HOST = "127.0.0.1"
PORT = 8000

session = GameSession()


class AnswerIn(BaseModel):
    """Ответ человека на текущее прерывание графа (поля зависят от типа хода)."""

    card: str | None = None
    target_id: int | None = None
    text: str | None = None
    new_notes: str = ""


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Стартует партию при запуске сервера (одна игра на процесс)."""
    session.start()
    yield


app = FastAPI(title="Бункер", lifespan=lifespan)


@app.get("/")
def index() -> FileResponse:
    """Отдаёт одностраничный интерфейс."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/state")
def get_state() -> dict:
    """Возвращает текущий снапшот партии (для загрузки и поллинга)."""
    return serialize.serialize_state(session)


@app.post("/api/restart")
def restart() -> dict:
    """Начинает новую партию с новой раздачей."""
    session.restart()
    return serialize.serialize_state(session)


@app.post("/api/answer")
def answer(payload: AnswerIn) -> dict:
    """Принимает ход человека, валидирует его и продолжает партию."""
    pending = session.pending
    if session.status != "awaiting_human" or not pending:
        raise HTTPException(status_code=409, detail="Сейчас не ход человека.")

    resume = _build_resume(pending, payload)
    if not session.submit(resume):
        raise HTTPException(status_code=409, detail="Ход уже обработан.")
    return serialize.serialize_state(session)


def _build_resume(pending: dict, payload: AnswerIn) -> dict | str:
    """Строит значение resume под тип прерывания, отвергая некорректный ввод."""
    kind = pending["type"]
    if kind == "reveal":
        valid = {key for _, key in pending["hidden"]}
        if payload.card not in valid:
            raise HTTPException(status_code=400, detail="Нужно выбрать доступную карту.")
        return {"card": payload.card, "new_notes": payload.new_notes}
    if kind == "vote":
        valid = {candidate["id"] for candidate in pending["candidates"]}
        if payload.target_id not in valid:
            raise HTTPException(status_code=400, detail="Нужно выбрать кандидата из списка.")
        return {"target_id": payload.target_id, "new_notes": payload.new_notes}
    if kind in {"discuss", "last_word"}:
        text = (payload.text or "").strip()
        if not text:
            raise HTTPException(status_code=400, detail="Текст не может быть пустым.")
        return text
    raise HTTPException(status_code=400, detail=f"Неизвестный тип хода: {kind}")


app.mount("/static", StaticFiles(directory=STATIC_DIR, check_dir=False), name="static")


def run() -> None:
    """Запускает сервер и открывает интерфейс в браузере."""
    import uvicorn

    logging.basicConfig(level=logging.WARNING, format="[%(levelname)s] %(message)s")
    url = f"http://{HOST}:{PORT}"
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    logger.warning("Бункер: веб-интерфейс на %s", url)
    uvicorn.run(app, host=HOST, port=PORT)
