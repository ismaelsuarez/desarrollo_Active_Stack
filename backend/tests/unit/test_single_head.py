import subprocess
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[2]
SCRIPT = BACKEND / 'scripts/check_single_head.py'


@pytest.mark.parametrize('fixture,expected,heads', [
    ('alembic_single_head', 0, ['first']),
    ('alembic_two_heads', 1, ['left', 'right']),
])
def test_head_check_reports_linear_and_branched_histories(fixture, expected, heads):
    result = subprocess.run([sys.executable, str(SCRIPT), str(BACKEND / 'tests/fixtures' / fixture)], capture_output=True, text=True)
    assert result.returncode == expected
    assert all(head in result.stdout for head in heads)


def test_current_project_has_one_head():
    result = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True)
    assert result.returncode == 0
    assert '0001_turnos_sin_solapamiento' in result.stdout
