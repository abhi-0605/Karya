"""Person, Candidate, Employee, and EmploymentEvent models."""
from __future__ import annotations
from datetime import date, datetime
from typing import Optional
from sqlalchemy import String, Date, DateTime, Boolean, Text, JSON, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin
import enum


class PersonStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    exited = "exited"


class Person(Base, TimestampMixin):
    __tablename__ = "person"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    legal_name: Mapped[str] = mapped_column(String(200))
    dob: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    # Contact stored encrypted; model never receives raw values
    contact_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    purpose_tags: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    status: Mapped[PersonStatus] = mapped_column(SAEnum(PersonStatus), default=PersonStatus.active)

    employee: Mapped[Optional["Employee"]] = relationship(back_populates="person", uselist=False)
    candidate: Mapped[Optional["Candidate"]] = relationship(back_populates="person", uselist=False)
    consent_records: Mapped[list["ConsentRecord"]] = relationship(back_populates="person")


class EmploymentEventType(str, enum.Enum):
    hire = "hire"
    transfer = "transfer"
    resignation = "resignation"
    exit = "exit"
    grade_change = "grade_change"
    role_change = "role_change"


class Employee(Base, TimestampMixin):
    __tablename__ = "employee"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    person_id: Mapped[str] = mapped_column(String(50), ForeignKey("person.id"))
    emp_code: Mapped[str] = mapped_column(String(50), unique=True)
    status: Mapped[str] = mapped_column(String(30), default="active")
    manager_id: Mapped[Optional[str]] = mapped_column(String(50), ForeignKey("employee.id"), nullable=True)
    grade: Mapped[str] = mapped_column(String(10))
    org_unit: Mapped[str] = mapped_column(String(100))
    location: Mapped[str] = mapped_column(String(100))
    department: Mapped[str] = mapped_column(String(100))
    role_title: Mapped[str] = mapped_column(String(200))
    start_date: Mapped[date] = mapped_column(Date)
    effective_from: Mapped[date] = mapped_column(Date)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    # Never store actual salary here; only grade-based routing
    grade_band: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    person: Mapped["Person"] = relationship(back_populates="employee")
    events: Mapped[list["EmploymentEvent"]] = relationship(back_populates="employee")


class EmploymentEvent(Base, TimestampMixin):
    __tablename__ = "employment_event"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    employee_id: Mapped[str] = mapped_column(String(50), ForeignKey("employee.id"))
    type: Mapped[EmploymentEventType] = mapped_column(SAEnum(EmploymentEventType))
    effective_date: Mapped[date] = mapped_column(Date)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    triggered_by: Mapped[str] = mapped_column(String(100))

    employee: Mapped["Employee"] = relationship(back_populates="events")


class CandidateStage(str, enum.Enum):
    applied = "applied"
    screening = "screening"
    interview = "interview"
    offered = "offered"
    hired = "hired"
    rejected = "rejected"
    withdrawn = "withdrawn"


class Candidate(Base, TimestampMixin):
    __tablename__ = "candidate"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    person_id: Mapped[str] = mapped_column(String(50), ForeignKey("person.id"))
    requisition_id: Mapped[str] = mapped_column(String(50))
    stage: Mapped[CandidateStage] = mapped_column(SAEnum(CandidateStage), default=CandidateStage.applied)
    # JSON blob with factor-wise score breakdown (no salary, no protected attributes)
    rank_explanation: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    human_reviewed_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # NO auto-reject: agent can only recommend, human must confirm
    agent_recommendation: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    person: Mapped["Person"] = relationship(back_populates="candidate")


class ConsentRecord(Base, TimestampMixin):
    __tablename__ = "consent_record"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    person_id: Mapped[str] = mapped_column(String(50), ForeignKey("person.id"))
    purpose: Mapped[str] = mapped_column(String(200))
    granted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    withdrawn_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    person: Mapped["Person"] = relationship(back_populates="consent_records")
