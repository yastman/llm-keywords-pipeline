#!/usr/bin/env python3
"""
config.py — Unified Configuration (SSOT)

Единый источник конфигурации для модулей проекта.
Заменяет разбросанные "магические числа" и дублирующиеся константы.

Version: v8.5 (Google 2025 Approach)
Updated: 2025-12-15
"""

import os
from pathlib import Path

# =============================================================================
# Project Paths
# =============================================================================

# LLM_KEYWORDS_PROJECT_ROOT wins; otherwise walk up from this file.
_FILE_DIR = Path(__file__).parent.resolve()
_ENV_ROOT = os.environ.get("LLM_KEYWORDS_PROJECT_ROOT")
if _ENV_ROOT:
    PROJECT_ROOT = Path(_ENV_ROOT).resolve()
elif _FILE_DIR.name == "core" and _FILE_DIR.parent.name == "llm_keywords_pipeline":
    # src/llm_keywords_pipeline/core/ → go up 3 levels to project root
    # core → llm_keywords_pipeline → src → llm-keywords-pipeline (project root)
    PROJECT_ROOT = _FILE_DIR.parent.parent.parent
else:
    # Fallback for legacy direct execution.
    PROJECT_ROOT = _FILE_DIR.parent

CATEGORIES_DIR = PROJECT_ROOT / "categories"
DATA_DIR = PROJECT_ROOT / "data"
TASKS_DIR = DATA_DIR / "tasks"
SEMANTICS_CSV = PROJECT_ROOT / "Структура _Ultimate.csv"

# =============================================================================
# Quality Thresholds (SEO 2025 v8.5)
# =============================================================================

QUALITY_THRESHOLDS = {
    # Water (%)
    "water_target_min": 40.0,
    "water_target_max": 65.0,
    "water_blocker_low": 30.0,
    "water_blocker_high": 70.0,
    # Classic Nausea (√freq)
    "nausea_classic_target": 3.5,
    "nausea_classic_blocker": 4.0,
    # Academic Nausea (%): top significant lemma frequency / sum of repeated
    # significant lemma frequencies x 100 (audit/water.py)
    "nausea_academic_min": 7.0,
    "nausea_academic_max": 9.5,
    "nausea_academic_blocker": 12.0,
    # Meta tags (chars) - soft limits
    "title_min": 30,
    "title_max": 60,
    "description_min": 100,
    "description_max": 160,
    # Main keyword frequency (occurrences in text)
    "keyword_freq_min": 3,
    "keyword_freq_max": 7,
    "keyword_freq_spam": 10,
    # Coverage (%) - adaptive by keywords count
    "coverage_shallow": 70,  # ≤5 keywords
    "coverage_medium": 60,  # 6-15 keywords
    "coverage_deep": 50,  # 16+ keywords
    # Length (words) - soft guidelines, not blockers
    "words_soft_min": 150,
    "words_soft_max": 600,
}

# =============================================================================
# Validation Modes
# =============================================================================

VALIDATION_MODES = {
    "quality": {
        "description": "Full QA mode - catches LLM degradation",
        "checks": [
            "structure",
            "primary_keyword",
            "coverage",
            "quality",
            "blacklist",
            "length",
            "content_standards",
            "md_lint",
        ],
        "blockers": ["structure", "primary_keyword", "quality", "blacklist"],
    },
    "seo": {
        "description": "Minimal SEO mode - ready for publish",
        "checks": ["structure", "primary_keyword", "strict_blacklist"],
        "blockers": ["primary_keyword", "strict_blacklist"],
    },
}

# =============================================================================
# Category Mapping (L3 → Slug)
# =============================================================================

L3_TO_SLUG: dict[str, str] = {
    "Активная пена": "aktivnaya-pena",
    "Для ручной мойки": "dlya-ruchnoy-moyki",
    "Очистители стекол": "ochistiteli-stekol",
    "Глина и автоскрабы": "glina-i-avtoskraby",
    "Антимошка": "antimoshka",
    "Антибитум": "antibitum",
    "Чернители шин": "cherniteli-shin",
    "Очистители дисков": "ochistiteli-diskov",
    "Очистители шин": "ochistiteli-shin",
    "Аппараты Tornador": "apparaty-tornador",
    "Меховые": "mekhovye",
    "Поролоновые": "porolonovye",
    "Наборы для мойки": "nabory-dlya-moyki",
    "Наборы для полировки": "nabory-dlya-polirovki",
    "Наборы для ухода за кожей": "nabory-dlya-ukhoda-za-kozhey",
    "Наборы для химчистки": "nabory-dlya-khimchistki",
    "Подарочные наборы": "podarochnye-nabory",
}

