import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
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
    origin_hash_secret: SecretStr = Field(validation_alias='ORIGIN_HASH_SECRET')
    app_env: Literal['development', 'test', 'production'] = Field(validation_alias='APP_ENV')
    consultorio_activo_id: int = Field(validation_alias='CONSULTORIO_ACTIVO_ID', gt=0)
    trusted_proxy_hops: int = Field(default=0, ge=0, validation_alias='TRUSTED_PROXY_HOPS')
    login_max_attempts: int = Field(default=5, gt=0, validation_alias='LOGIN_MAX_ATTEMPTS')
    login_lockout_minutes: int = Field(default=15, gt=0, le=1440, validation_alias='LOGIN_LOCKOUT_MINUTES')
    login_max_attempts_per_origin: int = Field(default=20, gt=0, validation_alias='LOGIN_MAX_ATTEMPTS_PER_ORIGIN')
    cookie_secure: bool | None = Field(default=None, validation_alias='COOKIE_SECURE')
    redis_url: str | None = None
    app_timezone: str = 'America/Argentina/Buenos_Aires'

    @field_validator('jwt_secret_key')
    @classmethod
    def validate_signing_key(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value().encode('utf-8')) < 32:
            raise ValueError('JWT_SECRET_KEY must contain at least 32 bytes')
        return value

    @field_validator('origin_hash_secret')
    @classmethod
    def validate_origin_secret(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value().encode('utf-8')) < 32:
            raise ValueError('ORIGIN_HASH_SECRET must contain at least 32 bytes')
        return value

    @model_validator(mode='after')
    def set_default_cookie_secure(self) -> 'Settings':
        if self.cookie_secure is None:
            self.cookie_secure = self.app_env != 'development'
        return self


class SeedSettings(DatabaseSettings):
    consultorio_activo_id: int = Field(validation_alias='CONSULTORIO_ACTIVO_ID', gt=0)
    app_timezone: str = 'America/Argentina/Buenos_Aires'
    bootstrap_admin_email: str = Field(default='admin@consultorio.com', validation_alias='BOOTSTRAP_ADMIN_EMAIL')
    bootstrap_admin_password: SecretStr = Field(validation_alias='BOOTSTRAP_ADMIN_PASSWORD')


@lru_cache
def get_settings() -> Settings:
    return Settings()
