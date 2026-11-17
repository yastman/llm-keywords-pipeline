#!/usr/bin/env python3
"""
Batch generate meta tags for all categories.
Formula: {ВЧ Ключ} — купить, цены | {brand}; brand from <data root>/project.toml
[project] brand, none = no suffix. Description: [meta] description_template.<lang>
of project.toml ({keyword}, {name}, {types}, {brand}), else "{name}. {types}." plus a
neutral filler up to 100 chars. Types skip [meta] type_skip_brands of project.toml.

Usage:
    uv run python -m llm_keywords_pipeline.generate.all_meta [--dry-run] [--force] [--lang ru|uk]

Options:
    --dry-run   Show what would be generated without writing files
    --force     Regenerate ALL meta files, even existing ones
    --lang      Language: ru (default) or uk
"""

import json
import sys
from datetime import date
from pathlib import Path

from llm_keywords_pipeline.core.clean_json import keyword_entries
from llm_keywords_pipeline.core.config import PROJECT_ROOT, QUALITY_THRESHOLDS
from llm_keywords_pipeline.core.project import load_project

DESC_MIN_LENGTH = int(QUALITY_THRESHOLDS["description_min"])
DESC_MAX_LENGTH = int(QUALITY_THRESHOLDS["description_max"])

# Neutral sentences added, in order, to a description shorter than DESC_MIN_LENGTH.
DESCRIPTION_FILLER = {
    "ru": [
        "Цены, наличие и характеристики товаров — в каталоге.",
        "Подберите подходящий вариант по описанию и параметрам.",
    ],
    "uk": [
        "Ціни, наявність і характеристики товарів — у каталозі.",
        "Оберіть відповідний варіант за описом і параметрами.",
    ],
}


