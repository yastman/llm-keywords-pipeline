#!/usr/bin/env python3
"""
Generate SQL for plural meta update.
"""

import json
from pathlib import Path

from llm_keywords_pipeline.generate.sql import escape_sql


def generate_plural_sql(
    mapping_file: Path = Path("data/opencart_mapping.json"),
    output_file: Path = Path("data/generated/plural_meta_update.sql"),
) -> list[str]:
    """Generate SQL statements for plural meta updates."""
    with open(mapping_file) as f:
        mapping = json.load(f)
    slug_to_id = mapping.get("slug_to_id", {})

    with open("data/generated/plural_manual_uk.json") as f:
        json.load(f)
    with open("data/generated/plural_manual_ru.json") as f:
        plural_ru = json.load(f)

    sql_lines = []

    # UK (language_id=1) - from local meta files
    for meta_file in sorted(Path("uk/categories").glob("*/meta/*_meta.json")):
        slug = meta_file.parent.parent.name
        cat_id = slug_to_id.get(slug)
        if not cat_id:
            continue

        with open(meta_file) as f:
            meta = json.load(f)

        h1 = escape_sql(meta.get("h1", ""))
        # Nested {"meta": {"title"}} or top-level {"title"} (prompts/produce.md).
        meta_block = meta["meta"] if isinstance(meta.get("meta"), dict) else meta
        title = escape_sql(meta_block.get("title", ""))

        sql_lines.append(
            f"UPDATE oc_category_description SET meta_h1='{h1}', meta_title='{title}' WHERE category_id={int(cat_id)} AND language_id=1;"
        )

    # RU (language_id=3) - from plural mapping directly
    for slug, new_h1 in plural_ru.items():
        cat_id = slug_to_id.get(slug)
        if not cat_id:
            continue

        h1_escaped = escape_sql(new_h1)
        title = escape_sql(f"{new_h1} — купить, цены | Ultimate")

        sql_lines.append(
            f"UPDATE oc_category_description SET meta_h1='{h1_escaped}', meta_title='{title}' WHERE category_id={int(cat_id)} AND language_id=3;"
        )

    output_file.write_text("\n".join(sql_lines) + "\n")
    return sql_lines


if __name__ == "__main__":
    sql_lines = generate_plural_sql()
    print(f"Generated {len(sql_lines)} SQL statements")
