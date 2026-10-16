# Skill Resolver — Universal Protocol

Any agent that **delegates work to sub-agents** MUST use this protocol to resolve relevant skills and pass them safely.

## Why This Exists

Sub-agents start with no project skill context. The registry gives delegators a cheap index of available skills without rewriting or summarizing those skills.

## When to Apply

Before every sub-agent launch that involves reading, writing, reviewing, testing, documenting, or creating project artifacts. Skip only for purely mechanical commands.

## The Protocol

### Step 1: Obtain the Skill Registry

The registry is an **index** of skill names, triggers, scopes, and exact `SKILL.md` paths. It is not a compact-rules bundle.

For this repository, normalize before every registry read or delegation:

```bash
python3 .agents/skills/skill-registry/scripts/refresh.py
```

Read `.atl/skill-registry.md` from the selected repository, not a stale session or
Engram copy. The index is versioned and contains only relative canonical paths in
`.agents/skills/`. Resolve paths against that repository root and check they exist.
If the wrapper fails or a required local bundle is missing, report it; do not
silently substitute a global skill. Engram remains a recovery mirror, not an
alternative source of paths. Load the internal registry skill directly from
`.agents/skills/skill-registry/SKILL.md` because native indexing excludes it.

Global startup hooks can overwrite this projection after a native source change
or forced refresh. The project wrapper restores it; native cache hits preserve
it. This policy does not modify or intercept those global hooks.

### Step 2: Match Relevant Skills

Match on two dimensions:

| Context | Match against |
| --- | --- |
| Code/files | Registry trigger/description mentions the language, framework, tool, or path context |
| Task/action | Registry trigger/description mentions actions like PR, review, docs, tests, Jira, comments, release |

Prefer the smallest useful set. If more than five skills match, keep the five most relevant and prioritize code context over task context.

### Step 3: Pass Skill Paths

Inject paths, not summaries:

```markdown
## Skills to load before work

Read these exact files before reading, writing, reviewing, testing, or creating artifacts:

- .agents/skills/go-testing/SKILL.md
- .agents/skills/fastapi/SKILL.md
```

The sub-agent MUST read those files before task-specific work. `SKILL.md` is the runtime contract and source of truth.

### Step 4: Report Resolution

Sub-agents MUST report `skill_resolution`:

- `paths-injected` — received exact skill paths from the delegator and loaded them.
- `fallback-registry` — no paths received, self-loaded paths from the registry.
- `fallback-path` — loaded an explicit fallback path outside the registry.
- `none` — no skills loaded.

If a sub-agent reports anything other than `paths-injected`, the orchestrator MUST re-read the registry before the next delegation.

## Compaction Safety

- The registry persists in Engram and `.atl/skill-registry.md`.
- Delegators can recover selected paths after compaction by re-reading the registry.
- Sub-agents receive exact files to read, so skill meaning is not degraded by generated summaries.

## Integration Points

- **ODD Orchestrator**: resolves paths for bounded exploration, implementation and verification delegations.
- **judgment-day**: resolves paths before Judge A, Judge B, and Fix Agent.
- **pr-review and future delegators**: use this protocol when launching sub-agents.
