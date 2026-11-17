"""_clean.json writers keep stats.after/total_volume in step with the keyword entries."""

import json

from llm_keywords_pipeline.core.clean_json import refresh_stats_totals
from llm_keywords_pipeline.core.synonyms import apply_cleanup

STATS = {"before": 9, "after": 3, "total_volume": 175}


def _keywords():
    return {
        "primary": [{"keyword": "alpha", "volume": 100}],
        "secondary": [{"keyword": "beta", "volume": 50}],
        "supporting": [{"keyword": "gamma", "volume": 25}],
    }


def _write(categories_dir, slug, data):
    path = categories_dir / slug / "data" / f"{slug}_clean.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_stats_count_extra_group_and_missing_volume():
    keywords = _keywords()
    keywords["extra"] = [{"keyword": "epsilon", "volume": 7}, {"keyword": "zeta"}]
    data = {"keywords": keywords, "stats": dict(STATS)}

    refresh_stats_totals(data)

    # every list group counts; an entry without volume counts as 0
    assert data["stats"] == {"before": 9, "after": 5, "total_volume": 182}


def _synonym_category(tmp_path, data):
    _write(tmp_path, "cat", data)
    return tmp_path / "cat"


def _synonym_keywords():
    # The two keywords normalize alike ("для" is a stop word): the lower volume one goes
    return {
        "primary": [
            {"keyword": "шампунь для ручной мойки", "volume": 100},
            {"keyword": "шампунь ручной мойки", "volume": 50},
        ],
        "secondary": [{"keyword": "воск", "volume": 30}],
    }


def test_synonyms_cleanup_refreshes_stats(tmp_path):
    cat = _synonym_category(
        tmp_path, {"keywords": _synonym_keywords(), "stats": {"after": 3, "total_volume": 180}}
    )

    assert apply_cleanup(cat) == 1

    assert _read(cat / "data" / "cat_clean.json")["stats"] == {"after": 2, "total_volume": 130}


def test_synonyms_cleanup_adds_no_stats(tmp_path):
    cat = _synonym_category(tmp_path, {"keywords": _synonym_keywords()})

    assert apply_cleanup(cat) == 1

    assert "stats" not in _read(cat / "data" / "cat_clean.json")
