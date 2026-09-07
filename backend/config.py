import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

LlmProvider = Literal[
    "gemini",
    "openai",
    "deepseek",
    "qwen",
]


class Settings(BaseSettings):
    career_data_dir: str = "./data"

    default_llm_provider: LlmProvider = "gemini"

    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-3.5-flash-lite"

    model_config = SettingsConfigDict(
        env_file=Path(__file__).with_name(".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def resolved_data_dir(self) -> Path:
        expanded_path = os.path.expandvars(
            os.path.expanduser(self.career_data_dir)
        )

        data_path = Path(expanded_path)

        if not data_path.is_absolute():
            data_path = PROJECT_ROOT / data_path

        return data_path.resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()