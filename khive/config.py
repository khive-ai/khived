from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )

    CACHED_CONFIG: dict = {
        "ttl": 300,
        "key": None,
        "namespace": None,
        "key_builder": None,
        "skip_cache_func": lambda x: False,
        "serializer": None,
        "plugins": None,
        "alias": None,
        "noself": lambda x: False,
    }

    OPENAI_API_KEY: str | None = None
    OPENROUTER_API_KEY: str | None = None
    EXA_API_KEY: str | None = None
    PERPLEXITY_API_KEY: str | None = None

    CACHED_CONFIG_KEY: str = Field("CACHED_CONFIG", env="CACHED_CONFIG_KEY")


settings = Settings()
