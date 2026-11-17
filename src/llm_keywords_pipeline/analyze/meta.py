#!/usr/bin/env python3
"""Анализ соответствия мета-тегов главным ключам после обновления частотности."""

import json
from datetime import datetime
from pathlib import Path

from llm_keywords_pipeline.core.clean_json import keyword_entries
from llm_keywords_pipeline.core.config import PROJECT_ROOT

ROOT = PROJECT_ROOT
CATEGORIES_DIR = ROOT / "categories"
OUTPUT_FILE = ROOT / "tasks" / "active" / "META_UPDATE_TZ.md"


def analyze_category(slug_dir: Path) -> dict | None:
    """Анализирует соответствие мета главному ключу."""
    clean_files = list(slug_dir.rglob("*_clean.json"))
    meta_files = list(slug_dir.rglob("*_meta.json"))

    if not clean_files or not meta_files:
        return None

    clean_file = clean_files[0]
    meta_file = meta_files[0]

    try:
        clean_data = json.loads(clean_file.read_text(encoding="utf-8"))
        meta_data = json.loads(meta_file.read_text(encoding="utf-8"))
    except Exception:
        return None

    slug = clean_data.get("id", "")
    name = clean_data.get("name", slug)
    keywords = keyword_entries(clean_data)

    if not keywords:
        return None

    # Главный ключ - первый (с наибольшим volume; в dict групп - первый в primary)
    main_kw = keywords[0]["keyword"]
    main_volume = keywords[0].get("volume", 0)

    # Мета данные (структура: meta.title, meta.description, h1)
    meta_block = meta_data.get("meta", {})
    title = meta_block.get("title", "") if isinstance(meta_block, dict) else ""
    description = meta_block.get("description", "") if isinstance(meta_block, dict) else ""
    h1 = meta_data.get("h1", "")

    # Проверяем наличие главного ключа в мета
    main_kw_lower = main_kw.lower()
    in_title = main_kw_lower in title.lower()
    in_desc = main_kw_lower in description.lower()
    in_h1 = main_kw_lower in h1.lower()

    # Собираем проблемы
    issues = []
    if not in_title:
        issues.append("главный ключ отсутствует в Title")
    if not in_desc:
        issues.append("главный ключ отсутствует в Description")
    if not in_h1:
        issues.append("главный ключ отсутствует в H1")

    return {
        "slug": slug,
        "name": name,
        "main_keyword": main_kw,
        "main_volume": main_volume,
        "keywords_top3": keywords[:3],
        "title": title,
        "description": description,
        "h1": h1,
        "in_title": in_title,
        "in_desc": in_desc,
        "in_h1": in_h1,
        "issues": issues,
        "clean_file": str(clean_file.relative_to(ROOT)),
        "meta_file": str(meta_file.relative_to(ROOT)),
    }


def generate_tz(results: list) -> str:
    """Генерирует ТЗ."""
    with_issues = [r for r in results if r and r["issues"]]
    ok_results = [r for r in results if r and not r["issues"]]

    lines = [
        "# ТЗ: Актуализация мета-тегов после обновления ключей",
        "",
        f"**Дата создания:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "**Статус:** ⬜ В работе",
        "",
        "---",
        "",
        "## Описание задачи",
        "",
        "После обновления частотности ключей изменился порядок keywords.",
        "Главный ключ (первый по volume) должен присутствовать в:",
        "- **Title** — обязательно",
        "- **Description** — обязательно",
        "- **H1** — рекомендуется (может быть вариация)",
        "",
        "---",
        "",
        "## Статистика",
        "",
        f"- Категорий проанализировано: **{len([r for r in results if r])}**",
        f"- Требуют проверки: **{len(with_issues)}**",
        f"- В порядке: **{len(ok_results)}**",
        "",
        "---",
        "",
    ]

    if with_issues:
        lines.append("## Категории для проверки")
        lines.append("")

        for r in sorted(with_issues, key=lambda x: x["main_volume"], reverse=True):
            status_title = "✅" if r["in_title"] else "❌"
            status_desc = "✅" if r["in_desc"] else "❌"
            status_h1 = "✅" if r["in_h1"] else "❌"

            lines.append(f"### ⬜ {r['name']} (`{r['slug']}`)")
            lines.append("")
            lines.append(f"**Главный ключ:** `{r['main_keyword']}` (volume: {r['main_volume']})")
            lines.append("")
            lines.append("**ТОП-3 ключа:**")
            for i, kw in enumerate(r["keywords_top3"], 1):
                lines.append(f"{i}. `{kw['keyword']}` — {kw.get('volume', 0)}")
            lines.append("")
            lines.append("**Текущие мета:**")
            lines.append(f"- Title: `{r['title']}`")
            lines.append(
                f"- Description: `{r['description'][:100]}...`"
                if len(r["description"]) > 100
                else f"- Description: `{r['description']}`"
            )
            lines.append(f"- H1: `{r['h1']}`")
            lines.append("")
            lines.append(f"**Статус:** Title {status_title} | Desc {status_desc} | H1 {status_h1}")
            lines.append("")
            lines.append("**Проблемы:**")
            for issue in r["issues"]:
                lines.append(f"- {issue}")
            lines.append("")
            lines.append("**Действия:**")
            lines.append(f"- [ ] Проверить/обновить мета с учётом ключа `{r['main_keyword']}`")
            lines.append(f"- [ ] Файл: `{r['meta_file']}`")
            lines.append("")
            lines.append("---")
            lines.append("")

    # Категории в порядке
    if ok_results:
        lines.append("## Категории в порядке (главный ключ присутствует)")
        lines.append("")
        for r in sorted(ok_results, key=lambda x: x["slug"]):
            lines.append(f"- ✅ {r['name']} (`{r['slug']}`) — `{r['main_keyword']}`")
        lines.append("")

    return "\n".join(lines)


def main():
    print("🔍 Анализ соответствия мета-тегов главным ключам...\n")

    results = []

    # Проходим по всем категориям
    for item in sorted(CATEGORIES_DIR.iterdir()):
        if item.is_dir():
            result = analyze_category(item)
            if result:
                results.append(result)
                if result["issues"]:
                    print(f"⚠️  {result['slug']}: {', '.join(result['issues'])}")

    # Генерируем ТЗ
    tz_content = generate_tz(results)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(tz_content, encoding="utf-8")

    with_issues = [r for r in results if r and r["issues"]]
    print(f"\n✅ Проанализировано: {len([r for r in results if r])} категорий")
    print(f"⚠️  Требуют проверки: {len(with_issues)}")
    print(f"\n📄 ТЗ сохранено: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
