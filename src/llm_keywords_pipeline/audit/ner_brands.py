#!/usr/bin/env python3
"""
NER Brand/City Checker using Natasha

Автоматически находит и предупреждает о:
- бренды из [blacklist] brands в <data root>/project.toml; ORG (организации) из NER
- LOC (локации) → города: Киев, Харьков, Одесса
- PER (персоны) → имена: нежелательны в SEO текстах

Usage:
    uv run python -m llm_keywords_pipeline.audit.ner_brands <file.md>
    uv run python -m llm_keywords_pipeline.audit.ner_brands <file.md> --json

Exit codes:
    0 = PASS (no forbidden entities)
    1 = WARNING (found entities) or FAIL (strict phrases found)
"""

from __future__ import annotations

import json
import re
import sys
from functools import lru_cache
from pathlib import Path

from llm_keywords_pipeline.core.config import (
    AI_FLUFF_PATTERNS,
    FALSE_POSITIVE_CITIES,
    STRICT_BLACKLIST_PHRASES,
)
from llm_keywords_pipeline.core.keywords import MorphAnalyzer
from llm_keywords_pipeline.core.project import get_project
from llm_keywords_pipeline.core.text import clean_markdown
from llm_keywords_pipeline.validate.seo import detect_language

try:
    from natasha import Doc, NewsEmbedding, NewsNERTagger, Segmenter

    NATASHA_FULL = True
except ImportError:
    try:
        from natasha import Doc, Segmenter

        NATASHA_FULL = False
    except ImportError:
        print("❌ Natasha не установлена: uv sync --group nlp")
        NATASHA_FULL = False

# Бренды (явные упоминания): [blacklist] brands из project.toml, по умолчанию нет.

# Blacklist городов; [blacklist] cities = false в project.toml отключает проверку
CITY_BLACKLIST = {
    # Украина
    "київ",
    "киев",
    "kyiv",
    "kiev",
    "харків",
    "харьков",
    "kharkiv",
    "одеса",
    "одесса",
    "odesa",
    "odessa",
    "дніпро",
    "днепр",
    "dnipro",
    "львів",
    "львов",
    "lviv",
    "запоріжжя",
    "запорожье",
    "zaporizhzhia",
    "вінниця",
    "винница",
    "vinnytsia",
    "полтава",
    "poltava",
    "чернігів",
    "чернигов",
    "chernihiv",
    "черкаси",
    "черкассы",
    "cherkasy",
    "суми",
    "сумы",
    "sumy",
    "житомир",
    "zhytomyr",
    "миколаїв",
    "николаев",
    "mykolaiv",
    "херсон",
    "kherson",
    "рівне",
    "ровно",
    "rivne",
    "луцьк",
    "луцк",
    "lutsk",
    "ужгород",
    "uzhhorod",
    "тернопіль",
    "тернополь",
    "ternopil",
    "івано-франківськ",
    "ивано-франковск",
    "кропивницький",
    "кропивницкий",
    # Другие
    "москва",
    "moscow",
    "санкт-петербург",
    "минск",
    "варшава",
}

# Предлоги для географического контекста
LOCATION_PREPOSITIONS = {"в", "из", "до", "на", "під", "под", "у", "із", "з"}


def is_false_positive_location(word: str, context: str) -> bool:
    """Check if found word is a false positive city."""
    word_lower = word.lower()

    if word_lower not in FALSE_POSITIVE_CITIES:
        return False

    context_lower = context.lower()

    for prep in LOCATION_PREPOSITIONS:
        pattern = rf"\b{prep}\s+{re.escape(word_lower)}\b"
        if re.search(pattern, context_lower):
            return False

    return True


_PERSON_NAME_TAGS = {"Name", "Surn", "Patr"}

# Предлоги места перед формой, которая читается и как город, и как обычное слово
_CITY_PREPOSITIONS = {
    # UK
    "у", "в", "до", "з", "із", "по", "на", "під", "біля",
    # RU
    "во", "из", "под", "около",
}  # fmt: skip
# Разделитель городов в списке: "Києві, Миколаєві", "Києві та Рівному", "Черкасах і Луцьку"
_CITY_LIST_CONJUNCTIONS = {"та", "і", "й", "и"}
_CITY_LIST_SEP_RE = re.compile(r"\s*,\s*(?:(?:та|і|й|и)\s+)?|\s+(?:та|і|й|и)\s+")
# "|" — граница ячейки таблицы
_SENTENCE_END = ".!?…\n|"
# Сокращение "місто"/"город" перед названием: "у м. Києві", "в г. Киеве"
_CITY_ABBREVIATIONS = {"м", "г"}


