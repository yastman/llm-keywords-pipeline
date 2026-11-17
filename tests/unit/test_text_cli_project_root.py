"""Text-production CLIs must resolve the project root via core.config (audit B1, B19)."""

import importlib
import json

import pytest

from llm_keywords_pipeline.core import config

ROOT_ATTRS = [
    ("llm_keywords_pipeline.generate.sql", "PROJECT_DIR"),
    ("llm_keywords_pipeline.generate.all_meta", "PROJECT_ROOT"),
    ("llm_keywords_pipeline.batch.generate", "PROJECT_ROOT"),
    ("llm_keywords_pipeline.analyze.category", "PROJECT_ROOT"),
    ("llm_keywords_pipeline.analyze.meta", "ROOT"),
    ("llm_keywords_pipeline.analyze.order", "ROOT"),
    ("llm_keywords_pipeline.analyze.synonyms", "ROOT"),
    ("llm_keywords_pipeline.generate.checklists", "BASE_DIR"),
]


@pytest.mark.parametrize(("module_name", "attr"), ROOT_ATTRS)
def test_module_root_is_project_root(module_name, attr):
    module = importlib.import_module(module_name)
    root = getattr(module, attr)
    assert root == config.PROJECT_ROOT
    assert (root / "pyproject.toml").is_file()


def test_synonyms_counts_entity_dictionary(tmp_path, monkeypatch):
    from llm_keywords_pipeline.analyze import synonyms

    monkeypatch.setattr(synonyms, "ROOT", tmp_path)
    clean_file = tmp_path / "x_clean.json"
    clean_file.write_text(
        json.dumps(
            {
                "id": "x",
                "entity_dictionary": {
                    "brands": ["A", "B", "C"],
                    "terms": ["d", "e"],
                },
            }
        ),
        encoding="utf-8",
    )

    result = synonyms.analyze_category(clean_file)

    assert result["entities_count"] == 5
    assert not any(issue.startswith("entities:") for issue in result["issues"])


def test_synonyms_flags_short_entity_dictionary(tmp_path, monkeypatch):
    from llm_keywords_pipeline.analyze import synonyms

    monkeypatch.setattr(synonyms, "ROOT", tmp_path)
    clean_file = tmp_path / "x_clean.json"
    clean_file.write_text(
        json.dumps({"id": "x", "entity_dictionary": {"brands": ["A", "B"]}}),
        encoding="utf-8",
    )

    result = synonyms.analyze_category(clean_file)

    assert result["entities_count"] == 2
    assert "entities: 2 < 5" in result["issues"]
