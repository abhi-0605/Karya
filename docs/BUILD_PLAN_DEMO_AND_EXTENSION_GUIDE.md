# KaryaOS: Build Plan, Demo Script & Developer Guide

## 1. Round-wise Plan

| Round | Deliverable | What we ship |
|---|---|---|
| **1. Concept** | ≤6-page architecture doc + 5-min video | Use `01_PRD`, `03_ARCHITECTURE`, `04_COST` (estimates) → condense to 6 pages |
| **2. Build** | Working demo, repo + README, measured cost and automation figures, developer guide | Sections 2–5 below |
| **3. Finale** | Live demo + live extension test | Sections 6–7 |

## 2. Team Roles (adjust to team size)

| Role | Owns |
|---|---|
| Platform lead | Workflow engine, gateway, idempotency |
| Governance engineer | Policy engine, reserved decisions, audit chain, kill switch |
| AI engineer | Model router, PII gateway, RAG, eval set, cost meter |
| Full-stack | Web UI, Slack bot, dashboard |
| Integrations and QA | Mock API adapters, tests, bench script, demo data |

## 3. Build Sequence (priority order)

| Phase | Build | Done when |
|---|---|---|
| P0 | Repo, Docker Compose, Postgres schema, synthetic data loader, mock APIs | `docker compose up` works |
| P1 | Workflow engine (YAML → runs), step state machine, audit log | Onboarding runs with stub skills |
| P2 | Integration gateway with idempotency + retry + circuit breaker | Forced-retry test: 1 laptop only |
| P3 | Policy engine + reserved-decision config + approval flow + RBAC | Agent cannot approve; reserved step blocks |
| P4 | Human queue + kill switch | Failure and pause land in queue with context |
| P5 | PII gateway + model router + cost meter | Per-step ₹ visible |
| P6 | Chat (web + Slack), policy RAG with citations | Status and policy Q&A work under RBAC |
| P7 | Dashboard + DSR (access/correction) workflow | Metrics from real runs |
| P8 | Exit workflow as YAML-only extension, developer guide, tests, README | Extension takes <30 min |

Cut line if time is short: Slack (keep web chat), Teams stub, Grafana, Temporal.

## 4. Repo Checklist
- [ ] README: run steps, demo users, license table, AI-assistant disclosure, assumptions
- [ ] `docs/developer_guide.md` (see §7)
- [ ] `tests/`: policy tests, idempotency tests, RBAC tests, reserved-decision tests, E2E
- [ ] `make bench` produces `docs/results.md`
- [ ] Clean commit history, one feature per PR/commit by its owner
- [ ] No real data, no secrets

## 5. Test Plan (maps to "Engineering quality 15%")

| Test | Asserts |
|---|---|
| Duplicate-on-retry | Crash after the external call, retry → exactly 1 asset allocated |
| Duplicate event | Same `employee.hired` twice → 1 run |
| Reserved enforcement | Any step matching the reserved list in `auto` mode fails validation at load time |
| Agent cannot approve | Approve endpoint rejects `principal_type=agent` |
| RBAC subset | Agent run permissions never exceed the acting user's |
| Kill switch latency | Pause takes effect on the next step (≤ 2 s) |
| Policy tests | Every rule has fixtures; CI blocks failures |
| PII | No Aadhaar/PAN/phone/email patterns appear in outbound model payloads (regex check on logged payloads) |
| Audit integrity | Tampering with any row breaks the hash chain verification |
| Fair hiring | Auto-reject path does not exist; protected attributes absent from features |

## 6. Demo Script (5–7 min)

