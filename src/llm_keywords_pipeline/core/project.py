"""Per-project config: <data root>/project.toml.

Client-specific rules live in this file, not in code. No file means an empty
config: no client rule applies; generic defaults stay in code.

    [project]
    brand = "Genesis"             # title suffix " | Genesis"; empty = no suffix
    [meta]
    required_phrases = { uk = ["опт\\b"], ru = [] }        # regexes per language, FAIL if missing
    recommended_phrases = { uk = ["роздріб"] }              # regexes per language, WARNING if missing
    description_template = { uk = "{name} оптом від {brand}. {types}." }  # all_meta; else filler
    [slugs.ru]                    # category name -> slug; a name not listed = slugify(name)
    "Активная пена" = "aktivnaya-pena"
    [markers]
    commercial = { ru = ["киев"] }                          # added to the generic commercial words
    [synonyms]
    strip_terms = ["авто"]        # core.synonyms: dropped from a keyword before comparing
    stems = { "полиров" = "полир" }                         # core.synonyms: word prefix -> stem
    map = { "машина" = "авто" }   # analyze.duplicates: substring -> replacement
    [blacklist]
    brands = ["koch"]             # audit.ner_brands findings; all_meta skips them as types
    cities = true                 # city check of audit.ner_brands; false = off
    phrases_allow = ["широкий асортимент"]                  # strict phrases not checked
    [density.category_substrings.ru]
    aktivnaya-pena = { primary = ["пен"], anti = ["шампун"] }
    [structure.l2_forbidden]
    avtoshampuni = ["ручн.*мойк"]                           # regexes per L2 slug
    [content_standards]           # validate.content quality mode; all false when not set
    safety_block = true
    howto_steps = true
    evergreen_math = true
    warnings = true
    [niche]
    tone = "эксперт по оптовым поставкам сладостей"         # editorial tone of the analyze brief
"""

import re
import tomllib
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

PROJECT_FILE = "project.toml"
CONTENT_STANDARD_KEYS = ("safety_block", "howto_steps", "evergreen_math", "warnings")
DESCRIPTION_FIELDS = {"keyword": "", "name": "", "types": "", "brand": ""}


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
    recommended_phrases: dict[str, tuple[str, ...]] = field(default_factory=dict)
    description_template: dict[str, str] = field(default_factory=dict)
    slugs: dict[str, dict[str, str]] = field(default_factory=dict)
    commercial_markers: dict[str, tuple[str, ...]] = field(default_factory=dict)
    synonym_strip_terms: tuple[str, ...] = ()
    synonym_stems: dict[str, str] = field(default_factory=dict)
    synonym_map: dict[str, str] = field(default_factory=dict)
    blacklist_brands: tuple[str, ...] = ()
    blacklist_cities: bool = True
    phrases_allow: tuple[str, ...] = ()
    # lang -> slug -> (primary substrings, anti substrings)
    category_substrings: dict[str, dict[str, tuple[tuple[str, ...], tuple[str, ...]]]] = field(
        default_factory=dict
    )
    l2_forbidden: dict[str, tuple[str, ...]] = field(default_factory=dict)
    content_standards: dict[str, bool] = field(
        default_factory=lambda: dict.fromkeys(CONTENT_STANDARD_KEYS, False)
    )
    tone: str = ""


def _table(data: dict[str, Any], key: str, path: Path, where: str | None = None) -> dict[str, Any]:
    value = data.get(key, {})
    if not isinstance(value, dict):
        raise ProjectConfigError(f"{path}: [{where or key}] must be a table")
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


def _str_map(value: Any, where: str, path: Path) -> dict[str, str]:
    if not isinstance(value, dict) or not all(isinstance(v, str) for v in value.values()):
        raise ProjectConfigError(f"{path}: {where} must be a table of strings")
    return dict(value)


def _regexes(patterns: tuple[str, ...], where: str, path: Path) -> tuple[str, ...]:
    for pattern in patterns:
        try:
            re.compile(pattern)
        except re.error as exc:
            raise ProjectConfigError(f"{path}: {where}: bad regex {pattern!r}: {exc}") from exc
    return patterns


def _lang_lists(
    table: dict[str, Any], key: str, where: str, path: Path, regex: bool = False
) -> dict[str, tuple[str, ...]]:
    value = table.get(key, {})
    if not isinstance(value, dict):
        raise ProjectConfigError(f"{path}: {where}.{key} must be a table of languages")
    result = {}
    for lang, items in value.items():
        lang_where = f"{where}.{key}.{lang}"
        result[lang] = _str_list(items, lang_where, path)
        if regex:
            _regexes(result[lang], lang_where, path)
    return result


