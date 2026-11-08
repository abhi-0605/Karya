# KaryaOS: Product Requirements Document

> *Karya* (कार्य) means "work / task". **KaryaOS is the operating system where HR work gets done: agents do the routine, humans decide what matters.**

**Hackathon:** TBO, AI-Native HR Services Platform (Darwinbox)
**Chosen service line (deep):** Employee Onboarding (hire → Day 30)
**Extension-proof line (config only):** Exit & Final Settlement (built live or pre-staged as a YAML-only add)

---

## 1. Vision

Replace the "HRMS records events, humans chase work" model with an **agent-first services platform**. When a new hire is added, KaryaOS opens the IT, Admin, Finance and manager loops on its own, closes them, and stops only at decisions with legal, financial or human consequences. A named human approves those decisions, and every action is audited.

**Pitch line:** *"Agents do the work. Humans own the decisions. Every rupee and every action is measured."*

## 2. Problem

| Today | With KaryaOS |
|---|---|
| HR emails IT for a laptop, Admin for an access card and Finance for payroll setup, then chases each | Agents trigger all tasks in parallel, track them and retry safely |
| Policies live in PDFs and people's heads | Policies are versioned, testable rules in a governed layer |
| No visibility into cost or cycle time | Live dashboard: ₹/workflow, automation %, cycle time, escalation % |
| Adding a new HR process means a new project | Adding one means a YAML workflow plus an optional skill plugin |

## 3. Personas

| Persona | Needs |
|---|---|
| **New Hire / Employee** | Ask questions in chat (Slack/Teams/web), see onboarding status, submit documents, give consent |
| **Hiring / Reporting Manager** | One-tap approvals, buddy assignment, see "is my new hire ready for Day 1?" |
| **HR Business Partner (approver)** | Approve reserved decisions with full context, edit reserved-decision list, pause agents |
| **IT / Admin / Finance fulfilment** | Receive structured requests via mock APIs, never get duplicates |
| **HR Ops Lead / Auditor** | Audit trail, dashboard, policy versions, DPDP requests |
| **TBO Developer** | Add workflows, skills and integrations without touching the core |

## 4. Scope

### In scope (MVP vertical slice, Onboarding)
1. Trigger: `employee.hired` event (from synthetic dataset)
2. Agent plans the checklist from workflow definition + employee attributes (role, location, grade)
3. Parallel cross-team tasks: IT (laptop, email, directory), Admin (access card, desk), Finance (payroll setup), Manager (buddy, 30-60-90 plan)
4. Policy check on every action; reserved decisions routed to a named human
5. Conversational assistant for new hire and manager
6. Safe failure: human queue with context, idempotent retries
7. Dashboard with measured numbers
8. Full audit log, RBAC, kill switch, DPDP controls

### Out of scope
Real HRMS migration, real SSO, real payroll computation, voice, mobile app, multi-tenant.

## 5. Objective → Requirement Map

| # | Objective | Key requirements |
|---|---|---|
| 1 | Automate end to end | FR-1 to FR-6, automation-rate metric |
| 2 | Platform, not point solution | FR-20 to FR-24 (workflow YAML, skill registry, integration adapters, dev guide) |
| 3 | Humans on decisions | FR-10 to FR-13 (reserved-decision config, named approver) |
| 4 | Comply by design | FR-30 to FR-35 (policy engine, DPDP, PII gateway) |
| 5 | Clean system of record | FR-40 to FR-43 (lifecycle data model, RBAC, audit) |
| 6 | Fail safely | FR-50 to FR-54 (human queue, idempotency, circuit breaker) |
| 7 | Where people work | FR-60 to FR-63 (Slack/Teams/web chat) |
| 8 | Cost and impact | FR-70 to FR-73 (cost meter, dashboard, projection) |

## 6. Functional Requirements

### A. Automation (Obj 1)
- **FR-1** Subscribe to lifecycle events and instantiate a workflow run from a definition.
- **FR-2** Planner agent produces a task list; rule-based steps run as code, not LLM.
- **FR-3** Executor runs tasks in parallel with dependencies (for example, directory account → email → access).
- **FR-4** Every task records `human_touch: true|false`. Automation rate = tasks with no human touch / total tasks.
- **FR-5** Cross-team loop closure: a task is "done" only when the mock API confirms and the requester is notified.
- **FR-6** Auto-reminders and escalation if a fulfilment team does not respond within the SLA.

### B. Reserved decisions (Obj 3)
- **FR-10** `reserved_decisions.yaml` is editable by HR via UI (no code deploy).
- **FR-11** Minimum reserved set (cannot be removed, only extended):
  - Accepting resignation, release date or buyout
  - Final hiring decision, offer approval, compensation
  - Termination, disciplinary action, PIP
  - Salary, grade or role change, and any policy exception
  - POSH, grievance, whistleblower (route only)
  - Statutory filings and payroll-run sign-off
