#!/usr/bin/env python3
"""Извлечение всех ключей из _clean.json категорий."""

import csv
import json
from pathlib import Path

from llm_keywords_pipeline.core.clean_json import FLAT_GROUP, keyword_groups
from llm_keywords_pipeline.core.config import PROJECT_ROOT

ROOT = PROJECT_ROOT
CATEGORIES_DIR = ROOT / "categories"
OUTPUT_FILE = ROOT / "data" / "generated" / "all_from_categories.csv"


def extract_from_file(clean_file: Path) -> list[dict]:
    """Извлекает все ключи из одного _clean.json файла."""
    rows = []
    try:
        data = json.loads(clean_file.read_text(encoding="utf-8"))
        category = data.get("id", clean_file.stem.replace("_clean", ""))

        synonyms_data = data.get("synonyms", [])

        # Keywords: dict of groups {"primary": [...], "synonyms_base": [...], ...} or flat list
        for group_name, items in keyword_groups(data).items():
            for kw in items:
                # primary and a flat list are keywords; every other group is synonyms
                source_type = "keyword" if group_name in ("primary", FLAT_GROUP) else "synonym"

                rows.append(
                    {
                        "keyword": kw["keyword"],
                        "volume": kw.get("volume", 0),
                        "category": category,
                        "source_type": source_type,
                    }
                )

        # Synonyms (a dict of groups may also keep synonyms inside keywords)
        if isinstance(synonyms_data, list):
            for syn in synonyms_data:
                rows.append(
                    {
                        "keyword": syn["keyword"],
                        "volume": syn.get("volume", 0),
                        "category": category,
                        "source_type": "synonym",
                    }
                )

        # Variations
        for var in data.get("variations", []):
            rows.append(
                {
                    "keyword": var["keyword"],
                    "volume": var.get("volume", 0),
                    "category": category,
                    "source_type": "variation",
                }
            )

    except Exception as e:
        print(f"⚠️  {clean_file.name}: {e}")

    return rows


def main():
    all_rows = []

    for clean_file in sorted(CATEGORIES_DIR.rglob("*_clean.json")):
        rows = extract_from_file(clean_file)
        all_rows.extend(rows)
        if not rows:
            print(f"⚠️  {clean_file.name}: пустой файл")

    # Save CSV
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["keyword", "volume", "category", "source_type"])
        writer.writeheader()
        writer.writerows(all_rows)

    # Stats
    keywords_count = sum(1 for r in all_rows if r["source_type"] == "keyword")
    synonyms_count = sum(1 for r in all_rows if r["source_type"] == "synonym")
    variations_count = sum(1 for r in all_rows if r["source_type"] == "variation")
    categories_count = len(set(r["category"] for r in all_rows))

    print(f"✅ Извлечено {len(all_rows)} записей → {OUTPUT_FILE}")
    print(
        f"   keywords: {keywords_count}, synonyms: {synonyms_count}, variations: {variations_count}"
    )
    print(f"   категорий: {categories_count}")


if __name__ == "__main__":
    main()
