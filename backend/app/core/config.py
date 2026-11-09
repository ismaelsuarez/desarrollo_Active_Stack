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
    openapi_docs_enabled: bool | None = Field(default=None, validation_alias='OPENAPI_DOCS_ENABLED')
    redis_url: str | None = None
    app_timezone: str = 'America/Argentina/Buenos_Aires'

    email_verification_ttl_hours: int = Field(default=24, gt=0, validation_alias='EMAIL_VERIFICATION_TTL_HOURS')
    password_reset_ttl_minutes: int = Field(default=30, gt=0, validation_alias='PASSWORD_RESET_TTL_MINUTES')
    email_daily_limit: int = Field(default=500, gt=0, validation_alias='EMAIL_DAILY_LIMIT')
    email_daily_limit_account: int = Field(default=150, gt=0, validation_alias='EMAIL_DAILY_LIMIT_ACCOUNT')
    email_daily_alert_ratio: float = Field(default=0.8, gt=0, le=1, validation_alias='EMAIL_DAILY_ALERT_RATIO')
    registration_limit_per_origin: int = Field(default=10, gt=0, validation_alias='REGISTRATION_LIMIT_PER_ORIGIN')
    registration_limit_global: int = Field(default=50, gt=0, validation_alias='REGISTRATION_LIMIT_GLOBAL')
    registration_limit_window_minutes: int = Field(default=60, gt=0, le=1440, validation_alias='REGISTRATION_LIMIT_WINDOW_MINUTES')
    account_request_limit_per_origin: int = Field(default=10, gt=0, validation_alias='ACCOUNT_REQUEST_LIMIT_PER_ORIGIN')
    account_request_limit_global: int = Field(default=50, gt=0, validation_alias='ACCOUNT_REQUEST_LIMIT_GLOBAL')
    account_request_limit_window_minutes: int = Field(default=60, gt=0, le=1440, validation_alias='ACCOUNT_REQUEST_LIMIT_WINDOW_MINUTES')
    account_email_limit: int = Field(default=3, gt=0, validation_alias='ACCOUNT_EMAIL_LIMIT')
    account_email_window_minutes: int = Field(default=15, gt=0, validation_alias='ACCOUNT_EMAIL_WINDOW_MINUTES')
    notification_max_attempts: int = Field(default=3, gt=0, validation_alias='NOTIFICATION_MAX_ATTEMPTS')
    notification_claim_ttl_seconds: int = Field(default=120, gt=0, validation_alias='NOTIFICATION_CLAIM_TTL_SECONDS')
    smtp_timeout_seconds: float = Field(default=30, gt=0, validation_alias='SMTP_TIMEOUT_SECONDS')
    smtp_host: str = Field(default='mailpit', validation_alias='SMTP_HOST')
    smtp_port: int = Field(default=587, gt=0, validation_alias='SMTP_PORT')
    smtp_starttls: bool = Field(default=True, validation_alias='SMTP_STARTTLS')
    smtp_user: str | None = Field(default=None, validation_alias='SMTP_USER')
    smtp_password: SecretStr | None = Field(default=None, validation_alias='SMTP_PASSWORD')
    smtp_from: str = Field(default='Consultorio <no-reply@example.test>', validation_alias='SMTP_FROM')
    frontend_base_url: str = Field(default='http://localhost:5173', validation_alias='FRONTEND_BASE_URL')
    sweep_shared_secret: SecretStr | None = Field(default=None, validation_alias='SWEEP_SHARED_SECRET')
    sweep_in_process_enabled: bool = Field(default=False, validation_alias='SWEEP_IN_PROCESS_ENABLED')
    sweeper_interval_seconds: int = Field(default=300, gt=0, validation_alias='SWEEPER_INTERVAL_SECONDS')

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
        if self.app_env == 'production' and not self.cookie_secure:
            raise ValueError('COOKIE_SECURE must be enabled in production')
        return self

    @model_validator(mode='after')
    def set_default_openapi_docs(self) -> 'Settings':
        if self.openapi_docs_enabled is None:
            self.openapi_docs_enabled = self.app_env != 'production'
        return self

    @model_validator(mode='after')
    def validate_mail_limits(self) -> 'Settings':
        if self.email_daily_limit_account >= self.email_daily_limit:
            raise ValueError('EMAIL_DAILY_LIMIT_ACCOUNT must be less than EMAIL_DAILY_LIMIT')
        if self.smtp_timeout_seconds >= self.notification_claim_ttl_seconds:
            raise ValueError('SMTP_TIMEOUT_SECONDS must be less than NOTIFICATION_CLAIM_TTL_SECONDS')
        return self


class SeedSettings(DatabaseSettings):
    consultorio_activo_id: int = Field(validation_alias='CONSULTORIO_ACTIVO_ID', gt=0)
    app_timezone: str = 'America/Argentina/Buenos_Aires'
    bootstrap_admin_email: str = Field(default='admin@consultorio.com', validation_alias='BOOTSTRAP_ADMIN_EMAIL')
    bootstrap_admin_password: SecretStr = Field(validation_alias='BOOTSTRAP_ADMIN_PASSWORD')


@lru_cache
def get_settings() -> Settings:
    return Settings()
