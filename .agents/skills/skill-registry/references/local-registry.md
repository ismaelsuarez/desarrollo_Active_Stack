# Refresh the repository-local skill index

Run this command from the project root before reading the index or delegating work:

```bash
python3 .agents/skills/skill-registry/scripts/refresh.py
```

Use `--force` to force native metadata regeneration. From another directory, invoke the script by its path; its default repository is inferred from its own location. `--cwd <repository>` explicitly selects an isolated target for tests or another authorized repository. Selecting another directory does not authorize copying skills into it.

## What the command does

1. Run `gentle-ai skill-registry refresh --no-gitignore --cwd <repository>` and then the read-only native `list --json` command.
2. Preserve native metadata parsing, name deduplication and exclusions; do not reimplement YAML parsing.
3. Resolve selected files through compatibility links, retaining only existing physical `.agents/skills/<directory>/SKILL.md` files inside the selected repository.
4. Write `.atl/skill-registry.md` atomically with sorted rows, escaped cells, project scope and paths relative to the repository root. Do not modify the native cache schema or add `.atl/` to `.gitignore`.

Native failure or malformed metadata returns nonzero and restores the previous index (or removes the intermediate native-only index on a first run). This is not a fallback scanner. Native caches are runtime state; copying the repository does not require its old cache or access to the original home directory.

The native tool deliberately omits `skill-registry` and `_shared` from the index. Load the registry workflow directly at `.agents/skills/skill-registry/SKILL.md`. Keep supporting resources and licensing with every canonical skill bundle. `.claude/skills/` links are compatibility aliases inside this repository, not links to global installations.

## Global-hook boundary

The installed Codex SessionStart hook still invokes native refresh, and Claude may refresh on prompt submission. The native tool has hardcoded local and global scan roots and no repository configuration for project-only relative output. A source change or `--force` can therefore replace the projected index with a global/absolute version. Run the project wrapper before consuming it. Subsequent native cache hits leave the projection intact.

This local workflow does not intercept hooks, change their order, modify global installations or guarantee native output. An agent must normalize before reading any cached or Engram-mirrored registry; on failure it must report the missing proof instead of using global skill paths.

## Verification

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s .agents/skills/skill-registry/tests -p 'test_*.py'
```

Tests exercise the public CLI with an isolated fake native executable and the installed native binary when available. They cover compatibility links, global decoys, escaping, native failure, cache hits, repeated bytes and relocation to a different home directory. Fixtures are created outside the worktree; each run prints the retained scratch directory for parent cleanup. `SKILL_REGISTRY_TEST_TMPDIR` can select an existing external scratch parent.

Some bundled domain skills already reference optional sibling skills not installed in this project (`web-quality-audit`, `e2e-testing`, `react-patterns`, `tdd-workflow`) or an absent React-rules file. These pre-existing links are not added capabilities; report them when relevant rather than importing unrelated global skills automatically.
