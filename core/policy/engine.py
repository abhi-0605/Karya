"""
Policy Engine — evaluates versioned YAML rules deterministically in plain code.
No LLM is ever used for statutory or policy calculations.
Policies contain their own test fixtures and version tags for audit trails.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
import yaml
import structlog

log = structlog.get_logger()

POLICIES_DIR = Path(__file__).parent.parent.parent / "extensions" / "policies"


@dataclass
class PolicyRule:
    name: str
    when: dict[str, Any]
    then: dict[str, Any]


@dataclass
class PolicyDefinition:
    id: str
    version: int
    effective_from: str
    rules: list[PolicyRule]
    tests: list[dict[str, Any]] = field(default_factory=list)
    description: str = ""


class PolicyEngine:
    def __init__(self, directory: Path = POLICIES_DIR):
        self.directory = directory
        self.policies: dict[str, PolicyDefinition] = {}
        self.load_all_policies()

    def load_policy(self, path: Path) -> PolicyDefinition:
        """Parse a policy YAML file."""
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        rules = [
            PolicyRule(name=r["name"], when=r["when"], then=r["then"])
            for r in data.get("rules", [])
        ]
        return PolicyDefinition(
            id=data["id"],
            version=data.get("version", 1),
            effective_from=str(data.get("effective_from", "2026-01-01")),
            rules=rules,
            tests=data.get("tests", []),
            description=data.get("description", ""),
        )

    def load_all_policies(self) -> dict[str, PolicyDefinition]:
        """Load all policies from extensions/policies/."""
        if not self.directory.exists():
            return {}
        for path in self.directory.glob("*.yaml"):
            try:
                p = self.load_policy(path)
                self.policies[p.id] = p
                log.info("Loaded policy", id=p.id, version=p.version, rules=len(p.rules))
            except Exception as e:
                log.error("Failed to load policy", path=str(path), error=str(e))
        return self.policies

    def _matches_condition(self, condition_val: Any, actual_val: Any) -> bool:
        """Check if actual_val satisfies condition_val."""
        if isinstance(condition_val, list):
            return actual_val in condition_val
        elif isinstance(condition_val, dict):
            # Comparison operators e.g. {">=": 5}
            for op, target in condition_val.items():
                if op == ">" and not (actual_val > target):
                    return False
                elif op == ">=" and not (actual_val >= target):
                    return False
                elif op == "<" and not (actual_val < target):
                    return False
                elif op == "<=" and not (actual_val <= target):
                    return False
                elif op == "==" and not (actual_val == target):
                    return False
                elif op == "!=" and not (actual_val != target):
                    return False
            return True
        return actual_val == condition_val

    def evaluate(self, policy_id: str, context: dict[str, Any]) -> tuple[dict[str, Any], str]:
        """
        Evaluate a policy against input context.
        Returns: (output_dict, policy_version_tag) e.g. ({'notice_days': 30}, 'notice_period@4')
        """
        policy = self.policies.get(policy_id)
        if not policy:
            raise KeyError(f"Policy '{policy_id}' not found in registry")

        version_tag = f"{policy.id}@{policy.version}"

        for rule in policy.rules:
            matches = True
            for field, cond in rule.when.items():
                val = context.get(field)
                if not self._matches_condition(cond, val):
                    matches = False
                    break

            if matches:
                log.debug("Policy rule matched", policy=policy_id, rule=rule.name, then=rule.then)
                return rule.then.copy(), version_tag

        return {}, version_tag

    def run_policy_tests(self, policy_id: str) -> list[dict]:
        """Run built-in fixture tests defined inside the policy YAML."""
        policy = self.policies.get(policy_id)
        if not policy:
            raise KeyError(f"Policy '{policy_id}' not found")

        results = []
        for idx, test_case in enumerate(policy.tests):
            given = test_case.get("given", {})
            expect = test_case.get("expect", {})
            actual, _ = self.evaluate(policy_id, given)
            passed = all(actual.get(k) == v for k, v in expect.items())
            results.append({
                "test_index": idx,
                "given": given,
                "expect": expect,
                "actual": actual,
                "passed": passed,
            })
        return results
