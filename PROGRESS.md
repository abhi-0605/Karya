# KaryaOS Progress

## Status Summary
- Overall completion: 13% (6/48 tasks verified DONE)
- Current phase: P1 (Workflow Engine & State Machine)
- Last updated: 2026-11-08T11:20:00+05:30
- Last agent/session: 2 (recovered & reconciled)

## How to Run (kept current)
```bash
# Host Python: Python 3.14 on Windows (C:\Users\ADMIN\AppData\Local\Python\bin\python.exe)
# Note: On Windows sandbox, commands executing host Python must use BypassSandbox: true due to AppData ACLs.

# 1. Install Python dependencies:
& "C:\Users\ADMIN\AppData\Local\Python\bin\python.exe" -m pip install -e ".[dev]"

# 2. Run mock APIs standalone (port 8001):
& "C:\Users\ADMIN\AppData\Local\Python\bin\python.exe" -m uvicorn mocks.main:app --port 8001

# 3. Generate synthetic dataset & seed database:
$env:DATABASE_URL = "sqlite+aiosqlite:///./karyaos.db"   # or postgresql+asyncpg://karya:karya@localhost:5432/karyaos
& "C:\Users\ADMIN\AppData\Local\Python\bin\python.exe" scripts/seed_data.py

# 4. Start backend (port 8000):
cd backend && & "C:\Users\ADMIN\AppData\Local\Python\bin\python.exe" -m uvicorn app.main:app --port 8000 --reload

# 5. Run tests:
& "C:\Users\ADMIN\AppData\Local\Python\bin\python.exe" -m pytest tests/ -v

# 6. Docker full stack (PostgreSQL + Redis + Mocks + Backend + Frontend):
docker compose up --build
```

