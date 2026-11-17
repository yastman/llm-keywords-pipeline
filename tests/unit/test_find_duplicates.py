"""Tests for fix/find_duplicates.py keyword comparison."""

from llm_keywords_pipeline.fix import find_duplicates as fd


def _categories(monkeypatch, data_by_slug):
    monkeypatch.setattr(fd, "load_category_keywords", lambda slug: data_by_slug.get(slug, {}))


def test_exact_duplicates_match_case_yo_apostrophe_variants(monkeypatch):
    """'Пам’ять Ёлки' in one category and 'пам'ять елки' in another are one duplicate."""
    _categories(
        monkeypatch,
        {
            "a": {"keywords": {"primary": [{"keyword": "Пам’ять Ёлки", "volume": 10}]}},
            "b": {"keywords": {"secondary": [{"keyword": "пам'ять елки", "volume": 5}]}},
        },
    )

    duplicates = fd.find_exact_duplicates(["a", "b"])

    assert duplicates == {"Пам’ять Ёлки": [("a", "primary", 10), ("b", "secondary", 5)]}


def test_hierarchy_conflict_matches_variants_and_keeps_child_form(monkeypatch):
    _categories(
        monkeypatch,
        {
            "parent": {"keywords": {"primary": [{"keyword": "ёлка", "volume": 1}]}},
            "child": {"keywords": {"primary": [{"keyword": "Елка", "volume": 2}]}},
        },
    )
    monkeypatch.setattr(fd, "HIERARCHY", {"parent": ["child"]})

    conflicts = fd.find_hierarchy_conflicts()

    assert [c["keyword"] for c in conflicts] == ["Елка"]
