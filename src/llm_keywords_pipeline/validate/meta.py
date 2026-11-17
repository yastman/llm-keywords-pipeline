#!/usr/bin/env python3
"""
validate_meta.py — Meta Tags Validation (v17.0)

Валідація Title + Description для категорій.

Перевірки:
- Title містить primary keyword
- Title довжина 30-60 chars (core/config.py)
- Title без двокрапки
- Description містить primary keyword
- Description довжина 100-160 chars (core/config.py)
- Description містить фрази [meta] required_phrases з <data root>/project.toml
  (немає файлу або мови = фраза не потрібна)
- Description містить фрази [meta] recommended_phrases (немає = WARNING, не FAIL)

Usage:
    uv run python -m llm_keywords_pipeline.validate.meta <meta.json>
    uv run python -m llm_keywords_pipeline.validate.meta <meta.json> --keywords <keywords.json>
    uv run python -m llm_keywords_pipeline.validate.meta --all
    uv run python -m llm_keywords_pipeline.validate.meta --all --fix
    uv run python -m llm_keywords_pipeline.validate.meta <meta.json> --json

Exit codes:
    0 = PASS
    1 = WARNING
    2 = FAIL
"""

import json
import re
import sys
from pathlib import Path
from typing import Any

from llm_keywords_pipeline.core.config import QUALITY_THRESHOLDS
from llm_keywords_pipeline.core.keywords import MorphAnalyzer, keyword_matches_text
from llm_keywords_pipeline.core.project import get_project
from llm_keywords_pipeline.validate.seo import detect_language

# Fix Windows encoding is moved to main() block to avoid pytest conflicts


# =============================================================================
# Constants
# =============================================================================

# Soft limits (warnings, not failures), from core/config.py
TITLE_MIN_LENGTH = QUALITY_THRESHOLDS["title_min"]
TITLE_MAX_LENGTH = QUALITY_THRESHOLDS["title_max"]
DESC_MIN_LENGTH = QUALITY_THRESHOLDS["description_min"]
DESC_MAX_LENGTH = QUALITY_THRESHOLDS["description_max"]

# Patterns to detect
COLON_PATTERN = re.compile(r":\s")

MARKETING_FLUFF = [
    r"быстро",
    r"швидко",
    r"качественн",
    r"якісн",
    r"лучшие цены",
    r"найкращі ціни",
]


# =============================================================================
# Validation Functions
# =============================================================================


# from typing import Any


