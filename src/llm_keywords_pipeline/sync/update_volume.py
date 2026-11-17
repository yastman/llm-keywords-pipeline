#!/usr/bin/env python3
"""Обновление частотности keywords из CSV файла."""

import csv
import json
from pathlib import Path

from llm_keywords_pipeline.core.config import PROJECT_ROOT

ROOT = PROJECT_ROOT
CSV_FILE = ROOT / "key_all.csv"
CATEGORIES_DIR = ROOT / "categories"


def load_csv_volumes() -> dict:
    """Загружает keyword -> volume из CSV."""
    volumes = {}
    with open(CSV_FILE, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            keyword = row["Ключевое слово"].strip().strip('"')
            volume = int(row["Показов в месяц"])
            volumes[keyword] = volume
    return volumes


def update_category(clean_file: Path, volumes: dict) -> tuple[int, int]:
    """Обновляет volume в _clean.json. Возвращает (обновлено, всего)."""
    data = json.loads(clean_file.read_text(encoding="utf-8"))
    updated = 0
    total = 0

    # Обновляем keywords: плоский список или dict групп (primary/secondary/...)
    keywords = data.get("keywords", [])
    if isinstance(keywords, dict):
        keywords = [kw for group in keywords.values() for kw in group]
    for kw in keywords:
        total += 1
        keyword = kw["keyword"]
        if keyword in volumes:
            old_vol = kw.get("volume", 0)
            new_vol = volumes[keyword]
            if old_vol != new_vol:
                kw["volume"] = new_vol
                updated += 1

    # Обновляем synonyms
    for kw in data.get("synonyms", []):
        total += 1
        keyword = kw["keyword"]
        if keyword in volumes:
            old_vol = kw.get("volume", 0)
            new_vol = volumes[keyword]
            if old_vol != new_vol:
                kw["volume"] = new_vol
                updated += 1

    if updated > 0:
        clean_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    return updated, total


def main():
    print("📊 Обновление частотности из key_all.csv...\n")

    volumes = load_csv_volumes()
    print(f"✅ Загружено {len(volumes)} ключей из CSV\n")

    total_updated = 0
    total_keywords = 0
    files_updated = 0

    for clean_file in sorted(CATEGORIES_DIR.rglob("*_clean.json")):
        updated, total = update_category(clean_file, volumes)
        total_updated += updated
        total_keywords += total
        if updated > 0:
            files_updated += 1
            slug = clean_file.stem.replace("_clean", "")
            print(f"  {slug}: {updated} обновлено")

    print(f"\n✅ Итого: {total_updated} из {total_keywords} ключей обновлено")
    print(f"✅ Файлов изменено: {files_updated}")


if __name__ == "__main__":
    main()
