# KaryaOS: Product Requirements Document 

> *Karya* (कार्य) means "work / task". **KaryaOS is the operating system where HR work gets done: automation does the routine, humans decide what matters.**

**Hackathon:** TBO, AI-Native HR Services Platform (Darwinbox)
**Deep service line:** Employee Onboarding
**Extension proofs (YAML/config only, zero `/core` changes):** Exit & Final Settlement, DSR (data access/correction), Probation Confirmation, ID-Card Reprint (via chat), Internal Transfer
**Status of this document:** v2 reflects what was actually built and verified by the build agent's reports. Anything not yet real is marked **Stubbed** or **Planned**.

**Status legend:** ✅ Built · 🟡 Partial · 🧪 Stubbed (works, but fake/simulated) · 🔜 Planned

---

## 1. Vision

Replace the "HRMS records events, humans chase work" model with a services platform that closes cross-team loops on its own. When a new hire is added, KaryaOS opens the IT, Admin, Finance and manager tasks, tracks them to completion, and stops only at decisions with legal, financial or human consequences. A named human approves those decisions, and every action is audited.

**Pitch line:** *"The system does the chasing. Humans own the decisions. Every action is recorded and every rupee is measured."*

## 2. Problem

| Today | With KaryaOS |
|---|---|
| HR emails IT for a laptop, Admin for an access card and Finance for payroll setup, then chases each | One event starts all tasks in parallel, tracks them and retries safely |
| Policies live in PDFs and people's heads | Policies are versioned YAML rules with embedded tests |
| No visibility into cost or cycle time | Dashboard: ₹/workflow, automation %, cycle time, escalation % |
| Adding a new HR process means a new project | Adding one means a YAML workflow, optional policy and skill (rehearsed at 1 to 3 minutes each) |

## 3. Personas

| Persona | Needs | Where served |
|---|---|---|
| **New Hire / Employee** | Ask questions in chat, see onboarding status | HR Conversational Assistant |
| **Hiring / Reporting Manager** | Approvals, transfer requests | Chat + Reserved Approvals |
| **HR Business Partner (approver)** | Approve reserved decisions, pause agents | Reserved Approvals, Kill Switch Panel |
| **IT / Admin / Finance fulfilment** | Structured requests, no duplicates | Mock APIs via idempotent gateway |
| **HR Ops Lead / Auditor** | Audit trail, KPIs, policy versions, DPDP requests | Audit Chain, Executive KPIs, Policies screen |
| **TBO Developer** | Add workflows/skills without touching core | `/extensions`, developer guide, playbook |

## 4. What We Built (summary)

- **Workflow engine:** DAG executor driven by YAML definitions, with parallel steps, dependencies, per-step status, deduplication on replayed events.
- **Skills:** 11 pluggable skills auto-discovered from `extensions/skills/`.
- **Workflows (6):** onboarding, exit, dsr, probation confirmation, ID-card reprint, internal transfer.
- **Policies (4 rulebooks with embedded tests):** notice_period, probation, leave_policy, final_settlement.
- **Governance:** reserved decisions as config, load-time blocking of `auto` mode on reserved steps, agent tokens get 403 on approve, SHA-256 hash-chained audit log, kill switch checked before every step.
- **Safe failure:** idempotent integration gateway, circuit breaker, Human Queue with context bundle.
- **Privacy:** PII masker with Indian identifiers (Aadhaar, PAN etc.) applied before any model call.
- **Chat:** web assistant with intent classification, policy Q&A and RBAC.
- **Dashboard (Streamlit, 8 screens):** Executive KPIs · Live Workflows & Demo Trigger · Reserved Approvals · Human Queue & Safe Failure · Kill Switch Panel · Cryptographic Audit Chain · HR Conversational Assistant · Extensibility & Policies.
- **Quality:** 44 automated tests (policy, engine, idempotency, reserved decisions, kill switch, PII, chat, RBAC, audit tampering, fair hiring, full-lifecycle E2E).
- **Ops:** `make dev` (one-command local start), `make demo` / Docker, benchmark script, router eval script, validator, workflow scaffolder.

