"""Конфигурация приложения: чтение настроек из переменных окружения и .env."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Настройки игры и подключения к языковой модели.

    Значения берутся из переменных окружения с префиксом BUNKER_ или из файла
    .env; при их отсутствии применяются значения по умолчанию.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="BUNKER_",
        extra="ignore",
        protected_namespaces=(),
    )

    lm_base_url: str = "http://localhost:1234/v1"
    lm_api_key: str = "lm-studio"
    model_name: str = "meta-llama-3.1-8b-instruct"
    temperature: float = 0.7
    decision_temperature: float = 0.2
    max_tokens: int = 300
    request_timeout: int = 60
    retries: int = 3
    structured_method: str = "json_schema"

    capacity: int = 3
    players_count: int = 7
    human_seat: int = 0
    cards_dir: Path = PROJECT_ROOT / "data" / "cards"
    deal_seed: int | None = None
    memory_window: int = 3
    thread_id: str = "game-1"


settings = Settings()
