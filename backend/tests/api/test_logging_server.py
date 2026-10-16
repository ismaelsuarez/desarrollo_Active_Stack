"""Exercise the production Uvicorn entrypoint, not just the formatter."""

import json
import os
from pathlib import Path
import socket
import signal
import subprocess
import sys
import time
from datetime import datetime

import httpx
import pytest


KEY = 'server-signing-secret-0123456789abcdef'
PASSWORD = 'server-database-password'
BACKEND = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize('supplied', [None, 'abc-123'])
def test_production_server_logs_are_json_redacted_and_correlated(supplied, tmp_path):
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]

    # Keep the Dockerfile command, changing only the bind address and ephemeral port.
    command_line = next(line for line in (BACKEND / 'Dockerfile').read_text().splitlines() if line.startswith('CMD '))
    command = json.loads(command_line.removeprefix('CMD '))
    command[0] = str(Path(sys.executable).with_name(command[0]))
    command[command.index('--host') + 1] = '127.0.0.1'
    command[command.index('--port') + 1] = str(port)
    env = {name: value for name, value in os.environ.items() if name not in {
        'DATABASE_URL', 'MIGRATIONS_DATABASE_URL', 'JWT_SECRET_KEY', 'APP_ENV', 'SECRETS_DIR',
    }}
    env.update({
        'DATABASE_URL': f'postgresql+asyncpg://user:{PASSWORD}@127.0.0.1:1/test',
        'JWT_SECRET_KEY': KEY,
        'APP_ENV': 'test',
        'SECRETS_DIR': str(tmp_path / 'no-secrets'),
    })
    process = subprocess.Popen(command, cwd=BACKEND, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        deadline = time.monotonic() + 10
        while True:
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=0.2):
                    break
            except OSError:
                if process.poll() is not None or time.monotonic() >= deadline:
                    pytest.fail('Uvicorn did not start')
                time.sleep(0.02)
        with httpx.Client(trust_env=False) as client:
            response = client.get(
                f'http://127.0.0.1:{port}/api/v1/health',
                params={'signing_key': KEY, 'password': PASSWORD},
                headers={'X-Request-ID': supplied} if supplied else {},
            )
    finally:
        process.terminate()
        stdout, stderr = process.communicate(timeout=10)
    assert process.returncode in {0, -signal.SIGTERM}
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}
    identifier = response.headers['X-Request-ID']
    if supplied:
        assert identifier == supplied
    else:
        assert len(identifier) == 32 and all(character in '0123456789abcdef' for character in identifier)
    raw = stdout + stderr
    assert KEY not in raw
    assert PASSWORD not in raw
    records = [json.loads(line) for line in raw.splitlines()]
    assert records
    for record in records:
        assert {'timestamp', 'level', 'logger', 'message'} <= record.keys()
        assert datetime.fromisoformat(record['timestamp']).utcoffset().total_seconds() == 0
    lifecycle = [record for record in records if record['logger'] == 'uvicorn.error']
    assert any('startup complete' in record['message'] for record in lifecycle)
    assert any('shutdown complete' in record['message'] for record in lifecycle)
    per_request = [record for record in records if record['logger'] in {'uvicorn.access', 'tpi.api'}]
    assert len([record for record in per_request if record['logger'] == 'uvicorn.access']) == 1
    assert len([record for record in per_request if record['logger'] == 'tpi.api']) == 1
    assert all(record['request_id'] == identifier for record in per_request)
