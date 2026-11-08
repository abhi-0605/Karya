"""
Synthetic data generator and database seeder for KaryaOS.
Generates 200 synthetic employees, reporting hierarchy, candidates, and initial records.
NO REAL PERSONAL DATA IS USED. All names, emails, and identifiers are purely synthetic.
"""
from __future__ import annotations
import asyncio
import json
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# Indian synthetic first & last names
FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayaan", "Krishna", "Ishaan",
    "Shaurya", "Dhruv", "Kabir", "Ritvik", "Ananya", "Diya", "Saanvi", "Aadhya", "Kiara", "Myra",
    "Pari", "Anushka", "Navya", "Riya", "Kavya", "Ira", "Meera", "Pooja", "Rohan", "Neha",
    "Vikram", "Deepa", "Suresh", "Sunita", "Rajesh", "Priya", "Amit", "Sneha", "Karan", "Tanvi",
]

LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Nair", "Rao", "Reddy", "Iyer", "Pillai", "Menon", "Kumar",
    "Singh", "Gupta", "Deshmukh", "Joshi", "Bhat", "Banerjee", "Chatterjee", "Bose", "Mehta", "Shah",
    "Kulkarni", "Chopra", "Malhotra", "Kapoor", "Saxena", "Agarwal", "Mishra", "Pandey", "Trivedi", "Soni",
]

DEPARTMENTS = ["Engineering", "Product", "HR", "Finance", "Operations", "Sales", "Customer Success"]
GRADES = ["L1", "L2", "L3", "L4", "L5", "L6"]
LOCATIONS = ["Bengaluru", "Gurugram", "Mumbai", "Hyderabad", "Remote"]

ORG_UNITS = {
    "Engineering": ["Core Platform", "Travel APIs", "DevOps", "Data Platform"],
    "Product": ["Search & Booking", "Partner Portal", "Mobile Apps"],
    "HR": ["Talent Acquisition", "HR Operations", "Total Rewards"],
    "Finance": ["Corporate Finance", "Revenue Ops", "Payroll"],
    "Operations": ["Customer Fulfilment", "Vendor Ops"],
    "Sales": ["Enterprise Sales", "Agency Sales"],
    "Customer Success": ["Support Ops", "Partner Support"],
}

DATA_DIR = Path(__file__).parent.parent / "data"


def generate_synthetic_dataset(n_employees: int = 200) -> dict:
    random.seed(42)  # Deterministic generation
    DATA_DIR.mkdir(exist_ok=True)

    persons = []
    employees = []
    candidates = []

    # 1. Create Leadership / Managers first (L5, L6)
    manager_ids = []
    for i in range(1, 21):
        pid = f"PER{i:04d}"
        eid = f"EMP{i:04d}"
        fname = random.choice(FIRST_NAMES)
        lname = random.choice(LAST_NAMES)
        dept = random.choice(DEPARTMENTS)
        grade = "L6" if i <= 5 else "L5"
        role = f"Director of {dept}" if grade == "L6" else f"Engineering Manager - {random.choice(ORG_UNITS[dept])}"
        
        persons.append({
            "id": pid,
            "legal_name": f"{fname} {lname}",
            "dob": (date(1980, 1, 1) + timedelta(days=random.randint(0, 5000))).isoformat(),
            "contact_encrypted": f"ENC_PHONE_+91{random.randint(9000000000, 9999999999)}",
            "purpose_tags": {"employment": True, "payroll": True},
            "status": "active",
        })

        employees.append({
            "id": eid,
            "person_id": pid,
            "emp_code": f"TBO{i:05d}",
            "status": "active",
            "manager_id": None if i <= 5 else f"EMP{random.randint(1, 5):04d}",
            "grade": grade,
            "org_unit": random.choice(ORG_UNITS[dept]),
            "location": random.choice(LOCATIONS),
            "department": dept,
            "role_title": role,
            "start_date": (date(2020, 1, 1) + timedelta(days=random.randint(0, 1000))).isoformat(),
            "effective_from": "2020-01-01",
            "grade_band": f"BAND-{grade}",
        })
        manager_ids.append(eid)

    # 2. Create Remaining Employees (L1 to L4)
    for i in range(21, n_employees + 1):
        pid = f"PER{i:04d}"
        eid = f"EMP{i:04d}"
        fname = random.choice(FIRST_NAMES)
        lname = random.choice(LAST_NAMES)
        dept = random.choice(DEPARTMENTS)
        grade = random.choice(["L1", "L2", "L2", "L3", "L3", "L4"])
        
        roles_by_grade = {
            "L1": f"Junior Associate - {dept}",
            "L2": f"Associate Software Engineer",
            "L3": f"Senior Software Engineer",
            "L4": f"Staff Software Engineer",
        }
        
        persons.append({
            "id": pid,
            "legal_name": f"{fname} {lname}",
            "dob": (date(1990, 1, 1) + timedelta(days=random.randint(0, 4000))).isoformat(),
            "contact_encrypted": f"ENC_PHONE_+91{random.randint(9000000000, 9999999999)}",
            "purpose_tags": {"employment": True, "payroll": True},
            "status": "active",
        })

        employees.append({
            "id": eid,
            "person_id": pid,
            "emp_code": f"TBO{i:05d}",
            "status": "active",
            "manager_id": random.choice(manager_ids),
            "grade": grade,
            "org_unit": random.choice(ORG_UNITS[dept]),
            "location": random.choice(LOCATIONS),
            "department": dept,
            "role_title": roles_by_grade.get(grade, f"Specialist - {dept}"),
            "start_date": (date(2022, 1, 1) + timedelta(days=random.randint(0, 700))).isoformat(),
            "effective_from": "2022-01-01",
            "grade_band": f"BAND-{grade}",
        })

    # 3. Create 30 Candidates in various stages
    for i in range(1, 31):
        cid = f"CAN{i:04d}"
        pid = f"PER_CAN{i:04d}"
        fname = random.choice(FIRST_NAMES)
        lname = random.choice(LAST_NAMES)
        dept = random.choice(DEPARTMENTS)
        stage = random.choice(["applied", "screening", "interview", "offered", "hired"])
        
        persons.append({
            "id": pid,
            "legal_name": f"{fname} {lname}",
            "dob": (date(1995, 1, 1) + timedelta(days=random.randint(0, 3000))).isoformat(),
            "contact_encrypted": f"ENC_PHONE_+91{random.randint(9000000000, 9999999999)}",
            "purpose_tags": {"recruitment": True},
            "status": "active",
        })

        candidates.append({
            "id": cid,
            "person_id": pid,
            "requisition_id": f"REQ-2026-{random.randint(100, 999)}",
            "stage": stage,
            "rank_explanation": {
                "skills_match": round(random.uniform(0.7, 0.98), 2),
                "experience_score": round(random.uniform(0.6, 0.95), 2),
                "interview_rating": round(random.uniform(3.5, 5.0), 1),
                "fair_hiring_audit": "No protected attributes evaluated",
            },
            "human_reviewed_by": "Deepa Menon (HRBP)" if stage in ("offered", "hired") else None,
            "agent_recommendation": "advance" if stage in ("offered", "hired") else "review",
        })

    dataset = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "synthetic_notice": "ALL DATA IS 100% SYNTHETIC. NO REAL PII.",
            "counts": {
                "persons": len(persons),
                "employees": len(employees),
                "candidates": len(candidates),
            },
        },
        "persons": persons,
        "employees": employees,
        "candidates": candidates,
    }

    # Save to JSON
    json_path = DATA_DIR / "synthetic_dataset.json"
    json_path.write_text(json.dumps(dataset, indent=2))
    print(f"✅ Generated synthetic dataset at {json_path}")
    print(f"   Persons: {len(persons)}, Employees: {len(employees)}, Candidates: {len(candidates)}")
    return dataset


