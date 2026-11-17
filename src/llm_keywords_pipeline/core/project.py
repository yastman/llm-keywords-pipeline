"""Per-project config: <data root>/project.toml.

Client-specific rules live in this file, not in code. No file means an empty
config: no client rule applies. Sections read so far: [project], [paths], [meta].

    [project]
    brand = "Genesis"             # title suffix " | Genesis"; empty = no suffix
    [meta]
    required_phrases = { uk = ["опт\\b"], ru = [] }   # regexes per language
"""

import re
import tomllib
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

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
    # Meta description regexes per language; a language not listed requires none.
    required_phrases: dict[str, tuple[str, ...]] = field(default_factory=dict)


def _table(data: dict[str, Any], key: str, path: Path) -> dict[str, Any]:
    value = data.get(key, {})
    if not isinstance(value, dict):
        raise ProjectConfigError(f"{path}: [{key}] must be a table")
    return value


def _str(table: dict[str, Any], key: str, where: str, path: Path) -> str | None:
    value = table.get(key)
    if value is not None and not isinstance(value, str):
        raise ProjectConfigError(f"{path}: {where}.{key} must be a string")
    return value


def _str_list(value: Any, where: str, path: Path) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ProjectConfigError(f"{path}: {where} must be a list of strings")
    return tuple(value)


def _required_phrases(meta: dict[str, Any], path: Path) -> dict[str, tuple[str, ...]]:
    value = meta.get("required_phrases", {})
    if not isinstance(value, dict):
        raise ProjectConfigError(f"{path}: meta.required_phrases must be a table of languages")
    phrases = {}
    for lang, patterns in value.items():
        where = f"meta.required_phrases.{lang}"
        phrases[lang] = _str_list(patterns, where, path)
        for pattern in phrases[lang]:
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ProjectConfigError(f"{path}: {where}: bad regex {pattern!r}: {exc}") from exc
    return phrases


@cache
def load_project(root: Path) -> ProjectConfig:
    """Read <root>/project.toml once per root."""
    path = root / PROJECT_FILE
    if not path.is_file():
        return ProjectConfig()
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        raise ProjectConfigError(f"{path}: not UTF-8: {exc}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ProjectConfigError(f"{path}: invalid TOML: {exc}") from exc
    project = _table(data, "project", path)
    paths = _table(data, "paths", path)
    meta = _table(data, "meta", path)
    return ProjectConfig(
        brand=_str(project, "brand", "project", path) or "",
        site=_str(project, "site", "project", path) or "",
        languages=_str_list(project.get("languages", []), "project.languages", path),
        semantics_csv=_str(paths, "semantics_csv", "paths", path),
        required_phrases=_required_phrases(meta, path),
    )


def get_project() -> ProjectConfig:
    """Config of the current data root (core.config.PROJECT_ROOT)."""
    from llm_keywords_pipeline.core.config import PROJECT_ROOT

    return load_project(PROJECT_ROOT)