| Min | Scene | What judges see |
|---|---|---|
| 0:00 | Pitch | "Agents do the work. Humans own the decisions." |
| 0:30 | **Happy path** | New hire event → run graph lights up: directory, email, laptop, card, payroll in parallel → welcome message in Slack |
| 1:45 | **Reserved decision** | Compensation confirmation stops → named HRBP approves in UI → audit shows who, rule version, reason |
| 2:45 | **Safe failure** | Toggle mock asset API to fail → retry → circuit opens → human-queue item with context → fix and resume → the mock ledger shows **1 laptop** |
| 3:45 | **Kill switch** | HR pauses the IT agent without a code change → new run parks instantly |
| 4:15 | **Chat** | Employee: "When do I get my laptop?" Manager: "approve buddy plan" → both under RBAC |
| 4:45 | **Dashboard** | ₹/workflow, automation % (both figures), cycle time, escalation %, model mix, monthly projection |
| 5:30 | **Governance tour** | Policy file + tests, versioned reserved list, PII outbound log, DPDP correction request |
| 6:15 | **Extension teaser** | "Exit workflow was added with 1 YAML + 1 policy; no core files changed (git diff)" |

## 7. Developer Guide (outline for `docs/developer_guide.md`)

### 7.1 Add a new workflow (config only)
1. Copy `extensions/workflows/_template.yaml`.
2. Set `id`, `trigger`, and list steps with `skill`, `mode` (`auto|approval|route_only`), `depends_on`.
3. Reference existing skills, or add one (7.2).
4. Run `make validate`. It checks that skills exist, that reserved actions are not `auto`, and that policy refs resolve.
5. Add `tests/workflows/<id>_test.py` using the fixture harness.
6. Restart or hot-reload (`POST /admin/reload`).

### 7.2 Add a skill
1. Create `extensions/skills/<name>/skill.py` and `manifest.yaml` (permissions, idempotency fields, model tier, timeout, retry).
2. Implement `run(ctx, inputs) -> outputs`. Use `ctx.gateway.call(...)` for side effects (this gives you idempotency for free).
3. Register by dropping the folder in. The registry auto-discovers it.

### 7.3 Add an integration
Implement `IntegrationAdapter` (`invoke`, `health`, `idempotency_header`). Add it to `config/integrations.yaml` with base URL and auth reference.

### 7.4 Add a policy
Add `extensions/policies/<id>.yaml` with `rules` and `tests`. Bump `version` on every change, and the audit log records it.

### 7.5 Add a reserved decision
Edit `config/reserved_decisions.yaml` or use the HR admin UI. The engine blocks any `auto` step matching the new entry.

### 7.6 Core-change rule
If a task needs a change under `core/`, the design has failed the extension test. Raise it as an architecture bug.

## 8. Live Extension Test Playbook (Round 3)

Rehearse with 3 mock requirements:

| Mock requirement | Expected approach | Target time |
|---|---|---|
| "Add **probation confirmation**: manager reviews at 90 days, HR confirms, payroll flags confirmed status" | New workflow YAML (timer trigger), existing `manager.review` skill, a reserved entry for confirmation | 15 min |
| "Add **exit & final settlement**: resignation → notice calc → handover tasks → F&F within statutory timeline" | New workflow YAML, `notice_period` + `final_settlement` policy files, reserved: resignation accept/buyout | 25 min |
| "Add **ID-card reprint request** through chat" | New workflow YAML plus an intent mapping in `config/intents.yaml` | 10 min |

**Day-of routine:** (1) read the requirement aloud, (2) map each step to an existing skill or note which new skill is needed, (3) mark reserved steps first, (4) write policy and tests, (5) `make validate && make test`, (6) demo via chat and show `git diff --stat` touching only `extensions/` and `config/`.

## 9. Scorecard Self-check

| Criterion | Weight | Our evidence |
|---|---|---|
| Governance and compliance | 20% | Reserved-decision config, policy tests, audit chain, PII outbound log, DPDP DSR workflow |
| Extensibility and architecture | 20% | Core vs. extensions split, YAML workflows, skill registry, developer guide, rehearsed extension test |
| Automation depth | 20% | Cross-team loop closed, automation % (two figures), safe-failure demo |
| Cost efficiency | 15% | Rules-first, router threshold justified with eval, measured ₹ + infra, monthly projection |
| Engineering quality | 15% | Idempotency test, RBAC tests, CI, clean commits |
| Experience and demo | 10% | Chat + approval UI + single-page dashboard, tight 6-minute script |