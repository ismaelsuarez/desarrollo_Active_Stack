"""Exercise the project registry command through its public CLI."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'refresh.py'
NATIVE = shutil.which('gentle-ai')
FAKE_NATIVE = '''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
root = Path(args[args.index('--cwd') + 1])
log = Path(os.environ['NATIVE_LOG'])
with log.open('a') as handle:
    handle.write(json.dumps(args) + '\\n')
command = args[1]
if command == 'refresh':
    (root / '.atl').mkdir(exist_ok=True)
    (root / '.atl/skill-registry.md').write_text('NATIVE ONLY\\n')
    (root / '.atl/.skill-registry.cache.json').write_text('{"fingerprint":"native-owned"}\\n')
if os.environ.get('FAIL_NATIVE') == command:
    print('native fixture failed at ' + command, file=sys.stderr)
    sys.exit(7)
if command == 'list':
    print(Path(os.environ['NATIVE_ROWS']).read_text())
'''


class RegistryCLI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch = Path(tempfile.mkdtemp(
            prefix='skill-registry-tests.',
            dir=os.environ.get('SKILL_REGISTRY_TEST_TMPDIR'),
        ))
        print(f'\nRegistry test scratch (retained): {cls.scratch}', flush=True)

    def setUp(self):
        self.case = Path(tempfile.mkdtemp(dir=self.scratch))
        self.root = self.case / 'repository'
        self.root.mkdir()
        (self.root / '.git').mkdir()
        self.home = self.case / 'home'
        self.home.mkdir()
        self.bin = self.case / 'bin'
        self.bin.mkdir()
        native = self.bin / 'gentle-ai'
        native.write_text(FAKE_NATIVE)
        native.chmod(0o755)
        # Keep the fake executable independent of the ambient PATH.
        (self.bin / 'python3').symlink_to(sys.executable)
        self.rows_path = self.case / 'rows.json'
        self.log = self.case / 'native.log'
        self.env = os.environ | {
            'HOME': str(self.home), 'PATH': str(self.bin),
            'NATIVE_ROWS': str(self.rows_path), 'NATIVE_LOG': str(self.log),
            'PYTHONDONTWRITEBYTECODE': '1',
        }

    def skill(self, name, *, root=None, description='A project skill'):
        path = (root or self.root) / '.agents' / 'skills' / name / 'SKILL.md'
        path.parent.mkdir(parents=True)
        path.write_text(f'---\nname: {name}\ndescription: "{description}"\n---\n\nLocal instructions.\n')
        return path

    def row(self, name, path, description='A project skill', scope='project'):
        return dict(name=name, path=str(path), description=description, scope=scope)

    def run_cli(self, rows, *flags, script=SCRIPT, cwd=None, env=None):
        self.rows_path.write_text(json.dumps(rows))
        return subprocess.run(
            [sys.executable, str(script), *flags],
            cwd=cwd or self.case, env=env or self.env,
            text=True, capture_output=True,
        )

    def registry(self, root=None):
        return (root or self.root) / '.atl' / 'skill-registry.md'

    def test_resolves_compatibility_link_and_excludes_global_rows(self):
        local = self.skill('local')
        alias = self.root / '.claude' / 'skills' / 'local'
        alias.parent.mkdir(parents=True)
        alias.symlink_to('../../.agents/skills/local', target_is_directory=True)
        global_skill = self.skill('global-only', root=self.home)
        result = self.run_cli([
            self.row('global-only', global_skill, scope='user'),
            self.row('local', alias / 'SKILL.md'),
        ], '--cwd', str(self.root), '--force')
        self.assertEqual(result.returncode, 0, result.stderr)
        content = self.registry().read_text()
        self.assertIn('| `local` | A project skill | project | `.agents/skills/local/SKILL.md` |', content)
        self.assertNotIn('global-only', content)
        self.assertNotIn(str(self.home), content)
        self.assertNotIn(str(self.root), content)
        self.assertEqual((self.root / '.atl/.skill-registry.cache.json').read_text(), '{"fingerprint":"native-owned"}\n')
        calls = [json.loads(line) for line in self.log.read_text().splitlines()]
        self.assertEqual(calls, [
            ['skill-registry', 'refresh', '--no-gitignore', '--cwd', str(self.root), '--force'],
            ['skill-registry', 'list', '--json', '--cwd', str(self.root)],
        ])
        self.assertFalse((self.root / '.gitignore').exists())
        self.assertEqual(local.read_text(), (alias / 'SKILL.md').read_text())

    def test_default_root_is_script_location_not_process_directory(self):
        local = self.skill('default-root')
        script = self.root / '.agents/skills/skill-registry/scripts/refresh.py'
        script.parent.mkdir(parents=True)
        shutil.copy2(SCRIPT, script)
        result = self.run_cli([self.row('default-root', local)], script=script)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('.agents/skills/default-root/SKILL.md', self.registry().read_text())
        self.assertFalse((self.case / '.atl').exists())

    def test_relative_paths_sorted_rows_and_escaped_descriptions(self):
        zed, alpha = self.skill('zed'), self.skill('alpha')
        result = self.run_cli([
            self.row('zed', zed, 'first | second\nthird'),
            self.row('alpha', alpha),
        ], '--cwd', str(self.root))
        self.assertEqual(result.returncode, 0, result.stderr)
        content = self.registry().read_text()
        self.assertLess(content.index('| `alpha`'), content.index('| `zed`'))
        self.assertIn('first \\| second third', content)
        self.assertNotIn(str(self.case), content)

    def test_repeated_refresh_preserves_final_bytes(self):
        local = self.skill('repeat')
        rows = [self.row('repeat', local)]
        first = self.run_cli(rows, '--cwd', str(self.root), '--force')
        self.assertEqual(first.returncode, 0, first.stderr)
        before = self.registry().read_bytes()
        second = self.run_cli(rows, '--cwd', str(self.root))
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(before, self.registry().read_bytes())

    def test_outside_symlink_missing_and_noncanonical_rows_not_indexed(self):
        local = self.skill('safe')
        external = self.skill('external', root=self.home)
        escape = self.root / '.agents/skills/escape'
        escape.symlink_to(external.parent, target_is_directory=True)
        nested = self.root / '.agents/skills/safe/examples/phantom/SKILL.md'
        nested.parent.mkdir(parents=True)
        nested.write_text('not a canonical skill')
        result = self.run_cli([
            self.row('safe', local), self.row('escape', escape / 'SKILL.md'),
            self.row('missing', self.root / '.agents/skills/missing/SKILL.md'),
            self.row('phantom', nested),
        ], '--cwd', str(self.root))
        self.assertEqual(result.returncode, 0, result.stderr)
        content = self.registry().read_text()
        self.assertIn('| `safe`', content)
        for absent in ['`escape`', '`missing`', '`phantom`']:
            self.assertNotIn(absent, content)

    def test_native_failure_restores_previous_registry(self):
        local = self.skill('safe')
        for stage in ['refresh', 'list']:
            with self.subTest(stage=stage):
                self.registry().parent.mkdir(exist_ok=True)
                self.registry().write_text('previous index\n')
                result = self.run_cli([self.row('safe', local)], '--cwd', str(self.root),
                                      env=self.env | {'FAIL_NATIVE': stage})
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('native fixture failed at ' + stage, result.stderr)
                self.assertEqual(self.registry().read_text(), 'previous index\n')
                self.assertNotIn('refreshed', result.stdout.lower())

    def test_failed_first_run_does_not_leave_native_only_index(self):
        result = self.run_cli([], '--cwd', str(self.root),
                              env=self.env | {'FAIL_NATIVE': 'list'})
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.registry().exists())

    def test_missing_native_reports_failure_without_creating_registry(self):
        result = self.run_cli([], '--cwd', str(self.root),
                              env=self.env | {'PATH': str(self.case / 'absent')})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('gentle-ai', result.stderr)
        self.assertFalse(self.registry().exists())

    def test_invalid_native_json_is_not_success(self):
        result = self.run_cli({'not': 'an array'}, '--cwd', str(self.root))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('array', result.stderr)
        self.assertFalse(self.registry().exists())

    @unittest.skipUnless(NATIVE, 'installed gentle-ai is required for integration proof')
    def test_real_native_relocation_new_home_and_cache_hit(self):
        first = self.skill('native-local')
        folded = self.skill('folded')
        folded.write_text('---\nname: folded\ndescription: >\n  folded native\n  description\n---\n')
        global_decoy = self.skill('global-decoy', root=self.home)
        native_bin = self.bin / 'gentle-ai'
        native_bin.unlink()
        native_bin.symlink_to(NATIVE)
        alias = self.root / '.claude/skills/native-local'
        alias.parent.mkdir(parents=True)
        alias.symlink_to('../../.agents/skills/native-local', target_is_directory=True)
        before_global = hashlib.sha256(global_decoy.read_bytes()).hexdigest()
        result = self.run_cli([], '--cwd', str(self.root), '--force')
        self.assertEqual(result.returncode, 0, result.stderr)
        original = self.registry().read_bytes()
        self.assertNotIn(b'global-decoy', original)
        self.assertIn(b'.agents/skills/native-local/SKILL.md', original)
        self.assertIn(b'folded native description', original)
        cache = (self.root / '.atl/.skill-registry.cache.json').read_bytes()
        index_mtime = self.registry().stat().st_mtime_ns
        repeated = self.run_cli([], '--cwd', str(self.root))
        self.assertEqual(repeated.returncode, 0, repeated.stderr)
        self.assertEqual(self.registry().read_bytes(), original)
        self.assertEqual(self.registry().stat().st_mtime_ns, index_mtime)
        self.assertEqual((self.root / '.atl/.skill-registry.cache.json').read_bytes(), cache)
        self.assertIn('cache-hit', repeated.stdout)
        self.assertEqual(hashlib.sha256(global_decoy.read_bytes()).hexdigest(), before_global)
        moved = self.case / 'relocated'
        self.root.rename(moved)
        new_home = self.case / 'empty-home'
        new_home.mkdir()
        relocated = self.run_cli([], '--cwd', str(moved), env=self.env | {'HOME': str(new_home)})
        self.assertEqual(relocated.returncode, 0, relocated.stderr)
        self.assertEqual(self.registry(moved).read_bytes(), original)
        self.assertTrue((moved / '.agents/skills/native-local/SKILL.md').is_file())
        self.assertFalse((moved / '.gitignore').exists())


if __name__ == '__main__':
    unittest.main()
