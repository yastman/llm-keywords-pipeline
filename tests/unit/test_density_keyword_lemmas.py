"""validate/density.py: keyword counts by whole-token lemma n-grams, not substrings."""

from llm_keywords_pipeline.validate.density import check_keyword_density


def test_uk_multiword_keyword_counts_inflected_forms():
    text = "Наносимо активну піну. Активну піну змивають. Активна піна працює."
    assert check_keyword_density(text, "активна піна", lang="uk")["exact_count"] == 3


def test_ru_keyword_not_counted_inside_longer_word():
    # "пенопласт" shares the stem, "пенал" contains the substring "пена": neither is the keyword
    text = "Пенопласт лёгкий. Пенал школьный. Пенопласт режут."
    result = check_keyword_density(text, "пена", lang="ru")
    assert result["exact_count"] == 0
    assert result["partial_count"] == 0


def test_ru_single_keyword_counts_inflected_forms():
    text = "Пена густая. Наносите пену. Остатки пены смывают. Пенопласт не считается."
    result = check_keyword_density(text, "пена", lang="ru")
    assert result["exact_count"] == 3
    assert result["partial_count"] == 3


def test_partial_count_uses_whole_token_lemmas():
    # "активную" and "пену" count; "пенал" and "радиоактивная" only contain the substrings
    text = "Активную пену берут. Пенал радиоактивная. Пенал."
    assert check_keyword_density(text, "активная пена", lang="ru")["partial_count"] == 2
