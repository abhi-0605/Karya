# KaryaOS — Build Progress

## Status Legend
| Symbol | Meaning |
|--------|---------|
| ✅ | Done |
| 🔄 | In Progress |
| ⬜ | Pending |

---

## T002 + T003 — Repo Scaffold & Config Files ✅
**Completed:** 2026-11-08

### Directories created
- `core/{engine,policy,gateway,audit,pii,llm,rbac,killswitch}/`
- `extensions/{workflows,skills,integrations,policies}/`
- `config/`
- `apps/{web,slack}/`
- `mocks/`
- `data/`, `scripts/`, `tests/{policy,e2e,fixtures}/`, `docs/`
- `backend/app/{api,models}/`

### Root config files
| File | Status |
|------|--------|
| `.gitignore` | ✅ |
| `.env.example` | ✅ |
| `docker-compose.yml` | ✅ |
| `Makefile` | ✅ |

### Backend
| File | Status |
|------|--------|
| `backend/pyproject.toml` | ✅ |
| `backend/Dockerfile` | ✅ |
| `backend/app/config.py` | ✅ |
| `backend/app/database.py` | ✅ |
| `backend/app/main.py` | ✅ |
| `backend/app/api/auth.py` | ✅ Demo JWT, 8 synthetic users |
| `backend/app/api/events.py` | ✅ POST /employee.hired stub |
| `backend/app/api/workflows.py` | ✅ GET / list stub |
| `backend/app/api/approvals.py` | ✅ Agent-token guard enforced |
| `backend/app/api/human_queue.py` | ✅ |
| `backend/app/api/admin.py` | ✅ Killswitch pause/resume |
| `backend/app/api/chat.py` | ✅ |

### Mocks
| File | Status |
|------|--------|
| `mocks/Dockerfile` | ✅ |
| `mocks/requirements.txt` | ✅ |

### Config YAML
| File | Status |
|------|--------|
| `config/reserved_decisions.yaml` | ✅ |
| `config/models.yaml` | ✅ |
| `config/infra_costs.yaml` | ✅ |
| `config/integrations.yaml` | ✅ |
| `config/retention.yaml` | ✅ |

### Python packages (`__init__.py`)
- `backend/`, `backend/app/`, `backend/app/api/`, `backend/app/models/`
- `core/` + all 8 sub-packages
- `extensions/`, `extensions/skills/`

---

## Upcoming Tasks
| Task | Description | Status |
|------|-------------|--------|
| T004 | Core engine — workflow state machine | ⬜ |
| T005 | Gateway — idempotent integration client | ⬜ |
| T006 | Audit — hash-chained audit log | ⬜ |
| T007 | PII masking pipeline | ⬜ |
| T008 | LLM router + cost meter | ⬜ |
| T009 | RBAC / policy evaluator | ⬜ |
| T010 | Mock APIs (IT, Admin, Payroll, Email, Directory) | ⬜ |
| T011 | Seed data + synthetic employees | ⬜ |
| T012 | Frontend (Next.js 14) | ⬜ |
| T013 | End-to-end tests | ⬜ |
