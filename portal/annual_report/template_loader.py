"""Load annual report Markdown analysis template."""

from __future__ import annotations

from pathlib import Path

DEFAULT_TEMPLATE_REL = Path("annual-report") / "templates" / "output-template.md"


def resolve_skills_dir(explicit: Path | None = None) -> Path:
    if explicit is not None:
        return explicit
    return Path(__file__).resolve().parent.parent / "skills"


def load_default_template(skills_dir: Path | None = None) -> str:
    path = resolve_skills_dir(skills_dir) / DEFAULT_TEMPLATE_REL
    if not path.is_file():
        raise FileNotFoundError(f"未找到分析模板: {path}")
    return path.read_text(encoding="utf-8")
