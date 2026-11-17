#!/usr/bin/env python3
"""Анализ порядка ключей и нулевой частотности для создания ТЗ."""

import json
from datetime import datetime
from pathlib import Path

from llm_keywords_pipeline.core.config import PROJECT_ROOT

ROOT = PROJECT_ROOT
CATEGORIES_DIR = ROOT / "categories"
OUTPUT_FILE = ROOT / "tasks" / "active" / "KEYWORDS_CLEANUP_TZ.md"


def analyze_category(clean_file: Path) -> dict:
    """Анализирует категорию на проблемы с ключами."""
    data = json.loads(clean_file.read_text(encoding="utf-8"))
    slug = data.get("id", clean_file.stem.replace("_clean", ""))
    name = data.get("name", slug)

    result = {
        "slug": slug,
        "name": name,
        "file": str(clean_file.relative_to(ROOT)),
        "issues": [],
        "keywords_zero": [],
        "synonyms_zero": [],
        "keywords_order_wrong": False,
        "synonyms_order_wrong": False,
    }

    # Проверяем keywords
    keywords = data.get("keywords", [])
    if keywords:
        volumes = [k.get("volume", 0) for k in keywords]
        # Проверка на 0
        for kw in keywords:
            if kw.get("volume", 0) == 0:
                result["keywords_zero"].append(kw["keyword"])
        # Проверка порядка (должен быть по убыванию)
        if volumes != sorted(volumes, reverse=True):
            result["keywords_order_wrong"] = True

    # Проверяем synonyms
    synonyms = data.get("synonyms", [])
    if synonyms:
        # Разделяем на обычные и meta_only
        regular = [s for s in synonyms if s.get("use_in") != "meta_only"]
        [s for s in synonyms if s.get("use_in") == "meta_only"]

        # Проверка на 0 (только regular)
        for kw in regular:
            if kw.get("volume", 0) == 0:
                result["synonyms_zero"].append(kw["keyword"])

        # Проверка порядка regular синонимов
        if regular:
            volumes = [k.get("volume", 0) for k in regular]
            if volumes != sorted(volumes, reverse=True):
                result["synonyms_order_wrong"] = True

    # Формируем issues
    if result["keywords_zero"]:
        result["issues"].append(f"keywords с 0 volume: {len(result['keywords_zero'])}")
    if result["synonyms_zero"]:
        result["issues"].append(f"synonyms с 0 volume: {len(result['synonyms_zero'])}")
    if result["keywords_order_wrong"]:
        result["issues"].append("keywords не отсортированы по volume")
    if result["synonyms_order_wrong"]:
        result["issues"].append("synonyms не отсортированы по volume")

    return result


def generate_tz(results: list) -> str:
    """Генерирует ТЗ в формате Markdown."""
    # Фильтруем только категории с проблемами
    with_issues = [r for r in results if r["issues"]]

    lines = [
        "# ТЗ: Актуализация ключевых слов",
        "",
        f"**Дата создания:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "**Статус:** ⬜ В работе",
        "",
        "---",
        "",
        "## Описание задачи",
        "",
        "После обновления частотности из `key_all.csv` необходимо:",
        "1. **Удалить** ключи с нулевой частотностью (volume = 0)",
        "2. **Отсортировать** keywords по убыванию volume",
        "3. **Отсортировать** synonyms по убыванию volume (кроме meta_only)",
        "",
        "---",
        "",
        "## Статистика",
        "",
        f"- Всего категорий проанализировано: **{len(results)}**",
        f"- Категорий с проблемами: **{len(with_issues)}**",
        f"- Категорий без проблем: **{len(results) - len(with_issues)}**",
        "",
        "---",
        "",
        "## Чеклист по категориям",
        "",
    ]

    if not with_issues:
        lines.append("✅ Все категории в порядке!")
    else:
        for r in sorted(with_issues, key=lambda x: x["slug"]):
            lines.append(f"### ⬜ {r['name']} (`{r['slug']}`)")
            lines.append("")
            lines.append(f"**Файл:** `{r['file']}`")
            lines.append("")
            lines.append("**Проблемы:**")
            for issue in r["issues"]:
                lines.append(f"- {issue}")
            lines.append("")

            # Детали по нулевым ключам
            if r["keywords_zero"]:
                lines.append("**Keywords для удаления (volume=0):**")
                for kw in r["keywords_zero"]:
                    lines.append(f"- [ ] `{kw}`")
                lines.append("")

            if r["synonyms_zero"]:
                lines.append("**Synonyms для удаления (volume=0):**")
                for kw in r["synonyms_zero"]:
                    lines.append(f"- [ ] `{kw}`")
                lines.append("")

            # Чеклист действий
            lines.append("**Действия:**")
            if r["keywords_zero"]:
                lines.append("- [ ] Удалить keywords с volume=0")
            if r["synonyms_zero"]:
                lines.append("- [ ] Удалить synonyms с volume=0")
            if r["keywords_order_wrong"]:
                lines.append("- [ ] Отсортировать keywords по volume (desc)")
            if r["synonyms_order_wrong"]:
                lines.append("- [ ] Отсортировать synonyms по volume (desc)")
            lines.append("- [ ] Проверить результат")
            lines.append("")
            lines.append("---")
            lines.append("")

    return "\n".join(lines)


def main():
    print("🔍 Анализ ключевых слов во всех категориях...\n")

    results = []
    for clean_file in sorted(CATEGORIES_DIR.rglob("*_clean.json")):
        result = analyze_category(clean_file)
        results.append(result)
        if result["issues"]:
            print(f"⚠️  {result['slug']}: {', '.join(result['issues'])}")

    # Генерируем ТЗ
    tz_content = generate_tz(results)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(tz_content, encoding="utf-8")

    with_issues = [r for r in results if r["issues"]]
    print(f"\n✅ Проанализировано: {len(results)} категорий")
    print(f"⚠️  С проблемами: {len(with_issues)}")
    print(f"\n📄 ТЗ сохранено: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
