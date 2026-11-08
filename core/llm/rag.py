"""
Policy RAG — grounded policy Q&A with file:line citations.
No vector DB needed: keyword search over loaded YAML policy files.
Returns answer text + citation references for auditability.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import yaml
import structlog

from core.llm.fake_provider import FakeLLMProvider, LLMResponse

log = structlog.get_logger()

POLICIES_DIR = Path(__file__).parent.parent.parent / "extensions" / "policies"


@dataclass
class RAGResult:
    answer: str
    citations: list[str] = field(default_factory=list)
    policy_name: Optional[str] = None
    policy_version: Optional[int] = None
    confidence: float = 0.9


class PolicyRAG:
    """Keyword-based policy retrieval + FakeLLMProvider answer generation."""

    def __init__(self, policies_dir: Path = POLICIES_DIR, provider: Optional[FakeLLMProvider] = None):
        self.provider = provider or FakeLLMProvider()
        self.policies: list[dict] = []
        self._load_policies(policies_dir)

    def _load_policies(self, policies_dir: Path) -> None:
        if not policies_dir.exists():
            log.warning("Policies dir not found", path=str(policies_dir))
            return
        for yaml_file in policies_dir.glob("*.yaml"):
            try:
                data = yaml.safe_load(yaml_file.read_text(encoding="utf-8")) or {}
                data["_source_file"] = str(yaml_file)
                data["_source_name"] = yaml_file.stem
                self.policies.append(data)
                log.debug("Loaded policy", name=yaml_file.stem)
            except Exception as e:
                log.warning("Failed to load policy", file=str(yaml_file), error=str(e))

    def _find_relevant_policy(self, query: str) -> Optional[dict]:
        """Return best matching policy doc by keyword overlap."""
        q = query.lower()
        best_policy = None
        best_score = 0

        for policy in self.policies:
            name = policy.get("name", policy.get("_source_name", "")).lower()
            # Score = how many query words appear in name or policy name keywords
            score = 0
            if "notice" in q and "notice" in name:
                score += 3
            if "probation" in q and "probation" in name:
                score += 3
            if "leave" in q and "leave" in name:
                score += 3
            if "settlement" in q and "settlement" in name:
                score += 3
            if "exit" in q and ("exit" in name or "settlement" in name):
                score += 2
            # Generic: check if any policy keyword appears in query
            for word in name.split("_"):
                if len(word) > 3 and word in q:
                    score += 1

            if score > best_score:
                best_score = score
                best_policy = policy

        return best_policy if best_score > 0 else None

    def _extract_summary(self, policy: dict) -> str:
        """Extract a brief human-readable summary from YAML structure."""
        lines = []
        name = policy.get("name", policy.get("_source_name", "policy"))
        version = policy.get("version", "?")
        lines.append(f"**{name}** (v{version}):")

        rules = policy.get("rules", [])
        if rules:
            for rule in rules[:4]:  # Show first 4 rules
                desc = rule.get("description", "")
                if not desc:
                    # Build description from conditions
                    conds = rule.get("conditions", {})
                    action = rule.get("action", {})
                    cond_str = ", ".join(f"{k}={v}" for k, v in conds.items())
                    act_str = ", ".join(f"{k}={v}" for k, v in action.items())
                    desc = f"If [{cond_str}] → {act_str}"
                lines.append(f"  • {desc}")
        else:
            lines.append("  Policy loaded but no rules section found.")

        return "\n".join(lines)

    async def answer(self, question: str) -> RAGResult:
        """Answer a policy question grounded in loaded YAML policies."""
        policy = self._find_relevant_policy(question)

        if policy:
            summary = self._extract_summary(policy)
            source_file = policy.get("_source_file", "")
            source_name = policy.get("_source_name", "")
            version = policy.get("version", None)

            # Use FakeLLMProvider for final answer drafting
            resp: LLMResponse = await self.provider.generate(
                f"Answer based on policy: {summary}\n\nQuestion: {question}",
                task="policy_qa",
            )

            citation = f"{source_name}.yaml"
            if source_file:
                citation = source_file.replace("\\", "/")

            return RAGResult(
                answer=resp.text,
                citations=[citation] + (resp.citations or []),
                policy_name=source_name,
                policy_version=version,
                confidence=resp.confidence,
            )
        else:
            # No matching policy — LLM fallback
            resp = await self.provider.generate(question, task="policy_qa")
            return RAGResult(
                answer=resp.text,
                citations=resp.citations or ["extensions/policies/"],
                confidence=resp.confidence,
            )
