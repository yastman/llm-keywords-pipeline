"""UK apostrophe words (м'який, п’ять, обʼєм) stay whole in the lemma tokenizers."""

from llm_keywords_pipeline.core.coverage import PreparedText, check_keyword
from llm_keywords_pipeline.core.keywords import KeywordMatcher, MorphAnalyzer
from llm_keywords_pipeline.validate.density import check_keyword_density
from llm_keywords_pipeline.validate.seo import (
    contains_keyword,
    count_keyword_lemma_ngrams,
    get_token_lemmas,
)

PROBE = "м'який п’ять обʼєм"
UK_TEXT = "Беріть м’якого воску трохи. Шар м’якого воску тонкий. Якого воску взяти?"


def test_token_lemmas_keep_apostrophe_words_whole():
    assert get_token_lemmas(PROBE, "uk") == ["м'який", "п'ять", "об'єм"]


def test_normalize_phrase_keeps_apostrophe_words_whole():
    assert MorphAnalyzer("uk").normalize_phrase(PROBE) == ["м'який", "п'ять", "об'єм"]


def test_lemma_tokens_still_split_latin_digits_and_skip_short_cyrillic():
    assert get_token_lemmas("5л шт koch2 ab", "ru") == ["5", "koch2", "ab"]


def test_contains_keyword_not_matched_by_yakyi_without_apostrophe_word():
    # "якого" lemmatizes to "який"; before the fix "м'який" was reduced to "який" too
    assert not contains_keyword("Якого кольору віск?", "м'який віск", "uk")
    assert contains_keyword(UK_TEXT, "м'який віск", "uk")


def test_count_ngrams_counts_inflected_apostrophe_forms_only():
    assert count_keyword_lemma_ngrams(UK_TEXT, "м'який віск", "uk") == 2


def test_density_counts_inflected_apostrophe_forms_only():
    result = check_keyword_density(UK_TEXT, "м'який віск", lang="uk")
    assert result["exact_count"] == 2


def test_keyword_matcher_single_word_apostrophe():
    assert KeywordMatcher("uk").match_lemma("м'який", "Візьміть м’якого воску") == (True, "м'якого")
    assert KeywordMatcher("uk").match_lemma("м'який", "Якого кольору віск?") == (False, None)


def test_coverage_lemma_match_apostrophe_keyword():
    prepared = PreparedText("Якого кольору віск?", "uk")
    assert not check_keyword("м'який віск", prepared, []).covered
    assert check_keyword("м'який віск", PreparedText(UK_TEXT, "uk"), []).covered