SLUG_TO_L3: dict[str, str] = {v: k for k, v in L3_TO_SLUG.items()}

# =============================================================================
# Commercial Keywords (for coverage split)
# =============================================================================

COMMERCIAL_MODIFIERS: list[str] = [
    "купить",
    "цена",
    "заказать",
    "стоимость",
    "в наличии",
    "доставка",
    "недорого",
    "оптом",
    "магазин",
    "интернет-магазин",
]

# =============================================================================
# Blacklist Configuration
# =============================================================================

# AI-fluff phrases (regex, lowercase) that should trigger WARNING, by text language.
# UK is a direct translation of RU.
AI_FLUFF_PATTERNS: dict[str, list[str]] = {
    "ru": [
        r"в этой статье",
        r"давайте разберёмся",
        r"давайте разберемся",
        r"в данной статье",
        r"мы рассмотрим",
        r"вы узнаете",
        r"в заключение",
        r"подводя итоги",
        r"как было сказано выше",
        r"как мы уже говорили",
        r"не секрет, что",
        r"ни для кого не секрет",
        r"стоит отметить",
        r"важно отметить",
        r"следует отметить",
        r"необходимо отметить",
        r"нельзя не отметить",
        r"безусловно",
        r"несомненно",
        r"очевидно, что",
    ],
    "uk": [
        r"[ву] цій статті",
        r"давайте розберемося",
        r"давайте розберемось",
        r"[ву] даній статті",
        r"ми розглянемо",
        r"ви дізнаєтеся",
        r"на завершення",
        r"підбиваючи підсумки",
        r"як було сказано вище",
        r"як ми вже говорили",
        r"не секрет, що",
        r"ні для кого не секрет",
        r"варто зазначити",
        r"важливо зазначити",
        r"слід зазначити",
        r"необхідно зазначити",
        r"не можна не зазначити",
        r"безумовно",
        r"безсумнівно",
        r"очевидно, що",
    ],
}

# Strict phrases (plain substrings, lowercase) that should trigger FAIL, by text language.
# UK is a direct translation of RU (both в/у forms and both apostrophes).
STRICT_BLACKLIST_PHRASES: dict[str, list[str]] = {
    "ru": [
        "в современном мире",
        "широкий ассортимент",
        "высокое качество по доступной цене",
        "является неотъемлемой частью",
    ],
    "uk": [
        "у сучасному світі",
        "в сучасному світі",
        "широкий асортимент",
        "висока якість за доступною ціною",
        "є невід'ємною частиною",
        "є невід’ємною частиною",
    ],
}

# Words that look like cities but are often false positives
FALSE_POSITIVE_CITIES: list[str] = [
    "ровно",  # наречие: "ровно столько"
    "суми",  # может быть опечатка "суммы"
    "сумах",  # UK "у сумах до 1000 грн" (суми/сума)
]

# =============================================================================
# Content Standards Requirements (CONTENT_GUIDE.md)
# =============================================================================

CONTENT_STANDARDS = {
    "required": {
        "safety_block": True,  # ## Safety или test spot
        "howto_steps": True,  # нумерованные шаги
        "evergreen_math": True,  # расход/концентрация
        "warnings": True,  # "так не делайте"
    },
    "recommended": {
        "crosslinks_min": 0,  # SSOT: перелинковка отдельным этапом
        "faq_min": 2,  # FAQ вопросов
    },
}

# =============================================================================
# Version Info
# =============================================================================

__version__ = "8.5.0"
__standard__ = "Google 2025 (Depth over Length, Two-Mode Validation)"
__updated__ = "2025-12-15"


def get_adaptive_coverage_target(keywords_count: int) -> int:
    """Get coverage target based on keywords count."""
    if keywords_count <= 5:
        return int(QUALITY_THRESHOLDS["coverage_shallow"])
    elif keywords_count <= 15:
        return int(QUALITY_THRESHOLDS["coverage_medium"])
    else:
        return int(QUALITY_THRESHOLDS["coverage_deep"])


def get_guidelines_coverage_target(keywords_count: int) -> int:
    """Coverage target for content guidelines (legacy thresholds)."""
    if keywords_count <= 10:
        return 70
    elif keywords_count <= 20:
        return 60
    else:
        return 50


def get_data_path(slug: str, clean: bool = True) -> Path:
    """Get path to keywords data file."""
    if clean:
        return CATEGORIES_DIR / slug / "data" / f"{slug}_clean.json"
    return CATEGORIES_DIR / slug / "data" / f"{slug}.json"
