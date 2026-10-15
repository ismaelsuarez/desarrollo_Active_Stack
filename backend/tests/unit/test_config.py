import pytest
from pydantic import ValidationError

from app.core.config import Settings

DB = 'postgresql+asyncpg://tester:private-password@localhost/test'
KEY = 'jwt-secreto-de-prueba-0123456789-abcd'


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch, tmp_path):
    for name in ['APP_ENV', 'DATABASE_URL', 'MIGRATIONS_DATABASE_URL', 'JWT_SECRET_KEY', 'REDIS_URL', 'APP_TIMEZONE']:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv('SECRETS_DIR', str(tmp_path))


@pytest.mark.parametrize('missing', ['database_url', 'jwt_secret_key', 'app_env'])
def test_missing_required_configuration_is_safe(missing):
    values = dict(database_url=DB, jwt_secret_key=KEY, app_env='test')
    values.pop(missing)
    with pytest.raises(ValidationError) as error:
        Settings(**values)
    assert missing.upper() in str(error.value)
    assert DB not in str(error.value)
    assert KEY not in str(error.value)


def test_complete_configuration_and_minimum_key():
    config = Settings(database_url=DB, jwt_secret_key='x' * 32, app_env='test')
    assert config.database_url.get_secret_value() == DB
    assert config.jwt_secret_key.get_secret_value() == 'x' * 32


def test_short_key_rejected_without_disclosure():
    secret = 'x' * 31
    with pytest.raises(ValidationError) as error:
        Settings(database_url=DB, jwt_secret_key=secret, app_env='test')
    assert 'JWT_SECRET_KEY' in str(error.value)
    assert secret not in str(error.value)


def test_secrets_loaded_from_files_with_trailing_newline(monkeypatch, tmp_path):
    monkeypatch.setenv('APP_ENV', 'test')
    (tmp_path / 'database_url').write_text(DB + '\n')
    (tmp_path / 'jwt_secret_key').write_text(KEY + '\n')
    config = Settings()
    assert config.database_url.get_secret_value() == DB
    assert config.jwt_secret_key.get_secret_value() == KEY


def test_environment_overrides_secret_files(monkeypatch, tmp_path):
    monkeypatch.setenv('APP_ENV', 'test')
    monkeypatch.setenv('DATABASE_URL', DB)
    monkeypatch.setenv('JWT_SECRET_KEY', KEY)
    (tmp_path / 'jwt_secret_key').write_text('file-secret-0123456789-abcdefghijklm\n')
    assert Settings().jwt_secret_key.get_secret_value() == KEY


def test_nonexistent_secrets_directory_allows_environment(monkeypatch, tmp_path):
    monkeypatch.setenv('SECRETS_DIR', str(tmp_path / 'missing'))
    monkeypatch.setenv('APP_ENV', 'test')
    monkeypatch.setenv('DATABASE_URL', DB)
    monkeypatch.setenv('JWT_SECRET_KEY', KEY)
    assert Settings().app_env == 'test'


def test_optional_redis_and_default_timezone():
    config = Settings(database_url=DB, jwt_secret_key=KEY, app_env='test')
    assert config.redis_url is None
    assert config.app_timezone == 'America/Argentina/Buenos_Aires'


def test_invalid_environment_names_only_field():
    with pytest.raises(ValidationError) as error:
        Settings(database_url=DB, jwt_secret_key=KEY, app_env='staging')
    assert 'APP_ENV' in str(error.value)
    assert DB not in str(error.value)


def test_database_configuration_does_not_require_api_secrets():
    from app.core.config import DatabaseSettings
    config = DatabaseSettings(database_url=DB)
    assert config.migration_url == DB


def test_migrations_prefer_their_own_url():
    from app.core.config import DatabaseSettings
    direct = 'postgresql+asyncpg://tester:direct-password@localhost/direct'
    assert DatabaseSettings(database_url=DB, migrations_database_url=direct).migration_url == direct
