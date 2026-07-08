"""Взаимодействие с языковой моделью через LangChain (эндпоинт LM Studio)."""

import logging

from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from bunker.config import settings

logger = logging.getLogger(__name__)

FREE_TEXT_FALLBACK = "(модель некорректно ответила)"


def make_llm(temperature: float | None = None) -> ChatOpenAI:
    """Создаёт клиент ChatOpenAI на локальный эндпоинт LM Studio."""
    return ChatOpenAI(
        base_url=settings.lm_base_url,
        api_key=settings.lm_api_key,
        model=settings.model_name,
        temperature=settings.temperature if temperature is None else temperature,
        max_tokens=settings.max_tokens,
        timeout=settings.request_timeout,
        max_retries=0,
    )


def decide[T: BaseModel](schema: type[T], system: str, user: str, default: T) -> T:
    """Возвращает структурированное решение модели.

    Делает settings.retries попыток; при неудаче возвращает default и логирует сбой.
    """
    structured = make_llm(settings.decision_temperature).with_structured_output(
        schema, method=settings.structured_method
    )
    messages = [("system", system), ("user", user)]
    for attempt in range(1, settings.retries + 1):
        try:
            result = structured.invoke(messages)
            return result if isinstance(result, schema) else schema.model_validate(result)
        except Exception as error:
            logger.warning(
                "Ответ модели не разобран (попытка %d/%d): %s", attempt, settings.retries, error
            )
    logger.warning("Модель некорректно ответила — беру запасной вариант")
    return default


def free_text(system: str, user: str) -> str:
    """Возвращает свободную реплику модели; при отказе — запасной текст."""
    llm = make_llm()
    messages = [("system", system), ("user", user)]
    for attempt in range(1, settings.retries + 1):
        try:
            content = llm.invoke(messages).content
            text = content.strip() if isinstance(content, str) else str(content).strip()
            if text:
                return text
        except Exception as error:
            logger.warning(
                "Ошибка запроса реплики (попытка %d/%d): %s", attempt, settings.retries, error
            )
    logger.warning("Модель некорректно ответила — использую запасную реплику")
    return FREE_TEXT_FALLBACK
