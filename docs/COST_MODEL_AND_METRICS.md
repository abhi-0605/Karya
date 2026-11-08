# KaryaOS: Cost Model, Metrics & Dashboard

> All figures below are **placeholder estimates for the Round 1 architecture doc**. In Round 2, replace them with **measured** numbers from real runs on the synthetic dataset.

## 1. Cost Formula (per completed workflow)

```
Cost_INR = Σ(LLM tokens × price)            # API-hosted calls
         + Σ(self-host inference share)      # GPU/CPU hours ÷ workflows served
         + Hosting share                     # app, DB, Redis, storage
         + Integration/API call cost         # if any
```
**Self-hosted is not free.** Example: GPU node ₹X/hour ÷ throughput (workflows/hour) = ₹ per workflow. Put it in `config/infra_costs.yaml` so the meter includes it.

## 2. Where the Rupees Go (Onboarding, per hire)

| Step | Engine | LLM? | Est. cost (₹) |
|---|---|---|---|
| Event → planned checklist | Workflow YAML + rules | No | ~0 |
| Eligibility / dates / routing | Code | No | ~0 |
| Directory, email, laptop, card, payroll calls | Adapters via gateway | No | ~0 |
| Welcome message draft | Small model | Yes | ~0.05 |
| Intent classification of chat messages (avg 3 msgs) | Embeddings/rules → small model | Yes | ~0.05 |
| Policy Q&A (avg 2 questions, RAG) | Small model | Yes | ~0.10 |
| Escalation model (≈ 5% of runs) | Mid-tier model | Yes | ~0.10 (amortised) |
| Hosting + inference infra share | n/a | n/a | ~1–3 |
| **Total (estimate)** | | | **~₹2–4 per workflow** |

Design lever: **most steps cost nothing because they are code, not LLM.**

## 3. Model Routing and Threshold Justification

| Rule | Reason | How to justify with data |
|---|---|---|
| Rules/code first | Deterministic, free, auditable | Count steps handled by code ÷ total |
| Small model default | HR text is short, repetitive, domain-bounded | Eval set: accuracy of small vs. large on 100 synthetic intents |
| Escalate when `confidence < 0.75` or validation fails | Below that, small-model accuracy on the eval set drops sharply | Plot accuracy vs. confidence; pick the knee; report % escalated |
| Never use a model for reserved decisions | Legal and human consequence | Policy engine blocks |

**Evaluation protocol:** build a labelled set of ~100–200 synthetic queries (intents, policy questions, document extractions). Run small and large models, record accuracy and cost, and choose the threshold that gives ≥ large-model accuracy at minimum cost. Save the notebook in `docs/model_eval/`.

## 4. Metrics (definitions)

| Metric | Definition | Source |
|---|---|---|
| **Cost per completed workflow (₹)** | Total metered cost of completed runs ÷ completed runs | `model_call_meter` + infra config |
| **Automation rate** | Steps with `human_touch=false` ÷ all steps (and a second figure excluding reserved steps) | `step_run` |
| **Straight-through runs** | Runs completed with zero human-queue items and zero approvals | `workflow_run` |
| **Cycle time (p50/p90)** | `ended_at − started_at` per workflow | `workflow_run` |
| **Human-escalation rate** | Runs with ≥1 human-queue item ÷ runs | `human_queue_item` |
| **Duplicate-action count** | Must be 0 | Mock API ledger vs. gateway log |
| **Reserved-decision compliance** | Reserved actions executed without an approval record: must be 0 | audit query |
| **Small-model share** | Small-model calls ÷ all LLM calls | meter |

Report two automation figures to be honest: *overall* and *excluding mandatory human decisions*.

## 5. Dashboard Layout (single page)

| Panel | Content |
|---|---|
| KPI strip | ₹/workflow · automation % · cycle time p50 · escalation % |
| Trend | Cost and volume per day (from simulated batch runs) |
| Funnel | Steps: auto vs. approval vs. human-queue |
| Model mix | Rules / small / large share and cost per share |
| Queue health | Open human-queue items by reason, oldest age |
| Compliance | Reserved decisions pending, policy versions in use, paused agents |
| Projection | Input headcount and hires/month → monthly INR cost |

## 6. Monthly Projection Template

Fill in once TBO shares volumes.

```
hires_per_month        = H     (TBO to provide)
chat_msgs_per_employee = M
employees              = E

monthly_cost = H × cost_per_onboarding
             + E × M × cost_per_chat_msg
             + fixed_infra_per_month
```
Illustrative: H=300, E=5,000, M=2, cost_per_onboarding=₹3, cost_per_chat_msg=₹0.10, infra=₹25,000/mo
→ 900 + 1,000 + 25,000 ≈ **₹27k/month**. Infra dominates, so right-size it and say so in the doc.

## 7. How to Measure
1. Seed 200 synthetic hires, 20% with injected failures and 10% with reserved decisions.
2. Run the batch via `make bench`.
3. The script outputs a CSV and writes `docs/results.md` (the dashboard reads the same SQL views).
4. Commit the results file so judges can reproduce them.