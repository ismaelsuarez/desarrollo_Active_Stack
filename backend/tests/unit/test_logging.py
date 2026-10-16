import io
import json
import logging
import pytest
from datetime import datetime

from app.core.logging import JsonFormatter


@pytest.mark.parametrize('level,message', [(logging.INFO, 'inicio'), (logging.ERROR, 'fallo')])
def test_log_record_is_json_with_utc_timestamp(level, message):
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger('c01.json')
    previous_level = logger.level
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    try:
        logger.log(level, message)
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)
    result = json.loads(stream.getvalue())
    assert result['message'] == message
    assert result['level'] == logging.getLevelName(level)
    assert result['logger'] == 'c01.json'
    assert datetime.fromisoformat(result['timestamp']).utcoffset().total_seconds() == 0


from pydantic import SecretStr, ValidationError
from app.core.config import Settings

DB = 'postgresql+asyncpg://tester:private-password@localhost/test'
KEY = 'jwt-secreto-de-prueba-0123456789-abcd'


class ExtendedSettings(Settings):
    additional_secret: SecretStr = SecretStr('new-sensitive-value')
    empty_secret: SecretStr = SecretStr('')
    short_secret: SecretStr = SecretStr('abc')


def settings():
    return ExtendedSettings(database_url=DB, jwt_secret_key=KEY, app_env='test')


@pytest.mark.parametrize('message,extra,absent', [
    ('key %s', {}, KEY),
    (DB, {}, 'private-password'),
    ('extra', {'payload': {'credential': KEY}}, KEY),
    ('new-sensitive-value', {}, 'new-sensitive-value'),
])
def test_sensitive_values_are_redacted(message, extra, absent):
    record = logging.LogRecord('c01.redact', logging.INFO, '', 0, message, (KEY,) if '%s' in message else (), None)
    record.__dict__.update(extra)
    output = JsonFormatter(settings()).format(record)
    assert absent not in output
    assert '***' in output
    result = json.loads(output)
    if extra:
        assert result['payload']['credential'] == '***'


def test_short_and_empty_additional_secrets_leave_message_intact():
    record = logging.LogRecord('c01.redact', logging.INFO, '', 0, 'inicio abc', (), None)
    assert json.loads(JsonFormatter(settings()).format(record))['message'] == 'inicio abc'


def test_invalid_configuration_error_does_not_disclose_values(monkeypatch, tmp_path):
    monkeypatch.setenv('SECRETS_DIR', str(tmp_path))
    monkeypatch.delenv('APP_ENV', raising=False)
    with pytest.raises(ValidationError) as error:
        Settings(database_url=DB, jwt_secret_key=KEY)
    record = logging.LogRecord('c01.invalid', logging.ERROR, '', 0, str(error.value), (), None)
    output = JsonFormatter().format(record)
    assert DB not in output
    assert KEY not in output
    assert 'APP_ENV' in output


def test_new_secret_is_redacted_even_when_it_looks_like_an_invalid_url():
    raw = 'secret://[not-a-host'
    config = ExtendedSettings(database_url=DB, jwt_secret_key=KEY, app_env='test', additional_secret=raw)
    record = logging.LogRecord('c01.redact', logging.INFO, '', 0, raw, (), None)
    assert json.loads(JsonFormatter(config).format(record))['message'] == '***'


@pytest.mark.parametrize('message', [
    'configured database credential: private-password',
    f'configured signing key: {KEY}',
])
def test_ordinary_application_logger_uses_current_redaction_without_duplicate_handlers(message, capsys):
    from app.main import create_app

    create_app(Settings(database_url=DB, jwt_secret_key='old-key-' * 4, app_env='test'))
    create_app(settings())
    logging.getLogger('app.api.v1.routers.health').error(message, extra={'credential': KEY})
    raw = capsys.readouterr().err
    assert 'private-password' not in raw
    assert KEY not in raw
    records = [json.loads(line) for line in raw.splitlines()]
    assert len(records) == 1
    assert records[0]['logger'] == 'app.api.v1.routers.health'
    assert records[0]['level'] == 'ERROR'
    assert records[0]['credential'] == '***'
    assert '***' in records[0]['message']
