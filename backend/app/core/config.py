import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=False,
        populate_by_name=True,
        extra='forbid',
        hide_input_in_errors=True,
    )

    database_url: SecretStr = Field(validation_alias='DATABASE_URL')
    migrations_database_url: SecretStr | None = Field(default=None, validation_alias='MIGRATIONS_DATABASE_URL')

    def __init__(self, **values: object) -> None:
        directory = Path(os.environ.get('SECRETS_DIR', '/run/secrets'))
        values.setdefault('_secrets_dir', directory if directory.is_dir() else None)
        # Normalize explicit field names too, so validation errors name environment variables.
        normalized = {}
        for name, value in values.items():
            field = type(self).model_fields.get(name)
            alias = field.validation_alias if field else None
            normalized[alias if isinstance(alias, str) else name] = value
        super().__init__(**normalized)

    @property
    def migration_url(self) -> str:
        return (self.migrations_database_url or self.database_url).get_secret_value()


class Settings(DatabaseSettings):
    jwt_secret_key: SecretStr = Field(validation_alias='JWT_SECRET_KEY')
    app_env: Literal['development', 'test', 'production'] = Field(validation_alias='APP_ENV')
    redis_url: str | None = None
    app_timezone: str = 'America/Argentina/Buenos_Aires'

    @field_validator('jwt_secret_key')
    @classmethod
    def validate_signing_key(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value().encode('utf-8')) < 32:
            raise ValueError('JWT_SECRET_KEY must contain at least 32 bytes')
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
