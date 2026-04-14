# AI Coding Agent Blueprint
*Build a persistent Claude Code agent from scratch*
*Version 2.0 — April 2026*

---

## What You Get

This is a working system, not a template. Copy the files into your project, fill in the bracketed values, and run it.

**Deliverables:**
- Production-ready CLAUDE.md with project memory hierarchy
- 4 Claude Code skills (feature build, PR review, debug, deploy)
- 2 custom subagents (security reviewer, test writer)
- Hook configurations for automatic linting and safety
- Complete .claude/ directory structure ready to deploy
- Docker setup with Claude Code CLI pre-installed
- CI/CD integration (GitHub Actions + pre-commit hooks)
- Cost management guide with budget controls
- Token optimization strategies

Everything here is built on Claude Code's official architecture: the agentic loop (gather context → take action → verify results), CLAUDE.md memory hierarchy, skills, subagents, hooks, and MCP integrations. No reinventing the wheel — just wiring it up correctly.

---

## Why This Works

Claude Code is already the agent. Most developers install it and use it like ChatGPT with file access. They're missing 90% of its power.

This blueprint activates the full stack:

1. **CLAUDE.md** — persistent instructions Claude reads every session. Project conventions, code style, workflow rules. Without this, Claude re-learns your project every time.

2. **Skills** — reusable workflows Claude invokes on demand. Instead of typing "review this PR for security issues" every time, you run `/security-review`. Claude knows exactly what to do.

3. **Subagents** — isolated Claude instances with their own context. Send investigation tasks to subagents so your main conversation doesn't fill up with file reads.

4. **Hooks** — deterministic scripts that run at specific points. Unlike CLAUDE.md (advisory), hooks always fire. Use them for linting, testing, and safety gates.

5. **MCP servers** — connect Claude to external services: databases, Figma, Notion, GitHub, monitoring. Claude reads your Jira tickets and implements fixes.

6. **Agent teams** — coordinate multiple Claude sessions with shared tasks and peer-to-peer messaging. Writer/Reviewer patterns, parallel feature development.

Most people use #1. This blueprint gives you #1-6.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    YOUR PROJECT                          │
│                                                         │
│  .claude/                                               │
│  ├── CLAUDE.md          ← persistent instructions       │
│  ├── CLAUDE.local.md    ← personal overrides (gitignored)│
│  ├── settings.json      ← permissions, hooks            │
│  ├── rules/             ← path-specific rules           │
│  │   ├── frontend.md    ← frontend-specific rules       │
│  │   └── backend.md     ← backend-specific rules        │
│  ├── skills/            ← reusable workflows            │
│  │   ├── feature-build/SKILL.md                         │
│  │   ├── pr-review/SKILL.md                             │
│  │   ├── debug/SKILL.md                                 │
│  │   └── deploy/SKILL.md                                │
│  ├── agents/            ← custom subagents              │
│  │   ├── security-reviewer.md                           │
│  │   └── test-writer.md                                 │
│  └── worktrees/         ← isolated git worktrees        │
│                                                         │
│  ~/  (home directory)                                   │
│  └── .claude/                                           │
│      └── CLAUDE.md        ← global rules (all projects) │
│                                                         │
│  External:                                              │
│  ├── MCP servers (DB, Figma, GitHub, monitoring)        │
│  ├── Claude Code CLI (terminal, VS Code, web)           │
│  └── Agent teams (parallel sessions)                    │
└─────────────────────────────────────────────────────────┘
```

---

## 1. CLAUDE.md — The Foundation

Place this at your project root. Claude reads it every session.

```markdown
# [PROJECT_NAME]

## Tech Stack
- Language: [LANGUAGE] v[VERSION]
- Framework: [FRAMEWORK] v[VERSION]
- Database: [DATABASE]
- Package manager: [pnpm/npm/yarn/pip/poetry]
- Runtime: [node/python/rust/go]