def _is_city_abbreviation(text: str, dot: int) -> bool:
    """True if the '.' at `dot` closes a one-letter 'м.'/'г.' ('у м. Києві').

    After a number it is a unit ('5 м.', '50 г.'), not a city abbreviation.
    """
    if not (
        dot >= 1
        and text[dot] == "."
        and text[dot - 1].lower() in _CITY_ABBREVIATIONS
        and (dot == 1 or not text[dot - 2].isalnum())
    ):
        return False
    before = text[: dot - 1].rstrip()
    return not (before and before[-1].isdigit())


def _is_title_case(word: str) -> bool:
    """Capital first letter and not ALL-CAPS ('Рівне', not 'РІВНЕ' or 'рівне')."""
    return word[:1].isupper() and not word.isupper()


def _starts_sentence(text: str, pos: int) -> bool:
    """True if the word at `pos` opens the text, a line or a sentence (quotes/markers skipped)."""
    i = pos
    while i > 0 and not text[i - 1].isalnum() and text[i - 1] not in _SENTENCE_END:
        i -= 1
    if i > 0 and _is_city_abbreviation(text, i - 1):
        return False
    return i == 0 or text[i - 1] in _SENTENCE_END


@lru_cache(maxsize=10000)
def _city_parse(word: str) -> tuple[str, bool] | None:
    """City lemma of `word` from any UK/RU parse, and whether it also reads as a common word.

    Every parse counts, not only the first ('києві': 'кий' first, 'київ' third).
    Person-name parses (харкові → Surn 'харко', львові → Surn 'львов') are ignored.
    A city reading is a NOUN parse: adverb 'ровно' shares the normal form of 'Ровно'.
    """
    for lang in ("uk", "ru"):
        morph = MorphAnalyzer(lang)._morph
        if morph is None:
            continue
        parses = [p for p in morph.parse(word) if not _PERSON_NAME_TAGS & p.tag.grammemes]
        cities = [
            p.normal_form for p in parses if p.normal_form in CITY_BLACKLIST and "NOUN" in p.tag
        ]
        if cities:
            return cities[0], len(cities) < len(parses)
    return None


