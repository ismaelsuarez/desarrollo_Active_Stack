import pytest
from pydantic import ValidationError

from app.core.config import Settings

DB = 'postgresql+asyncpg://tester:private-password@localhost/test'
KEY = 'jwt-secreto-de-prueba-0123456789-abcd'
ORIGIN_SECRET = 'origin-secret-hash-key-0123456789-abcdef'
CID = 1


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch, tmp_path):
    for name in [
        'APP_ENV',
        'DATABASE_URL',
        'MIGRATIONS_DATABASE_URL',
        'JWT_SECRET_KEY',
        'ORIGIN_HASH_SECRET',
        'TRUSTED_PROXY_HOPS',
        'LOGIN_MAX_ATTEMPTS',
        'LOGIN_LOCKOUT_MINUTES',
        'LOGIN_MAX_ATTEMPTS_PER_ORIGIN',
        'COOKIE_SECURE',
        'REDIS_URL',
        'APP_TIMEZONE',
        'CONSULTORIO_ACTIVO_ID',
        'BOOTSTRAP_ADMIN_EMAIL',
        'BOOTSTRAP_ADMIN_PASSWORD',
    ]:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv('SECRETS_DIR', str(tmp_path))


@pytest.mark.parametrize('missing', ['database_url', 'jwt_secret_key', 'app_env', 'consultorio_activo_id', 'origin_hash_secret'])
def test_missing_required_configuration_is_safe(missing):
    values = dict(
        database_url=DB,
        jwt_secret_key=KEY,
        origin_hash_secret=ORIGIN_SECRET,
        app_env='test',
        consultorio_activo_id=CID,
    )
    values.pop(missing)
    with pytest.raises(ValidationError) as error:
        Settings(**values)
    assert missing.upper() in str(error.value)
    assert DB not in str(error.value)
    assert KEY not in str(error.value)
    assert ORIGIN_SECRET not in str(error.value)


@pytest.mark.parametrize('invalid_id', [0, -1, 'no-numerico'])
def test_consultorio_activo_id_must_be_positive_integer(invalid_id):
    with pytest.raises(ValidationError) as error:
        Settings(
            database_url=DB,
            jwt_secret_key=KEY,
            origin_hash_secret=ORIGIN_SECRET,
            app_env='test',
            consultorio_activo_id=invalid_id,
        )
    assert 'CONSULTORIO_ACTIVO_ID' in str(error.value)


def test_complete_configuration_and_minimum_key():
    config = Settings(
        database_url=DB,
        jwt_secret_key='x' * 32,
        origin_hash_secret='y' * 32,
        app_env='test',
        consultorio_activo_id=CID,
    )
    assert config.database_url.get_secret_value() == DB
    assert config.jwt_secret_key.get_secret_value() == 'x' * 32
    assert config.origin_hash_secret.get_secret_value() == 'y' * 32
    assert config.consultorio_activo_id == CID
    assert config.trusted_proxy_hops == 0
    assert config.login_max_attempts == 5
    assert config.login_lockout_minutes == 15
    assert config.login_max_attempts_per_origin == 20
    assert config.cookie_secure is True


def test_short_key_rejected_without_disclosure():
    secret = 'x' * 31
    with pytest.raises(ValidationError) as error:
        Settings(
            database_url=DB,
            jwt_secret_key=secret,
            origin_hash_secret=ORIGIN_SECRET,
            app_env='test',
            consultorio_activo_id=CID,
        )
    assert 'JWT_SECRET_KEY' in str(error.value)
    assert secret not in str(error.value)


def test_short_origin_hash_secret_rejected_without_disclosure():
    short_origin = 'y' * 31
    with pytest.raises(ValidationError) as error:
        Settings(
            database_url=DB,
            jwt_secret_key=KEY,
            origin_hash_secret=short_origin,
            app_env='test',
            consultorio_activo_id=CID,
        )
    assert 'ORIGIN_HASH_SECRET' in str(error.value)
    assert short_origin not in str(error.value)


def test_secrets_loaded_from_files_with_trailing_newline(monkeypatch, tmp_path):
    monkeypatch.setenv('APP_ENV', 'test')
    monkeypatch.setenv('CONSULTORIO_ACTIVO_ID', '1')
    (tmp_path / 'database_url').write_text(DB + '\n')
    (tmp_path / 'jwt_secret_key').write_text(KEY + '\n')
    (tmp_path / 'origin_hash_secret').write_text(ORIGIN_SECRET + '\n')
    config = Settings()
    assert config.database_url.get_secret_value() == DB
    assert config.jwt_secret_key.get_secret_value() == KEY
    assert config.origin_hash_secret.get_secret_value() == ORIGIN_SECRET
    assert config.consultorio_activo_id == 1


