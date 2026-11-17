"""validate/seo.py: lemma-aware keyword frequency and Latin/digit keyword tokens."""

from llm_keywords_pipeline.validate.seo import check_keyword_frequency, contains_keyword


def test_frequency_counts_inflected_forms():
    text = "Пена хорошая. Наносите пену на кузов. Остатки пены смывают водой."
    result = check_keyword_frequency(text, "пена")
    assert result["count"] == 3
    assert result["status"] == "OK"


def test_frequency_multiword_keyword_counts_inflected_sequence():
    text = "Активную пену наносят снизу. Активной пены хватает. Пена активная? Нет."
    # "пена активная" is a different word order and does not count
    assert check_keyword_frequency(text, "активная пена")["count"] == 2


def test_latin_keyword_word_must_be_present():
    assert not contains_keyword("Наносите пену на кузов", "пена Koch Chemie")
    assert contains_keyword("Наносите пену Koch Chemie на кузов", "пена Koch Chemie")


def test_latin_only_keyword_not_matched_by_unrelated_text():
    assert not contains_keyword("Наносите пену на кузов", "Koch Chemie")
    assert contains_keyword("Шампунь KOCH chemie", "Koch Chemie")


def test_digit_keyword_token_compared():
    assert not contains_keyword("Канистра пены", "пена 5")
    assert contains_keyword("Канистра пены 5 литров", "пена 5")


def test_empty_token_set_is_not_found():
    # only short words: no token survives, so nothing can match
    assert not contains_keyword("на кузов и в салон", "на и")