def _description_template(meta: dict[str, Any], path: Path) -> dict[str, str]:
    templates = _str_map(meta.get("description_template", {}), "meta.description_template", path)
    for lang, template in templates.items():
        try:
            template.format(**DESCRIPTION_FIELDS)
        except (KeyError, IndexError, ValueError) as exc:
            raise ProjectConfigError(
                f"{path}: meta.description_template.{lang}: bad template {template!r}: "
                f"placeholders are {{{'}, {'.join(DESCRIPTION_FIELDS)}}} ({exc!r})"
            ) from exc
    return templates


def _slugs(data: dict[str, Any], path: Path) -> dict[str, dict[str, str]]:
    slugs = _table(data, "slugs", path)
    return {lang: _str_map(names, f"slugs.{lang}", path) for lang, names in slugs.items()}


def _category_substrings(
    density: dict[str, Any], path: Path
) -> dict[str, dict[str, tuple[tuple[str, ...], tuple[str, ...]]]]:
    by_lang = _table(density, "category_substrings", path, "density.category_substrings")
    result = {}
    for lang, slugs in by_lang.items():
        where = f"density.category_substrings.{lang}"
        if not isinstance(slugs, dict):
            raise ProjectConfigError(f"{path}: [{where}] must be a table of slugs")
        result[lang] = {}
        for slug, entry in slugs.items():
            if not isinstance(entry, dict):
                raise ProjectConfigError(f"{path}: {where}.{slug} must be {{primary, anti}}")
            result[lang][slug] = (
                _str_list(entry.get("primary", []), f"{where}.{slug}.primary", path),
                _str_list(entry.get("anti", []), f"{where}.{slug}.anti", path),
            )
    return result


def _l2_forbidden(structure: dict[str, Any], path: Path) -> dict[str, tuple[str, ...]]:
    table = _table(structure, "l2_forbidden", path, "structure.l2_forbidden")
    return {
        slug: _regexes(
            _str_list(patterns, f"structure.l2_forbidden.{slug}", path),
            f"structure.l2_forbidden.{slug}",
            path,
        )
        for slug, patterns in table.items()
    }


def _content_standards(data: dict[str, Any], path: Path) -> dict[str, bool]:
    table = _table(data, "content_standards", path)
    unknown = set(table) - set(CONTENT_STANDARD_KEYS)
    if unknown:
        raise ProjectConfigError(
            f"{path}: [content_standards] unknown keys {sorted(unknown)}; "
            f"known: {', '.join(CONTENT_STANDARD_KEYS)}"
        )
    if not all(isinstance(v, bool) for v in table.values()):
        raise ProjectConfigError(f"{path}: [content_standards] values must be true or false")
    return {key: table.get(key, False) for key in CONTENT_STANDARD_KEYS}


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
    markers = _table(data, "markers", path)
    synonyms = _table(data, "synonyms", path)
    blacklist = _table(data, "blacklist", path)
    niche = _table(data, "niche", path)
    cities = blacklist.get("cities", True)
    if not isinstance(cities, bool):
        raise ProjectConfigError(f"{path}: blacklist.cities must be true or false")
    return ProjectConfig(
        brand=_str(project, "brand", "project", path) or "",
        site=_str(project, "site", "project", path) or "",
        languages=_str_list(project.get("languages", []), "project.languages", path),
        semantics_csv=_str(paths, "semantics_csv", "paths", path),
        required_phrases=_lang_lists(meta, "required_phrases", "meta", path, regex=True),
        recommended_phrases=_lang_lists(meta, "recommended_phrases", "meta", path, regex=True),
        description_template=_description_template(meta, path),
        slugs=_slugs(data, path),
        commercial_markers=_lang_lists(markers, "commercial", "markers", path),
        synonym_strip_terms=_str_list(
            synonyms.get("strip_terms", []), "synonyms.strip_terms", path
        ),
        synonym_stems=_str_map(synonyms.get("stems", {}), "synonyms.stems", path),
        synonym_map=_str_map(synonyms.get("map", {}), "synonyms.map", path),
        blacklist_brands=tuple(
            b.lower() for b in _str_list(blacklist.get("brands", []), "blacklist.brands", path)
        ),
        blacklist_cities=cities,
        phrases_allow=tuple(
            p.lower()
            for p in _str_list(blacklist.get("phrases_allow", []), "blacklist.phrases_allow", path)
        ),
        category_substrings=_category_substrings(_table(data, "density", path), path),
        l2_forbidden=_l2_forbidden(_table(data, "structure", path), path),
        content_standards=_content_standards(data, path),
        tone=_str(niche, "tone", "niche", path) or "",
    )


def get_project() -> ProjectConfig:
    """Config of the current data root (core.config.PROJECT_ROOT)."""
    from llm_keywords_pipeline.core.config import PROJECT_ROOT

    return load_project(PROJECT_ROOT)