def check_blacklist(text: str, lang: str = "ru") -> dict:
    """Проверяет текст на наличие запрещённых слов; strict и AI-fluff — списки языка lang (ru/uk)."""
    text_lower = text.lower()
    project = get_project()

    found_brands = []
    found_cities = []
    found_ai_fluff = []
    found_strict = []

    # Проверка брендов
    for brand in project.blacklist_brands:
        if brand in text_lower:
            # Только целое слово: "ауди" не ловится внутри "аудиосистемы"
            for match in re.finditer(rf"(?<!\w){re.escape(brand)}(?!\w)", text_lower):
                start = max(0, match.start() - 30)
                end = min(len(text), match.end() + 30)
                context = text[start:end].replace("\n", " ")
                found_brands.append(
                    {"entity": brand, "type": "BRAND", "context": f"...{context}..."}
                )

    # Слова с городским разбором (Києві, Рівному, Львові) проверяются по разбору ниже,
    # а не по основе-подстроке ("львов" внутри "львові"); cities = false — без городов
    words = list(re.finditer(r"\w+", text_lower)) if project.blacklist_cities else []
    parses = [_city_parse(m.group()) for m in words]
    city_words = [(m, parsed) for m, parsed in zip(words, parses, strict=True) if parsed]

    # Предлог места прямо перед формой или перед первым городом списка
    # ("у Києві, Миколаєві, Черкасах і Луцьку"), в любом регистре; "м."/"г." между
    # ними прозрачно ("у м. Києві"). Одно "на" перед строчной формой — не место
    # ("на ровном месте", "на рівному майданчику"); заглавная или КАПС после "на" — место.
    after_preposition = [False] * len(words)
    for k, m in enumerate(words):
        if not parses[k] or k == 0:
            continue
        prep_k = k - 1
        abbr = words[k - 1]
        if (
            k >= 2
            and abbr.group() in _CITY_ABBREVIATIONS
            and _is_city_abbreviation(text_lower, abbr.end())
            and text_lower[abbr.end() + 1 : m.start()].isspace()
        ):
            prep_k = k - 2
        prev = words[prep_k]
        if (
            prev.group() in _CITY_PREPOSITIONS
            and text_lower[prev.end() : words[prep_k + 1].start()].isspace()
            and not (prev.group() == "на" and not text[m.start()].isupper())
        ):
            after_preposition[k] = True
            continue
        prev = words[k - 1]
        j = k - 2 if prev.group() in _CITY_LIST_CONJUNCTIONS else k - 1
        if (
            j >= 0
            and after_preposition[j]
            and _CITY_LIST_SEP_RE.fullmatch(text_lower[words[j].end() : m.start()])
        ):
            after_preposition[k] = True

    # Проверка городов (с фильтрацией false positives)
    for city in CITY_BLACKLIST if project.blacklist_cities else ():
        if city in text_lower:
            for match in re.finditer(re.escape(city), text_lower):
                if any(m.start() <= match.start() < m.end() for m, _ in city_words):
                    continue
                start = max(0, match.start() - 30)
                end = min(len(text), match.end() + 30)
                context = text[start:end].replace("\n", " ")

                if is_false_positive_location(city, context):
                    continue

                found_cities.append({"entity": city, "type": "CITY", "context": f"...{context}..."})

    # Форма, которая читается и как обычное слово (рівному: рівне/рівний, сумах: суми/сума,
    # києві: київ/кий), — город, если (а) с заглавной буквы не в начале предложения
    # или (б) после предлога места / в списке после него. Строчная форма из
    # FALSE_POSITIVE_CITIES ("у сумах до 1000 грн", "до суми замовлення")
    # по (б) не считается, кроме "ровно": "в ровно" — город, как в is_false_positive_location.
    # Слово КАПСОМ ("## НАНЕСІТЬ РІВНИМ ШАРОМ") по (а) не считается.
    for k, match in enumerate(words):
        if not parses[k]:
            continue
        lemma, ambiguous = parses[k]
        if ambiguous:
            word = match.group()
            upper = text[match.start()].isupper()
            title_case = _is_title_case(text[match.start() : match.end()])
            by_capital = title_case and not _starts_sentence(text, match.start())
            vetoed = not upper and word in FALSE_POSITIVE_CITIES and word != "ровно"
            if not by_capital and not (after_preposition[k] and not vetoed):
                continue
        start = max(0, match.start() - 30)
        end = min(len(text), match.end() + 30)
        context = text[start:end].replace("\n", " ")
        found_cities.append({"entity": lemma, "type": "CITY", "context": f"...{context}..."})

    # Проверка Strict Phrases (FAIL)
    for phrase in STRICT_BLACKLIST_PHRASES[lang]:
        if phrase in text_lower and phrase not in project.phrases_allow:
            for match in re.finditer(re.escape(phrase), text_lower):
                start = max(0, match.start() - 30)
                end = min(len(text), match.end() + 30)
                context = text[start:end].replace("\n", " ")
                found_strict.append(
                    {"entity": phrase, "type": "STRICT_BLACKLIST", "context": f"...{context}..."}
                )

    # Проверка AI-fluff
    for pattern in AI_FLUFF_PATTERNS[lang]:
        matches = re.finditer(pattern, text_lower)
        for match in matches:
            start = max(0, match.start() - 20)
            end = min(len(text), match.end() + 20)
            context = text[start:end].replace("\n", " ")
            found_ai_fluff.append(
                {"entity": match.group(), "type": "AI_FLUFF", "context": f"...{context}..."}
            )

    return {
        "brands": found_brands,
        "cities": found_cities,
        "ai_fluff": found_ai_fluff,
        "strict_phrases": found_strict,
    }


def check_ner(text: str, lang: str = "ru") -> dict:
    """Natasha NER для поиска сущностей; модель только русская (RU-only), для uk не запускается."""
    if lang == "uk":
        return {
            "ner_entities": [],
            "skipped": True,
            "warning": "NER пропущен: natasha NER только для русского (RU-only), для uk не запускается",
        }

    if not NATASHA_FULL:
        return {
            "ner_entities": [],
            "warning": "NER недоступен (установите natasha: uv sync --group nlp)",
        }

    segmenter = Segmenter()
    emb = NewsEmbedding()
    ner_tagger = NewsNERTagger(emb)

    clean_text = clean_markdown(text)

    doc = Doc(clean_text)
    doc.segment(segmenter)
    doc.tag_ner(ner_tagger)

    entities = []
    for span in doc.spans:
        entity_text = span.text
        entity_type = span.type

        start = max(0, span.start - 30)
        end = min(len(clean_text), span.stop + 30)
        context = clean_text[start:end].replace("\n", " ")

        entities.append({"entity": entity_text, "type": entity_type, "context": f"...{context}..."})

    return {"ner_entities": entities}


