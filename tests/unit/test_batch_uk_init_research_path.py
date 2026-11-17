"""batch.uk_init points CONTEXT.md at the README research layout."""

import json

from llm_keywords_pipeline.batch.uk_init import process_category


def test_context_points_to_category_research_data(tmp_path, monkeypatch):
    ru_meta_path = "categories/aksessuary/meta/aksessuary_meta.json"
    ru_meta = tmp_path / ru_meta_path
    ru_meta.parent.mkdir(parents=True)
    ru_meta.write_text(
        json.dumps(
            {"h1": "Аксессуары", "meta": {"title": "Аксессуары", "description": "Аксессуары"}}
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    result = process_category("aksessuary", ru_meta_path)

    context = (tmp_path / result["context_created"]).read_text(encoding="utf-8")
    assert "See: categories/aksessuary/research/RESEARCH_DATA.md" in context
