import os
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / 'scripts/dev_secrets.sh'


def test_generates_consistent_secrets_and_is_idempotent(tmp_path):
    result = subprocess.run(['bash', str(SCRIPT), str(tmp_path)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    files = {name: (tmp_path / 'secrets' / f'{name}.txt').read_text().strip() for name in ['postgres_password', 'database_url', 'jwt_secret_key']}
    assert unquote(urlsplit(files['database_url']).password) == files['postgres_password']
    assert len(files['jwt_secret_key'].encode()) >= 32
    assert not any(value in result.stdout + result.stderr for value in files.values())
    before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in (tmp_path / 'secrets').iterdir()}
    assert subprocess.run(['bash', str(SCRIPT), str(tmp_path)], capture_output=True).returncode == 0
    assert before == {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in (tmp_path / 'secrets').iterdir()}
    assert (tmp_path / 'secrets').stat().st_mode & 0o777 == 0o700


def test_uses_configured_database_identity_without_disclosing_values(tmp_path):
    env = {**os.environ, 'POSTGRES_USER': 'local-test', 'POSTGRES_DB': 'test-agenda'}
    result = subprocess.run(['bash', str(SCRIPT), str(tmp_path)], env=env, capture_output=True, text=True)
    assert result.returncode == 0
    url = urlsplit((tmp_path / 'secrets/database_url.txt').read_text().strip())
    assert url.username == 'local-test'
    assert url.hostname == 'db'
    assert url.path == '/test-agenda'