def load_json(filepath: Path, silent: bool = False) -> dict | None:
    """Load JSON file safely."""
    try:
        with open(filepath, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        if not silent:
            print(f"  ⚠️ File not found: {filepath.name}")
        return None
    except json.JSONDecodeError as e:
        print(f"  ❌ JSON error in {filepath.name}: {e}")
        return None


def save_json(filepath: Path, data: dict) -> bool:
    """Save JSON file with pretty formatting."""
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")  # trailing newline
        return True
    except Exception as e:
        print(f"  ❌ Error saving {filepath}: {e}")
        return False


def get_primary_keyword(data: dict) -> str:
    """Get highest volume keyword from _clean.json (first of primary in a dict of groups)."""
    keywords = keyword_entries(data)
    if not keywords:
        return data.get("name", "Unknown")
    return keywords[0].get("keyword", data.get("name", "Unknown"))


def get_types_from_entities(data: dict) -> list[str]:
    """Extract product types from entities (max 3, skip brands)."""
    # entity_dictionary: {group: [terms]}; old files keep a flat "entities" list.
    entity_dictionary = data.get("entity_dictionary") or {}
    entities = [term for terms in entity_dictionary.values() for term in terms] or data.get(
        "entities", []
    )
    types = []
    brands = load_project(PROJECT_ROOT).meta_type_skip_brands
    for entity in entities:
        if any(brand in entity.lower() for brand in brands):
            continue
        if any(char.isdigit() for char in entity):
            continue
        types.append(entity)
    return types[:3]


def build_title(primary_kw: str, buy: str, buy_short: str) -> str:
    """{kw} — {buy} | {brand}, shortened to fit 60 chars; no brand = no suffix."""
    brand = load_project(PROJECT_ROOT).brand
    suffix = f" | {brand}" if brand else ""
    title = f"{primary_kw} — {buy}{suffix}"
    if len(title) > 60:
        title = f"{primary_kw} — {buy_short}{suffix}"
    if len(title) > 60:
        title = f"{primary_kw[:40]}...{suffix}"
    return title


def capitalize_first(text: str) -> str:
    """Capitalize first letter only."""
    return text[0].upper() + text[1:] if text else text


def build_description(lang: str, primary_kw: str, name: str, types: list[str]) -> str:
    """[meta] description_template of project.toml, else name, types and a neutral filler."""
    project = load_project(PROJECT_ROOT)
    types_str = capitalize_first(", ".join(types))
    template = project.description_template.get(lang)
    if template:
        description = template.format(
            keyword=primary_kw, name=name, types=types_str, brand=project.brand
        ).strip()
    else:
        description = f"{name}. {types_str}." if types_str else f"{name}."
        for sentence in DESCRIPTION_FILLER[lang]:
            if len(description) >= DESC_MIN_LENGTH:
                break
            description = f"{description} {sentence}"
    if len(description) > DESC_MAX_LENGTH:
        description = description[: DESC_MAX_LENGTH - 3] + "..."
    return description


def generate_meta_ru(slug: str, data: dict) -> dict:
    """Generate Russian meta tags following Front-Loading principle."""
    primary_kw = capitalize_first(get_primary_keyword(data))
    name = capitalize_first(data.get("name", slug))
    types = get_types_from_entities(data)

    title = build_title(primary_kw, "купить, цены", "купить")

    # H1: Primary keyword
    h1 = primary_kw

    description = build_description("ru", primary_kw, name, types)

    return {
        "slug": slug,
        "language": "ru",
        "meta": {"title": title, "description": description},
        "h1": h1,
        "status": "generated",
        "updated_at": str(date.today()),
    }


def generate_meta_uk(slug: str, data: dict) -> dict:
    """Generate Ukrainian meta tags following Front-Loading principle."""
    primary_kw = capitalize_first(get_primary_keyword(data))
    name = capitalize_first(data.get("name", slug))
    types = get_types_from_entities(data)

    title = build_title(primary_kw, "купити, ціни", "купити")

    h1 = primary_kw

    description = build_description("uk", primary_kw, name, types)

    return {
        "slug": slug,
        "language": "uk",
        "meta": {"title": title, "description": description},
        "h1": h1,
        "status": "generated",
        "updated_at": str(date.today()),
    }


def process_categories(
    lang: str = "ru", dry_run: bool = False, force: bool = False
) -> tuple[int, int, int]:
    """Process all categories for given language."""
    categories_dir = PROJECT_ROOT / ("categories" if lang == "ru" else "uk/categories")
    meta_generator = generate_meta_ru if lang == "ru" else generate_meta_uk

    if not categories_dir.exists():
        print(f"❌ Directory not found: {categories_dir}")
        return 0, 0, 0

    generated, skipped, preserved = 0, 0, 0

    for category_dir in sorted(categories_dir.iterdir()):
        if not category_dir.is_dir():
            continue

        slug = category_dir.name
        data_file = category_dir / "data" / f"{slug}_clean.json"
        meta_file = category_dir / "meta" / f"{slug}_meta.json"

        data = load_json(data_file, silent=True)
        if not data:
            print(f"  ⚠️ {slug}: No _clean.json, skipping")
            skipped += 1
            continue

        existing_meta = load_json(meta_file, silent=True)

        # Skip existing unless --force
        if meta_file.exists() and not force:
            print(f"  ℹ️ {slug}: Preserved (existing meta)")
            preserved += 1
            continue

        meta = meta_generator(slug, data)

        if dry_run:
            action = "Would regenerate" if existing_meta else "Would generate"
            print(f"  📝 {slug}: {action}")
            print(f"      Title: {meta['meta']['title']}")
        else:
            if save_json(meta_file, meta):
                action = "Regenerated" if existing_meta else "Generated"
                print(f"  ✅ {slug}: {action}")
                generated += 1
            else:
                skipped += 1

    return generated, skipped, preserved


def main():
    dry_run = "--dry-run" in sys.argv
    force = "--force" in sys.argv
    lang = "ru"

    for arg in sys.argv[1:]:
        if arg.startswith("--lang="):
            lang = arg.split("=")[1]
        elif arg in ["ru", "uk"]:
            lang = arg

    print(f"\n{'=' * 60}")
    print(f"Meta Generation for {lang.upper()} categories")
    print(f"{'=' * 60}")
    flags = []
    if dry_run:
        flags.append("DRY RUN")
    if force:
        flags.append("FORCE")
    if flags:
        print(f"Flags: {', '.join(flags)}\n")
    else:
        print("")

    generated, skipped, preserved = process_categories(lang=lang, dry_run=dry_run, force=force)

    print(f"\n{'=' * 60}")
    print(f"Results: Generated {generated}, Preserved {preserved}, Skipped {skipped}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