## 5. Honest Limits (read before demoing)

| Area | Reality |
|---|---|
| **LLM** | All model calls go through `FakeLLMProvider`. Zero external API calls. Welcome email, policy Q&A and intent fallback return templated or deterministic output. The provider interface is config-switchable, but no real model is connected yet. |
| **Planner agent** | None. Step lists come from static YAML. Nothing plans steps dynamically. The "agent" is the engine plus skills. |
| **Cost numbers** | Measured from benchmark runs, but token cost is simulated because no real model is called, and hosting/inference share comes from `config/infra_costs.yaml`. Present as "estimated from test runs". |
| **Integrations** | `/mocks` are our own stubs (in-memory/JSON state, failure-switchable), not TBO's provided mock APIs. |
| **Slack/Teams** | Slack is a stub; web chat is the working channel. |
| **Manual baselines** | Dashboard comparisons (for example "vs manual ₹50 / 48h") are assumed, not measured. |
| **Router eval** | The 50-query eval was written by us; the 100% intent accuracy is on that synthetic set only. |
| **KPI badge** | Escalation shows 6.0% but is badged "<5% SLA". Either fix the badge or the target. |

## 6. Objective Status

| # | Objective | Status | Evidence |
|---|---|---|---|
| 1 | Automate end to end | ✅ | Onboarding runs IT/Admin/Finance/manager steps in parallel; 86.8% overall, 99.1% ex-reserved steps automated |
| 2 | Platform, not point solution | ✅ | 5 extra workflows added via `/extensions` + `/config` only; 1 generic extension point added (`config/intents.yaml`) |
| 3 | Humans on decisions | ✅ | `config/reserved_decisions.yaml`; load-time block; 403 on agent approve |
| 4 | Comply by design | 🟡 | Versioned, tested policy files; PII masking; DPDP DSR workflow. Retention enforcement and consent records are lighter than the design doc |
| 5 | System of record | 🟡 | Hash-chained audit, RBAC, lifecycle workflows. Full effective-dated lifecycle model is simplified |
| 6 | Fail safely | ✅ | Idempotent gateway test (0 duplicate assets), circuit breaker, human queue, resume |
| 7 | Where people work | 🟡 | Web chat ✅, Slack 🧪 stub, Teams 🔜 |
| 8 | Cost and impact | 🧪 | Dashboard and benchmark exist; token costs simulated until a real model is connected |

## 7. Functional Requirements (with status)

