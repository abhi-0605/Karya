# KaryaOS 6-Minute Live Demo Runbook

> **Theme:** *"Agents do the work. Humans own the decisions."*  
> **Target Audience:** Hackathon Judges & Engineering Leadership  
> **Total Time:** 6 Minutes  

---

## 0. Demo Credentials & Pre-requisites

Start the platform in advance using a single command:
```bash
docker compose up --build -d
# Or locally:
# python -m uvicorn mocks.main:app --port 8001 &
# cd backend && python -m uvicorn app.main:app --port 8000 &
# streamlit run apps/web/dashboard.py --server.port 8501
```

### Demo Personas:
| Persona | Role | Token Identity | Demo Responsibility |
|---|---|---|---|
| **Vikram Malhotra** | `candidate` / `new hire` | `EMP-9081` | Joining L4 Lead Platform Engineer |
| **Pooja Sharma** | `hrbp` | `hrbp001` | Approves reserved compensation, resolves human queue |
| **Rajesh Iyer** | `hr_head` | `hr_head` | Safety controls, kill-switches, executive exits |
| **Autonomous Agent**| `agent` | `agent-it-ops` | Prohibited from approving reserved decisions |

---

## 1. Step-by-Step Script & Narration

### Scene 1: Pitch & Hook (0:00 - 0:45)
- **Speaker Narration:**
  > *"Every modern enterprise wants AI agents in HR. But real HR operations aren't just chatbot answers—they involve laptop provisioning, salary signoffs, and statutory compliance. Today, when an agent fails or hallucinates in HR, it orders duplicate laptops or approves unauthorized compensation.
  > We built **KaryaOS**: an AI-native HR platform where **agents do the execution, but humans retain decision authority**, backed by an idempotent integration gateway, cryptographic audit trails, and sub-second kill switches."*
- **Action on Screen:**
  - Open `http://localhost:8501` to show the **Executive KPI Strip** (Avg cost ₹2.54, 99.4% automation ex-reserved, p50 cycle time 4.0s).

---

### Scene 2: The Happy Path (0:45 - 1:45)
- **Speaker Narration:**
  > *"Let's watch a real hire event for Vikram Malhotra joining as L4 Lead Platform Engineer."*
- **Action on Screen:**
  - Navigate to **"🔄 Live Workflows & Demo Trigger"**.
  - Click **"▶ Dispatch 'employee.hired' Event"**.
  - Show the response DAG:
    - `directory.create_account` -> COMPLETED
    - `email.provision` -> COMPLETED
    - `assets.allocate_laptop` -> COMPLETED
    - `admin.issue_access_card` -> COMPLETED
    - `payroll.setup_employee` -> COMPLETED
    - `manager.assign_buddy` -> COMPLETED
    - `comms.send_welcome` -> COMPLETED
    - `confirm_compensation` -> **AWAITING_APPROVAL** (Parked)
- **Judges See:**
  - 7 automated steps execute in parallel in under 4 seconds; compensation step safely stops.

---

### Scene 3: Reserved Decision Boundary (1:45 - 2:45)
- **Speaker Narration:**
  > *"Notice that step 8—compensation confirmation—did not execute automatically. Compensation is in our versioned `reserved_decisions.yaml`. An agent cannot approve it. Let's prove it."*
- **Action on Screen:**
  - Navigate to **"⚖️ Reserved Approvals (Human Barrier)"**.
  - Click **"🤖 Simulate Agent Approval Attempt"**.
  - **Judges See:** Instant red alert: `HTTP 403 Forbidden: Agent tokens are strictly forbidden from approving reserved decisions!`
  - Now, click **"✅ Approve as Human HRBP"**.
  - **Judges See:** Green confirmation: `Decision APPROVED by hrbp001. Step completed. Audit log cryptographically signed.`

---

### Scene 4: Safe Failure, Circuit Breaker & Idempotency (2:45 - 3:45)
- **Speaker Narration:**
  > *"What happens when an external fulfillment API goes down? Let's inject a 503 failure into the mock IT Asset API."*
- **Action on Screen:**
  - Navigate to **"🛡️ Human Queue & Safe Failure"**.
  - Select `503` under Mock Asset API and click **"Set Asset API Mode"**.
  - Trigger asset allocation retry.
  - **Judges See:**
    - Step retries with exponential backoff.
    - Circuit breaker trips to `OPEN`.
    - Automatically enqueued into the **Human Queue** with context bundle.
    - Click **"Resolve Item & Resume Workflow"**.
    - Show mock ledger: **Exactly 1 laptop allocated. 0 duplicate assets created.**

---

### Scene 5: Real-Time Kill Switch (3:45 - 4:15)
- **Speaker Narration:**
  > *"If HR needs to halt an agent immediately—without engineering redeploying code—they flip the Kill Switch."*
- **Action on Screen:**
  - Navigate to **"⛔ Kill Switch Panel"**.
  - Toggle **"IT Agent (Asset & Email)"** to `ON` (Paused).
  - Click **"Apply Safety Overrides"**.
  - **Judges See:** Sub-second propagation. Any new IT step immediately parks into triage.

---

### Scene 6: Conversational Assistant under RBAC (4:15 - 4:45)
- **Speaker Narration:**
  > *"Our chat assistant combines rules-first classification with grounded policy citations."*
- **Action on Screen:**
  - Navigate to **"💬 HR Conversational Assistant"**.
  - Ask: *"When do I get my laptop?"* -> Answers with dispatch status.
  - Ask: *"What is my notice period?"* -> Returns 30 days for L2-L3, 90 days for L4-L6 with citation `notice_period.yaml`.
  - Switch role to `employee` and ask: *"Approve the compensation"* -> Rejected by RBAC gate (minimum role: `hrbp`).

---

### Scene 7: Cryptographic Audit & Extensibility (4:45 - 6:00)
- **Speaker Narration:**
  > *"Finally, two critical proof points:
  > First, our Audit Log. Every action is chained via SHA-256. Let's verify the entire chain live."*
- **Action on Screen:**
  - Navigate to **"🔐 Cryptographic Audit Chain"** and click **"🔍 Verify Hash Chain"**.
  - **Judges See:** `✅ Chain Verified: Cryptographic integrity intact across all entries (0 tampering)`.
  - Navigate to **"📜 Extensibility & Policies (Exit/DSR)"**:
  > *"Second, extensibility. We added the Exit & Final Settlement workflow and DPDP Data Subject Request workflows entirely via declarative YAML. A `git diff` proves zero lines changed in `/core`."*
- **Closing Line:**
  > *"KaryaOS delivers 95% cost savings and sub-5-second cycle times—while keeping humans in command."*
