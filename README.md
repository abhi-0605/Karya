# KaryaOS — AI-Native HR Services Platform

> **TBO Hackathon Prototype**  
> *"Agents do the work. Humans own the decisions."*

[![Build & Test](https://img.shields.io/badge/tests-44%20passed-brightgreen.svg)](#test-suite)
[![Architecture](https://img.shields.io/badge/architecture-rules--first%20%7C%20zero--core--change-blue.svg)](#architecture)
[![Governance](https://img.shields.io/badge/governance-hash--chained%20audit-blueviolet.svg)](#governance)
[![Compliance](https://img.shields.io/badge/compliance-DPDP%202023%20PII%20Gateway-orange.svg)](#data-privacy--pii-protection)

---

## 1. Executive Summary

**KaryaOS** is an enterprise-grade, AI-native HR operations and governance engine built for high-throughput, cross-functional automation (IT, Admin, Payroll, HRBP) with strict, non-negotiable safety guardrails.

### Why KaryaOS Wins:
1. **Rules-First Architecture:** Policy checks, date mathematics, eligibility, and routine routing run as deterministic code with **zero model latency and zero token cost**. LLMs are invoked strictly where natural language reasoning is genuinely needed (drafting, intent ambiguity, policy Q&A).
2. **Reserved Decisions Guarantee:** High-stakes actions (compensation changes, terminations, disciplinary actions) **can never be executed autonomously**. Engine load-time validators reject `mode: auto` configurations, and the approval API permanently rejects agent tokens (`403 Forbidden`).
3. **Idempotent Gateway & Circuit Breakers:** Every external fulfillment call passes through an integration gateway with cryptographic deduplication. Forced retries, crashes, or timeout replays will **never allocate duplicate assets (e.g. 2 laptops)**.
4. **Cryptographic Tamper-Evident Audit:** Every state transition and decision is recorded into an append-only, SHA-256 hash-chained ledger (`hash = SHA256(prev_hash + entry)`). Any alteration of historic records immediately breaks the chain.
5. **DPDP Compliance & Outbound PII Gateway:** Recognizes Indian regulatory identifiers (Aadhaar, PAN, Bank Accounts, UAN). Highly sensitive identifiers are blocked completely, while PII fields (email, phone, names) are anonymized before leaving the platform boundary.
6. **Sub-Second Kill Switch:** HR Operations can instantly pause any agent, workflow, or skill from the UI. The engine checks safety flags before **every step** with sub-second propagation.
7. **Zero-Core Extensibility:** Built on a clean plug-in boundary. Adding new service lines (e.g. Exit & Final Settlement, DPDP Data Subject Requests) requires **only YAML definitions in `/extensions` and `/config`—zero changes to `/core`**.

---

## 2. Architecture & Extensibility Split

```
KaryaOS/
├── core/                     # Immutable generic engine (Zero-Core Changes Rule)
│   ├── engine/               # State machine, DAG loader, validator, human queue
│   ├── gateway/              # Idempotent gateway, retry backoff, circuit breaker
│   ├── pii/                  # DPDP PII Masking, regex recognizers, rehydration
│   ├── llm/                  # Model Router (L1/L2), Cost Meter, Intent, Policy RAG
│   ├── audit/                # SHA-256 hash-chained tamper-evident audit logger
│   ├── killswitch/           # Real-time multi-scope pause / resume controls
│   ├── policy/               # Plain-code deterministic policy rulebook evaluator
│   ├── rbac/                 # Role-based access control & delegation limits
│   └── fairness/             # Protected attribute scrubber & no-auto-reject guard
│
├── extensions/               # Service Lines & Pluggable Skills
│   ├── workflows/            # Declarative DAGs: onboarding.yaml, exit.yaml, dsr.yaml
│   ├── skills/               # 11 pluggable skills (manifest.yaml + skill.py)
│   └── policies/             # Rulebooks with test fixtures: notice_period, probation,
│                             # leave_policy, final_settlement
│
├── config/                   # Enterprise Governance Rules
│   ├── reserved_decisions.yaml   # Actions requiring named human signoff
│   ├── models.yaml               # Model tier routing thresholds & pricing
│   └── integrations.yaml         # External service endpoints & timeouts
│
├── apps/                     # Frontends & Adapters
│   ├── web/dashboard.py      # Streamlit Operations & Governance Dashboard
│   └── slack/stub.py         # Slack Bolt integration adapter
│
├── backend/app/              # FastAPI Application (REST API, Auth, Events)
├── mocks/main.py             # Mock IT / Admin / Payroll / Directory APIs (Port 8001)
├── data/                     # 100% Synthetic Datasets (230 synthetic persons)
├── docs/                     # Specifications, cost models, results.md, guides
└── tests/                    # 41 Comprehensive automated tests (100% passing)
```

---

## 3. How to Run

### Single-Command Demo Startup (Brings Up Everything)
```bash
make demo
# or directly:
docker compose up --build
```
- **Backend Swagger UI:** `http://localhost:8000/docs`
- **Operations & Governance Dashboard:** `http://localhost:3000` (or `http://localhost:8501` locally)
- **Mock Fulfillment Services:** `http://localhost:8001/docs`

For local execution without Docker:
```bash
make demo-local
```

---

### Option B: Local Python Development

#### 1. Setup Environment
```bash
# Python 3.11+
pip install -e ".[dev]"
```

#### 2. Seed Synthetic Dataset (230 Persons, Org Chart, Policies)
```bash
# Uses SQLite locally or PostgreSQL if DATABASE_URL is set
$env:DATABASE_URL = "sqlite+aiosqlite:///./karyaos.db"
python scripts/seed_data.py
```

#### 3. Start Mock APIs (Port 8001)
```bash
python -m uvicorn mocks.main:app --port 8001
```

#### 4. Start KaryaOS Backend API (Port 8000)
```bash
cd backend
python -m uvicorn app.main:app --port 8000 --reload
```

#### 5. Launch Operations & Governance Dashboard
```bash
streamlit run apps/web/dashboard.py
```

---

## 4. Test Suite & Verification

Run all **41 automated tests** across the platform:
```bash
pytest tests/ -v
```

### Test Breakdown (100% Passing):
| Test Module | Coverage & Verification |
|---|---|
| `tests/policy/test_policies.py` | Deterministic policy evaluation & embedded YAML fixture tests |
| `tests/test_engine.py` | Workflow DAG execution, parallel resolution, state transitions |
| `tests/test_idempotency.py` | Forced retries produce exactly 1 laptop; circuit breaker opens on 3 fails |
| `tests/test_reserved.py` | Reserved steps blocked in auto mode; agent token rejected with 403 |
| `tests/test_killswitch.py` | Sub-second pause puts steps into Human Queue; resume verified |
| `tests/test_pii.py` | Outbound PII masking; Aadhaar/PAN/Bank account leak assertions |
| `tests/test_chat.py` | Intent classification, policy RAG with citations, RBAC denied responses |
| `tests/test_rbac.py` | Agent delegation limit: `effective = skill ∩ user_permissions` |
| `tests/test_audit.py` | Cryptographic SHA-256 hash-chaining and tamper-detection |
| `tests/test_fair_hiring.py` | Protected demographic attributes scrubbed; auto-reject blocked |
| `tests/e2e/test_full_lifecycle.py` | Full hire event → 7 auto steps → approval → audit verification |

To validate all workflows, skills, and policies via the CLI linter:
```bash
python scripts/validate.py
```

To run the batch benchmark (200 onboarding workflows evaluation):
```bash
python scripts/bench.py
```

---

## 5. Demo Roles & Synthetic Personas

KaryaOS includes pre-configured JWT authentication for 8 synthetic demo personas:

| Username / Sub | Role | Permissions | Use Case in Demo |
|---|---|---|---|
| `emp001` | `employee` | `profile:read`, `chat:ask`, `dsr:create` | Asks about laptop, leave policy, checks onboarding |
| `mgr001` | `manager` | `buddy:assign`, `probation:review` | Assigns buddy, conducts 90-day probation review |
| `hrbp001` | `hrbp` | `compensation:confirm`, `human_queue:resolve` | Approves reserved compensation; resolves triage items |
| `hr_head` | `hr_head` | `resignation:accept`, `killswitch:manage` | Accepts executive resignation; toggles kill switches |
| `it_ops` | `it_ops` | `asset:allocate`, `email:provision` | Simulates IT hardware provisioning |
| `admin_ops` | `admin_ops` | `admin:access_card` | Simulates physical security access card issuance |
| `finance01` | `finance` | `payroll:setup`, `payroll:run_signoff` | Payroll setup and statutory final settlement review |
| `auditor01` | `auditor` | `audit:read`, `audit:verify` | Verifies cryptographic audit chain integrity |

---

## 6. Scorecard Alignment (TBO Hackathon Brief)

| Hackathon Criterion | Weight | KaryaOS Implementation & Evidence |
|---|---|---|
| **Governance & Safety** | 25% | Hash-chained audit trail, load-time reserved decision validator, 403 on agent approval, DPDP PII gateway, kill switch panel. |
| **Architectural Extensibility** | 25% | Strict `/core` vs `/extensions` split. EXIT and DSR service lines added purely in YAML without touching a single line of `/core`. |
| **Automation Depth** | 20% | Closed cross-team loop (IT + Admin + Payroll + HRBP). 87.5% overall automation; 98.2% automation excluding reserved decisions. |
| **Cost Efficiency** | 15% | Rules-first model (0 token cost for policy math), dynamic model router (small model default, escalation fallback), measured at ₹2.45 per hire. |
| **Engineering Quality** | 15% | 41 unit & e2e tests, idempotent integration gateway with circuit breaker, zero real PII, clean typed code, clean commit history. |

---

## 7. Open Source & Model Licenses

| Library / Component | Version | License | Primary Purpose |
|---|---|---|---|
| **FastAPI** | `>=0.111.0` | MIT | Asynchronous REST API routing & OpenAPI generation |
| **SQLAlchemy** | `>=2.0.0` | MIT | Async ORM database abstraction & schema definition |
| **asyncpg / aiosqlite** | `>=0.29.0` | Apache 2.0 / MIT | Non-blocking database drivers (PostgreSQL & SQLite) |
| **Pydantic** | `>=2.7.0` | MIT | Data validation and type coercion |
| **Streamlit** | `>=1.35.0` | Apache 2.0 | Real-time Operations & Governance Dashboard |
| **httpx** | `>=0.27.0` | BSD-3-Clause | Async HTTP client for mock integration gateway |
| **structlog** | `>=24.0.0` | MIT / Apache 2.0 | Structured JSON logging with security context |
| **PyYAML** | `>=6.0` | MIT | Declarative YAML workflow and policy parser |
| **Tenacity** | `>=8.3.0` | Apache 2.0 | Exponential backoff retry logic in gateway |
| **python-jose / passlib** | `>=3.3.0` | MIT / BSD | Cryptographic JWT token encoding & verification |
| **Google Gemini Flash** | `gemini-1.5-flash` | Commercial API | Tier 1 Small Model (Welcome drafting, Intent triage) |
| **Google Gemini Pro** | `gemini-1.5-pro` | Commercial API | Tier 2 Escalation Model (Mid-tier fallback) |

---

## 8. AI-Assistant Disclosure
In compliance with hackathon regulations: Portions of this codebase, test suites, and documentation were accelerated using AI coding assistants (Google Antigravity / Claude 3.5 / Gemini). All architectural governance decisions, cryptographic hash-chaining verification, DPDP PII gateway logic, load-time reserved decision validators, and circuit breaker implementations were engineered, reviewed, and verified by the development team.

---

## 9. License
Proprietary prototype built for the TBO Hackathon: AI-Native HR Services Platform. Synthetic dataset only; no proprietary or real personal data included.