async def seed_database(dataset: dict):
    """Seed data into PostgreSQL using asyncpg/SQLAlchemy."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
    from app.database import AsyncSessionLocal, engine, Base
    from app.models.person import Person, Employee, Candidate, PersonStatus, CandidateStage

    print("🌱 Connecting to database...")
    async with engine.begin() as conn:
        # Create tables if not existing
        await conn.run_sync(Base.metadata.create_all)
    print("   Tables verified.")

    async with AsyncSessionLocal() as session:
        # Check if already seeded
        from sqlalchemy import select, func
        count = await session.scalar(select(func.count(Person.id)))
        if count and count > 0:
            print(f"⚠️  Database already contains {count} persons. Skipping seed.")
            return

        print("   Inserting persons...")
        for p in dataset["persons"]:
            session.add(Person(
                id=p["id"],
                legal_name=p["legal_name"],
                dob=date.fromisoformat(p["dob"]) if p.get("dob") else None,
                contact_encrypted=p.get("contact_encrypted"),
                purpose_tags=p.get("purpose_tags", {}),
                status=PersonStatus(p.get("status", "active")),
            ))
        await session.flush()

        print("   Inserting employees...")
        for e in dataset["employees"]:
            session.add(Employee(
                id=e["id"],
                person_id=e["person_id"],
                emp_code=e["emp_code"],
                status=e["status"],
                manager_id=e["manager_id"],
                grade=e["grade"],
                org_unit=e["org_unit"],
                location=e["location"],
                department=e["department"],
                role_title=e["role_title"],
                start_date=date.fromisoformat(e["start_date"]),
                effective_from=date.fromisoformat(e["effective_from"]),
                grade_band=e.get("grade_band"),
            ))
        await session.flush()

        print("   Inserting candidates...")
        for c in dataset["candidates"]:
            session.add(Candidate(
                id=c["id"],
                person_id=c["person_id"],
                requisition_id=c["requisition_id"],
                stage=CandidateStage(c["stage"]),
                rank_explanation=c.get("rank_explanation"),
                human_reviewed_by=c.get("human_reviewed_by"),
                agent_recommendation=c.get("agent_recommendation"),
            ))
        await session.commit()
        print("✅ Database seeding complete!")


if __name__ == "__main__":
    data = generate_synthetic_dataset(200)
    try:
        asyncio.run(seed_database(data))
    except Exception as e:
        print(f"ℹ️  DB seeding skipped (Postgres might not be running locally yet): {e}")
        print("   JSON file saved in data/synthetic_dataset.json; will seed when docker compose up runs.")
