#!/usr/bin/env python3
"""Исправление порядка ключей и удаление нулевой частотности."""

import json
from pathlib import Path

from llm_keywords_pipeline.core.clean_json import keyword_groups, set_keyword_groups
from llm_keywords_pipeline.core.config import PROJECT_ROOT

ROOT = PROJECT_ROOT
CATEGORIES_DIR = ROOT / "categories"


def fix_category(clean_file: Path) -> dict:
    """Исправляет категорию. Возвращает статистику изменений."""
    data = json.loads(clean_file.read_text(encoding="utf-8"))
    slug = data.get("id", clean_file.stem.replace("_clean", ""))

    stats = {
        "slug": slug,
        "keywords_removed": 0,
        "synonyms_removed": 0,
        "keywords_sorted": False,
        "synonyms_sorted": False,
    }

    changed = False

    # Исправляем keywords: каждая группа отдельно (плоский список - одна группа)
    groups = keyword_groups(data)
    for group, keywords in groups.items():
        # Удаляем с volume=0
        original_len = len(keywords)
        keywords = [k for k in keywords if k.get("volume", 0) > 0]
        stats["keywords_removed"] += original_len - len(keywords)

        # Сортируем по volume desc
        sorted_kw = sorted(keywords, key=lambda x: x.get("volume", 0), reverse=True)
        if keywords != sorted_kw:
            stats["keywords_sorted"] = True
        groups[group] = sorted_kw

    if stats["keywords_removed"] > 0 or stats["keywords_sorted"]:
        set_keyword_groups(data, groups)
        changed = True

    # Исправляем synonyms
    synonyms = data.get("synonyms", [])
    if synonyms:
        # Разделяем на regular и meta_only
        regular = [s for s in synonyms if s.get("use_in") != "meta_only"]
        meta_only = [s for s in synonyms if s.get("use_in") == "meta_only"]

        # Удаляем regular с volume=0
        original_len = len(regular)
        regular = [s for s in regular if s.get("volume", 0) > 0]
        stats["synonyms_removed"] = original_len - len(regular)

        # Сортируем regular по volume desc
        sorted_reg = sorted(regular, key=lambda x: x.get("volume", 0), reverse=True)
        if regular != sorted_reg:
            stats["synonyms_sorted"] = True
            regular = sorted_reg

        # Сортируем meta_only по volume desc
        meta_only = sorted(meta_only, key=lambda x: x.get("volume", 0), reverse=True)

        if stats["synonyms_removed"] > 0 or stats["synonyms_sorted"]:
            data["synonyms"] = regular + meta_only
            changed = True

    # Сохраняем если были изменения
    if changed:
        clean_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    return stats


def main():
    print("🔧 Исправление ключевых слов...\n")

    total_kw_removed = 0
    total_syn_removed = 0
    total_kw_sorted = 0
    total_syn_sorted = 0
    files_changed = 0

    for clean_file in sorted(CATEGORIES_DIR.rglob("*_clean.json")):
        stats = fix_category(clean_file)

        has_changes = (
            stats["keywords_removed"] > 0
            or stats["synonyms_removed"] > 0
            or stats["keywords_sorted"]
            or stats["synonyms_sorted"]
        )

        if has_changes:
            files_changed += 1
            changes = []
            if stats["keywords_removed"]:
                changes.append(f"-{stats['keywords_removed']} kw")
                total_kw_removed += stats["keywords_removed"]
            if stats["synonyms_removed"]:
                changes.append(f"-{stats['synonyms_removed']} syn")
                total_syn_removed += stats["synonyms_removed"]
            if stats["keywords_sorted"]:
                changes.append("sorted kw")
                total_kw_sorted += 1
            if stats["synonyms_sorted"]:
                changes.append("sorted syn")
                total_syn_sorted += 1

            print(f"✅ {stats['slug']}: {', '.join(changes)}")

    print(f"\n{'=' * 50}")
    print(f"✅ Файлов изменено: {files_changed}")
    print(f"✅ Keywords удалено: {total_kw_removed}")
    print(f"✅ Synonyms удалено: {total_syn_removed}")
    print(f"✅ Keywords отсортировано: {total_kw_sorted} категорий")
    print(f"✅ Synonyms отсортировано: {total_syn_sorted} категорий")


if __name__ == "__main__":
    main()
