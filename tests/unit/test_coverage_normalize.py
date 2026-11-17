import pytest

from llm_keywords_pipeline.core.coverage import keyword_key, normalize_text


@pytest.mark.parametrize("apostrophe", ["’", "‘"])
def test_typographic_apostrophe_matches_ascii(apostrophe: str) -> None:
    assert normalize_text(f"пам{apostrophe}ять") == normalize_text("пам'ять")


def test_keyword_key_equates_case_yo_apostrophe_and_spaces() -> None:
    assert keyword_key("  Пам’ять   Ёлки ") == keyword_key("пам'ять елки") == "пам'ять елки"
