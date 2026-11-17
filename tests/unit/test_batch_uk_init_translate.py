"""batch.uk_init.translate_keyword replaces whole words only."""

from llm_keywords_pipeline.batch.uk_init import translate_keyword


def test_word_containing_a_key_stays_intact():
    # "кожа" is a key; "кожаный" must not become "шкіраный".
    assert translate_keyword("кожаный салон") == "кожаный салон"


def test_whole_word_key_is_translated():
    assert translate_keyword("резина для авто") == "гума для авто"
