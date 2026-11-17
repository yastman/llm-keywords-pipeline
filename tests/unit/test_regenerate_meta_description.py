"""regenerate_meta.generate_description must stay within 160 chars (audit B22)."""

from llm_keywords_pipeline.generate import regenerate_meta

SUFFIX = "Опт и розница."


def test_long_description_capped_at_160(monkeypatch):
    monkeypatch.setattr(
        regenerate_meta,
        "extract_product_info",
        lambda slug: {"types": [], "forms": [], "volumes": []},
    )
    desc = regenerate_meta.generate_description("а" * 200, "any-slug")
    assert len(desc) <= 160
    assert desc.endswith(SUFFIX)


def test_short_description_unchanged(monkeypatch):
    monkeypatch.setattr(
        regenerate_meta,
        "extract_product_info",
        lambda slug: {"types": [], "forms": [], "volumes": []},
    )
    kw = "б" * 100
    desc = regenerate_meta.generate_description(kw, "any-slug")
    assert desc == f"{kw.capitalize()} от производителя Ultimate. {SUFFIX}"
