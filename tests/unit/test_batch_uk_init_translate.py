"""batch.uk_init.translate_keyword replaces whole words only."""

import re
from pathlib import Path

from llm_keywords_pipeline.batch.uk_init import TRANSLATIONS, translate_keyword

# Real RU keywords from data/ru_semantics_master.csv at a5ad333^ (see the file header).
SAMPLE_PATH = Path(__file__).parent.parent / "fixtures" / "ru_keywords_sample.txt"


def _sample() -> list[str]:
    lines = SAMPLE_PATH.read_text(encoding="utf-8").splitlines()
    return [line for line in lines if line and not line.startswith("#")]


def test_word_containing_a_key_stays_intact():
    # "кожаный" is not a key; no shorter key may rewrite part of it.
    assert translate_keyword("кожаный салон") == "кожаный салон"


def test_whole_word_key_is_translated():
    assert translate_keyword("очиститель для авто") == "очищувач для авто"


def test_inflected_form_is_translated():
    assert translate_keyword("полировальная машинка") == "полірувальна машинка"


def test_every_key_is_a_whole_word_in_real_keywords():
    words = {w for kw in _sample() for w in re.findall(r"\w+", kw.lower())}
    dead = [key for key in TRANSLATIONS if key.lower() not in words]
    assert dead == []


def test_real_keywords_change_whole_words_only():
    for kw in _sample():
        before = re.findall(r"\w+", kw)
        after = re.findall(r"\w+", translate_keyword(kw))
        assert len(before) == len(after), kw
        for ru, uk in zip(before, after, strict=True):
            allowed = {ru} | {v for k, v in TRANSLATIONS.items() if k.lower() == ru.lower()}
            assert uk in allowed, (kw, ru, uk)
