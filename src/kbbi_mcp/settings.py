from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class KBBISettings(BaseSettings):
    """Runtime configuration for KBBI integration.

    Values are read from the environment (prefix: `KBBI_`).
    """

    model_config = SettingsConfigDict(
        env_prefix="KBBI_",
        extra="ignore",
    )

    # Official KBBI VI Daring host.
    base_url: str = "https://kbbi.kemendikdasmen.go.id"

    # Network timeout in seconds.
    timeout_seconds: float = 10.0

    # Log level for the stdio server's stderr logs.
    log_level: str = "INFO"


@lru_cache(maxsize=1)
def get_settings() -> KBBISettings:
    return KBBISettings()
