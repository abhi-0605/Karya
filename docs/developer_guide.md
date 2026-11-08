# KaryaOS Developer & Extension Guide

> **Core Governance Principle:** Agents execute autonomous operational work, but humans retain decision authority.
> New HR workflows, policies, and integrations **MUST NOT touch `/core`**. All extensions live strictly in `/extensions` and `/config`.

---

## 1. Architecture Overview

```
KaryaOS/
├── core/                  # Immutable generic engine (DO NOT TOUCH)
│   ├── engine/            # State machine, DAG loader, validator, human queue
│   ├── gateway/           # Idempotent integration gateway & circuit breaker
│   ├── pii/               # DPDP PII Masking & Rehydration Gateway
│   ├── llm/               # Model Router, Cost Meter, Intent Classifier, RAG
│   ├── audit/             # SHA-256 hash-chained tamper-evident audit logger
│   ├── killswitch/        # Sub-second pause / resume safety controls
│   ├── policy/            # Plain-code deterministic policy evaluator
│   └── rbac/              # Role-based access control & delegation limits
│
├── extensions/            # Extensibility domain (Where you build)
│   ├── workflows/         # Declarative YAML workflow DAGs (onboarding, exit, dsr)
│   ├── skills/            # Pluggable skills (manifest.yaml + skill.py)
│   └── policies/          # Policy rulebooks with embedded fixtures (*.yaml)
│
└── config/                # Organizational governance configuration
    ├── reserved_decisions.yaml  # Decisions requiring human signoff
    ├── models.yaml              # Model tier definitions and thresholds
    └── integrations.yaml        # Service endpoints & timeout configs
```

---

## 2. How to Add a New Workflow in < 30 Minutes

### Step 1: Define the Workflow in YAML
Create `extensions/workflows/<workflow_name>.yaml`:

```yaml
id: probation_confirmation
version: 1
trigger: employee.probation_review_due
description: "Review at 90 days with manager signoff"
inputs:
  - employee_id
steps:
  - id: evaluate_probation_policy
    skill: manager.assign_buddy
    mode: auto
    timeout_s: 15

  - id: manager_confirmation
    skill: hr.confirm_compensation
    action: hiring.final_decision
    mode: approval
    approver_role: manager

  - id: notify_employee
    skill: comms.send_welcome
    depends_on:
      - manager_confirmation
    mode: auto
```

### Step 2: Validate Governance Rules
Run the validation utility:
```bash
python scripts/validate.py
```
Validation ensures:
1. Every referenced skill exists in `extensions/skills/`.
2. The step graph is a directed acyclic graph (no circular deadlocks).
3. Any step matching `config/reserved_decisions.yaml` has `mode != 'auto'`.

---

## 3. How to Add a Pluggable Skill

Create a directory `extensions/skills/<skill_name>/`:

### 1. `manifest.yaml`
```yaml
name: parking.assign_slot
version: 1.0.0
type: integration
permissions_required:
  - parking:assign
idempotency:
  - employee_id
integration: admin
model: none
timeout_s: 15
retry:
  max: 3
  backoff: exponential
```

### 2. `skill.py`
```python
from typing import Any

async def run(ctx: Any, inputs: dict) -> dict:
    employee_id = inputs["employee_id"]
    payload = {"employee_id": employee_id}
    
    # Always route side effects through ctx.gateway for idempotency
    if ctx.gateway:
        return await ctx.gateway.call("admin", "/parking/slots", payload, ctx.idempotency_key)
    
    return {"status": "assigned", "slot": "B-42", "idempotency_key": ctx.idempotency_key}
```

---

## 4. How to Add a Policy with Embedded Fixtures

Create `extensions/policies/<policy_id>.yaml`:

```yaml
id: gym_allowance
version: 1
effective_from: 2026-01-01
description: "Monthly fitness allowance eligibility by grade"
rules:
  - name: standard_gym
    when:
      grade: [L1, L2, L3]
    then:
      monthly_inr: 1500
      taxable: true

  - name: leadership_gym
    when:
      grade: [L4, L5, L6]
    then:
      monthly_inr: 3500
      taxable: false

tests:
  - given:
      grade: L2
    expect:
      monthly_inr: 1500
      taxable: true

  - given:
      grade: L5
    expect:
      monthly_inr: 3500
      taxable: false
```

All test cases under `tests:` are executed by CI via `pytest tests/policy/test_policies.py`.

---

## 5. How to Enforce Reserved Decisions

To lock an action so that **no agent token can ever execute it autonomously**:
Add the action key to `config/reserved_decisions.yaml`:

```yaml
reserved:
  - action: parking.vip_allocation
    approver: [admin_head]
```

At workflow load time, any workflow defining `parking.vip_allocation` with `mode: auto` is rejected with `WorkflowValidationError`.
At runtime, `POST /api/approvals/{id}/approve` strictly checks `principal_type == 'human'`. Agent tokens receive `403 Forbidden`.
