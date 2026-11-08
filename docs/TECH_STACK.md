# KaryaOS: Tech Stack

**Principles:** open-source and commercially licensed · rules before LLMs · config over code · provider-agnostic models · runs on one laptop with `docker compose up`.

## 1. Stack at a Glance

| Layer | Choice | Why | License | Swap-in alternative |
|---|---|---|---|---|
| Backend API | **Python 3.12 + FastAPI** | Fast to build, typed, great async support | MIT | Node + NestJS |
| Workflow engine | **Custom lightweight engine** (YAML definitions + Postgres-backed state machine) | Fully controllable, keeps core tiny, easy to explain in the extension test | own code | Temporal (stretch), Prefect |
| Task queue / scheduler | **Redis + RQ** (or Celery) | Simple, retries and backoff built in | BSD | Kafka, SQS |
| Database | **PostgreSQL 16** | System of record, JSONB for audit and context, row-level security | PostgreSQL | MySQL |
| Vector store (policy RAG) | **pgvector** | One DB, no extra infra | PostgreSQL | Qdrant (Apache-2.0) |
| Policy engine | **YAML rules + `json-logic` / Python rule evaluator** (OPA/Rego as option) | Versioned, testable, auditable | MIT / Apache-2.0 | Open Policy Agent |
| LLM gateway | **LiteLLM** | One config line to switch vendors, built-in cost tracking | MIT | Portkey |
| Small / default model | **Qwen2.5-7B-Instruct or Llama-3.1-8B via vLLM/Ollama** (or a vendor's "flash/mini" tier) | Cheap, good enough for HR routine tasks | Apache-2.0 / Llama community licence (check commercial terms) | Phi-3, Gemma |
| Escalation model | **One mid-tier hosted model** (used only past a confidence threshold) | Handles ambiguous or complex text | vendor ToS | any |
| Embeddings | **bge-small-en / e5-small** | Tiny, CPU-friendly | MIT | OpenAI embeddings |
| PII masking | **Microsoft Presidio + custom Indian recognisers** (Aadhaar, PAN, UAN, phone) | Mask before any external call | MIT | spaCy rules |
| Auth | **Keycloak (demo realm)** or JWT demo users | RBAC and roles, no real SSO needed | Apache-2.0 | Auth0 |
| Frontend | **Next.js 14 + TypeScript + Tailwind + shadcn/ui** | Fast, polished UI | MIT | Vite + React |
| Chat channels | **Slack Bolt SDK** + web chat widget; Teams adapter stub | Where people already work | MIT | MS Bot Framework |
| Dashboard | **Next.js + Recharts** fed by SQL views (Grafana optional) | Fully custom ₹ metrics | MIT | Grafana (AGPL: check) |
| Observability | **OpenTelemetry + Prometheus** | Trace every agent step | Apache-2.0 | — |
| Testing | **pytest, Hypothesis (property tests), Playwright** | Policy tests, idempotency tests, E2E | MIT / MPL / Apache | — |
| CI | **GitHub Actions** | Runs policy tests and linting on every push | n/a | — |
| Packaging | **Docker Compose** | One command to run everything | Apache-2.0 | — |

> ⚠️ Confirm each license in the README table (hackathon rule: commercial use must be allowed). Prefer Apache-2.0/MIT models to avoid doubt.

## 2. Model Routing (cost rule)

| Step type | Handled by | Why |
|---|---|---|
| Eligibility, date maths (notice period, probation end), routing, checklist generation | **Plain code / rules** | Deterministic and zero cost |
| Classify employee message into intent | **Small model** (or rules + embeddings first) | Cheap, fast |
| Draft welcome message, summarise status | **Small model** | Low risk |
| Answer policy question (RAG) | **Small model + retrieval** with citations | Grounded in policy store |
| Extract fields from an uploaded document | **Small model** + validation rules | Validated by code |
| Ambiguous or conflicting input, confidence < threshold | **Escalation model** | Used only when the measured need arises |
| Reserved decision | **No model decides** | Human approves |

**Router rule (justify with measurements):**
`confidence < 0.75 OR input_tokens > 3k OR validation_failed → escalation model; else small model`.
Tune the threshold using the synthetic dataset and report the % of calls hitting the larger model.

## 3. Provider Independence

```yaml
# config/models.yaml
default:
  provider: ollama
  model: qwen2.5:7b-instruct
  cost_per_1k_tokens_inr: 0.0   # self-host cost is amortised in infra_costs.yaml
escalation:
  provider: openai_compatible   # any vendor
  model: ${ESCALATION_MODEL}
  cost_per_1k_in_inr: 0.4
  cost_per_1k_out_inr: 1.6
router:
  confidence_threshold: 0.75
  max_small_tokens: 3000
```
Changing the vendor means editing this file only.

## 4. Repo Layout

```
karyaos/
├─ core/                    # NEVER edited for new service lines
│  ├─ engine/               # workflow runner, state machine
│  ├─ policy/               # rule evaluator, versioning
│  ├─ gateway/              # idempotent integration gateway
│  ├─ audit/                # hash-chained audit log
│  ├─ pii/                  # masking pipeline
│  ├─ llm/                  # router + cost meter
│  ├─ rbac/                 # permissions
│  └─ killswitch/
├─ extensions/              # developers add things here
│  ├─ workflows/            # onboarding.yaml, exit.yaml, ...
│  ├─ skills/               # skill plugins (python + manifest.yaml)
│  ├─ integrations/         # adapters: it_assets, admin_cards, payroll...
│  └─ policies/             # notice_period.yaml, leave.yaml, ...
├─ config/                  # reserved_decisions.yaml, models.yaml, retention.yaml
├─ apps/
│  ├─ web/                  # Next.js UI + dashboard
│  └─ slack/                # bot
├─ mocks/                   # TBO provided mock IT/Admin/Payroll APIs
├─ data/                    # synthetic dataset
├─ tests/
└─ docs/                    # developer guide, architecture
```

## 5. Security Basics
- No secrets in the repo (`.env`, Docker secrets)
- Input validation with Pydantic on all endpoints
- Postgres row-level security; least privilege DB roles
- Agent service accounts carry the *delegated* user's scopes
- Signed audit entries, TLS in the demo deployment