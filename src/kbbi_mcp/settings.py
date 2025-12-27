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

    email: str | None = None
    password: str | None = None
    cookie_path: str | None = None

    def has_credentials(self) -> bool:
        return bool(self.email and self.password)


@lru_cache(maxsize=1)
def get_settings() -> KBBISettings:
    return KBBISettings()
