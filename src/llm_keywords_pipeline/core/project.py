"""Per-project config: <data root>/project.toml.

Client-specific rules live in this file, not in code. No file means an empty
config: no client rule applies. Sections read so far: [project], [paths].
"""

import tomllib
from dataclasses import dataclass
from functools import cache
from pathlib import Path

PROJECT_FILE = "project.toml"


class ProjectConfigError(ValueError):
    """project.toml exists but cannot be parsed."""


@dataclass(frozen=True)
class ProjectConfig:
    brand: str = ""
    site: str = ""
    languages: tuple[str, ...] = ()
    # Structure CSV, relative to the data root; None = the module's legacy name.
    semantics_csv: str | None = None


@cache
def load_project(root: Path) -> ProjectConfig:
    """Read <root>/project.toml once per root."""
    path = root / PROJECT_FILE
    if not path.is_file():
        return ProjectConfig()
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ProjectConfigError(f"{path}: invalid TOML: {exc}") from exc
    project = data.get("project", {})
    paths = data.get("paths", {})
    return ProjectConfig(
        brand=project.get("brand", ""),
        site=project.get("site", ""),
        languages=tuple(project.get("languages", ())),
        semantics_csv=paths.get("semantics_csv"),
    )


def get_project() -> ProjectConfig:
    """Config of the current data root (core.config.PROJECT_ROOT)."""
    from llm_keywords_pipeline.core.config import PROJECT_ROOT

    return load_project(PROJECT_ROOT)
