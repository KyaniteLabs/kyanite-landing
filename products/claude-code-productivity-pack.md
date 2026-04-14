# Claude Code Productivity Pack
*100 Claude Code prompts with worked examples and anti-patterns*
*Version 2.0 — April 2026*

---

## What You Get

**100 prompts** designed specifically for Claude Code — not generic LLM prompts. Every prompt leverages Claude Code's agentic capabilities: file operations, shell commands, subagents, skills, hooks, and the gather-act-verify loop.

What makes this different from free prompt lists:
- **Claude Code-specific syntax** — uses `@file` references, `/commands`, Plan Mode, and skill invocations
- **Worked examples** — shows actual input/output for every category
- **Anti-patterns** — what NOT to do and why it wastes tokens/money
- **Context management** — every prompt is optimized for context window efficiency
- **Verification built in** — every prompt includes a check step (the #1 thing Anthropic recommends)

Organized into:
- Getting Started & Setup (10)
- Architecture & Design (12)
- Implementation (16)
- Code Review & Security (12)
- Debugging & Troubleshooting (14)
- Testing (14)
- Documentation (8)
- DevOps & Deployment (8)
- Context & Session Management (6)

Plus: 10 chaining recipes, 5 anti-pattern deep dives.

---

## How Claude Code Is Different

Before the prompts, understand why Claude Code prompts are not ChatGPT prompts.

**The agentic loop:** When you give Claude Code a task, it works through three phases: gather context, take action, verify results. Good prompts give Claude enough information to start the loop correctly.

**Context is your scarcest resource:** Every file Claude reads, every command it runs, fills the context window. Performance degrades as context fills. The best prompts are specific enough to avoid unnecessary exploration.

**Claude Code has tools:** It can read files, edit code, run commands, search the web, spawn subagents, and connect to external services via MCP. Good prompts leverage these capabilities.

**Verification is everything:** Anthropic's official guidance: "Include tests, screenshots, or expected outputs so Claude can check itself. This is the single highest-leverage thing you can do."

---

## Anti-Patterns: What NOT to Do

### Anti-Pattern #1: The Kitchen Sink Session
```
# ❌ BAD — mixing unrelated tasks
claude> fix the login bug
claude> also explain how the auth module works
claude> and while you're at it, refactor the user model
claude> now go back to the login bug
```
Context is full of irrelevant information. Performance tanks.
**Fix:** `/clear` between unrelated tasks. Each task gets a fresh session.

### Anti-Pattern #2: Vague Without Verification
```
# ❌ BAD — no success criteria
claude> make the dashboard look better
```
Claude produces something that looks right but might not work. You become the only feedback loop.
**Fix:** Paste a screenshot. Define what "better" means. Include test cases.

### Anti-Pattern #3: Over-Specified CLAUDE.md
```
# ❌ BAD — bloated CLAUDE.md
- Write clean code
- Follow best practices
- Use meaningful variable names
- Handle errors properly
- Test your code
- Document your changes
```
Claude already knows all of this. Adding it to CLAUDE.md wastes context on every session and drowns out your actual rules.
**Fix:** Only include things Claude can't infer. "Use ES modules, not CommonJS" is good. "Write clean code" is noise.

### Anti-Pattern #4: The Infinite Exploration
```
# ❌ BAD — unscoped investigation
claude> investigate why the app is slow
```
Claude reads hundreds of files, fills context, and you still don't have an answer.
**Fix:** Scope it. "Investigate why /api/users takes 3+ seconds. Check src/api/users.ts and the database queries it makes."

### Anti-Pattern #5: Correcting Without Clearing
```
# ❌ BAD — repeated corrections in same session
claude> that's wrong, fix it
claude> still wrong, try again
claude> no, the issue is in the auth middleware
claude> you're not listening to me
```
Context is polluted with failed approaches. Claude keeps going back to them.
**Fix:** After 2 failed corrections, `/clear` and write a better initial prompt incorporating what you learned.

---

## Prompt Format Legend

- `@path/to/file` — Claude reads the file before responding
- `Plan Mode` — Press Shift+Tab twice; Claude reads files but makes no edits
- `/command` — Built-in Claude Code slash command
- `[BRACKETS]` — Replace with your specific values
- `→` — Expected behavior or output

---

## Getting Started & Setup

### 1. Initialize Project
```
/init
```
→ Generates a starter CLAUDE.md based on your codebase structure. Run this first in every project.

### 2. Diagnose Installation
```
/doctor
```
→ Checks for common issues with your Claude Code installation.

### 3. Set Up Project Memory
```
Run /init, then customize the generated CLAUDE.md for this project.
Add code style rules, build commands, and architecture overview.
Check @.claude/ for the directory structure.
```
→ Gives Claude persistent context across sessions.

### 4. Configure Permissions
```
Set up .claude/settings.json to allow these commands without prompting:
- [LINT_COMMAND]
- [TEST_COMMAND]
- git status, git diff, git log
Deny: rm -rf, DROP, DELETE FROM
```

### 5. Add MCP Servers
```
claude mcp add github -- npx -y @anthropic/mcp-server-github
claude mcp add postgres -- npx -y @anthropic/mcp-server-postgres $DATABASE_URL
```
→ Claude can now query your database and manage GitHub directly.

### 6. Create a Debug Skill
```
Create a skill at .claude/skills/debug/SKILL.md that:
1. Reproduces the issue
2. Isolates the cause (binary search through code)
3. Finds root cause (5 Whys)
4. Fixes and writes regression test
5. Verifies fix
```
→ Run `/debug [issue]` any time.

### 7. Set Up Auto-Commit Hook
```
Write a hook in .claude/settings.json that runs [LINT_COMMAND] after every Edit or Write tool use.
This catches issues immediately, not at PR review time.
```

### 8. Connect to Figma
```
claude mcp add figma -- npx -y @anthropic/mcp-server-figma
```
→ Claude can read Figma designs and implement them directly.

### 9. Create a Security Subagent
```
Create .claude/agents/security-reviewer.md:
- model: opus
- tools: Read, Grep, Glob, Bash
- Focus: injection, auth bypasses, secrets, data exposure
Use it: "Use the security-reviewer subagent to audit @src/api/"
```

### 10. Cost Control Setup
```
For CI/CD runs, always use:
claude -p "task" --max-turns 10 --max-budget-usd 1.00
For exploration, use subagents to keep main context clean.
Run /context to see what's using space.
```

---

## Architecture & Design

### 11. Explore Before Building
```
Plan Mode: Read @src/auth/ and @src/payments/ and understand how we handle sessions, authentication, and payment processing. Create a plan for adding [FEATURE].
```
→ Claude reads files, creates a plan, makes no edits. Review the plan, then switch to Normal Mode to implement.

### 12. API Design with OpenAPI
```
Design the REST API for [FEATURE_NAME]. For each endpoint provide: method, path, request/response JSON schema, auth requirements, error codes. Format as OpenAPI 3.0 spec. Write it to docs/api/[FEATURE].yaml.
```

### 13. Architecture Decision Record
```
Create an ADR for [DECISION]. Format: Context → Decision → Consequences → Alternatives. Write it to docs/adr/[NUMBER]-[slug].md. Reference existing ADRs in docs/adr/ if they exist.
```

### 14. Database Schema Design
```
Design the database schema for [DOMAIN]. Include: tables, types, constraints, indexes for common queries, foreign keys, migration up/down. Consider: normalization level, audit trails, soft deletes. Write migration files.
```

### 15. Component Architecture
```
Design the [COMPONENT] component. Cover: public interface, internal structure, dependencies, error handling, testing approach. Check @src/components/ for existing patterns and follow them.
```

### 16. Caching Strategy
```
Design caching for [ENDPOINT]. Consider: cache location (CDN, app, DB), invalidation strategy (TTL, event-driven), key schema, cache warming, what cannot be cached, fallback on miss.
```

### 17. Event-Driven Architecture
```
Design event architecture for [SUBSYSTEM]. Cover: event types and payloads, pub/sub vs event sourcing, idempotency, ordering, consumer groups, dead letter queue, backfill strategy.
```

### 18. Tech Stack Evaluation
```
Evaluate [TECH] for [USE_CASE]. Score 1-5 on: developer experience, scalability, maintainability, ecosystem, cost. Compare with [ALTERNATIVE_1] and [ALTERNATIVE_2]. Give a recommendation with justification.
```

### 19. Microservice Boundary Definition
```
Define service boundaries for [SYSTEM]. Cover: bounded contexts, sync vs async communication, data ownership, transaction boundaries, API contracts, deployment independence.
```

### 20. Observability Design
```
Design observability for [SERVICE]. Cover: structured logging fields, key metrics (RED method), distributed tracing, health check endpoints, alerting thresholds, on-call dashboard layout.
```

### 21. Security Design Review
```
Do a security design review for [FEATURE]. Identify: auth/authz points, input validation surfaces, data exposure risks, injection vectors, rate limiting needs, secrets management. Recommend specific mitigations.
```

### 22. Scalability Assessment
```
Assess scalability for [ENDPOINT]. Current: [CURRENT_LOAD]. Growth: [EXPECTED_GROWTH]. Identify bottlenecks at 10x and 100x. Recommend: caching, indexing, horizontal scaling, connection pooling.
```

---

## Implementation

### 23. Feature: Full Stack
```
Implement [FEATURE] end to end:
1. Create data model and migration
2. Build API endpoint with validation
3. Build frontend component with loading/error/empty states
4. Write unit tests for business logic
5. Write integration tests for the API
6. Run [TEST_COMMAND] and fix failures
7. Run [BUILD_COMMAND] to verify compilation
```

### 24. API Endpoint
```
Build [METHOD] [PATH]. Include: input validation, request/response schemas, auth check, database operations with transaction, error responses with correct HTTP status, unit tests for success and failure paths. Follow patterns in @src/api/.
```

### 25. React Component (Server + Client)
```
Build a [COMPONENT] component. Use Server Components by default. Only add 'use client' if state or browser APIs are needed. Include: props interface, loading/error/empty states, responsive layout, ARIA labels, tests with testing-library. Follow patterns in @src/components/.
```

### 26. Background Job
```
Build a background job for [TASK]. Include: retry logic with exponential backoff, dead letter queue handling, idempotency check, monitoring events (start/success/failure), job-specific metrics.
```

### 27. Webhook Handler
```
Build a webhook handler for [SERVICE]. Include: signature verification, idempotency (store event IDs), async processing (don't block the response), error handling, logging of raw payload for debugging.
```

### 28. Authentication Flow
```
Build [AUTH_TYPE] authentication. Include: login/signup, token storage with HTTP-only cookies, token refresh, protected routes, session invalidation, CSRF protection. Follow patterns in @src/auth/.
```

### 29. File Upload
```
Build file upload for [USE_CASE]. Client: multipart form or presigned URL. Server: receive, validate (type, size), store (local or cloud), thumbnail generation, access control on downloads.
```

### 30. Search Feature
```
Build search for [DOMAIN]. Include: index schema, full-text + filter query building, ranking and relevance tuning, faceted search with counts, <200ms SLA, fallback to database LIKE if search is unavailable.
```

### 31. Real-Time Feature
```
Build real-time updates for [FEATURE]. Choose transport: WebSockets or SSE based on requirements. Include: channel design, connection management, reconnection with backfill, client subscription, auth for connections.
```

### 32. Rate Limiting
```
Implement rate limiting for [ENDPOINT]. Use [ALGORITHM: token bucket/sliding window]. Scope: per user and per IP. Response: 429 with Retry-After header. Include rate limit headers on successful responses.
```

### 33. Feature Flags
```
Implement feature flags for [FEATURE]. Include: storage, gradual rollout percentage, user segment targeting, admin toggle, fallback if flag service is down, metrics: evaluation rate and feature engagement.
```

### 34. Pagination
```
Implement cursor-based pagination for [ENDPOINT]. Include: consistent sorting, cursor encoding/decoding, count metadata, no OFFSET (avoid large skip performance issue).
```

### 35. Data Migration
```
Build data migration for [CHANGE]. Include: migration up/down, data validation before processing, batch size and transaction boundaries, progress tracking, error report for failed rows, rollback capability.
```

### 36. Middleware
```
Build [PURPOSE] middleware. Include: preconditions check, side effects (logging, metrics), pass-through on failure, test cases for all branches. Follow patterns in @src/middleware/.
```

### 37. CLI Tool
```
Build a CLI tool for [TASK]. Include: argument parsing with [PARSER], help text with examples, error handling with user-friendly messages, exit codes (0 success, 1 error), config file support.
```

### 38. Batch Processing
```
Build batch processing for [OPERATION]. Include: batch size [SIZE], concurrency [LEVEL], progress tracking, checkpointing (resume from failure), partial failure handling, completion notification.
```

---

## Code Review & Security

### 39. Full PR Review
```
Review the PR at [PR_URL]. Cover: correctness (does it do what it says?), edge cases, performance implications, security, test coverage, readability. Use `gh pr diff [NUMBER]` and `gh pr view [NUMBER]`. Provide specific feedback with file:line references.
```

### 40. Security Review with Subagent
```
Use the security-reviewer subagent to audit @src/api/[PATH]. Focus on: injection vectors, auth bypasses, secrets in code, data exposure, input validation gaps. Report findings with severity and fix suggestions.
```

### 41. Performance Review
```
Review @src/[PATH] for performance. Check: N+1 queries, missing indexes, unnecessary re-renders/recomputation, memory leaks, caching opportunities, latency breakdown by layer. Use EXPLAIN ANALYZE for database queries.
```

### 42. Dependency Audit
```
Audit dependencies. Check: outdated packages with security advisories, unused dependencies, license compatibility, transitive dependency conflicts. Run: [AUDIT_COMMAND]. Recommend upgrades with risk assessment.
```

### 43. Concurrency Review
```
Review @src/[PATH] for concurrency issues. Check: race conditions, deadlocks, thread safety of shared state, transaction isolation levels, locking strategy, atomic operations.
```

### 44. Error Handling Audit
```
Audit error handling in @src/[PATH]. Check: all errors caught and handled, error messages useful for debugging, errors logged with context, graceful degradation, retry strategies for transient failures, circuit breakers.
```

### 45. API Contract Review
```
Review the API contract for [ENDPOINT]. Check: request schema validation, response consistency, error format, HTTP status codes, pagination/sorting consistency, OpenAPI spec accuracy.
```

### 46. Supply Chain Security
```
Audit supply chain. Check: verified build pipeline, SBOM generation, dependency scanning in CI, container image signing, secrets not in code or git history, third-party script audit.
```

### 47. Accessibility Review
```
Review @src/[COMPONENT] for accessibility. Check: color contrast (WCAG AA), keyboard navigation, screen reader compatibility, form labels and error messages, focus management, ARIA live regions.
```

### 48. Refactoring Plan
```
Plan a refactor of @src/[COMPONENT]. 1. Analyze current implementation. 2. Write tests covering current behavior (don't change behavior yet). 3. Plan stages (no big bang). 4. Execute one stage at a time. 5. Verify tests pass after each stage.
```

### 49. Code Quality Gate
```
Check code quality for @src/[PATH]. Run: [LINT_COMMAND], [TYPECHECK_COMMAND]. Check: cyclomatic complexity, duplication hotspots, naming conventions, file length. Flag anything that blocks merge.
```

### 50. Logging Standards Audit
```
Audit logging in @src/[PATH]. Check: structured logs (JSON), appropriate levels, correlation IDs, no PII or secrets, sensitive data redaction, log retention policy.
```

---

## Debugging & Troubleshooting

### 51. Systematic Debug
```
Debug [ISSUE]. 1. Reproduce with minimal steps. 2. Isolate cause (binary search through code changes). 3. Root cause (5 Whys). 4. Fix. 5. Write regression test. 6. Verify fix. Document each step.
```

### 52. Debug with Subagent
```
Use a subagent to investigate: [ISSUE]. Search the codebase in @src/ for the root cause. Check recent git changes with `git log --oneline -20`. Report back with: what's wrong, where, and suggested fix.
```

### 53. Memory Leak Hunt
```
Find memory leak in [SERVICE]. 1. Establish baseline. 2. Take heap snapshot under load. 3. Compare snapshots for growing allocations. 4. Trace allocation stacks. 5. Identify responsible code. 6. Fix. Track over 24h to confirm.
```

### 54. Performance Regression
```
Find cause of [PERFORMANCE_REGRESSION]. 1. Profile under normal load. 2. Compare: what changed since regression? 3. Identify: hot paths, slow queries, cache misses. 4. Measure: CPU/IO/memory/network. 5. Apply highest-impact optimization. 6. Re-profile.
```

### 55. Production Incident
```
Investigate: [INCIDENT]. 1. Scope (what's broken, who's affected). 2. Timeline from logs. 3. Trigger event. 4. Root cause (not symptom). 5. Immediate fix. 6. Prevention. Write post-mortem to docs/postmortems/.
```

### 56. Database Query Debug
```
Debug slow query at [ENDPOINT]. 1. EXPLAIN ANALYZE. 2. Identify expensive operation. 3. Check index usage. 4. Analyze join strategy. 5. Check statistics currency. 6. Test fix with EXPLAIN ANALYZE. 7. Verify with real data volume.
```

### 57. Race Condition Debug
```
Debug race condition in @src/[PATH]. 1. Identify symptom (intermittent failure, stale data). 2. List shared state access points. 3. Analyze timing windows. 4. Reproduce with stress test. 5. Fix (lock, atomic, queue). 6. Verify with repeated stress test.
```

### 58. Test Failure Debug
```
Debug failing test: [TEST_NAME]. 1. Run with verbose output. 2. Check if it passes in isolation. 3. Flaky vs consistent? 4. Isolate: test setup, test code, or actual bug. 5. Fix the right thing. 6. Add to flaky test suite if unfixable.
```

### 59. Docker Debug
```
Debug Docker issue: [DESCRIPTION]. 1. Container logs: `docker logs [NAME]`. 2. Exit code. 3. Inspect: `docker inspect [NAME]`. 4. Run interactively to reproduce. 5. Check resource limits (OOM, CPU throttle). 6. Verify image version.
```

### 60. Auth Debug
```
Debug auth failure for [USER/SERVICE]. 1. Check token expiry. 2. Check signature (right secret?). 3. Check clock skew (NTP?). 4. Check scope/permission assignments. 5. Check if token was revoked. 6. Check auth server denial reason.
```

### 61. Cache Debug
```
Debug [CACHE_ISSUE] in [SERVICE]. 1. Is cache being used? Check metrics. 2. Hit rate healthy? 3. TTL and expiration behavior. 4. Invalidation firing when it shouldn't? 5. Cache stampede? 6. Test with cache disabled for baseline.
```

### 62. Build Failure Debug
```
Debug CI/CD failure. 1. Full build log. 2. First error (ignore cascade). 3. Type: compilation, test, lint, deploy? 4. Does local build work on same commit? 5. Dependency registry status? 6. Reproduce locally?
```

### 63. Network Debug
```
Debug [NETWORK_ISSUE] in [SERVICE]. 1. Layer: DNS, TLS, TCP, or HTTP? 2. `curl -v` for full trace. 3. Test from service's network location. 4. Firewall/security groups. 5. tcpdump. 6. Upstream service status.
```

### 64. Dependency Conflict Debug
```
Debug dependency conflict in [PROJECT]. 1. [AUDIT_COMMAND] for conflicts. 2. List transitive deps. 3. Identify version constraint causing conflict. 4. Test update in branch. 5. If no resolution: consider alternatives.
```

---

## Testing

### 65. Test Suite Design
```
Design test strategy for [PROJECT]. Define: test pyramid ratios, what to mock vs integrate, test data strategy, flaky test handling, coverage targets by layer, CI integration. Check @CLAUDE.md for existing test framework.
```

### 66. Happy Path Tests
```
Write happy path tests for @src/[PATH]. Test the success flow end to end. Verify: response structure, status code, database state after operation. Include realistic request payload.
```

### 67. Edge Case Tests
```
Write edge case tests for @src/[PATH]. Cover: empty input, max input, malformed input (wrong type, missing required), boundary conditions, unicode/special characters, concurrent access patterns.
```

### 68. Error Path Tests
```
Write error path tests for @src/[PATH]. Cover: 400 invalid input, 401 unauthorized, 403 forbidden, 404 not found, 409 conflict, 500 server error, timeout behavior.
```

### 69. Test with Subagent
```
Use the test-writer subagent to write tests for @src/[PATH]. Focus on: public function contracts, happy/edge/error paths, integration points. Follow existing test patterns. Run tests and fix failures.
```

### 70. Property-Based Tests
```
Write property-based tests for @src/[FUNCTION]. Define invariants: output always valid type/range/format, encode/decode roundtrip, idempotence, commutativity. Generate 100+ random cases.
```

### 71. Performance Tests
```
Write performance tests for [ENDPOINT]. Baseline: measure current latency. Target: P95 < [X]ms, TPS > [Y]. Load profile: 1x to 10x normal. Measure: latency, throughput, error rate. Find breaking point.
```

### 72. Contract Tests
```
Write contract tests for [API]. Define expected request/response schemas. Verify consumer expectations match provider reality. Run on every PR. Use [CONTRACT_FRAMEWORK] or store contracts centrally.
```

### 73. Chaos Tests
```
Write chaos tests for [SERVICE]. Test: kill dependency (graceful degradation), network partition (timeout/retry), CPU spike (load shedding), memory pressure (stay in limits), clock skew. Verify recovery after each event.
```

### 74. Visual Regression Tests
```
Set up visual regression tests for [COMPONENT]. Use [PLAYWRIGHT/PERCY]. Define viewports (mobile, tablet, desktop). Set baseline. Compare on every PR. Alert on unexpected changes.
```

### 75. Migration Tests
```
Write tests for migration [NAME]. Test: migration up, migration down, data integrity after migration, production-size data volume, zero-downtime compatibility, edge cases (empty, large, concurrent writes).
```

### 76. Security Tests
```
Write security tests for [ENDPOINT]. Cover: SQL injection in all input fields, XSS in user-controlled output, CSRF token validation, auth bypass attempts, authorization boundary tests, rate limiting enforcement.
```

### 77. Accessibility Tests
```
Write accessibility tests for [COMPONENT]. Run axe-core on rendered component. Verify: keyboard navigation (Tab/Enter/Escape), color contrast ratios, ARIA labels on interactive elements, screen reader compatibility.
```

### 78. Integration Tests
```
Write integration tests for [API/SERVICE]. Use real test database. Cover: full stack flow, transaction isolation, seed data, cleanup after each test.
```

---

## Documentation

### 79. README
```
Write README for [PROJECT]. 1. What it does (one paragraph). 2. Quick start (3 steps max). 3. Architecture overview with diagram. 4. Configuration reference. 5. Dev setup. 6. Deployment. 7. Contributing. Keep under 500 words.
```

### 80. API Docs
```
Write API docs for [ENDPOINT]. Cover: overview and auth, each endpoint (method, path, purpose), request/response schemas with examples, error codes, rate limits, code samples in [LANG_1] and [LANG_2].
```

### 81. Architecture Doc
```
Write architecture doc for [SYSTEM]. Cover: overview (what/why), high-level design with diagram, components and responsibilities, data flow, deployment model, monitoring, failure modes and mitigations.
```

### 82. Runbook
```
Write operations runbook for [SERVICE]. Cover: normal ops checklist, common failure modes and fixes, escalation path, rollback procedure, monitoring dashboards, on-call notes.
```

### 83. Onboarding Doc
```
Write developer onboarding doc for [PROJECT]. Cover: what it does, architecture overview, local setup (step by step), first task suggestions, who to ask what, common gotchas.
```

### 84. ADR
```
Write ADR for [DECISION]. Format: date, author, context/problem, decision, alternatives considered, consequences (positive and negative), status (accepted/deprecated/superseded).
```

### 85. Changelog Entry
```
Write changelog entry for [VERSION]. Include: breaking changes (highlighted), new features, bug fixes, deprecations, migration notes. Follow Keep a Changelog format.
```

### 86. Decision Log
```
Maintain architectural decision log. For each decision: date, author, context, decision, alternatives, consequences, status. Keep at [PATH/adr/]. Check @docs/adr/ for existing entries.
```

---

## DevOps & Deployment

### 87. CI/CD Pipeline
```
Design CI/CD for [PROJECT]. Pipeline: lint → type check → unit tests → build → security scan (SAST, dependency audit) → deploy to [ENV] → smoke tests. Use GitHub Actions. Store in .github/workflows/.
```

### 88. Docker Optimization
```
Optimize Docker setup for [SERVICE]. Include: minimal base image (alpine/distroless), multi-stage build, layer caching, non-root user, health check, no secrets in image, CVE scanning.
```

### 89. Kubernetes Manifests
```
Write K8s manifests for [SERVICE]. Include: deployment (replicas, resource limits, health checks), service and ingress, ConfigMap/Secret management, HPA, PDB, network policy.
```

### 90. Monitoring Dashboard
```
Build monitoring dashboard for [SERVICE]. Include: RED metrics (Rate, Errors, Duration), business metrics, error rate by type, resource utilization (CPU, memory, connections), alert thresholds, on-call reference.
```

### 91. Alert Rules
```
Design alerting for [SERVICE]. Page-level (immediate): error rate > [X]%, P99 latency > [X]ms, health check failing. Warning (business hours): unusual traffic patterns. Include runbook link in every alert.
```

### 92. Backup Strategy
```
Design backup for [SERVICE]. Include: frequency and retention, verification (can we restore?), point-in-time recovery, off-site storage, RTO/RPO targets, recovery procedure, quarterly test.
```

### 93. Incident Response Playbook
```
Build incident response playbook for [SERVICE]. Cover: detection (how do we know?), triage (severity/scope), communication (who/how), mitigation (reduce impact), resolution (root cause), post-mortem (blameless, 48h).
```

### 94. Rollout Strategy
```
Design rollout for [FEATURE]. Include: feature flags with percentage rollout, canary deployment, A/B testing setup, metrics to watch (bounce, error, latency), automated rollback trigger, post-rollout monitoring.
```

---

## Context & Session Management

### 95. Clear Between Tasks
```
/clear
```
→ Resets context entirely. Use between unrelated tasks. Fresh context almost always outperforms accumulated corrections.

### 96. Compact with Focus
```
/compact Focus on the [SPECIFIC_AREA] changes
```
→ Tells Claude what to preserve during auto-compaction. "Focus on the API changes" keeps API context, drops unrelated exploration.

### 97. Investigate with Subagent
```
Use a subagent to investigate [TOPIC] in @src/[PATH]. Report findings as a summary. This keeps your main context clean for implementation.
```

### 98. Quick Question Without Context
```
/btw what's the default timeout for [LIBRARY]?
```
→ Answer appears in a dismissible overlay. Never enters conversation history. Zero context cost.

### 99. Rewind After Mistake
```
Esc Esc
```
→ Opens rewind menu. Restore conversation, code, or both to any previous checkpoint. Checkpoints persist across sessions.

### 100. Resume Previous Work
```
claude --continue
```
→ Resumes most recent conversation. Use `claude --resume` to pick from recent sessions. Use `/rename` to give sessions descriptive names.

---

## Chaining Recipes

### Recipe 1 — New Feature: Full Stack
```
1. Plan Mode: Read relevant files, create plan
2. Switch to Normal Mode
3. /feature-build [FEATURE_NAME]
4. Use test-writer subagent for comprehensive tests
5. Use security-reviewer subagent for audit
6. claude -p "commit with conventional message and open PR"
```

### Recipe 2 — Production Incident
```
1. /debug [INCIDENT_DESCRIPTION]
2. /clear (fresh context for fix)
3. Implement fix based on debug findings
4. Write regression test
5. Write post-mortem to docs/postmortems/
6. /clear (fresh context for PR)
7. Create PR with fix + test + post-mortem
```

### Recipe 3 — Codebase Refactor
```
1. Plan Mode: Analyze current implementation
2. Create refactoring plan with stages
3. For each stage: implement, run tests, verify
4. Use subagent for review after each stage
5. Final: run full test suite + coverage
6. Create PR with staged commits
```

### Recipe 4 — Security Review: Full Stack
```
1. Use security-reviewer subagent on @src/api/
2. Use security-reviewer subagent on @src/auth/
3. Run dependency audit
4. /pr-review with security focus
5. Document findings and remediation plan
```

### Recipe 5 — PR Review + Merge
```
1. /pr-review [PR_URL]
2. Use test-writer subagent for additional tests
3. /clear (fresh context for unbiased review)
4. Run code quality gate
5. Approve and merge
```

### Recipe 6 — Onboarding a New Developer
```
1. Run /init to generate CLAUDE.md
2. Customize CLAUDE.md with project specifics
3. Create skill: /feature-build
4. Create subagent: security-reviewer
5. Set up hooks in settings.json
6. Add MCP servers (GitHub, DB)
7. Write onboarding doc (#83)
```

### Recipe 7 — CI/CD Integration
```
1. Design pipeline (#87)
2. Write GitHub Actions workflow
3. Add claude -p review step with --max-turns and --max-budget-usd
4. Add pre-commit hook for lint-on-edit
5. Test pipeline on a PR
6. Add branch protection rules
```

### Recipe 8 — Performance Investigation
```
1. /debug [PERFORMANCE_ISSUE]
2. Profile under load
3. Identify bottleneck (CPU/IO/memory/network/DB)
4. /clear (fresh context)
5. Implement optimization
6. Re-profile to verify improvement
7. Write regression test for performance
```

### Recipe 9 — Database Migration
```
1. Design schema changes (#14)
2. Write migration files (up/down)
3. Write migration tests (#75)
4. Test on production-size data
5. Plan rollback procedure
6. Deploy with zero-downtime strategy
7. Verify data integrity post-migration
```

### Recipe 10 — Feature Flags + Rollout
```
1. Implement feature flags (#33)
2. Set up monitoring dashboard (#90)
3. Design alert rules (#91)
4. Design rollout strategy (#94)
5. Write chaos tests for flag-off scenarios (#73)
6. Roll out: 1% → 10% → 50% → 100%
7. Monitor metrics at each stage
```

---

*Based on Claude Code official documentation as of April 2026. Updated for: agentic loop architecture, CLAUDE.md memory hierarchy, skills, subagents, hooks, MCP integrations, agent teams, context management, and permission modes.*