def load_json(path: str) -> dict[str, Any]:
    """Load JSON file."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)  # type: ignore


def get_primary_keywords(keywords_data: dict[str, Any]) -> list[str]:
    """
    Extract primary keyword from keywords JSON.

    Supports two formats:
    1. _clean.json: {"keywords": [{"keyword": "...", "volume": N}, ...]} → MAX(volume)
    2. Old format: {"keywords": {"primary": [...]}}
    """
    keywords = []

    if "keywords" in keywords_data:
        kw_section = keywords_data["keywords"]

        # Format 1: _clean.json with list of {keyword, volume}
        if isinstance(kw_section, list) and kw_section:
            # Find keyword with MAX volume
            max_item = max(
                kw_section, key=lambda x: x.get("volume", 0) if isinstance(x, dict) else 0
            )
            if isinstance(max_item, dict) and max_item.get("keyword"):
                keywords.append(max_item["keyword"].lower())

        # Format 2: Old format with {"primary": [...]}
        elif isinstance(kw_section, dict) and "primary" in kw_section:
            for item in kw_section["primary"]:
                if isinstance(item, dict):
                    keywords.append(item.get("keyword", "").lower())
                else:
                    keywords.append(str(item).lower())

    return keywords


def keyword_matches(keyword: str, text: str, lang: str = "ru") -> bool:
    """
    Backward-compatible wrapper using keyword_utils.

    Check if keyword matches text, accounting for plural/singular forms.
    Uses morphological analysis for accurate matching.

    Args:
        keyword: Keyword to search for
        text: Text to search in
        lang: 'ru' (default) or 'uk' for morphology
    """
    return keyword_matches_text(keyword, text, lang=lang)


def validate_title(
    title: str, primary_keywords: list[str] | None = None, lang: str = "ru"
) -> dict[str, Any]:
    """
    Validate meta title.

    Checks:
    - Length TITLE_MIN_LENGTH-TITLE_MAX_LENGTH chars (before the | brand suffix)
    - No colon
    - Contains primary keyword
    - No marketing fluff

    Args:
        title: Meta title text
        primary_keywords: List of primary keywords to check
        lang: 'ru' (default) or 'uk' for morphology
    """
    checks: dict[str, Any] = {
        "length": {"passed": False, "message": ""},
        "no_colon": {"passed": False, "message": ""},
        "primary_keyword": {"passed": False, "message": ""},
        "no_fluff": {"passed": False, "message": ""},
    }
    results: dict[str, Any] = {
        "value": title,
        "length": len(title),
        "checks": checks,
        "overall": "FAIL",
    }

    # Extract title without brand suffix
    title_clean = title
    if "|" in title:
        title_clean = title.split("|")[0].strip()

    title_length = len(title_clean)
    results["length_without_brand"] = title_length

    # 1. Length check
    if TITLE_MIN_LENGTH <= title_length <= TITLE_MAX_LENGTH:
        results["checks"]["length"]["passed"] = True
        results["checks"]["length"]["message"] = f"OK ({title_length} chars)"
    elif title_length < TITLE_MIN_LENGTH:
        results["checks"]["length"]["message"] = f"Too short ({title_length} < {TITLE_MIN_LENGTH})"
    else:
        results["checks"]["length"]["message"] = f"Too long ({title_length} > {TITLE_MAX_LENGTH})"

    # 2. No colon check
    if not COLON_PATTERN.search(title_clean):
        results["checks"]["no_colon"]["passed"] = True
        results["checks"]["no_colon"]["message"] = "OK (no colon)"
    else:
        results["checks"]["no_colon"]["message"] = (
            "Contains colon (:) - replace with 'для' or brackets"
        )

    # 3. Primary keyword check (with stem matching, language-aware)
    # Also check plural form since Title/H1 use plural formula
    if primary_keywords:
        from llm_keywords_pipeline.core.keywords import MorphAnalyzer

        morph = MorphAnalyzer(lang)
        found = []
        for kw in primary_keywords:
            # Check original form
            if keyword_matches(kw, title, lang=lang):
                found.append(kw)
            # Check plural form (Title uses phrase_to_plural)
            else:
                plural_kw = morph.phrase_to_plural(kw)
                if keyword_matches(plural_kw, title, lang=lang):
                    found.append(f"{kw} (plural: {plural_kw})")

        if found:
            results["checks"]["primary_keyword"]["passed"] = True
            results["checks"]["primary_keyword"]["message"] = f"Found: {found[0]}"
        else:
            results["checks"]["primary_keyword"]["message"] = "Missing primary keyword"
    else:
        results["checks"]["primary_keyword"]["passed"] = True
        results["checks"]["primary_keyword"]["message"] = "No keywords to check"

    # 4. No marketing fluff
    title_lower = title.lower()
    fluff_found = [p for p in MARKETING_FLUFF if re.search(p, title_lower)]
    if not fluff_found:
        results["checks"]["no_fluff"]["passed"] = True
        results["checks"]["no_fluff"]["message"] = "OK (no marketing fluff)"
    else:
        results["checks"]["no_fluff"]["message"] = f"Marketing fluff found: {fluff_found}"

    # Overall
    all_passed = all(c["passed"] for c in results["checks"].values())
    critical_passed = (
        results["checks"]["no_colon"]["passed"] and results["checks"]["primary_keyword"]["passed"]
    )

    if all_passed:
        results["overall"] = "PASS"
    elif critical_passed:
        results["overall"] = "WARNING"
    else:
        results["overall"] = "FAIL"

    return results


def validate_description(
    description: str, primary_keywords: list[str] | None = None, lang: str = "ru"
) -> dict[str, Any]:
    """
    Validate meta description.

    Checks:
    - Length DESC_MIN_LENGTH-DESC_MAX_LENGTH chars
    - Contains primary keyword
    - Contains each [meta] required_phrases regex of project.toml for lang (FAIL if missing)
    - Contains each [meta] recommended_phrases regex of project.toml for lang (WARNING)
    - No marketing fluff

    Args:
        description: Meta description text
        primary_keywords: List of primary keywords to check
        lang: 'ru' (default) or 'uk' for language-specific patterns
    """
    checks: dict[str, Any] = {
        "length": {"passed": False, "message": ""},
        "primary_keyword": {"passed": False, "message": ""},
        "required_phrases": {"passed": False, "message": ""},
        "recommended_phrases": {"passed": False, "message": ""},
        "no_fluff": {"passed": False, "message": ""},
    }
    results: dict[str, Any] = {
        "value": description,
        "length": len(description),
        "checks": checks,
        "overall": "FAIL",
    }

    desc_lower = description.lower()

    # 1. Length check
    desc_length = len(description)
    if DESC_MIN_LENGTH <= desc_length <= DESC_MAX_LENGTH:
        results["checks"]["length"]["passed"] = True
        results["checks"]["length"]["message"] = f"OK ({desc_length} chars)"
    elif desc_length < DESC_MIN_LENGTH:
        results["checks"]["length"]["message"] = f"Too short ({desc_length} < {DESC_MIN_LENGTH})"
    else:
        results["checks"]["length"]["passed"] = True  # Warning only
        results["checks"]["length"]["message"] = (
            f"Slightly long ({desc_length} > {DESC_MAX_LENGTH})"
        )

    # 2. Primary keyword check (with stem matching, language-aware)
    # Also check plural form since Description may start with plural
    if primary_keywords:
        from llm_keywords_pipeline.core.keywords import MorphAnalyzer

        morph = MorphAnalyzer(lang)
        found = []
        for kw in primary_keywords:
            # Check original form
            if keyword_matches(kw, description, lang=lang):
                found.append(kw)
            # Check plural form
            else:
                plural_kw = morph.phrase_to_plural(kw)
                if keyword_matches(plural_kw, description, lang=lang):
                    found.append(f"{kw} (plural: {plural_kw})")

        if found:
            results["checks"]["primary_keyword"]["passed"] = True
            results["checks"]["primary_keyword"]["message"] = f"Found: {found[0]}"
        else:
            results["checks"]["primary_keyword"]["message"] = "Missing primary keyword"
    else:
        results["checks"]["primary_keyword"]["passed"] = True
        results["checks"]["primary_keyword"]["message"] = "No keywords to check"

    # 3. Client phrases from project.toml [meta] required_phrases (none configured = none required)
    required = get_project().required_phrases.get(lang, ())
    missing = [p for p in required if not re.search(p, description, re.IGNORECASE)]
    if missing:
        results["checks"]["required_phrases"]["message"] = "Missing required phrases: " + ", ".join(
            missing
        )
    else:
        results["checks"]["required_phrases"]["passed"] = True
        results["checks"]["required_phrases"]["message"] = (
            "OK (required phrases found)" if required else "OK (no required phrases configured)"
        )

    # 3b. Recommended phrases from project.toml [meta] recommended_phrases: WARNING only
    recommended = get_project().recommended_phrases.get(lang, ())
    missing = [p for p in recommended if not re.search(p, description, re.IGNORECASE)]
    checks["recommended_phrases"]["passed"] = not missing
    if missing:
        message = "Missing recommended phrases: " + ", ".join(missing)
    elif recommended:
        message = "OK (recommended phrases found)"
    else:
        message = "OK (no recommended phrases configured)"
    checks["recommended_phrases"]["message"] = message

    # 4. No marketing fluff
    fluff_found = [p for p in MARKETING_FLUFF if re.search(p, desc_lower)]
    if not fluff_found:
        results["checks"]["no_fluff"]["passed"] = True
        results["checks"]["no_fluff"]["message"] = "OK (no marketing fluff)"
    else:
        results["checks"]["no_fluff"]["message"] = f"Marketing fluff found: {fluff_found}"

    # Overall
    all_passed = all(c["passed"] for c in results["checks"].values())
    critical_passed = (
        results["checks"]["primary_keyword"]["passed"]
        and results["checks"]["required_phrases"]["passed"]
    )

    if all_passed:
        results["overall"] = "PASS"
    elif critical_passed:
        results["overall"] = "WARNING"
    else:
        results["overall"] = "FAIL"

    return results


def validate_h1(h1: str, primary_keyword: str, lang: str = "ru") -> dict[str, Any]:
    """
    Validate that H1 contains primary_keyword or its plural form.

    Args:
        h1: The H1 heading text
        primary_keyword: Primary keyword from _clean.json (MAX volume)
        lang: 'ru' or 'uk' for morphology

    Returns:
        {
            "passed": bool,
            "form": "exact" | "plural" | "morphological" | None,
            "message": str,
            "h1": str,
            "primary_keyword": str
        }
    """
    result: dict[str, Any] = {
        "passed": False,
        "form": None,
        "message": "",
        "h1": h1,
        "primary_keyword": primary_keyword,
    }

    if not h1 or not primary_keyword:
        result["message"] = "H1 or primary_keyword is empty"
        return result

    h1_lower = h1.lower()
    pk_lower = primary_keyword.lower()

    # Check 1: Exact match (keyword in H1)
    if pk_lower in h1_lower:
        result["passed"] = True
        result["form"] = "exact"
        result["message"] = "OK (exact match)"
        return result

    # Check 2: Plural form match
    morph = MorphAnalyzer(lang)
    plural_form = morph.phrase_to_plural(primary_keyword)

    if plural_form.lower() in h1_lower:
        result["passed"] = True
        result["form"] = "plural"
        result["message"] = "OK (plural form)"
        return result

    # Check 3: Morphological match (lemma-based)
    if keyword_matches(primary_keyword, h1, lang=lang):
        result["passed"] = True
        result["form"] = "morphological"
        result["message"] = "OK (morphological match)"
        return result

    # Failed all checks
    result["message"] = f"H1 '{h1}' не містить '{primary_keyword}' або '{plural_form}'"
    return result


def validate_meta_file(
    meta_path: str, keywords_path: str | None = None, lang: str | None = None
) -> dict[str, Any]:
    """
    Full validation of meta JSON file.

    Args:
        meta_path: Path to meta JSON file
        keywords_path: Optional path to keywords JSON file
        lang: 'ru' or 'uk' for language-specific validation. Precedence: this argument
            (CLI --lang) > the meta JSON "language" key > the path (detect_language) > 'ru'

    Returns:
        Validation results dict
    """
    explicit_lang = lang is not None
    lang = lang or detect_language(meta_path)
    results: dict[str, Any] = {
        "file": meta_path,
        "keywords_file": keywords_path,
        "lang": lang,
        "title": None,
        "description": None,
        "h1": None,
        "overall": "FAIL",
        "errors": [],
    }

    # Load meta file
    try:
        meta = load_json(meta_path)
    except Exception as e:
        results["errors"].append(f"Cannot load meta file: {e}")
        return results

    # Extract values
    title = meta.get("meta", {}).get("title", "")
    description = meta.get("meta", {}).get("description", "")
    h1 = meta.get("h1", "")

    results["h1"] = {"value": h1}

    # The meta JSON "language" key wins over the path, not over an explicit lang
    if not explicit_lang and meta.get("language") in ("ru", "uk"):
        lang = meta["language"]
        results["lang"] = lang

    # Load keywords if provided
    primary_keywords = []
    # commercial_keywords = []

    if keywords_path:
        try:
            keywords_data = load_json(keywords_path)

            # Priority: category_title > primary_keyword (MAX volume)
            # category_title используется для составных категорий (Губки и варежки, Керамика и жидкое стекло)
            if keywords_data.get("category_title"):
                primary_keywords = [keywords_data["category_title"].lower()]
            else:
                primary_keywords = get_primary_keywords(keywords_data)
        except Exception as e:
            results["errors"].append(f"Cannot load keywords file: {e}")

    # Also check keywords_in_content from meta file
    if not primary_keywords and "keywords_in_content" in meta:
        kic = meta["keywords_in_content"]
        if "primary" in kic:
            primary_keywords = [k.lower() for k in kic["primary"]]

    # Validate title (with language support)
    results["title"] = validate_title(title, primary_keywords, lang=lang)

    # Validate description (with language support)
    results["description"] = validate_description(description, primary_keywords, lang=lang)

    # Validate H1 against primary keyword
    h1_validation: dict[str, Any] = {
        "passed": True,
        "form": None,
        "message": "No keywords provided",
    }

    if primary_keywords and h1:
        h1_validation = validate_h1(h1, primary_keywords[0], lang=lang)

    results["h1"] = {
        "value": h1,
        "validation": h1_validation,
    }

    # Overall
    title_ok = results["title"]["overall"] in ["PASS", "WARNING"]
    desc_ok = results["description"]["overall"] in ["PASS", "WARNING"]

    # H1 mismatch is WARNING, not BLOCKER
    h1_ok = h1_validation["passed"]

    if (
        results["title"]["overall"] == "PASS"
        and results["description"]["overall"] == "PASS"
        and h1_ok
    ):
        results["overall"] = "PASS"
    elif title_ok and desc_ok:
        if not h1_ok:
            results["overall"] = "WARNING"
            results["warnings"] = results.get("warnings", []) + [
                f"H1 validation: {h1_validation['message']}"
            ]
        else:
            results["overall"] = "WARNING"
    else:
        results["overall"] = "FAIL"

    return results


def find_all_meta_files(base_path: str = ".") -> list[tuple[str, str | None]]:
    """
    Find all meta files and their corresponding keywords files.

    Uses rglob to find nested categories (L2, L3).

    Returns:
        List of (meta_path, keywords_path) tuples
    """
    base = Path(base_path)
    results = []

    # Search in categories/ (RU) - including nested
    categories_path = base / "categories"
    if categories_path.exists():
        for meta_file in categories_path.rglob("*_meta.json"):
            # Skip if not in meta/ folder
            if meta_file.parent.name != "meta":
                continue
            slug = meta_file.stem.replace("_meta", "")
            data_dir = meta_file.parent.parent / "data"
            keywords_file = data_dir / f"{slug}_clean.json"
            if not keywords_file.exists():
                keywords_file = data_dir / f"{slug}.json"
            results.append((str(meta_file), str(keywords_file) if keywords_file.exists() else None))

    # Search in uk/categories/ (UK) - including nested
    uk_categories_path = base / "uk" / "categories"
    if uk_categories_path.exists():
        for meta_file in uk_categories_path.rglob("*_meta.json"):
            # Skip if not in meta/ folder
            if meta_file.parent.name != "meta":
                continue
            slug = meta_file.stem.replace("_meta", "")
            data_dir = meta_file.parent.parent / "data"
            keywords_file = data_dir / f"{slug}_clean.json"
            if not keywords_file.exists():
                keywords_file = data_dir / f"{slug}.json"
            results.append((str(meta_file), str(keywords_file) if keywords_file.exists() else None))

    return results


# =============================================================================
# CLI Output
# =============================================================================


def print_results(results: dict[str, Any]):
    """Print human-readable validation results."""
    print()
    print("=" * 60)
    print("META VALIDATION (v17.0)")
    print("=" * 60)
    print(f"File: {results['file']}")
    if results.get("keywords_file"):
        print(f"Keywords: {results['keywords_file']}")
    print()

    if results.get("errors"):
        for err in results["errors"]:
            print(f"❌ ERROR: {err}")
        print()
        return

    # Title
    title = results["title"]
    icon = "✅" if title["overall"] == "PASS" else ("⚠️" if title["overall"] == "WARNING" else "❌")
    print(f"{icon} TITLE: {title['overall']}")
    print(f"   Value: {title['value'][:60]}...")
    print(
        f"   Length: {title.get('length_without_brand', title['length'])} chars (target: {TITLE_MIN_LENGTH}-{TITLE_MAX_LENGTH})"
    )
    for check_name, check_data in title["checks"].items():
        check_icon = "✓" if check_data["passed"] else "✗"
        print(f"   {check_icon} {check_name}: {check_data['message']}")
    print()

    # Description
    desc = results["description"]
    icon = "✅" if desc["overall"] == "PASS" else ("⚠️" if desc["overall"] == "WARNING" else "❌")
    print(f"{icon} DESCRIPTION: {desc['overall']}")
    print(f"   Value: {desc['value'][:80]}...")
    print(f"   Length: {desc['length']} chars (target: {DESC_MIN_LENGTH}-{DESC_MAX_LENGTH})")
    for check_name, check_data in desc["checks"].items():
        check_icon = "✓" if check_data["passed"] else "✗"
        print(f"   {check_icon} {check_name}: {check_data['message']}")
    print()

    # H1
    if results.get("h1"):
        print(f"ℹ️  H1: {results['h1']['value']}")
    print()

    # Overall
    print("=" * 60)
    if results["overall"] == "PASS":
        print("✅ OVERALL: PASS")
    elif results["overall"] == "WARNING":
        print("⚠️  OVERALL: WARNING (minor issues)")
    else:
        print("❌ OVERALL: FAIL (blocking issues)")
    print("=" * 60)
    print()


def print_summary(all_results: list[dict[str, Any]]):
    """Print summary of all validations."""
    print()
    print("=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)

    passed = sum(1 for r in all_results if r["overall"] == "PASS")
    warnings = sum(1 for r in all_results if r["overall"] == "WARNING")
    failed = sum(1 for r in all_results if r["overall"] == "FAIL")

    print(f"Total files: {len(all_results)}")
    print(f"✅ PASS: {passed}")
    print(f"⚠️  WARNING: {warnings}")
    print(f"❌ FAIL: {failed}")
    print()

    if failed > 0:
        print("Failed files:")
        for r in all_results:
            if r["overall"] == "FAIL":
                print(f"  ❌ {r['file']}")
    print()


# =============================================================================
# Main
# =============================================================================


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    output_json = "--json" in sys.argv
    validate_all = "--all" in sys.argv

    # Parse --lang argument; precedence --lang > meta JSON "language" > path > ru
    # is applied in validate_meta_file (lang=None when --lang is absent)
    lang: str | None = None
    if "--lang" in sys.argv:
        idx = sys.argv.index("--lang")
        if idx + 1 < len(sys.argv):
            lang = sys.argv[idx + 1]
            if lang not in ("ru", "uk"):
                print(f"Invalid language: {lang}. Use 'ru' or 'uk'.")
                sys.exit(1)

    if validate_all:
        # Validate all meta files
        meta_files = find_all_meta_files()

        if not meta_files:
            print("No meta files found")
            sys.exit(1)

        all_results = []
        for meta_path, keywords_path in meta_files:
            results = validate_meta_file(meta_path, keywords_path, lang=lang)
            all_results.append(results)

            if not output_json:
                # Print short status
                icon = (
                    "✅"
                    if results["overall"] == "PASS"
                    else ("⚠️" if results["overall"] == "WARNING" else "❌")
                )
                print(f"{icon} {meta_path}")

        if output_json:
            print(json.dumps(all_results, ensure_ascii=False, indent=2))
        else:
            print_summary(all_results)

        # Exit code based on worst result
        if any(r["overall"] == "FAIL" for r in all_results):
            sys.exit(2)
        elif any(r["overall"] == "WARNING" for r in all_results):
            sys.exit(1)
        sys.exit(0)

    else:
        # Validate single file
        meta_path = sys.argv[1]

        keywords_path = None
        if "--keywords" in sys.argv:
            idx = sys.argv.index("--keywords")
            if idx + 1 < len(sys.argv):
                keywords_path = sys.argv[idx + 1]

        results = validate_meta_file(meta_path, keywords_path, lang=lang)

        if output_json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            print_results(results)

        if results["overall"] == "PASS":
            sys.exit(0)
        elif results["overall"] == "WARNING":
            sys.exit(1)
        sys.exit(2)


if __name__ == "__main__":
    main()