def test_environment_overrides_secret_files(monkeypatch, tmp_path):
    monkeypatch.setenv('APP_ENV', 'test')
    monkeypatch.setenv('DATABASE_URL', DB)
    monkeypatch.setenv('JWT_SECRET_KEY', KEY)
    monkeypatch.setenv('ORIGIN_HASH_SECRET', ORIGIN_SECRET)
    monkeypatch.setenv('CONSULTORIO_ACTIVO_ID', '1')
    (tmp_path / 'jwt_secret_key').write_text('file-secret-0123456789-abcdefghijklm\n')
    assert Settings().jwt_secret_key.get_secret_value() == KEY


def test_nonexistent_secrets_directory_allows_environment(monkeypatch, tmp_path):
    monkeypatch.setenv('SECRETS_DIR', str(tmp_path / 'missing'))
    monkeypatch.setenv('APP_ENV', 'test')
    monkeypatch.setenv('DATABASE_URL', DB)
    monkeypatch.setenv('JWT_SECRET_KEY', KEY)
    monkeypatch.setenv('ORIGIN_HASH_SECRET', ORIGIN_SECRET)
    monkeypatch.setenv('CONSULTORIO_ACTIVO_ID', '1')
    assert Settings().app_env == 'test'
    assert Settings().consultorio_activo_id == 1


def test_optional_redis_and_default_timezone():
    config = Settings(
        database_url=DB,
        jwt_secret_key=KEY,
        origin_hash_secret=ORIGIN_SECRET,
        app_env='test',
        consultorio_activo_id=CID,
    )
    assert config.redis_url is None
    assert config.app_timezone == 'America/Argentina/Buenos_Aires'


def test_invalid_environment_names_only_field():
    with pytest.raises(ValidationError) as error:
        Settings(
            database_url=DB,
            jwt_secret_key=KEY,
            origin_hash_secret=ORIGIN_SECRET,
            app_env='staging',
            consultorio_activo_id=CID,
        )
    assert 'APP_ENV' in str(error.value)
    assert DB not in str(error.value)


@pytest.mark.parametrize('invalid_hops', [-1, 'invalido'])
def test_trusted_proxy_hops_must_be_non_negative_int(invalid_hops):
    with pytest.raises(ValidationError) as error:
        Settings(
            database_url=DB,
            jwt_secret_key=KEY,
            origin_hash_secret=ORIGIN_SECRET,
            app_env='test',
            consultorio_activo_id=CID,
            trusted_proxy_hops=invalid_hops,
        )
    assert 'TRUSTED_PROXY_HOPS' in str(error.value)


@pytest.mark.parametrize('invalid_lockout', [0, -5, 1441])
def test_login_lockout_minutes_bounds(invalid_lockout):
    with pytest.raises(ValidationError) as error:
        Settings(
            database_url=DB,
            jwt_secret_key=KEY,
            origin_hash_secret=ORIGIN_SECRET,
            app_env='test',
            consultorio_activo_id=CID,
            login_lockout_minutes=invalid_lockout,
        )
    assert 'LOGIN_LOCKOUT_MINUTES' in str(error.value)


def test_cookie_secure_defaults_by_environment():
    dev_config = Settings(
        database_url=DB,
        jwt_secret_key=KEY,
        origin_hash_secret=ORIGIN_SECRET,
        app_env='development',
        consultorio_activo_id=CID,
    )
    assert dev_config.cookie_secure is False

    prod_config = Settings(
        database_url=DB,
        jwt_secret_key=KEY,
        origin_hash_secret=ORIGIN_SECRET,
        app_env='production',
        consultorio_activo_id=CID,
    )
    assert prod_config.cookie_secure is True

    override_config = Settings(
        database_url=DB,
        jwt_secret_key=KEY,
        origin_hash_secret=ORIGIN_SECRET,
        app_env='development',
        consultorio_activo_id=CID,
        cookie_secure=True,
    )
    assert override_config.cookie_secure is True


def test_seed_settings_isolated_and_valid():
    from app.core.config import SeedSettings
    seed_config = SeedSettings(
        database_url=DB,
        consultorio_activo_id=CID,
        bootstrap_admin_password='AdminPassword123!',
    )
    assert seed_config.database_url.get_secret_value() == DB
    assert seed_config.consultorio_activo_id == 1
    assert seed_config.bootstrap_admin_email == 'admin@consultorio.com'
    assert seed_config.bootstrap_admin_password.get_secret_value() == 'AdminPassword123!'
    assert seed_config.app_timezone == 'America/Argentina/Buenos_Aires'


def test_seed_settings_fails_without_consultorio_id():
    from app.core.config import SeedSettings
    with pytest.raises(ValidationError) as error:
        SeedSettings(database_url=DB, bootstrap_admin_password='pwd')
    assert 'CONSULTORIO_ACTIVO_ID' in str(error.value)


def test_database_configuration_does_not_require_api_secrets():
    from app.core.config import DatabaseSettings
    config = DatabaseSettings(database_url=DB)
    assert config.migration_url == DB


def test_migrations_prefer_their_own_url():
    from app.core.config import DatabaseSettings
    direct = 'postgresql+asyncpg://tester:direct-password@localhost/direct'
    assert DatabaseSettings(database_url=DB, migrations_database_url=direct).migration_url == direct
