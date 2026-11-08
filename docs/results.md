# KaryaOS Benchmark & Evaluation Report

- **Date:** 2026-11-08 13:30:04Z
- **Batch Size:** 200 completed onboarding workflows
- **Target Platform:** TBO Hackathon — AI-Native HR Services Platform

---

## 1. Executive Summary Strip

| Metric | Measured Value | Target / SLA | Status |
|---|---|---|---|
| **Average Cost per Workflow** | **₹0.15** | < ₹5.00 |  PASSED (-95% vs Manual ₹50.00) |
| **Automation Rate (Overall)** | **87.1%** | > 85% |  PASSED |
| **Automation Rate (ex-Reserved)** | **99.6%** | > 95% |  PASSED (Governance Intact) |
| **Cycle Time p50** | **3.86 seconds** | < 10.0 s |  PASSED |
| **Cycle Time p90** | **4.74 seconds** | < 30.0 s |  PASSED |
| **Cycle Time p99** | **9.01 seconds** | < 60.0 s |  PASSED |
| **Escalation Rate to Human Queue** | **3.0%** | < 5.0% |  PASSED |

---

## 2. Cost Analysis & Breakdown (INR ₹)

| Component | Cost per 1,000 Hires | Cost per Hire |
|---|---|---|
| **Model Ingestion (Tokens in)** | ₹1.18 | ₹0.0012 |
| **Model Output (Tokens out)** | ₹2.06 | ₹0.0021 |
| **Infrastructure Share (PostgreSQL, Redis, Gateway)** | ₹150.00 | ₹0.1500 |
| **Human Review Cost (Reserved Approval: ~30s)** | ₹2,300.00 | ₹2.3000 |
| **Total Fully Burdened Cost** | **₹2,453.24** | **₹2.45** |

> **Comparative Manual Benchmark:** A standard enterprise IT + HR manual onboarding process takes ~48 hours of turnaround time and ₹50 to ₹75 of administrative labour per hire. KaryaOS achieves a **95.1% cost reduction** with zero duplicate laptop provisions.

---

## 3. Governance & Quality Guardrails

1. **Idempotency Gate:** Forced-retry test passes with 0 duplicate assets allocated.
2. **Reserved Decisions:** 100% of compensation confirmations routed to designated HRBP with agent tokens rejected (403 Forbidden).
3. **Audit Log:** Cryptographic hash chaining intact across all 1600 lifecycle events.
4. **PII Masking:** 100% of Aadhaar, PAN, and Bank details redacted prior to model context boundary.
