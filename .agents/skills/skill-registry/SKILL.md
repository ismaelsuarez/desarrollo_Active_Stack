---
name: skill-registry
description: "Trigger: update skills, skill registry, actualizar skills, after skill changes. Index available skills by trigger and path."
license: MIT
metadata:
  author: gentleman-programming
  version: "1.0"
---

## Activation Contract

Use after installing, removing, creating, moving or renaming project skills, and before consuming the registry for delegation.

## Hard Rules

- Canonical, self-contained bundles live in this repository's `.agents/skills/`. Global installations remain unchanged.
- The versioned `.atl/skill-registry.md` is an index of relative local paths, not a summary. Read full `SKILL.md` files and pass their exact canonical paths; do not inject compact rules.
- Use the project wrapper below: native Gentle AI owns metadata parsing and deduplication; the wrapper filters to physical canonical files and normalizes paths. Never silently fall back to global skills or a hand-written metadata scan.
- Do not ignore `.atl/` in this project. The native command runs with `--no-gitignore`; its cache remains native-owned.
- Persist the completed index to Engram under `topic_key: skill-registry`, `type: config`, with `capture_prompt: false` when available. A failed mirror does not invalidate the local index; report it.

## Decision Gates

| Situation | Action |
| --- | --- |
| Same skill exists globally and in the repository | Use the complete physical local bundle |
| Native command missing, failed or returns malformed metadata | Stop and report failure; do not fabricate success or substitute global paths |
| Required local skill missing | Report it and request a local installation if needed |
| Native startup hook overwrote the index | Run the project wrapper before reading it |

## Execution Steps

1. Run from the repository root:
   ```bash
   python3 .agents/skills/skill-registry/scripts/refresh.py
   ```
   Add `--force` after skill changes if needed, or `--cwd <repository>` when invoked elsewhere. Without `--cwd`, the script finds its own repository independently of the process directory.
2. Read back `.atl/skill-registry.md`: every indexed path must exist under `.agents/skills/`, be relative to the repository root, and have project scope. Native intentionally excludes `_shared`, `skill-registry` and retired `sdd-*` entries; load this internal skill directly by path.
3. Update only the `registry` metadata in `.active-orchestrator-state.json`; preserve completed foundation state and other sections. Mirror the read-back index in Engram when available.
4. Report count, canonical location, native cache/refresh outcome, and mirror result.

## Output Contract

Return the project and registry paths, number of local skills, native cache/refresh status, projection result, failures and Engram mirror status.

## References

- [Local workflow and limitations](references/local-registry.md) — command behavior, native hooks, validation and portability.
- [Skill style guide](references/skill-style-guide.md) — authoring guidance.
- [Skill resolver](../_shared/skill-resolver.md) — delegation path contract.
