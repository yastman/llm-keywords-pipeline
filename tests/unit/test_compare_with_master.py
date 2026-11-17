"""Tests for compare/with_master.py"""

from llm_keywords_pipeline.compare.with_master import load_categories_csv


def test_load_categories_csv_reads_utf8_bom(tmp_path):
    """CSV saved with a UTF-8 BOM must still expose the `keyword` header."""
    path = tmp_path / "cats.csv"
    path.write_bytes("keyword,volume\nKey  One,10\n".encode("utf-8-sig"))

    data = load_categories_csv(path)

    assert list(data) == ["key one"]
    assert data["key one"][0]["volume"] == 10


def test_load_categories_csv_groups_yo_apostrophe_variants(tmp_path):
    """'Пам’ять Ёлки' and 'пам'ять елки' land under one key; rows keep their form."""
    path = tmp_path / "cats.csv"
    path.write_text("keyword,volume\nПам’ять Ёлки,1\nпам'ять елки,2\n", encoding="utf-8")

    data = load_categories_csv(path)

    assert list(data) == ["пам'ять елки"]
    assert [r["keyword"] for r in data["пам'ять елки"]] == ["Пам’ять Ёлки", "пам'ять елки"]