## Code Style
- [YOUR SPECIFIC STYLE RULES — only include things Claude can't guess]
- Import style: [ES modules / CommonJS / named imports]
- Naming: [camelCase / snake_case / PascalCase for classes]
- [Any non-obvious conventions unique to your project]

## Commands
- Test: [TEST_COMMAND]
- Lint: [LINT_COMMAND]
- Type check: [TYPECHECK_COMMAND]
- Build: [BUILD_COMMAND]
- Dev server: [DEV_SERVER_COMMAND]

## Architecture
- [BRIEF description of how pieces fit together]
- API layer: [path]
- Business logic: [path]
- Database: [path]
- Frontend: [path]

## Conventions
- Branch naming: [feature/fix/refactor]/description
- Commit style: [conventional commits / custom]
- PR format: [description → what changed → why → testing]

## Testing
- Framework: [jest/pytest/vitest/etc]
- Run single test: [SINGLE_TEST_COMMAND]
- Coverage: [COVERAGE_COMMAND]
- IMPORTANT: Always run relevant tests after code changes

## IMPORTANT Rules
- Never modify [PROTECTED_FILES] without explicit approval
- All API endpoints must have [AUTH/VALIDATION/etc]
- [Any project-specific rules that prevent common mistakes]
```

**Key principles from Anthropic's official guidance:**
- Keep it concise. Every line should answer: "Would removing this cause Claude to make mistakes?"
- Don't include things Claude can figure out by reading code
- Don't include standard language conventions Claude already knows
- Use emphasis ("IMPORTANT", "YOU MUST") for rules Claude keeps missing
- Treat it like code: review when things go wrong, prune regularly
- Check it into git so your team contributes

**Advanced: Import additional files**

```markdown
# CLAUDE.md
See @README.md for project overview and @package.json for available commands.

# Additional rules
- Git workflow: @docs/git-workflow.md
- API conventions: @docs/api-standards.md
```

**Advanced: Directory-level CLAUDE.md**

Place CLAUDE.md in subdirectories for path-specific rules:
- `src/api/CLAUDE.md` — loaded when Claude works on API files
- `src/frontend/CLAUDE.md` — loaded when Claude works on frontend files

---

## 2. Settings — Permissions & Hooks

`.claude/settings.json`:

```json
{
  "permissions": {
    "allow": [
      "Bash(git log *)",
      "Bash(git diff *)",
      "Bash(git status)",
      "Bash([TEST_COMMAND])",
      "Bash([LINT_COMMAND])",
      "Bash([TYPECHECK_COMMAND])",
      "Bash([BUILD_COMMAND])",
      "Read",
      "Glob",
      "Grep"
    ],
    "deny": [
      "Bash(rm -rf *)",
      "Bash DROP *",
      "Bash DELETE FROM *"
    ]
  },
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "[LINT_COMMAND] --fix $FILE"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "if echo \"$COMMAND\" | grep -qE 'DROP|DELETE|rm -rf'; then echo 'BLOCKED: destructive command detected' && exit 2; fi"
          }
        ]
      }
    ]
  }
}
```

**What this does:**
- Auto-runs linter after every file edit
- Blocks destructive commands without explicit override
- Allows common safe commands without prompting
- Review with `/hooks` to see what's configured

---

## 3. Skills — Reusable Workflows

Skills are markdown files in `.claude/skills/`. Claude loads them on demand and can invoke them with `/skill-name`.

### Skill: Feature Build

`.claude/skills/feature-build/SKILL.md`:

```markdown
---
name: feature-build
description: Build a new feature end-to-end with tests
---

Build the feature: $ARGUMENTS

Follow this workflow:

1. EXPLORE (Plan Mode)
   - Read relevant files to understand existing patterns
   - Check @CLAUDE.md for project conventions
   - Identify files that need changes
   - Create a plan listing all changes needed

2. IMPLEMENT
   - Make changes one file at a time
   - Follow existing patterns in the codebase
   - Reference similar features for consistency
   - Run [LINT_COMMAND] after each file change

3. TEST
   - Write tests for new functionality
   - Run: [TEST_COMMAND]
   - Fix any failures
   - Run: [COVERAGE_COMMAND] if available

4. VERIFY
   - Run: [BUILD_COMMAND] to verify compilation
   - Run: [TYPECHECK_COMMAND] if applicable
   - Review all changes for consistency

5. COMMIT
   - Stage all changes
   - Commit with conventional commit message
   - Suggest PR title and description
```

### Skill: PR Review

`.claude/skills/pr-review/SKILL.md`:

```markdown
---
name: pr-review
description: Review a pull request for correctness, security, and style
---

Review the pull request: $ARGUMENTS

1. Get the PR diff: `gh pr diff [PR_NUMBER]`
2. Get the PR description: `gh pr view [PR_NUMBER]`

