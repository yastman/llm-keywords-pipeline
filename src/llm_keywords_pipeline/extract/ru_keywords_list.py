#!/usr/bin/env python3
"""Извлечение всех ключей из RU категорий в MD файл."""

import json
from pathlib import Path

from llm_keywords_pipeline.core.clean_json import keyword_entries
from llm_keywords_pipeline.core.config import PROJECT_ROOT
from llm_keywords_pipeline.core.coverage import keyword_key

ROOT = PROJECT_ROOT
CATEGORIES_DIR = ROOT / "categories"
OUTPUT_FILE = ROOT / "data" / "generated" / "RU_KEYWORDS.md"


def extract_keywords_from_file(filepath: Path) -> dict[str, str]:
    """Извлекает все ключи из _clean.json файла.

    Возвращает {keyword_key: исходная форма}; из вариантов одного ключа
    остаётся первый.
    """
    keywords: dict[str, str] = {}

    try:
        data = json.loads(filepath.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"⚠️  {filepath.name}: {e}")
        return keywords

    synonyms_data = data.get("synonyms", [])
    variations_data = data.get("variations", [])

    # Keywords: dict of groups or flat list
    for item in keyword_entries(data):
        if "keyword" in item:
            keywords.setdefault(keyword_key(item["keyword"]), item["keyword"].strip())

    # Synonyms
    if isinstance(synonyms_data, list):
        for item in synonyms_data:
            if "keyword" in item:
                keywords.setdefault(keyword_key(item["keyword"]), item["keyword"].strip())

    # Variations
    if isinstance(variations_data, list):
        for item in variations_data:
            if "keyword" in item:
                keywords.setdefault(keyword_key(item["keyword"]), item["keyword"].strip())

    return keywords


def main():
    all_keywords: dict[str, str] = {}
    files_count = 0

    for clean_file in sorted(CATEGORIES_DIR.rglob("*_clean.json")):
        keywords = extract_keywords_from_file(clean_file)
        for key, keyword in keywords.items():
            all_keywords.setdefault(key, keyword)
        files_count += 1

    # Sort and save
    sorted_keywords = sorted(all_keywords.values())

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text("\n".join(sorted_keywords), encoding="utf-8")

    print(f"Найдено {files_count} файлов _clean.json")
    print(f"Извлечено {len(sorted_keywords)} уникальных ключей")
    print(f"✅ Сохранено → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
