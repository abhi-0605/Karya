"""
Skill Registry — auto-discovers skill plugins from extensions/skills/.
Each skill folder must have a manifest.yaml and skill.py with an async run() function.
"""
from __future__ import annotations
import importlib.util
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional
import yaml
import structlog

log = structlog.get_logger()

SKILLS_DIR = Path(__file__).parent.parent.parent / "extensions" / "skills"


@dataclass
class SkillManifest:
    name: str
    version: str
    type: str  # integration | rules | llm
    permissions_required: list[str] = field(default_factory=list)
    idempotency_fields: list[str] = field(default_factory=list)
    integration: Optional[str] = None
    model: str = "none"
    timeout_s: int = 30
    retry_max: int = 3
    retry_backoff: str = "exponential"


@dataclass
class Skill:
    manifest: SkillManifest
    run: Callable  # async run(ctx, inputs) -> outputs


_registry: dict[str, Skill] = {}


def _load_skill_from_dir(skill_dir: Path) -> Optional[Skill]:
    """Load a skill from its directory."""
    manifest_path = skill_dir / "manifest.yaml"
    skill_path = skill_dir / "skill.py"
    if not manifest_path.exists() or not skill_path.exists():
        return None

    try:
        data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        retry = data.get("retry", {})
        manifest = SkillManifest(
            name=data["name"],
            version=str(data.get("version", "1.0.0")),
            type=data.get("type", "integration"),
            permissions_required=data.get("permissions_required", []),
            idempotency_fields=data.get("idempotency", []),
            integration=data.get("integration"),
            model=data.get("model", "none"),
            timeout_s=data.get("timeout_s", 30),
            retry_max=retry.get("max", 3),
            retry_backoff=retry.get("backoff", "exponential"),
        )

        module_name = f"skill_{manifest.name.replace('.', '_')}"
        spec = importlib.util.spec_from_file_location(module_name, skill_path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        if not hasattr(module, "run"):
            log.error("Skill missing run() function", skill=manifest.name)
            return None

        return Skill(manifest=manifest, run=module.run)
    except Exception as e:
        log.error("Failed to load skill", dir=str(skill_dir), error=str(e))
        return None


def load_all_skills(directory: Path = SKILLS_DIR) -> dict[str, Skill]:
    """Discover and load all skills. Called at startup."""
    skills: dict[str, Skill] = {}
    if not directory.exists():
        log.warning("Skills directory not found", path=str(directory))
        return skills

    for skill_dir in directory.iterdir():
        if skill_dir.is_dir() and not skill_dir.name.startswith("_"):
            # Check top level or subdirectories
            if (skill_dir / "manifest.yaml").exists():
                skill = _load_skill_from_dir(skill_dir)
                if skill:
                    skills[skill.manifest.name] = skill
            else:
                for sub in skill_dir.iterdir():
                    if sub.is_dir() and (sub / "manifest.yaml").exists():
                        skill = _load_skill_from_dir(sub)
                        if skill:
                            skills[skill.manifest.name] = skill

    log.info("Loaded skills count", count=len(skills))
    return skills


def get_registry() -> dict[str, Skill]:
    """Return the global registry (lazy-loaded on first call)."""
    global _registry
    if not _registry:
        _registry = load_all_skills()
    return _registry


def register_skill(skill: Skill) -> None:
    """Manually register a skill (useful for testing and built-ins)."""
    global _registry
    _registry[skill.manifest.name] = skill


def reload_registry() -> dict[str, Skill]:
    """Hot-reload all skills."""
    global _registry
    _registry = load_all_skills()
    return _registry


def get_skill(name: str) -> Optional[Skill]:
    return get_registry().get(name)
