# KaryaOS Live Extension Playbook (Round 3 Cheat Sheet)

> **Golden Rule:** Touch ONLY `/extensions` and `/config`. Zero changes in `/core`.

---

## 1. Quick Extension Commands

| Task | Command / Action | Target Directory |
|---|---|---|
| **Scaffold new workflow + policy + test** | `python scripts/new_workflow.py <name>` | `extensions/` & `tests/` |
| **Validate all extensions & DAGs** | `python scripts/validate.py` | Full platform |
| **Test specific extension** | `pytest tests/test_<name>.py -q` | Fast test |
| **Hot-reload running cluster** | `POST /api/admin/reload` | Live cluster |

---

## 2. Six Extension Patterns (Copy-Paste Recipes)

### A. Add a Workflow (YAML Only)
File: `extensions/workflows/<id>.yaml`
```yaml
id: <workflow_id>
version: 1
trigger: <domain.event_name>
inputs: [employee_id]
steps:
  - id: step_one
    skill: <existing_skill_name>
    mode: auto
  - id: step_two_approval
    skill: hr.confirm_compensation
    action: <reserved_action>
    mode: approval
    approver_role: hrbp
```

### B. Add a Pluggable Skill
Directory: `extensions/skills/<skill_folder>/`
1. `manifest.yaml`:
```yaml
name: <namespace.skill_name>
version: 1.0.0
type: integration
permissions_required: [admin:manage]
idempotency: [employee_id]
integration: admin
```
2. `skill.py`:
```python
from typing import Any
async def run(ctx: Any, inputs: dict) -> dict:
    if ctx.gateway:
        return await ctx.gateway.call("admin", "/endpoint", inputs, ctx.idempotency_key)
    return {"status": "ok", "idempotency_key": ctx.idempotency_key}
```

### C. Add a Policy Rulebook with Fixtures
File: `extensions/policies/<policy_id>.yaml`
```yaml
id: <policy_id>
version: 1
effective_from: 2026-01-01
rules:
  - name: standard_rule
    when: { grade: [L1, L2, L3] }
    then: { approved_limit: 50000 }
tests:
  - given: { grade: L2 }
    expect: { approved_limit: 50000 }
```

### D. Enforce a Reserved Decision (Human Gate)
File: `config/reserved_decisions.yaml`
```yaml
reserved:
  - action: <domain.action_name>
    approver: [hrbp, hr_head]
```
*(Engine automatically blocks `mode: auto` at load time and rejects agent tokens with HTTP 403).*

### E. Add a Chat Intent
File: `config/intents.yaml`
```yaml
intents:
  - id: <intent_id>
    keywords: ["word1", "phrase two", "keyword"]
    min_role: employee
    confidence: 0.95
```

---

## 3. Common HR Request Reusability Matrix

Use this lookup during live prompt surprises to compose workflows in < 15 minutes by reusing existing skills:

| Surprise Request | Reusable Trigger | Step 1 (Policy / Prep) | Step 2 (Reserved Human Gate) | Step 3 (Fulfillment) | Step 4 (Comms) |
|---|---|---|---|---|---|
| **Probation Confirmation** | `timer.probation_review_due` | `manager.assign_buddy` (Goals) | `probation.confirm` (`hrbp`) | `payroll.setup_employee` | `comms.send_welcome` |
| **ID-Card Reprint** | `chat.reprint_id_card` | `dsr.verify_identity` | None (`auto`) | `admin.reprint_id_card` | `comms.send_welcome` |
| **Internal Transfer** | `employee.transfer_requested` | `dsr.verify_identity` | `compensation.change` (`hrbp`) | Parallel: `directory`, `payroll`, `admin` | `comms.send_welcome` |
| **Promotion / Grade Bump** | `employee.promoted` | `leave_policy.yaml` (Recalc) | `compensation.change` (`hr_head`) | `payroll.setup_employee` | `comms.send_welcome` |
| **Leave Encashment** | `employee.leave_encash_req` | `leave_policy.yaml` (Balance) | `payroll.run_signoff` (`finance`) | `payroll.setup_employee` | `comms.send_welcome` |
| **Relocation Allowance** | `employee.relocated` | `final_settlement.yaml` | `policy.exception` (`hrbp`) | `payroll.setup_employee` | `comms.send_welcome` |
| **Employee Referral Bonus**| `referral.hired` | `dsr.verify_identity` | `compensation.confirm` (`hrbp`) | `payroll.setup_employee` | `comms.send_welcome` |
| **Disciplinary Handover** | `hr.disciplinary_initiated` | `dsr.extract_pii` | `disciplinary.any` (`hr_head`) | `admin.issue_access_card` (Revoke) | `comms.send_welcome` |
| **Resignation & Exit F&F** | `employee.resigned` | `notice_period.yaml` | `resignation.accept` (`hr_head`) | `assets.allocate_laptop` (Return) | `comms.send_welcome` |
| **DPDP Data Erasure** | `dsr.requested` | `dsr.extract_pii` | `policy.exception` (`hrbp` / DPO)| `directory.create_account` (Purge)| `dsr.notify_subject` |