Review for:

CORRECTNESS
- Does the code do what the PR description says?
- Are edge cases handled?
- Are there logic errors?

SECURITY
- Input validation on all user-controlled data
- No secrets, API keys, or credentials in code
- SQL injection / XSS / command injection vectors
- Authentication and authorization checks

STYLE
- Follows project conventions from CLAUDE.md
- Consistent with existing codebase patterns
- No unnecessary complexity

TESTING
- Are there tests for new functionality?
- Do existing tests still pass?
- Are edge cases covered?

PERFORMANCE
- N+1 query detection
- Missing indexes on new queries
- Unnecessary re-renders or recomputation

Provide specific, actionable feedback with file paths and line numbers.
```

### Skill: Debug

`.claude/skills/debug/SKILL.md`:

```markdown
---
name: debug
description: Systematic debugging with root cause analysis
---

Debug: $ARGUMENTS

Follow this systematic approach:

1. REPRODUCE
   - Identify the exact steps to trigger the issue
   - Run the failing test or reproduce the error
   - Capture the full error message and stack trace

2. ISOLATE
   - Binary search: narrow down which file/function/line causes the issue
   - Check recent changes: `git log --oneline -20`
   - Use `git bisect` if the bug was introduced in a past commit

3. DIAGNOSE (Root Cause)
   - Use the 5 Whys technique
   - Don't fix symptoms — find the root cause
   - Check for: race conditions, null/undefined, off-by-one, type mismatches

4. FIX
   - Make the minimal change that fixes the root cause
   - Don't refactor or "improve" unrelated code in the same change

5. VERIFY
   - Write a regression test that would have caught this bug
   - Run the test to confirm it passes
   - Run the full test suite to check for regressions
   - Run: [LINT_COMMAND] and [TYPECHECK_COMMAND]

6. DOCUMENT
   - If this was a subtle bug, add a comment explaining why
   - Update CLAUDE.md if this reveals a project gotcha
```

### Skill: Deploy

`.claude/skills/deploy/SKILL.md`:

```markdown
---
name: deploy
description: Deploy with safety checks and rollback plan
disable-model-invocation: true
---

Deploy: $ARGUMENTS

⚠️ This skill requires manual invocation. Run `/deploy [target]`.

1. PRE-DEPLOY CHECKS
   - Run: [TEST_COMMAND] — all tests must pass
   - Run: [LINT_COMMAND] — no lint errors
   - Run: [BUILD_COMMAND] — successful build
   - Check: `git status` — no uncommitted changes
   - Check: current branch is [MAIN_BRANCH]

2. DEPLOY
   - Run: [DEPLOY_COMMAND]
   - Monitor output for errors

3. VERIFY
   - Run health check: [HEALTH_CHECK_URL]
   - Check for error spikes in logs
   - Verify key functionality works

4. ROLLBACK PLAN
   - If deploy fails: [ROLLBACK_COMMAND]
   - Document what went wrong
   - Create issue to track the fix
```

---

## 4. Subagents — Isolated Workers

Subagents run in their own context window. They don't bloat your main conversation. Claude delegates to them and gets back a summary.

### Security Reviewer

`.claude/agents/security-reviewer.md`:

```markdown
---
name: security-reviewer
description: Reviews code for security vulnerabilities
tools: Read, Grep, Glob, Bash
model: opus
---

You are a senior security engineer. Review code for:

CRITICAL
- SQL injection, XSS, command injection, SSRF
- Authentication and authorization bypasses
- Secrets, credentials, API keys in code
- Path traversal, deserialization attacks

HIGH
- Insecure data handling (plaintext PII, weak hashing)
- Missing input validation
- Insecure defaults
- Race conditions on security-critical operations

MEDIUM
- Excessive error messages leaking internals
- Missing rate limiting
- CORS misconfiguration
- Outdated dependencies with known CVEs

For each finding, provide:
- Severity (Critical/High/Medium/Low)
- File path and line number
- Description of the vulnerability
- Suggested fix with code example
```

### Test Writer

`.claude/agents/test-writer.md`:

```markdown
---
name: test-writer
description: Writes comprehensive tests for specified code
tools: Read, Grep, Glob, Bash, Edit
model: sonnet
---

You are a test engineer. Write tests for: $ARGUMENTS

