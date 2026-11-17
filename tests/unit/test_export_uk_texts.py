"""extract.export_uk_texts: slug order from the structure CSV, else the uk category folders."""

from llm_keywords_pipeline.extract import export_uk_texts


def _uk_dirs(root, *slugs):
    uk_dir = root / "uk" / "categories"
    for slug in slugs:
        (uk_dir / slug).mkdir(parents=True)
    return uk_dir


def test_unset_semantics_csv_falls_back_to_uk_folders(tmp_path, monkeypatch):
    monkeypatch.setattr(export_uk_texts, "SEMANTICS_CSV", None)
    monkeypatch.setattr(
        export_uk_texts, "UK_CATEGORIES_DIR", _uk_dirs(tmp_path, "b-slug", "a-slug")
    )

    assert export_uk_texts.get_slugs_in_order() == ["a-slug", "b-slug"]


def test_semantics_csv_sets_slug_order(tmp_path, monkeypatch):
    csv_path = tmp_path / "structure.csv"
    csv_path.write_text("L3: b-slug,,\nkw,,1\nL3: a-slug,,\n", encoding="utf-8")
    monkeypatch.setattr(export_uk_texts, "SEMANTICS_CSV", csv_path)
    monkeypatch.setattr(
        export_uk_texts, "UK_CATEGORIES_DIR", _uk_dirs(tmp_path, "a-slug", "b-slug")
    )

    assert export_uk_texts.get_slugs_in_order() == ["b-slug", "a-slug"]
