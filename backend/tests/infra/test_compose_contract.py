from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]


def compose():
    return yaml.safe_load((ROOT / 'docker-compose.yml').read_text())


def test_services_profiles_and_persistence():
    document = compose()
    assert 'version' not in document
    services = document['services']
    assert set(services) == {'db', 'migrate', 'api', 'frontend', 'redis', 'mailpit'}
    assert services['db']['volumes'] == ['db_data:/var/lib/postgresql/data']
    assert services['db']['healthcheck']['test'][0:2] == ['CMD-SHELL', 'pg_isready -U ${POSTGRES_USER:-turnos} -d ${POSTGRES_DB:-turnos}']
    assert 'ports' not in services['db']
    assert services['redis']['profiles'] == ['redis']
    assert services['mailpit']['profiles'] == ['dev']
    assert any('8025' in str(port) for port in services['mailpit']['ports'])
    assert services['frontend']['build']['target'] == 'dev'


def test_startup_dependencies_and_nonroot_api():
    services = compose()['services']
    assert services['migrate']['command'] == 'alembic upgrade head'
    assert services['migrate']['depends_on']['db']['condition'] == 'service_healthy'
    assert services['api']['depends_on']['migrate']['condition'] == 'service_completed_successfully'
    assert services['frontend']['depends_on']['api']['condition'] == 'service_healthy'
    assert services['api']['restart'] == 'unless-stopped'
    assert '/api/v1/health' in ' '.join(services['api']['healthcheck']['test'])


def test_secrets_have_service_specific_mounts():
    document = compose()
    services = document['services']
    assert services['db']['secrets'] == ['postgres_password']
    assert services['migrate']['secrets'] == ['database_url']
    assert services['api']['secrets'] == ['database_url', 'jwt_secret_key']
    assert services['db']['environment']['POSTGRES_PASSWORD_FILE'] == '/run/secrets/postgres_password'
    for service in services.values():
        environment = service.get('environment', {})
        assert not {'POSTGRES_PASSWORD', 'DATABASE_URL', 'MIGRATIONS_DATABASE_URL', 'JWT_SECRET_KEY'} & environment.keys()
    assert document['secrets'] == {name: {'file': './secrets/' + name + '.txt'} for name in ['postgres_password', 'database_url', 'jwt_secret_key']}
