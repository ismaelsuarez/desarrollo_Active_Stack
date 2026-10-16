#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == --help ]]; then
  printf 'Usage: %s\nBuild and verify Compose in a disposable project; only its new volumes are removed.\n' "$0"
  exit 0
fi
if (( $# != 0 )); then printf 'No arguments expected.\n' >&2; exit 2; fi
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
[[ -f "$root/.env" ]] || cp "$root/.env.example" "$root/.env"
"$root/scripts/dev_secrets.sh" "$root"
project="c01-smoke-$(python3 -c 'import uuid; print(uuid.uuid4().hex)')"
export API_PORT=0 FRONTEND_PORT=0 MAILPIT_PORT=0
compose=(docker compose --project-name "$project" --project-directory "$root" --env-file "$root/.env" -f "$root/docker-compose.yml")
printf 'Verifying disposable Compose project: %s\n' "$project"
# No cleanup is authorized until the resolved volumes are proven project-owned.
"${compose[@]}" config --format json | python3 -c '
import json, sys
project = sys.argv[1]
config = json.load(sys.stdin)
for volume in config.get("volumes", {}).values():
    if volume.get("external") or not volume.get("name", "").startswith(project + "_"):
        raise SystemExit("Smoke check refuses non-disposable volumes.")
' "$project"
cleanup() {
  status=$?
  trap - EXIT
  if ! "${compose[@]}" --profile dev down --volumes --remove-orphans >/dev/null; then
    printf 'Disposable project cleanup failed: %s\n' "$project" >&2
    exit 1
  fi
  exit "$status"
}
trap cleanup EXIT
"${compose[@]}" config --quiet
services="$("${compose[@]}" config --services)"
if grep -Eq '^(redis|mailpit)$' <<< "$services"; then
  printf 'Optional services must not start without profiles.\n' >&2; exit 1
fi
"${compose[@]}" up -d --build --wait --wait-timeout 180
migrate="$("${compose[@]}" ps -aq migrate)"
[[ "$(docker inspect --format '{{.State.ExitCode}}' "$migrate")" == 0 ]]
api="$("${compose[@]}" ps -q api)"
[[ "$(docker inspect --format '{{.State.Health.Status}}' "$api")" == healthy ]]
[[ "$("${compose[@]}" exec -T api id -u)" != 0 ]]
endpoint="$("${compose[@]}" port api 8000)"
python3 - "$endpoint" <<'PY'
import json
import sys
import urllib.request
with urllib.request.urlopen('http://' + sys.argv[1] + '/api/v1/health', timeout=5) as response:
    assert response.status == 200
    assert json.load(response) == {'status': 'ok'}
PY
"${compose[@]}" --profile dev up -d --wait mailpit
mailpit="$("${compose[@]}" --profile dev port mailpit 8025)"
python3 - "$mailpit" <<'PY'
import sys
import time
import urllib.error
import urllib.request
for attempt in range(30):
    try:
        with urllib.request.urlopen('http://' + sys.argv[1], timeout=2) as response:
            assert response.status == 200
        break
    except (urllib.error.URLError, TimeoutError):
        if attempt == 29:
            raise
        time.sleep(1)
PY
printf 'Compose smoke passed: migration, health, non-root API, profiles and Mailpit port 8025.\n'