## Task Board
| ID | Task | Phase | Status | Files touched | Notes |
|----|------|-------|--------|---------------|-------|
| T001 | Read all /docs completely | P0 | DONE | docs/* | All 5 docs read and verified |
| T002 | Scaffold repo layout (.gitignore, .env.example, Makefile, pyproject.toml) | P0 | DONE | .gitignore, .env.example, Makefile, backend/pyproject.toml | Verified |
| T003 | Docker Compose: postgres, redis, mock-apis, backend, frontend | P0 | DONE | docker-compose.yml | Verified |
| T004 | Mock API server (FastAPI) for IT/Admin/Payroll with 503-toggle | P0 | DONE | mocks/main.py, mocks/requirements.txt, mocks/Dockerfile | Tested, import verified |
| T005 | Database models & Alembic migrations | P0 | DONE | backend/app/models/*, backend/alembic/* | All tables tested with engine.create_all |
| T006 | Synthetic data generator + seeder (200 employees, org chart, candidates) | P0 | DONE | scripts/seed_data.py, data/synthetic_dataset.json | 230 persons, 200 employees, 30 candidates seeded |
| T007 | Workflow engine: YAML loader + StepDefinition/WorkflowDefinition models | P1 | IN_PROGRESS | core/engine/models.py, core/engine/loader.py | models.py and loader.py created; testing in progress |
| T008 | Workflow state machine (BFS parallel step execution, DB persistence) | P1 | TODO | core/engine/state.py | To build next |
| T009 | Skill registry (auto-discovery of extensions/skills/) | P1 | TODO | core/engine/skill_registry.py | To build |
| T010 | Audit log (hash-chained, SHA-256 prev_hash, append-only) | P1 | TODO | core/audit/logger.py | To build |
| T011 | Onboarding workflow YAML + 8 stub skills in extensions/ | P1 | TODO | extensions/workflows/onboarding.yaml, extensions/skills/* | To build |
| T012 | End-to-end smoke test: trigger employee.hired event -> workflow executes | P1 | TODO | backend/app/api/events.py, tests/test_workflow_e2e.py | P1 milestone |
| T013 | Idempotent integration gateway | P2 | TODO | core/gateway/gateway.py | Key = run_id + step_id + hash |
| T014 | Retry with exponential backoff per integration | P2 | TODO | core/gateway/retry.py | Tenacity integration |
| T015 | Circuit breaker per integration | P2 | TODO | core/gateway/circuit_breaker.py | Circuit breaker pattern |
| T016 | Idempotency test (forced-retry / crash-mid-call -> exactly 1 laptop) | P2 | TODO | tests/test_idempotency.py | P2 milestone |
| T017 | Policy engine: YAML rule evaluator (json-logic / rules) | P3 | TODO | core/policy/engine.py | Notice, leave, compensation |
| T018 | Reserved-decision config loader + load-time auto-mode validator | P3 | TODO | config/reserved_decisions.yaml, core/engine/ | Reserved steps cannot run auto |
| T019 | Approval service + API (agent tokens REJECTED) | P3 | TODO | core/engine/approvals.py, backend/app/api/approvals.py | Hard reject on principal_type!=human |
| T020 | RBAC engine (agent permissions ⊆ acting user permissions) | P3 | TODO | core/rbac/ | Permissions intersection |
| T021 | Policy unit tests (CI-blocking) | P3 | TODO | tests/policy/ | Notice, probation, leave tests |
| T022 | Reserved-decision enforcement tests | P3 | TODO | tests/test_reserved.py | P3 milestone |
| T023 | Human Queue (enqueue on fail/low-conf/conflict + resolve API) | P4 | TODO | core/engine/human_queue.py, backend/app/api/human_queue.py | Context bundle attached |
| T024 | Kill switch (flag table, Redis pub/sub invalidation, <=1s cache) | P4 | TODO | core/killswitch/killswitch.py, backend/app/api/admin.py | Checked before every step |
| T025 | Kill switch test (pause IT agent -> next step parks in queue) | P4 | TODO | tests/test_killswitch.py | P4 milestone |
| T026 | PII gateway (mask Aadhaar, PAN, phone, email, bank details) | P5 | TODO | core/pii/masker.py | Regex + Indian recognisers |
| T027 | Model router (LiteLLM / Gemini with deterministic fake fallback) | P5 | TODO | core/llm/router.py | Confidence < 0.75 -> escalation |
| T028 | Cost meter (tokens, model, INR per step, infra share) | P5 | TODO | core/llm/meter.py, config/infra_costs.yaml | Per-step and per-workflow ₹ |
| T029 | PII leak test (assert no Aadhaar/PAN in outbound model payloads) | P5 | TODO | tests/test_pii.py | P5 milestone |
| T030 | Deterministic fake LLM provider (offline end-to-end execution) | P5 | TODO | core/llm/fake_provider.py | Guaranteed run with 0 API keys |
| T031 | Web chat widget & API | P6 | TODO | backend/app/api/chat.py, apps/web/ | Web chat |
| T032 | Chat intent classification under RBAC | P6 | TODO | core/llm/intent.py | Status, laptop, leave, approvals |
| T033 | Policy RAG with citations | P6 | TODO | core/llm/rag.py | Grounded in policy docs |
| T034 | Slack bot adapter (optional / stub) | P6 | TODO | apps/slack/ | Slack Bolt SDK |
| T035 | Dashboard: KPI strip (INR/workflow, automation %, cycle time, escalation %) | P7 | TODO | apps/web/ | Live SQL view metrics |
| T036 | Dashboard: trend, funnel, model mix, queue health panels | P7 | TODO | apps/web/ | Single-page operations view |
| T037 | DSR workflow (DPDP access / correction request) | P7 | TODO | extensions/workflows/dsr.yaml | DPDP compliance |
| T038 | make bench script (seed 200 hires, batch run, CSV + results.md) | P7 | TODO | scripts/bench.py, docs/results.md | P7 milestone |
| T039 | Exit & Final Settlement workflow (YAML-only extension proof) | P8 | TODO | extensions/workflows/exit.yaml | Zero core changes |
| T040 | Exit policy files (notice_period.yaml, final_settlement.yaml) | P8 | TODO | extensions/policies/ | Tests included |
| T041 | Developer guide (docs/developer_guide.md) | P8 | TODO | docs/developer_guide.md | How to add workflows/skills |
| T042 | make validate script (checks skill existence, reserved!=auto) | P8 | TODO | scripts/validate.py | Extension linting |
| T043 | RBAC test suite | P8 | TODO | tests/test_rbac.py | Delegation rule asserts |
| T044 | Audit integrity test (tampering breaks hash chain) | P8 | TODO | tests/test_audit.py | Hash chain verification |
| T045 | Fair hiring guard tests (no auto-reject, no protected attributes) | P8 | TODO | tests/test_fair_hiring.py | Bias prevention tests |
| T046 | End-to-end integration test suite | P8 | TODO | tests/e2e/test_full_lifecycle.py | Full happy path & failure paths |
| T047 | Root README.md (setup steps, demo users, license table, checklist) | P8 | TODO | README.md | Hackathon submission ready |
| T048 | Final verification: docker compose up clean run, git tag v1.0 | P8 | TODO | - | Final milestone |

## Currently In Progress
- **T007**: Workflow engine YAML loader + data classes (`core/engine/models.py`, `core/engine/loader.py`).
  - Next: implement and verify workflow validation (validate reserved actions cannot be mode='auto').

## Next 5 Steps (ordered, concrete)
1. Complete T007 & T008: Implement `core/engine/state.py` (workflow runner, dependency graph, step execution).
2. T009: Implement `core/engine/skill_registry.py` (auto-discovery of skills in `extensions/skills/`).
3. T010: Implement `core/audit/logger.py` (hash-chained append-only audit log with `verify_chain`).
4. T011: Create `extensions/workflows/onboarding.yaml` and 8 onboarding skills in `extensions/skills/`.
5. T012: Wire `backend/app/api/events.py` and run first end-to-end onboarding workflow test.

## Decisions Log
| Decision | Reason | Date |
|----------|--------|------|
| Single sequential execution model | Parallel subagents exhaust quota and leave half-written files on cutoff | 2026-11-08 |
| Use host Python 3.14 via BypassSandbox for execution commands | AppData Windows path not accessible from standard sandbox | 2026-11-08 |
| Support SQLite (aiosqlite) in addition to PostgreSQL | Fast local tests and seeding without needing PostgreSQL service running | 2026-11-08 |
| JWT demo users with strict RBAC | Fastest to demo without complex external IdP setup | 2026-11-08 |
| Deterministic fake LLM provider | Ensures end-to-end execution even with zero API keys or network cutoffs | 2026-11-08 |

## Known Issues / Bugs / Tech Debt
- `backend/app/database.py` had duplicate `Base` declaration; fixed to import from `app.models.base`.
- Host Python requires `BypassSandbox: true` because it resides in `C:\Users\ADMIN\AppData\Local\Python`.

## Assumptions
1. Mock APIs: Built in `mocks/main.py` with switchable failure modes (503/timeout) via `MOCK_{SERVICE}_FAIL_MODE`.
2. Demo Auth: JWT tokens with 8 synthetic users (employee, manager, hrbp, hr_head, it_ops, admin_ops, finance, auditor).
3. Synthetic Data: 230 persons, 200 employees, 30 candidates generated deterministically in `data/synthetic_dataset.json`.
4. Single-tenant TBO organization.

## Test Status
- Synthetic dataset generation: PASSED (230 persons, 200 employees, 30 candidates).
- Database table creation & seeding: PASSED on SQLite test database.
- Mocks server import & syntax: PASSED.
- Backend app import & syntax: PASSED.

## Handoff Notes
- Work strictly ONE task at a time. No parallel subagents.
- Python executable on this machine is `C:\Users\ADMIN\AppData\Local\Python\bin\python.exe`.
- When running commands with Python, pass `BypassSandbox: true` because of Windows AppData permissions.
- Database models are in `backend/app/models/` and registered on `app.models.base.Base`.
- Mock APIs are at `mocks/main.py` (FastAPI, port 8001).
