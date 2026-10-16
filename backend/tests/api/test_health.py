import importlib
import sys

import httpx
import pytest

from app.core.config import Settings


def configured_app():
    from app.main import create_app
    return create_app(Settings(database_url='postgresql+asyncpg://u:p@localhost/test', jwt_secret_key='x' * 32, app_env='test'))


async def test_health_endpoint_is_public_and_minimal():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=configured_app()), base_url='http://test') as client:
        response = await client.get('/api/v1/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}
    assert response.headers['content-type'] == 'application/json'


async def test_health_disallows_post():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=configured_app()), base_url='http://test') as client:
        response = await client.post('/api/v1/health')
    assert response.status_code == 405


def test_importing_app_does_not_load_configuration(monkeypatch):
    for name in ['APP_ENV', 'DATABASE_URL', 'JWT_SECRET_KEY']:
        monkeypatch.delenv(name, raising=False)
    sys.modules.pop('app.main', None)
    assert callable(importlib.import_module('app.main').create_app)


@pytest.mark.parametrize('database_url', ['postgresql+asyncpg://u:p@127.0.0.1:1/x', 'postgresql+asyncpg://u:p@not-a-database.invalid/x'])
async def test_health_does_not_connect_to_database(database_url):
    from app.main import create_app
    app = create_app(Settings(database_url=database_url, jwt_secret_key='x' * 32, app_env='test'))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        response = await client.get('/api/v1/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}


@pytest.mark.parametrize('provided,expected', [(None, None), ('abc-123', 'abc-123'), ('a' * 300, None), ('has spaces', None)])
async def test_request_identifiers_are_returned_and_logged(provided, expected, capsys):
    import json
    app = configured_app()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        response = await client.get('/api/v1/health', headers={'X-Request-ID': provided} if provided is not None else {})
    identifier = response.headers['X-Request-ID']
    assert identifier
    assert identifier == expected if expected else identifier != provided
    records = [json.loads(line) for line in capsys.readouterr().err.splitlines()]
    assert records and all(record['request_id'] == identifier for record in records)


async def test_generated_request_identifiers_differ():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=configured_app()), base_url='http://test') as client:
        first = await client.get('/api/v1/health')
        second = await client.get('/api/v1/health')
    assert first.headers['X-Request-ID'] != second.headers['X-Request-ID']


@pytest.mark.parametrize('supplied', [None, 'abc-123'])
async def test_application_logs_share_request_context_and_redaction(supplied, capsys):
    import json
    import logging
    from app.main import create_app

    key = 'application-signing-secret-0123456789'
    app = create_app(Settings(
        database_url='postgresql+asyncpg://u:private-password@127.0.0.1:1/test',
        jwt_secret_key=key,
        app_env='test',
    ))

    @app.get('/logging-probe')
    async def logging_probe():
        logging.getLogger('app.api.v1.routers.health').error(
            'configured database credential: private-password', extra={'credential': key},
        )
        return {'status': 'ok'}

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        response = await client.get('/logging-probe', headers={'X-Request-ID': supplied} if supplied else {})
    identifier = response.headers['X-Request-ID']
    logging.getLogger('app.api.v1.routers.health').info('outside request')
    raw = capsys.readouterr().err
    assert key not in raw and 'private-password' not in raw
    records = [json.loads(line) for line in raw.splitlines()]
    application, completed, outside = records
    assert response.status_code == 200 and response.json() == {'status': 'ok'}
    assert application['request_id'] == completed['request_id'] == identifier
    assert application['message'] == 'configured database credential: ***'
    assert application['credential'] == '***'
    assert 'request_id' not in outside