- **FR-12** A reserved action produces an `ApprovalRequest` assigned to a **named human** (by role and person). An agent token cannot call the approve endpoint.
- **FR-13** Low-confidence (< threshold) or "unsure" actions follow the same path.

### C. Compliance (Obj 4)
- **FR-30** Policy engine evaluates every action against versioned rules (notice period, probation, leave, settlement timeline, PF, gratuity).
- **FR-31** Policies have unit tests, run in CI, and each decision logs the `policy_version`.
- **FR-32** DPDP: purpose tags on every data field, consent records, retention schedule, access and correction request workflow.
- **FR-33** PII gateway masks or minimises data before any external model call and logs what left the boundary.
- **FR-34** Fair hiring guard: no auto-reject. Ranking shows factor-wise explanation, and a human confirms any rejection.
- **FR-35** Kill switch per agent, workflow or skill, takes effect immediately (feature flag in DB, checked on every step).

### D. System of record (Obj 5)
- **FR-40** Lifecycle entities: Candidate → Employee → Exit, with history (effective-dated).
- **FR-41** RBAC with the rule *agent permissions ⊆ acting user's permissions*.
- **FR-42** Append-only audit log: who or what, action, inputs, rule or prompt version, model, reasoning, outcome.
- **FR-43** Audit log is tamper-evident (hash chain).

### E. Fail safe (Obj 6)
- **FR-50** Any failure, conflict or low confidence → **Human Queue** item with context bundle.
- **FR-51** Every side-effecting call carries an **idempotency key** (`workflow_run_id + step_id + attempt-independent hash`).
- **FR-52** Retries with exponential backoff; circuit breaker per integration.
- **FR-53** Data-conflict detection (for example, the HRMS and directory disagree on manager) → human queue.
- **FR-54** Replay of a failed run from the last good step.

### F. Conversational (Obj 7)
- **FR-60** Chat interface: web widget plus Slack bot (Teams adapter stub).
- **FR-61** Intents: "What's my onboarding status?", "When do I get my laptop?", "Request leave policy", "Approve X" (manager).
- **FR-62** Chat actions respect the user's RBAC and go through the same policy gate.
- **FR-63** Answers that need policy knowledge are retrieved from the policy store (RAG) with citations.

### G. Cost and impact (Obj 8)
- **FR-70** Per-step meter: tokens, model, compute, infra → INR.
- **FR-71** Dashboard: ₹/completed workflow, automation rate, cycle time (p50 and p90), escalation rate.
- **FR-72** Monthly cost projection from TBO-provided headcount and volumes.
- **FR-73** Model router metrics: % calls on small model vs. large model.

## 7. Key User Journeys (demo script)

1. **Happy path:** New hire added → agent opens IT, Admin and Finance tasks → all confirm → new hire gets a welcome message in Slack → dashboard shows "100% steps, 0 human touch except offer-compensation confirmation".
2. **Reserved decision:** Compensation exception requested → agent drafts → stops → named HRBP approves → audit shows the human.
3. **Safe failure:** Asset API returns 503 mid-run → retry, no duplicate laptop → circuit opens → human queue with context → resolved → run resumes.
4. **Kill switch:** HR pauses the "IT provisioning agent" → new runs park in the human queue instantly.
5. **DPDP:** Employee raises a correction request → workflow routes to HR → change is audited.
6. **Live extension:** Add a "Probation confirmation" or "Exit" workflow via YAML only.

## 8. Success Metrics (targets, to be measured)

| Metric | Target |
|---|---|
| Onboarding steps with zero human touch | ≥ 80% (excluding reserved decisions) |
| Cost per completed onboarding workflow | < ₹10 (measured) |
| Duplicate side-effects on forced retry | 0 |
| Reserved decisions completed by an agent | 0 |
| Cycle time (hire event → all tasks confirmed) | < 5 min simulated |
| Time to add a new workflow | < 30 min for config-only |

## 9. Non-functional Requirements
- All data is synthetic; no real PII anywhere.
- Every dependency is commercially licensed (list in README).
- Model provider switch = config change (LiteLLM-style abstraction).
- Reproducible with `docker compose up`.

## 10. Risks

| Risk | Mitigation |
|---|---|
| Over-using LLMs → high cost | Rules-first design; LLM only for planning text, chat, unstructured extraction |
| Core coupling → fails live extension test | Strict plugin boundaries, workflow-as-data |
| Duplicate actions on retry | Idempotency keys enforced in the integration gateway, tested |
| Scope creep to many service lines | Depth on Onboarding; Exit is config-only proof |

## 11. Assumptions to State in README
- Demo auth instead of real IdP
- Mock IT/Admin/Finance APIs as provided by TBO
- Volume assumptions from TBO replace our placeholders
- Single-tenant TBO org