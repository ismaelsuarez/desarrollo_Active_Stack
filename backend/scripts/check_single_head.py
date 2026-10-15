"""Exit successfully only for a linear migration history with exactly one head."""
import argparse
from pathlib import Path

from alembic.script import ScriptDirectory


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', nargs='?', type=Path, default=Path(__file__).resolve().parents[1] / 'alembic', help='Alembic script directory (defaults to this backend)')
    args = parser.parse_args()
    heads = sorted(ScriptDirectory(str(args.directory)).get_heads())
    print('Heads: ' + ', '.join(heads))
    return 0 if len(heads) == 1 else 1


if __name__ == '__main__':
    raise SystemExit(main())
