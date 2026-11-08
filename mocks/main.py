"""
KaryaOS Mock TBO APIs
Simulates IT Assets, Admin (access cards), Payroll, Email, and Directory systems.
Supports forced failure modes for demo purposes.

Environment variables for failure modes (per service):
  MOCK_IT_FAIL_MODE      = none | 503 | timeout
  MOCK_ADMIN_FAIL_MODE   = none | 503 | timeout
  MOCK_PAYROLL_FAIL_MODE = none | 503 | timeout

Idempotency:
  Pass `Idempotency-Key` header on any POST. Identical keys return the same
  response. The ledger is persisted to LEDGER_FILE (JSON) so it survives
  restarts; use DELETE /admin/ledger/reset to clear between tests.
"""
import asyncio
import json
import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(title="KaryaOS Mock TBO APIs", version="1.0.0")

# ─── Failure mode helpers ────────────────────────────────────────────────────

def get_fail_mode(service: str) -> str:
    """Return the failure mode for a service: none | 503 | timeout"""
    key = f"MOCK_{service.upper()}_FAIL_MODE"
    return os.getenv(key, "none").lower()


async def maybe_fail(service: str):
    """Apply failure mode if set."""
    mode = get_fail_mode(service)
    if mode == "503":
        raise HTTPException(
            status_code=503,
            detail=f"{service} service unavailable (simulated)",
        )
    elif mode == "timeout":
        await asyncio.sleep(30)  # Will time out client


# ─── Idempotency store ────────────────────────────────────────────────────────

# On Windows `/tmp` may not exist; fall back to a local file in cwd.
_DEFAULT_LEDGER = Path(os.getenv("LEDGER_FILE", "/tmp/mock_ledger.json"))
LEDGER_FILE: Path = (
    _DEFAULT_LEDGER
    if _DEFAULT_LEDGER.parent.exists()
    else Path(__file__).parent / "mock_ledger.json"
)


def load_ledger() -> dict:
    """Load persisted idempotency ledger from disk."""
    if LEDGER_FILE.exists():
        try:
            return json.loads(LEDGER_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_ledger(ledger: dict) -> None:
    """Persist idempotency ledger to disk (atomic-ish write)."""
    tmp = LEDGER_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(ledger, indent=2), encoding="utf-8")
    tmp.replace(LEDGER_FILE)


def get_or_set(key: str, response: dict) -> tuple[dict, bool]:
    """
    Return (response, was_duplicate).
    If key was seen before, returns the stored response unchanged (idempotent).
    Otherwise stores and returns the new response.
    """
    ledger = load_ledger()
    if key in ledger:
        return ledger[key], True
    ledger[key] = response
    save_ledger(ledger)
    return response, False


# ─── Request models ──────────────────────────────────────────────────────────

class LaptopAllocateRequest(BaseModel):
    employee_id: str
    employee_name: str
    grade: str
    location: str
    asset_type: str = "laptop"


class EmailProvisionRequest(BaseModel):
    employee_id: str
    first_name: str
    last_name: str
    department: str


class DirectoryAccountRequest(BaseModel):
    employee_id: str
    first_name: str
    last_name: str
    department: str
    manager_id: str
    grade: str


class AccessCardRequest(BaseModel):
    employee_id: str
    employee_name: str
    location: str
    access_zones: list[str] = ["general", "cafeteria"]


class PayrollSetupRequest(BaseModel):
    employee_id: str
    grade: str
    location: str
    department: str
    start_date: str
    bank_account_ref: str = "BANK_REF_MASKED"  # Never the real account number


# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/health", tags=["meta"])
async def health():
    """Liveness probe used by Docker Compose healthcheck."""
    return {
        "status": "ok",
        "services": ["it", "admin", "payroll", "email", "directory"],
        "ledger_file": str(LEDGER_FILE),
    }


# ─── IT — Asset Allocation ───────────────────────────────────────────────────

