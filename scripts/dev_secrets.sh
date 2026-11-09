#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == --help ]]; then
  printf 'Usage: %s [project-directory]\nGenerate local Compose secrets without overwriting existing files.\n' "$0"
  exit 0
fi
if (( $# > 1 )); then printf 'Expected at most one project directory.\n' >&2; exit 2; fi
root="${1:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}"
python3 - "$root" <<'PY'
import os
import secrets
import sys
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

root = Path(sys.argv[1])
directory = root / 'secrets'
directory.mkdir(mode=0o700, parents=True, exist_ok=True)
if directory.stat().st_mode & 0o077:
    raise SystemExit('The secrets directory must be private (mode 0700).')
password_path = directory / 'postgres_password.txt'
url_path = directory / 'database_url.txt'
if url_path.exists() and not password_path.exists():
    raise SystemExit('A database URL exists without its password file; restore the matching file before continuing.')

def create(path: Path, value: str) -> None:
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        return
    # Compose file-backed secrets preserve host file permissions. The private
    # directory prevents host traversal; mounted files must be readable by UID 1001.
    with os.fdopen(fd, 'w') as output:
        output.write(value + '\n')
    path.chmod(0o644)

create(password_path, secrets.token_hex(24))
password = password_path.read_text().strip()
user = quote(os.environ.get('POSTGRES_USER', 'turnos'), safe='')
database = quote(os.environ.get('POSTGRES_DB', 'turnos'), safe='')
create(url_path, f'postgresql+asyncpg://{user}:{quote(password, safe="")}@db:5432/{database}')
parsed = urlsplit(url_path.read_text().strip())
if unquote(parsed.password or '') != password:
    raise SystemExit('Local database secret files do not match; existing files were not overwritten.')
try:
    compatible = (parsed.scheme == 'postgresql+asyncpg' and parsed.hostname == 'db' and parsed.port == 5432
                  and unquote(parsed.username or '') == unquote(user)
                  and unquote(parsed.path.removeprefix('/')) == unquote(database))
except ValueError:
    compatible = False
if not compatible:
    raise SystemExit('Local database URL does not match the configured database identity; existing files were not overwritten.')
create(directory / 'jwt_secret_key.txt', secrets.token_urlsafe(32))
create(directory / 'origin_hash_secret.txt', secrets.token_urlsafe(32))
create(directory / 'bootstrap_admin_password.txt', secrets.token_urlsafe(24))
print('Local Compose secret files are ready; existing values were preserved.')
PY