Approach:
1. Read the source code to understand what's being tested
2. Identify all public functions/methods and their contracts
3. Write tests covering:
   - Happy path (expected inputs → expected outputs)
   - Edge cases (empty, null, boundary values, unicode)
   - Error paths (invalid inputs, exceptions, timeouts)
   - Integration points (database, external APIs)
4. Use the project's test framework from CLAUDE.md
5. Follow existing test patterns in the codebase
6. Run the tests and fix any failures
7. Report coverage if [COVERAGE_COMMAND] is available
```

**Usage:** Tell Claude to use subagents:
- "Use the security-reviewer subagent to audit src/api/auth.ts"
- "Use the test-writer subagent to add tests for src/utils/validation.ts"

---

## 5. Path-Specific Rules

Rules that only load when Claude works in specific directories.

`.claude/rules/frontend.md`:

```markdown
---
description: Rules for frontend code
globs: src/frontend/**, src/components/**, src/pages/**
---

- Use Server Components by default. Only use 'use client' when state or browser APIs are needed.
- All user-facing strings must be i18n-ready (use the translation function, not hardcoded strings).
- Follow the component pattern: props interface → component → export.
- Test components with the project's testing library. Test user interactions, not implementation details.
- Use CSS modules or Tailwind. No inline styles except for dynamic values.
```

`.claude/rules/backend.md`:

```markdown
---
description: Rules for backend code
globs: src/api/**, src/services/**, src/db/**
---

- All API endpoints must validate input with [VALIDATION_LIBRARY].
- Use parameterized queries only. Never interpolate user input into SQL.
- All async operations must have proper error handling and timeouts.
- Database queries must use the repository pattern. No raw queries in route handlers.
- Log request IDs for tracing. Never log PII or secrets.
```

---

## 6. MCP Integrations

Connect Claude to external services with MCP servers.

### GitHub (built-in awareness)
Claude already uses the `gh` CLI. Install it for best results:
```bash
# Claude can create PRs, read issues, review code, manage branches
claude mcp add github -- npx -y @anthropic/mcp-server-github
```

### Database
```bash
claude mcp add postgres -- npx -y @anthropic/mcp-server-postgres $DATABASE_URL
```
Now you can ask Claude: "Show me all users who signed up this week" and it queries directly.

### Common MCP Servers
```bash
# Figma — read designs and implement UI
claude mcp add figma -- npx -y @anthropic/mcp-server-figma

# Filesystem — extended file operations
claude mcp add filesystem -- npx -y @anthropic/mcp-server-filesystem /path/to/project

# Notion — read/write Notion pages and databases
claude mcp add notion -- npx -y @anthropic/mcp-server-notion

# Slack — send messages, read channels
claude mcp add slack -- npx -y @anthropic/mcp-server-slack
```

Check MCP status: `claude mcp list`
Check per-server context costs: `/mcp`

---

## 7. Docker Deployment

For running Claude Code in containers (CI/CD, remote environments):

```dockerfile
FROM ubuntu:24.04

# Install Claude Code
RUN curl -fsSL https://claude.ai/install.sh | bash

# Install your project dependencies
RUN apt-get update && apt-get install -y git build-essential

WORKDIR /app
COPY . .

# Claude Code config
ENV CLAUDE_CODE_USE_BEDROCK=0
ENV ANTHROPIC_API_KEY=[YOUR_KEY]

ENTRYPOINT ["claude"]
```

**CI/CD with Claude Code:**

```yaml
# .github/workflows/claude-review.yml
name: Claude Code Review
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Install Claude Code
        run: curl -fsSL https://claude.ai/install.sh | bash
      - name: Run security review
        run: |
          claude -p "Review this PR for security vulnerabilities. Focus on input validation, auth, and data exposure. Use gh pr diff to get the changes." \
            --output-format json > review.json
      - name: Post review comment
        run: |
          claude -p "Post the review from review.json as a PR comment using gh pr comment"
```

**Pre-commit hook:**

```yaml
# .claude/settings.json addition
{
  "hooks": {
    "PreCommit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "claude -p 'Review staged changes for obvious bugs and style issues. Be brief.' --output-format text"
          }
        ]
      }
    ]
  }
}
```

---

## 8. Cost Management

Claude Code costs real money. Here's how to control it.

### Budget Controls

```bash
# Limit spending per invocation (CI/CD)
claude -p "task" --max-budget-usd 1.00

# Limit turns (agentic loop iterations)
claude -p "task" --max-turns 10
```

### Token Optimization

The single biggest cost factor is context window usage. Claude's performance degrades as context fills, AND you pay for every token.

**Strategies:**
1. **Use /clear between unrelated tasks** — resets context entirely
2. **Use subagents for investigation** — their file reads don't fill your context
3. **Use skills with `disable-model-invocation: true`** — loaded only when you invoke them
4. **Use /btw for quick questions** — answer appears in overlay, doesn't enter history
5. **Use --bare for scripted calls** — skips hooks, skills, MCP, memory discovery
6. **Compact strategically** — `/compact focus on the API changes`
7. **Keep CLAUDE.md concise** — every line costs context on every session

### Context Costs by Feature

| Feature | Context Cost | When It Loads |
|---------|-------------|---------------|
| CLAUDE.md (root) | Every session | Always |
| CLAUDE.md (directory) | When working in that dir | On demand |
| Skills (descriptions) | ~50 tokens each | Session start |
| Skills (full content) | Full file size | When invoked |
| Subagents | Zero (separate context) | When delegated |
| MCP tool names | ~10 tokens each | Session start |
| MCP tool schemas | Full schema size | When used |
| Auto memory | First 200 lines / 25KB | Session start |

### When to Use What

| Scenario | Use |
|----------|-----|
| Rules that always apply | CLAUDE.md |
| Rules for specific file paths | .claude/rules/ |
| Workflows you invoke manually | Skills (disable-model-invocation) |
| Knowledge Claude loads automatically | Skills (default) |
| Heavy investigation tasks | Subagents |
| External service integration | MCP servers |
| Actions that must always happen | Hooks |
| Running unattended (CI/CD) | claude -p with --max-turns and --max-budget-usd |

---

## 9. Advanced Patterns

### Writer/Reviewer Pattern
Run two Claude sessions in parallel:
- **Session A (Writer):** Implement the feature
- **Session B (Reviewer):** Review the implementation

Fresh context in Session B means unbiased review. Start with:
```bash
# Terminal 1
claude -w feature-auth  # worktree mode

# Terminal 2
claude -w feature-auth  # same worktree, different session
```

### Fan-Out Pattern
For large-scale changes (migrations, refactors):
```bash
# Generate task list
claude -p "List all files that need migrating from [X] to [Y]" > files.txt

# Process in parallel
for file in $(cat files.txt); do
  claude -p "Migrate $file from [X] to [Y]" \
    --allowedTools "Edit,Bash(git commit *)" \
    --max-turns 5
done
```

### Interview Pattern
For complex features, let Claude interview you first:
```
I want to build [brief description]. Interview me using AskUserQuestion.
Ask about edge cases, tradeoffs, and technical decisions I might not have considered.
Keep going until we've covered everything, then write a spec to SPEC.md.
```

### Plan Mode Workflow
```
claude  # Start session
# Press Shift+Tab twice for Plan Mode
# Claude reads files, creates plan, no edits
# Review plan, then Shift+Tab back to Normal Mode
# Claude implements
```

---

## 10. Quick Start

1. **Install Claude Code:** `curl -fsSL https://claude.ai/install.sh | bash`
2. **Initialize:** `claude` then run `/init` to generate a starter CLAUDE.md
3. **Customize:** Replace the generated CLAUDE.md with the template from Section 1
4. **Add skills:** Copy the 4 skill files from Section 3 into `.claude/skills/`
5. **Add subagents:** Copy the 2 agent files from Section 4 into `.claude/agents/`
6. **Configure hooks:** Set up `.claude/settings.json` from Section 2
7. **Add MCP:** Connect external services from Section 6
8. **Test:** Run `/feature-build add user authentication` to verify everything works
9. **Commit:** Check everything into git so your team benefits

---

## What Makes This Different

Every section is backed by Claude Code's official architecture. This isn't theoretical — it's how Anthropic's own teams use Claude Code, documented in their official best practices guide.

The agentic loop (gather → act → verify) is already built into Claude Code. CLAUDE.md, skills, subagents, hooks, and MCP are the official extension system. This blueprint wires them together into a coherent system that makes any developer dramatically more productive.

---

*Lifetime updates included. When Claude Code adds new features or changes its architecture, you'll get an updated blueprint. Based on Claude Code documentation as of April 2026.*