@app.post("/it/assets/allocate", tags=["IT"])
async def allocate_laptop(
    req: LaptopAllocateRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """
    Allocate a laptop/asset to an employee.
    Premium pool (MacBook Pro) for L4+; standard pool (Dell Latitude) for others.
    """
    await maybe_fail("IT")

    if not idempotency_key:
        idempotency_key = hashlib.sha256(
            f"{req.employee_id}:{req.asset_type}".encode()
        ).hexdigest()[:16]

    # Determine laptop pool by grade
    if req.grade in ("L4", "L5", "L6"):
        asset_pool = "premium"
        model = 'MacBook Pro 14"'
    else:
        asset_pool = "standard"
        model = "Dell Latitude 5540"

    asset_id = f"ASSET-{req.employee_id[-4:]}-{idempotency_key[:6].upper()}"

    response = {
        "status": "allocated",
        "asset_id": asset_id,
        "model": model,
        "pool": asset_pool,
        "employee_id": req.employee_id,
        "allocated_at": datetime.utcnow().isoformat(),
        "idempotency_key": idempotency_key,
    }

    result, was_duplicate = get_or_set(f"laptop:{idempotency_key}", response)
    headers = {"X-Idempotent-Replayed": "true"} if was_duplicate else {}
    return JSONResponse(content=result, headers=headers)


@app.get("/it/assets/ledger", tags=["IT"])
async def get_asset_ledger():
    """Returns the full laptop-allocation ledger — used by idempotency tests."""
    ledger = load_ledger()
    laptop_entries = {k: v for k, v in ledger.items() if k.startswith("laptop:")}
    return {"allocations": laptop_entries, "count": len(laptop_entries)}


# ─── Email Provisioning ───────────────────────────────────────────────────────

@app.post("/email/provision", tags=["IT"])
async def provision_email(
    req: EmailProvisionRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """
    Provision a corporate email account.
    Format: firstname.lastname@tbo-demo.com (synthetic domain).
    """
    await maybe_fail("IT")

    if not idempotency_key:
        idempotency_key = f"email-{req.employee_id}"

    email = f"{req.first_name.lower()}.{req.last_name.lower()}@tbo-demo.com"

    response = {
        "status": "provisioned",
        "email": email,
        "employee_id": req.employee_id,
        "provisioned_at": datetime.utcnow().isoformat(),
        "idempotency_key": idempotency_key,
    }

    result, was_duplicate = get_or_set(f"email:{idempotency_key}", response)
    headers = {"X-Idempotent-Replayed": "true"} if was_duplicate else {}
    return JSONResponse(content=result, headers=headers)


# ─── Directory (AD / LDAP simulation) ────────────────────────────────────────

@app.post("/directory/accounts", tags=["IT"])
async def create_directory_account(
    req: DirectoryAccountRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """Create a corporate directory (AD/LDAP) account for a new employee."""
    await maybe_fail("IT")

    if not idempotency_key:
        idempotency_key = f"dir-{req.employee_id}"

    response = {
        "status": "created",
        "account_id": f"DIR-{req.employee_id}",
        "display_name": f"{req.first_name} {req.last_name}",
        "department": req.department,
        "manager_id": req.manager_id,
        "employee_id": req.employee_id,
        "created_at": datetime.utcnow().isoformat(),
        "idempotency_key": idempotency_key,
    }

    result, was_duplicate = get_or_set(f"directory:{idempotency_key}", response)
    headers = {"X-Idempotent-Replayed": "true"} if was_duplicate else {}
    return JSONResponse(content=result, headers=headers)


# ─── Admin — Access Cards ─────────────────────────────────────────────────────

@app.post("/admin/access-cards/issue", tags=["Admin"])
async def issue_access_card(
    req: AccessCardRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """Issue a physical access card for an employee."""
    await maybe_fail("ADMIN")

    if not idempotency_key:
        idempotency_key = f"card-{req.employee_id}"

    card_id = f"CARD-{req.employee_id}-{idempotency_key[:6].upper()}"

    response = {
        "status": "issued",
        "card_id": card_id,
        "employee_id": req.employee_id,
        "location": req.location,
        "access_zones": req.access_zones,
        "issued_at": datetime.utcnow().isoformat(),
        "idempotency_key": idempotency_key,
    }

    result, was_duplicate = get_or_set(f"card:{idempotency_key}", response)
    headers = {"X-Idempotent-Replayed": "true"} if was_duplicate else {}
    return JSONResponse(content=result, headers=headers)


@app.post("/admin/desk/assign", tags=["Admin"])
async def assign_desk(
    req: Request,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """Assign a hot-desk or permanent desk to an employee."""
    await maybe_fail("ADMIN")

    body: dict = await req.json()
    employee_id: str = body.get("employee_id", "UNKNOWN")

    if not idempotency_key:
        idempotency_key = f"desk-{employee_id}"

    response = {
        "status": "assigned",
        "desk_id": f"DESK-{employee_id[-4:]}-A",
        "floor": "3",
        "building": "Tower-1",
        "employee_id": employee_id,
        "assigned_at": datetime.utcnow().isoformat(),
        "idempotency_key": idempotency_key,
    }

    result, was_duplicate = get_or_set(f"desk:{idempotency_key}", response)
    headers = {"X-Idempotent-Replayed": "true"} if was_duplicate else {}
    return JSONResponse(content=result, headers=headers)


# ─── Payroll ──────────────────────────────────────────────────────────────────

@app.post("/payroll/employees/setup", tags=["Payroll"])
async def setup_payroll(
    req: PayrollSetupRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """
    Initiate payroll setup for a new employee.
    PF enrolled for all grades; ESIC only for L1/L2 (gross ≤ ₹21,000/mo).
    NOTE: Compensation confirmation is required from HRBP before first run.
    """
    await maybe_fail("PAYROLL")

    if not idempotency_key:
        idempotency_key = f"payroll-{req.employee_id}"

    response = {
        "status": "setup_initiated",
        "payroll_id": f"PAY-{req.employee_id}",
        "employee_id": req.employee_id,
        "grade": req.grade,
        "pf_enrolled": True,
        "esic_applicable": req.grade in ("L1", "L2"),
        "setup_at": datetime.utcnow().isoformat(),
        "note": "Compensation confirmation required from HRBP before first payroll run",
        "idempotency_key": idempotency_key,
    }

    result, was_duplicate = get_or_set(f"payroll:{idempotency_key}", response)
    headers = {"X-Idempotent-Replayed": "true"} if was_duplicate else {}
    return JSONResponse(content=result, headers=headers)


@app.get("/payroll/employees/{employee_id}", tags=["Payroll"])
async def get_payroll_record(employee_id: str):
    """Retrieve payroll setup status for an employee."""
    await maybe_fail("PAYROLL")

    ledger = load_ledger()
    key = f"payroll:payroll-{employee_id}"
    if key not in ledger:
        raise HTTPException(status_code=404, detail=f"No payroll record for {employee_id}")
    return ledger[key]


# ─── Failure mode control (for demo / tests) ──────────────────────────────────

@app.post("/admin/fail-mode", tags=["meta"])
async def set_fail_mode(service: str, mode: str):
    """
    Toggle failure mode for a service. For demo use only.
    Query params: ?service=IT&mode=503
    """
    allowed_modes = {"none", "503", "timeout"}
    allowed_services = {"IT", "ADMIN", "PAYROLL"}
    if mode not in allowed_modes:
        raise HTTPException(400, f"mode must be one of {allowed_modes}")
    if service.upper() not in allowed_services:
        raise HTTPException(400, f"service must be one of {allowed_services}")
    os.environ[f"MOCK_{service.upper()}_FAIL_MODE"] = mode
    return {"service": service.upper(), "mode": mode, "set": True}


@app.get("/admin/fail-modes", tags=["meta"])
async def get_fail_modes():
    """Return current failure mode for all services."""
    return {
        "IT": get_fail_mode("IT"),
        "ADMIN": get_fail_mode("ADMIN"),
        "PAYROLL": get_fail_mode("PAYROLL"),
    }


@app.delete("/admin/ledger/reset", tags=["meta"])
async def reset_ledger():
    """
    Reset the idempotency ledger.
    For tests only — clears all stored idempotency keys.
    """
    if LEDGER_FILE.exists():
        LEDGER_FILE.unlink()
    return {"reset": True, "ledger_file": str(LEDGER_FILE)}


# ─── Entrypoint (dev mode) ────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
