"""batch.uk_init.translate_keyword replaces whole words only."""

import re

from llm_keywords_pipeline.batch.uk_init import TRANSLATIONS, translate_keyword

# Hand-written car-care phrases: every TRANSLATIONS key in a whole-word use, plus
# words that start with a key (стеклоомыватель, дисков, кожаный, ...) and must stay intact.
SAMPLE = [
    "средство и стеклоомыватель для лобового стекла",
    "стекло жидкое на кузов",
    "чернитель резины и шинами",
    "очиститель кожи с кожаный ремешком",
    "полироль и полировка фар",
    "полировальная машинка с кругом, полировальной пастой",
    "полировальную губку для полировальные работ",
    "полировальный круг на аккумуляторе",
    "аккумуляторная машина и аккумуляторную щётку",
    "работа машинкой по лаку",
    "воск и воски, восковый спрей",
    "покрытие керамика и покрытия на диски",
    "защитное и защитные пленки",
    "керамику на дисков блеск",
    "жидкий воск, жидкость для мойки",
    "твёрдый и твердый воск",
    "уход за пластика и пластиковый бампер",
    "уход за кожаного дивана кожей",
    "шторка салона, в салоне, обзор салонов",
    "мойка двигателя",
    "диск колеса",
    "шин блеск",
    "пена и пенники",
    "пятновыводитель для ткани",
    "запах и запаха нет",
    "обезжириватель перед покраской",
    "варежка для мойки",
    "микрофибра, микрофибру и микрофибры",
    "тряпка, тряпки, тряпку",
    "кисти для дисков",
    "щетка, щетки и щетку",
    "распылитель и пенник",
    "ведро и ведра",
    "набор и наборы",
    "скотч и скотчи",
    "оборудование для мойки",
    "торнадор для салона",
    "силант и силанты",
    "детейлинг и детейлинга",
    "круг и круги",
    "меховой круг",
    "набор паст и паста",
    "омыватель и омыватели",
    "ручной режим",
    "купить нейтрализатор и нейтрализаторы",
    "аксессуары для мойки",
    "химчистка, химчистки, химчистку",
    "наружного и наружный уход",
    "цена и по ценам",
    "Украина, украине",
]


def test_word_containing_a_key_stays_intact():
    # "кожаный" is not a key; no shorter key may rewrite part of it.
    assert translate_keyword("кожаный салон") == "кожаный салон"


def test_whole_word_key_is_translated():
    assert translate_keyword("очиститель для авто") == "очищувач для авто"


def test_inflected_form_is_translated():
    assert translate_keyword("полировальная машинка") == "полірувальна машинка"


def test_capitalised_word_keeps_capital():
    assert translate_keyword("доставка по Украине, Украина") == "доставка по Україні, Україна"
    assert translate_keyword("доставка по украине") == "доставка по україні"


def test_one_lowercase_key_per_word():
    assert all(key == key.lower() for key in TRANSLATIONS)


def test_every_key_is_a_whole_word_in_sample():
    words = {w for kw in SAMPLE for w in re.findall(r"\w+", kw.lower())}
    dead = [key for key in TRANSLATIONS if key not in words]
    assert dead == []


def test_sample_changes_whole_words_only():
    for kw in SAMPLE:
        before = re.findall(r"\w+", kw)
        after = re.findall(r"\w+", translate_keyword(kw))
        assert len(before) == len(after), kw
        for ru, uk in zip(before, after, strict=True):
            target = TRANSLATIONS.get(ru.lower())
            allowed = {ru} if target is None else {target, target[:1].upper() + target[1:]}
            assert uk in allowed, (kw, ru, uk)
