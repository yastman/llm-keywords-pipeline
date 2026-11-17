#!/usr/bin/env python3
"""
Generate SQL for plural meta update.

Reads and writes under the data root (core.config.PROJECT_ROOT). Table and language ids
come from [opencart] of its project.toml: `table_prefix`, `language_ids.uk` and
`language_ids.ru`; unset stops the command.
"""

import json
from pathlib import Path

from llm_keywords_pipeline.core.config import PROJECT_ROOT
from llm_keywords_pipeline.core.project import load_project
from llm_keywords_pipeline.generate.sql import escape_sql, opencart_target


def generate_plural_sql(
    mapping_file: Path | None = None,
    output_file: Path | None = None,
) -> list[str]:
    """Generate SQL statements for plural meta updates."""
    root = PROJECT_ROOT
    generated = root / "data" / "generated"
    uk_table, uk_language_id = opencart_target(root, "uk")
    ru_table, ru_language_id = opencart_target(root, "ru")

    with open(mapping_file or root / "data" / "opencart_mapping.json") as f:
        mapping = json.load(f)
    slug_to_id = mapping.get("slug_to_id", {})

    with open(generated / "plural_manual_uk.json") as f:
        json.load(f)
    with open(generated / "plural_manual_ru.json") as f:
        plural_ru = json.load(f)

    brand = load_project(root).brand
    suffix = f" | {brand}" if brand else ""
    sql_lines = []

    # UK - from local meta files
    for meta_file in sorted((root / "uk" / "categories").glob("*/meta/*_meta.json")):
        slug = meta_file.parent.parent.name
        cat_id = slug_to_id.get(slug)
        if not cat_id:
            continue

        with open(meta_file) as f:
            meta = json.load(f)

        h1 = escape_sql(meta.get("h1", ""))
        # Nested {"meta": {"title"}} (the shape validate.meta reads) or top-level {"title"}.
        meta_block = meta["meta"] if isinstance(meta.get("meta"), dict) else meta
        title = escape_sql(meta_block.get("title", ""))

        sql_lines.append(
            f"UPDATE {uk_table} SET meta_h1='{h1}', meta_title='{title}' "
            f"WHERE category_id={int(cat_id)} AND language_id={uk_language_id};"
        )

    # RU - from plural mapping directly
    for slug, new_h1 in plural_ru.items():
        cat_id = slug_to_id.get(slug)
        if not cat_id:
            continue

        h1_escaped = escape_sql(new_h1)
        title = escape_sql(f"{new_h1} — купить, цены{suffix}")

        sql_lines.append(
            f"UPDATE {ru_table} SET meta_h1='{h1_escaped}', meta_title='{title}' "
            f"WHERE category_id={int(cat_id)} AND language_id={ru_language_id};"
        )

    (output_file or generated / "plural_meta_update.sql").write_text("\n".join(sql_lines) + "\n")
    return sql_lines


if __name__ == "__main__":
    sql_lines = generate_plural_sql()
    print(f"Generated {len(sql_lines)} SQL statements")
