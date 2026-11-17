import json
import re

from llm_keywords_pipeline.core.config import CATEGORIES_DIR
from llm_keywords_pipeline.core.project import get_project


def check_category(slug: str) -> dict:
    json_path = CATEGORIES_DIR / slug / "data" / f"{slug}_clean.json"

    if not json_path.exists():
        return {"slug": slug, "status": "MISSING_JSON"}

    try:
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return {"slug": slug, "status": f"ERROR: {str(e)}"}

    cat_type = data.get("type", "L3")  # Default to L3 if not specified
    # parent = data.get("parent", {})
    keywords = []
    for cat in ["primary", "secondary", "supporting", "commercial"]:
        keywords.extend([k["keyword"] for k in data.get("keywords", {}).get(cat, [])])

    issues = []

    # Check 1: patterns that should not be in an L2 category,
    # [structure.l2_forbidden] <slug> = [regex] of <data root>/project.toml; none by default
    forbidden = get_project().l2_forbidden.get(slug, ()) if cat_type == "L2" else ()
    for kw in keywords:
        for pattern in forbidden:
            if re.search(pattern, kw.lower()):
                issues.append(f"L2 Forbidden: '{kw}' matches '{pattern}'")

    # Check 2: Empty categories
    if not keywords and cat_type != "Hub":  # Some hubs might be empty?
        issues.append("Empty category (0 keywords)")

    return {
        "slug": slug,
        "status": "OK" if not issues else "ISSUES",
        "type": cat_type,
        "kw_count": len(keywords),
        "issues": issues,
    }


def main():
    print(f"{'CATEGORY':<35} | {'TYPE':<5} | {'COUNT':<5} | {'STATUS'}")
    print("-" * 70)

    results = []
    for d in sorted(CATEGORIES_DIR.iterdir()):
        if d.is_dir():
            res = check_category(d.name)
            results.append(res)

            status_color = "[OK]" if res["status"] == "OK" else "[X]"
            if res["status"] == "MISSING_JSON":
                status_color = "[?]"

            print(
                f"{d.name:<35} | {res.get('type', '?'):<5} | {res.get('kw_count', 0):<5} | {status_color} {res['status']}"
            )

            if res.get("issues"):
                for issue in res["issues"]:
                    print(f"   (!)  {issue}")

    print("-" * 70)
    print(f"Total Categories: {len(results)}")


if __name__ == "__main__":
    main()
