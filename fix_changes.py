from pathlib import Path


STATUS = (
    '- **Estado**: `[x]` completado y archivado el 2026-10-31 en '
    '[`2026-10-31-c-04-abac-policies`]'
    '(openspec/changes/archive/2026-10-31-c-04-abac-policies/); '
    '12/12 tareas y especificaciones sincronizadas.'
)
PENDING = '- **Estado**: `[ ]` pendiente'


def update_c04(changes: str) -> tuple[str, bool]:
    lines = changes.splitlines(keepends=True)
    sections = [
        index for index, line in enumerate(lines)
        if line.startswith('### [C-04] `abac-policies`')
    ]
    if len(sections) != 1:
        raise ValueError(f'Esperaba una sección C-04 y encontré {len(sections)}')

    start = sections[0]
    end = next(
        (index for index in range(start + 1, len(lines)) if lines[index].startswith('### ')),
        len(lines),
    )
    status_lines = [
        index for index in range(start + 1, end)
        if lines[index].startswith('- **Estado**:')
    ]
    if len(status_lines) != 1:
        raise ValueError(f'Esperaba un estado en C-04 y encontré {len(status_lines)}')

    index = status_lines[0]
    current = lines[index].rstrip('\r\n')
    if current == STATUS:
        return changes, False
    if current != PENDING:
        raise ValueError(f'Estado C-04 inesperado: {current}')

    ending = '\r\n' if lines[index].endswith('\r\n') else '\n' if lines[index].endswith('\n') else ''
    lines[index] = STATUS + ending
    return ''.join(lines), True


def main() -> None:
    path = Path(__file__).resolve().with_name('CHANGES.md')
    original = path.read_text(encoding='utf-8')
    updated, changed = update_c04(original)
    if changed:
        path.write_text(updated, encoding='utf-8', newline='')
        print('OK: actualizado el estado de C-04')
    else:
        print('OK: el estado de C-04 ya estaba actualizado')


if __name__ == '__main__':
    main()
