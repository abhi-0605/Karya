"""Pure-Python data classes for workflow definitions (loaded from YAML)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class RetryConfig:
    max: int = 3
    backoff: str = "exponential"  # exponential | fixed

@dataclass
class StepDefinition:
    id: str
    skill: str
    mode: str = "auto"           # auto | approval | route_only
    depends_on: list[str] = field(default_factory=list)
    sla_minutes: Optional[int] = None
    on_failure: str = "fail"     # fail | human_queue
    llm: Optional[str] = None    # none | small | escalation
    approver_role: Optional[str] = None
    timeout_s: int = 30
    retry: RetryConfig = field(default_factory=RetryConfig)
    action: Optional[str] = None

@dataclass
class WorkflowDefinition:
    id: str
    version: int
    trigger: str
    inputs: list[str]
    steps: list[StepDefinition]
    description: str = ""
