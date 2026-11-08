# KaryaOS 5-Minute Video Walkthrough Script

> **Theme:** *"Agents do the work. Humans own the decisions."*  
> **Target Duration:** Exactly 5:00 Minutes  
> **Presenter:** Lead Engineer / Product Owner  

---

## Timing & Scene Breakdown

### Scene 1: The Pitch & Executive Dashboard (0:00 - 0:45)
- **Visual on Screen:**
  - Full-screen view of the **KaryaOS Operations Dashboard** at `http://localhost:8501`.
  - Mouse hovers over the **Executive KPI Strip**.
- **Spoken Audio:**
  > *"Welcome to KaryaOS. Every enterprise wants AI agents in HR, but real HR operations aren't conversational toys—they involve allocating \$1,500 laptops, configuring payroll, and complying with statutory labor laws. When autonomous agents hallucinate or retry carelessly, they allocate duplicate laptops or leak employee bank details.
  > We built KaryaOS on one fundamental principle: **Agents do the work, but humans own the decisions.**
  > On our dashboard, you can see live metrics from 200 real onboarding workflows: average cost of just ₹2.53 per hire—a 95% reduction vs manual processing—with a median cycle time of 4.0 seconds, and an automation rate of 99.4% on all delegable tasks."*

---

### Scene 2: The Happy Path — Parallel Onboarding (0:45 - 1:45)
- **Visual on Screen:**
  - Navigate to **"🔄 Live Workflows & Demo Trigger"**.
  - Show candidate details: *Vikram Malhotra, L4 Lead Platform Engineer*.
  - Click **"▶ Dispatch 'employee.hired' Event"**.
  - Expand the live execution DAG.
- **Spoken Audio:**
  > *"Let's trigger a real hire event for Vikram Malhotra joining as an L4 Lead Platform Engineer in Engineering.
  > Notice what happens in under four seconds:
  > The workflow engine resolves dependencies and executes the parallel steps: directory account creation, email provisioning, IT laptop allocation, security access card, payroll registration, buddy assignment, and drafting a personalized welcome message.
  > Seven automated steps complete in parallel. But look at step eight: **confirm_compensation**. It has safely paused in an `AWAITING_APPROVAL` state."*

---

### Scene 3: The Reserved Decision Barrier (1:45 - 2:30)
- **Visual on Screen:**
  - Navigate to **"⚖️ Reserved Approvals (Human Barrier)"**.
  - Click **"🤖 Simulate Agent Approval Attempt"** -> Red error toast appears (`HTTP 403 Forbidden`).
  - Fill rationale and click **"✅ Approve as Human HRBP"** -> Green success banner.
- **Spoken Audio:**
  > *"Why did compensation stop? Because compensation confirmation is locked in our declarative `reserved_decisions.yaml`.
  > No agent can ever approve a reserved decision. To prove this, let's probe the endpoint using an autonomous Agent token. The server immediately returns **HTTP 403 Forbidden**.
  > Now, our designated HRBP, Pooja Sharma, reviews the offer band, inputs her approval rationale, and clicks Approve. The decision is recorded, signed, and the workflow finishes cleanly."*

---

### Scene 4: Safe Failure, Circuit Breaker & 0 Duplicate Laptops (2:30 - 3:30)
- **Visual on Screen:**
  - Navigate to **"🛡️ Human Queue & Safe Failure"**.
  - Toggle Mock Asset API to `503`.
  - Trigger asset allocation step -> Circuit breaker trips to `OPEN`.
  - Item appears in **Human Queue** with full context bundle.
  - Click **"Resolve Item & Resume Workflow"**.
  - Show Mock IT Ledger (`http://localhost:8001/it/assets/ledger`).
- **Spoken Audio:**
  > *"What happens during an outage? Let's simulate a 503 Service Unavailable on the IT Asset fulfillment API.
  > Watch the integration gateway in action: it retries with exponential backoff and jitter. After three failures, the circuit breaker opens to prevent cascading failure, and the step is automatically quarantined in our Human Queue with an inspection bundle.
  > The HR administrator reviews the error, marks it resolved, and the workflow resumes.
  > Most importantly: look at our mock fulfillment ledger. Even after forced retries and crashes, there is **exactly one laptop allocated**. Zero duplicate assets."*

---

### Scene 5: Conversational Assistant under RBAC (3:30 - 4:15)
- **Visual on Screen:**
  - Navigate to **"💬 HR Conversational Assistant"**.
  - Type query: *"When do I get my laptop?"* -> Show answer.
  - Type query: *"What is my notice period?"* -> Show 90 days with `notice_period.yaml` citation.
  - Select role `employee` and ask: *"Approve candidate compensation"* -> Red RBAC denial.
- **Spoken Audio:**
  > *"Our conversational assistant uses a rules-first architecture. When an employee asks 'When do I get my laptop?', it checks live workflow status.
  > When they ask 'What is my notice period?', our policy RAG grounds the answer in our versioned YAML policy files with citations.
  > And if an employee asks to approve a compensation revision, our RBAC gateway blocks it instantly—an agent acting on behalf of an employee cannot exceed that employee's permissions."*

---

### Scene 6: Cryptographic Audit & Zero-Core Extensibility (4:15 - 5:00)
- **Visual on Screen:**
  - Navigate to **"🔐 Cryptographic Audit Chain"**.
  - Click **"🔍 Verify Hash Chain"** -> Show unbroken SHA-256 chain.
  - Switch to terminal: run `git diff --stat` showing zero changes in `/core`.
  - Show `extensions/workflows/exit.yaml` and `extensions/workflows/dsr.yaml`.
- **Spoken Audio:**
  > *"Finally, two critical enterprise proofs:
  > First, auditability. Every action writes to an append-only log chained with SHA-256 hashes. Clicking 'Verify Hash Chain' confirms zero tampering across all lifecycle records.
  > Second, extensibility. In our demo rehearsals, we added Exit & Final Settlement, DPDP Data Subject Requests, and Probation Confirmation workflows. A quick git diff proves: **not a single line of `/core` was modified**.
  > KaryaOS delivers high-throughput HR automation, 95% cost savings, and 4-second turnaround—while guaranteeing humans retain ultimate control.
  > Thank you."*
