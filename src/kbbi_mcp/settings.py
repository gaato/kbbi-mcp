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

    # Current official KBBI VI Daring host.
    base_url: str = "https://kbbi.kemendikdasmen.go.id"

    # Fallback mirror when official host is down/unreachable.
    fallback_base_url: str = "https://kbbi.web.id"

    # Network timeout in seconds.
    timeout_seconds: float = 10.0


@lru_cache(maxsize=1)
def get_settings() -> KBBISettings:
    return KBBISettings()