### A. Automation
- **FR-1** Event-triggered workflow runs from definitions. ✅
- **FR-2** Planner produces task list. 🔜 (today: static YAML; rule-based steps are code, which matches the brief's rules-first guidance)
- **FR-3** Parallel execution with dependencies. ✅
- **FR-4** `human_touch` per step; automation rate overall and ex-reserved. ✅
- **FR-5** Loop closure only on mock API confirmation. ✅
- **FR-6** SLA-based reminders/escalation. 🟡 (verify before claiming)

### B. Reserved decisions
- **FR-10** HR-editable reserved list (config file). ✅ (UI editing 🟡)
- **FR-11** Minimum reserved set locked. ✅
- **FR-12** Named human approver; agent cannot approve. ✅
- **FR-13** Low-confidence actions route to human. 🟡

### C. Compliance
- **FR-30/31** Versioned, tested policy engine; policy version logged. ✅
- **FR-32** DPDP: DSR workflow ✅; purpose tags, consent records, retention job 🟡
- **FR-33** PII masking and outbound logging. ✅ (no real model attached yet)
- **FR-34** Fair-hiring guard (no auto-reject, protected attributes excluded). ✅ tested
- **FR-35** Kill switch per agent/workflow/skill. ✅

### D. System of record
- **FR-40** Lifecycle hire → exit via workflows. 🟡
- **FR-41** RBAC with agent ⊆ user rule. ✅ tested
- **FR-42/43** Append-only, hash-chained audit with tamper test. ✅

### E. Fail safe
- **FR-50** Human Queue with context bundle. ✅
- **FR-51** Idempotency keys at the gateway. ✅ tested
- **FR-52** Backoff and circuit breaker. ✅
- **FR-53** Data-conflict detection. 🟡
- **FR-54** Replay from last good step. 🟡

### F. Conversational
- **FR-60** Web chat ✅; Slack 🧪; Teams 🔜
- **FR-61** Intents incl. status, laptop ETA, policy, ID reprint, approvals. ✅
- **FR-62** Chat respects RBAC. ✅
- **FR-63** Policy RAG with citations. 🧪 (fake provider)

### G. Cost and impact
- **FR-70** Per-step meter. 🧪
- **FR-71** KPI dashboard. ✅
- **FR-72** Monthly projection. 🟡 (needs TBO volumes)
- **FR-73** Model-mix metrics (small vs escalation). 🧪

## 8. Measured Results (from `scripts/bench.py`, simulated environment)

| Metric | Result | Notes |
|---|---|---|
| Cost per workflow | ₹2.53 | Simulated token cost + configured infra share |
| Automation (overall) | 86.8% | Includes steps that are meant to need a human |
| Automation (excluding reserved steps) | 99.1% | |
| Cycle time p50 | 4.0 s | Against local mocks |
| Escalation rate | 6.0% | Badge target "<5%" is currently inconsistent |
| Model mix (router eval) | 84% rules, 14.5% escalation share | Threshold 0.75 chosen on our 50-query synthetic eval |
| Tests | 44 passed, 0 failed | |
| Duplicate side-effects on forced retry | 0 | Tested |
| Reserved decisions completed by an agent | 0 | Tested |

## 9. Demo Journeys

1. **Happy path:** dispatch `employee.hired`, steps finish in parallel, stops at `confirm_compensation`.
2. **Reserved decision:** named human approves in Reserved Approvals; agent attempt returns 403.
3. **Safe failure:** switch a mock API to fail, retry, human-queue item appears, resolve, resume, ledger shows one laptop.
4. **Kill switch:** pause, dispatch a hire, run parks.
5. **Chat:** "When do I get my laptop?" under RBAC.
6. **Audit and KPIs:** verify the hash chain, show the scoreboard.
7. **Extension proof:** Exit, Probation, ID reprint, Transfer added with no `/core` diff.

## 10. Roadmap to Close the Gaps (priority order)

1. **Connect a real small model** through the config-switchable provider (LiteLLM), keep the fake as fallback. This makes costs and chat answers genuine.
2. **Add a planner agent** that reads employee attributes and selects optional steps, with reserved steps still forced to human approval and every plan logged.
3. **Re-measure** cost, model mix and escalation with the real model, then update Section 8.
4. **Swap in TBO's official mock IT/Admin/Payroll APIs** as adapters once the starter kit is shared, and use TBO's headcount and volumes in the projection.
5. **Fix dashboard labelling** (escalation badge, mark manual baselines as assumptions).
6. **Real Slack integration**, then Teams.
7. **Tighten compliance depth:** consent records, retention job, effective-dated lifecycle tables.

## 11. Non-functional Requirements
- All data is synthetic; no real PII anywhere.
- Licenses for every library and model listed in the README, plus AI-assistant disclosure.
- Model provider switch is a config change.
- Reproducible with `make dev` or `docker compose up`.
- No secrets in the repo; `.env.example` provided.

## 12. Risks

| Risk | Mitigation |
|---|---|
| Claims exceed reality (fake LLM, no planner) | Section 5 states limits; demo script says "stubbed" where true |
| Cost numbers questioned | Label as simulated until a real model is connected, then re-measure |
| Core coupling fails the live extension test | Rehearsed: 5 workflows added with zero `/core` change |
| Duplicate actions on retry | Idempotent gateway with passing test |
| Port collisions during a live demo | `make dev` pre-flight port checks; Docker fallback |

## 13. Assumptions
- Demo auth instead of a real identity provider
- Our own stub mock APIs until TBO's starter kit is available
- Volume assumptions to be replaced by TBO's numbers
- Single-tenant TBO org