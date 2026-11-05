import httpx
import pytest
import yaml
from pathlib import Path

from app.core.config import Settings


async def test_deep_link_serves_frontend_index(tmp_path, monkeypatch):
    import app.main

    (tmp_path / 'index.html').write_text('<main>SPA</main>')
    monkeypatch.setattr(app.main, 'SPA_DIR', tmp_path)
    app = app.main.create_app(Settings(database_url='postgresql+asyncpg://u:p@localhost/test',
        jwt_secret_key='x' * 32, origin_hash_secret='y' * 32, app_env='test', consultorio_activo_id=1))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        response = await client.get('/restablecer-password')
    assert response.status_code == 200
    assert response.text == '<main>SPA</main>'


@pytest.mark.parametrize('path,expected', [
    ('/', 200), ('/cuenta/perfil', 200), ('/assets/app.js', 200),
    ('/api/v1/no-existe', 404), ('/internal/no-existe', 404),
    ('/assets/falta.js', 404), ('/favicon.ico', 404),
])
async def test_static_assets_and_reserved_routes(tmp_path, monkeypatch, path, expected):
    import app.main

    (tmp_path / 'index.html').write_text('<main>SPA</main>')
    (tmp_path / 'assets').mkdir()
    (tmp_path / 'assets' / 'app.js').write_text('console.log(1)')
    monkeypatch.setattr(app.main, 'SPA_DIR', tmp_path)
    app = app.main.create_app(Settings(database_url='postgresql+asyncpg://u:p@localhost/test',
        jwt_secret_key='x' * 32, origin_hash_secret='y' * 32, app_env='test', consultorio_activo_id=1))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        response = await client.get(path)
    assert response.status_code == expected
    if path == '/assets/app.js':
        assert response.text == 'console.log(1)'
    if expected == 404:
        assert '<main>SPA</main>' not in response.text


async def test_post_does_not_fallback_to_index(tmp_path, monkeypatch):
    import app.main

    (tmp_path / 'index.html').write_text('<main>SPA</main>')
    monkeypatch.setattr(app.main, 'SPA_DIR', tmp_path)
    app = app.main.create_app(Settings(database_url='postgresql+asyncpg://u:p@localhost/test',
        jwt_secret_key='x' * 32, origin_hash_secret='y' * 32, app_env='test', consultorio_activo_id=1))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        response = await client.post('/cuenta/perfil')
    assert response.status_code in (404, 405)
    assert '<main>SPA</main>' not in response.text


async def test_matching_route_404_and_missing_build_remain_404(tmp_path, monkeypatch):
    import app.main
    from fastapi import HTTPException

    monkeypatch.setattr(app.main, 'SPA_DIR', tmp_path)
    app = app.main.create_app(Settings(database_url='postgresql+asyncpg://u:p@localhost/test',
        jwt_secret_key='x' * 32, origin_hash_secret='y' * 32, app_env='test', consultorio_activo_id=1))

    @app.get('/ruta-registrada')
    async def registered():
        raise HTTPException(status_code=404, detail='No disponible')

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        assert (await client.get('/cuenta')).status_code == 404
        (tmp_path / 'index.html').write_text('<main>SPA</main>')
        response = await client.get('/ruta-registrada')
    assert response.status_code == 404
    assert response.json() == {'detail': 'No disponible'}


def test_production_image_builds_frontend_from_root_and_excludes_secrets():
    root = Path(__file__).resolve().parents[3]
    compose = yaml.safe_load((root / 'docker-compose.yml').read_text())
    build = compose['services']['api']['build']
    assert build['context'] == '.'
    assert build['dockerfile'] == 'backend/Dockerfile'
    dockerfile = (root / 'backend' / 'Dockerfile').read_text()
    assert 'COPY --from=frontend' in dockerfile
    assert '/app/static' in dockerfile
    excluded = (root / '.dockerignore').read_text().splitlines()
    for secret in ('.env', 'secrets/', 'backend/.venv/', 'frontend/node_modules/'):
        assert secret in excluded
