from typing import Any

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_cache() -> dict[str, Any]:
    return {
        "ttl": 300,
        "key": None,
        "namespace": None,
        "key_builder": None,
        "skip_cache_func": lambda _: False,
        "serializer": None,
        "plugins": None,
        "alias": None,
        "noself": lambda _: False,
    }


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=(".env", ".secrets.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    ASYNC_CACHED_CONFIG: dict = Field(
        default_factory=_default_cache, description="Cache settings for aiocache"
    )

    # secrets
    OPENAI_API_KEY: SecretStr | None = None
    OPENROUTER_API_KEY: SecretStr | None = None
    EXA_API_KEY: SecretStr | None = None
    PERPLEXITY_API_KEY: SecretStr | None = None


settings = Settings()
