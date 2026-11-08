# KaryaOS Benchmark & Evaluation Report

- **Date Generated:** 2026-11-08 13:46:37Z
- **Sample Size:** 200 synthetic onboarding workflows
- **Failure Injection Rate:** 20% (transient 503/timeout retries simulated)
- **Status:** [Measured via `scripts/bench.py`]

---

## 1. Verified Key Metrics Strip

| Metric | Measured Value | Calculation Mode | Target / SLA | Verification Status |
|---|---|---|---|---|
| **Average Cost per Workflow** | **₹2.54** | Measured (Token ₹ + Infra share) | < ₹5.00 |  PASSED (-95% vs Manual ₹50.00) |
| **Model Token Cost per Workflow** | **₹0.0372** | Measured (Models config) | < ₹0.10 |  PASSED |
| **Infra Share per Workflow** | **₹2.50** | Configured (`infra_costs.yaml`) | < ₹5.00 |  PASSED |
| **Automation Rate (Overall)** | **86.9%** | Measured (Auto / Total steps) | > 85.0% |  PASSED |
| **Automation Rate (ex-Reserved)** | **99.4%** | Measured (Excluding mandatory human signoffs) | > 95.0% |  PASSED |
| **Cycle Time p50** | **4.02 seconds** | Measured (End-to-end execution) | < 10.0 s |  PASSED |
| **Cycle Time p90** | **5.78 seconds** | Measured (With retries & jitter) | < 30.0 s |  PASSED |
| **Cycle Time p99** | **11.36 seconds** | Measured (With triage delays) | < 60.0 s |  PASSED |
| **Escalation Rate to Human Queue** | **4.5%** | Measured (Quarantined runs) | < 5.0% |  PASSED |

---

## 2. Model Tier Routing Mix

| Model Tier | Model Identifier | Selection Share | Pricing Basis |
|---|---|---|---|
| **Small Model (Tier 1)** | `gemini-1.5-flash` / Local | **82.0%** | ₹0.00625 / 1k tokens |
| **Escalation Model (Tier 2)**| `gemini-1.5-pro` / Mid | **18.0%** | ₹0.40 in / ₹1.60 out per 1k |
| **Deterministic Rules** | Plain Python Code | **100% of policy & date math** | ₹0.00 (Zero tokens) |

> **Routing Rule:** Models run strictly through `core/llm/router.py`. If small model output confidence drops below **0.75** or prompt exceeds 3,000 tokens, it escalates to Tier 2. Zero PII leaves the platform boundary regardless of tier.

---

## 3. Cost Projection Template (Monthly at Scale)

Based on the formula in `docs/COST_MODEL_AND_METRICS.md §6`:
`monthly_cost = H × cost_per_onboarding + E × M × cost_per_chat_msg + fixed_infra_per_month`

| Volume Parameter | Assumption | Monthly Cost (INR ₹) |
|---|---|---|
| Monthly Hires ($H$) | 300 new hires | ₹761.15 |
| Employee Count ($E$) | 5,000 employees | - |
| Chat Inquiries per Employee ($M$) | 2 inquiries / month (10,000 chats) | ₹1,000.00 (at ₹0.10 / chat) |
| Fixed Infra Base (Container + DB) | Small production cluster | ₹25,000.00 [Estimated Baseline] |
| **Total Projected Monthly Cost** | **5,000 Headcount Organization** | **₹26761.15 / month** |

---

## 4. Governance & Safety Summary

1. **Duplicate Asset Allocations:** **0** duplicates across forced-retry tests (Idempotent Gateway).
2. **Autonomous Reserved Approvals:** **0** approvals by agents (HTTP 403 Forbidden enforced).
3. **Audit Log Tamper-Resistance:** 100% verified via cryptographic SHA-256 hash chaining.
4. **PII Masking:** 100% of Aadhaar, PAN, and Bank details scrubbed before model ingestion.
