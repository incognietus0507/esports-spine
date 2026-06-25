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

## NOT installed: hooks

ECC's `hooks/` (PreToolUse/PostToolUse dispatchers that run Node scripts on
every Bash/Write/Edit and inject context each turn) were **deliberately left
out** of this install pending explicit review/sign-off. They execute
third-party code with your permissions on every tool call and can gate
commands (e.g. git push) — a meaningful supply-chain and behavior surface.
See the conversation for the per-hook summary. To enable later, they must be
wired into `settings.json` explicitly.

## Trust note

These are third-party prompt/instruction files. They were copied verbatim and
not audited line-by-line. Treat their guidance as suggestions, not authority,
and review before relying on any single one.
