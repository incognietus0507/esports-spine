# Installed from ECC (Everything Claude Code)

Third-party Claude Code assets vendored into this repo's `.claude/` directory.

- **Source:** https://github.com/affaan-m/ECC (branch `main`)
- **Installed:** 2026-06-25
- **License:** see the upstream repo (`LICENSE`)
- **Method:** individual files fetched read-only over the session's allowed
  HTTPS egress (raw.githubusercontent.com). `git clone` of this repo is **not**
  permitted in this session (the credentialed git proxy is scoped to
  `incognietus0507/esports-spine`).

## Scope of this install

A **curated subset** relevant to this Python project — not the full marketplace
(which is ~700 files spanning Angular, Flutter, HarmonyOS, Kotlin, etc.). Add
more on request.

| Category | Count | What |
|----------|-------|------|
| `agents/`   | 15 | architect, code-architect, code-explorer, code-reviewer, code-simplifier, refactor-cleaner, planner, python-reviewer, security-reviewer, performance-optimizer, silent-failure-hunter, build-error-resolver, pr-test-analyzer, doc-updater, database-reviewer |
| `skills/`   | 15 | python-patterns, python-testing, tdd-workflow, error-handling, security-review, security-scan, api-design, api-connector-builder, backend-patterns, architecture-decision-records, hexagonal-architecture, git-workflow, github-ops, database-migrations, data-scraper-agent |
| `commands/` | 5  | code-review, plan, feature-dev, build-fix, checkpoint |
| `rules/`    | 16 | `common/*` (language-agnostic) + `python/*` |

## Hooks: INSTALLED + WIRED (full runtime)

The full ECC hook runtime is vendored and wired into `.claude/settings.json`
(explicitly authorized). This runs third-party Node on **every** tool call.

- **Runtime:** `.claude/scripts/` (~208 files: 48 hooks + 94 lib + support).
- **Wiring:** `.claude/settings.json` maps ECC's `hooks/hooks.json` events
  (PreToolUse, PostToolUse, PostToolUseFailure, PreCompact, Stop,
  SessionStart, SessionEnd) to commands rooted at `$CLAUDE_PROJECT_DIR/.claude`
  and routed through `scripts/hooks/plugin-hook-bootstrap.js`.
- **Deps:** `cd .claude && npm install` (only `@iarna/toml`, `ajv`, `sql.js`;
  `node_modules/` is gitignored). Core gating hooks work without them.

### What the hooks do (high-impact ones)
- **GateGuard fact-force** — *denies the first Bash command each session* and
  the first edit to each file until you state the request + intent.
- **block-no-verify** — hard-blocks `git commit/push --no-verify` (exit 2).
- **config-protection** — blocks edits to linter/formatter configs.
- **mcp-health-check** — blocks MCP calls deemed unhealthy.
- **ecc-context-monitor / observers** — inject context + record every tool use.

### Activation & safety
Claude Code does **not** auto-activate hooks from a changed `settings.json` —
it prompts you to review/approve new hooks first. So this config is inert until
you approve it (typically at next session start).

### How to disable / tune
- All hooks: remove/empty the `hooks` block in `.claude/settings.json`.
- GateGuard only: run the session with `ECC_GATEGUARD=off`.
- Specific hooks: set `ECC_DISABLED_HOOKS=pre:bash:gateguard-fact-force,...`
  (the `id` of each hook is in `settings.json`).

## Trust note

These are third-party prompt/instruction files. They were copied verbatim and
not audited line-by-line. Treat their guidance as suggestions, not authority,
and review before relying on any single one.