def analyze_file(filepath: str, output_json: bool = False) -> int:
    """
    Анализирует файл на наличие запрещённых сущностей.

    Язык — по пути файла (detect_language: /uk/ → uk): списки strict/AI-fluff этого языка; natasha NER только для ru.

    Returns:
        0 = PASS, 1 = WARNING (found issues) or FAIL (strict phrases)
    """
    path = Path(filepath)
    if not path.exists():
        print(f"❌ Файл не найден: {filepath}")
        return 2

    text = path.read_text(encoding="utf-8")

    lang = detect_language(str(path))
    blacklist_results = check_blacklist(text, lang)
    ner_results = check_ner(text, lang)

    results = {
        "file": str(path),
        "blacklist": blacklist_results,
        "ner": ner_results,
        "summary": {
            "brands_count": len(blacklist_results["brands"]),
            "cities_count": len(blacklist_results["cities"]),
            "ai_fluff_count": len(blacklist_results["ai_fluff"]),
            "strict_count": len(blacklist_results["strict_phrases"]),
            "ner_org_count": len(
                [e for e in ner_results.get("ner_entities", []) if e["type"] == "ORG"]
            ),
            "ner_loc_count": len(
                [e for e in ner_results.get("ner_entities", []) if e["type"] == "LOC"]
            ),
            "ner_per_count": len(
                [e for e in ner_results.get("ner_entities", []) if e["type"] == "PER"]
            ),
        },
    }

    total_issues = (
        results["summary"]["brands_count"]
        + results["summary"]["cities_count"]
        + results["summary"]["ai_fluff_count"]
        + results["summary"]["strict_count"]
    )

    results["summary"]["total_issues"] = total_issues
    if results["summary"]["strict_count"]:
        status = "FAIL"
    else:
        status = "PASS" if total_issues == 0 else "WARNING"
    results["summary"]["status"] = status

    if output_json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(f"\n{'=' * 60}")
        print(f"NER & Blacklist Check: {path.name}")
        print(f"{'=' * 60}")

        if blacklist_results["strict_phrases"]:
            print(f"\n❌ STRICT-ФРАЗЫ ({len(blacklist_results['strict_phrases'])}):")
            for item in blacklist_results["strict_phrases"][:5]:
                print(f'   • "{item["entity"]}": {item["context"]}')

        if blacklist_results["brands"]:
            print(f"\n⚠️  БРЕНДЫ ({len(blacklist_results['brands'])}):")
            for item in blacklist_results["brands"][:5]:
                print(f"   • {item['entity']}: {item['context']}")

        if blacklist_results["cities"]:
            print(f"\n⚠️  ГОРОДА ({len(blacklist_results['cities'])}):")
            for item in blacklist_results["cities"][:5]:
                print(f"   • {item['entity']}: {item['context']}")

        if blacklist_results["ai_fluff"]:
            print(f"\n⚠️  AI-FLUFF ({len(blacklist_results['ai_fluff'])}):")
            for item in blacklist_results["ai_fluff"][:5]:
                print(f'   • "{item["entity"]}": {item["context"]}')

        if ner_results.get("skipped"):
            print(f"\nℹ️  {ner_results['warning']}")

        ner_orgs = [e for e in ner_results.get("ner_entities", []) if e["type"] == "ORG"]
        ner_locs = [e for e in ner_results.get("ner_entities", []) if e["type"] == "LOC"]

        if ner_orgs:
            print(f"\nℹ️  NER ORG (организации): {len(ner_orgs)}")
            for item in ner_orgs[:3]:
                print(f"   • {item['entity']}")

        if ner_locs:
            print(f"\nℹ️  NER LOC (локации): {len(ner_locs)}")
            for item in ner_locs[:3]:
                print(f"   • {item['entity']}")

        print(f"\n{'=' * 60}")
        if total_issues == 0:
            print("✅ PASS: Запрещённые сущности не найдены")
        elif status == "FAIL":
            print(
                f"❌ FAIL: Найдено {total_issues} проблем, из них strict-фраз: {len(blacklist_results['strict_phrases'])}"
            )
            print("   Рекомендация: удалите strict-фразы, упоминания брендов, городов и AI-фраз")
        else:
            print(f"⚠️  WARNING: Найдено {total_issues} проблем")
            print("   Рекомендация: удалите упоминания брендов, городов и AI-фраз")
        print(f"{'=' * 60}\n")

    return 0 if total_issues == 0 else 1


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv

    if len(argv) < 1 or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0

    filepath = argv[0]
    output_json = "--json" in argv

    return analyze_file(filepath, output_json)


if __name__ == "__main__":
    raise SystemExit(main())
