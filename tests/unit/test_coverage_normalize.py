import pytest

from llm_keywords_pipeline.core.coverage import normalize_text


@pytest.mark.parametrize("apostrophe", ["’", "‘"])
def test_typographic_apostrophe_matches_ascii(apostrophe: str) -> None:
    assert normalize_text(f"пам{apostrophe}ять") == normalize_text("пам'ять")
