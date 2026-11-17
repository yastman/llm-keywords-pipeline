"""_clean.json writers keep stats.after/total_volume in step with the keyword entries."""

import json

from llm_keywords_pipeline.compare import raw_clean
from llm_keywords_pipeline.core.synonyms import apply_cleanup
from llm_keywords_pipeline.fix import cleanup_misplaced, find_orphan_keywords

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


def test_cleanup_misplaced_refreshes_stats(tmp_path, monkeypatch):
    monkeypatch.setattr(cleanup_misplaced, "CATEGORIES_DIR", tmp_path)
    path = _write(tmp_path, "cat", {"keywords": _keywords(), "stats": dict(STATS)})

    assert cleanup_misplaced.remove_keywords_from_category("cat", ["BETA"]) == 1

    assert _read(path)["stats"] == {"before": 9, "after": 2, "total_volume": 125}


def test_stats_count_extra_group_and_missing_volume(tmp_path, monkeypatch):
    monkeypatch.setattr(cleanup_misplaced, "CATEGORIES_DIR", tmp_path)
    keywords = _keywords()
    keywords["extra"] = [{"keyword": "epsilon", "volume": 7}, {"keyword": "zeta"}]
    path = _write(tmp_path, "cat", {"keywords": keywords, "stats": dict(STATS)})

    assert cleanup_misplaced.remove_keywords_from_category("cat", ["beta"]) == 1

    # every list group counts; an entry without volume counts as 0
    assert _read(path)["stats"] == {"before": 9, "after": 4, "total_volume": 132}


def test_raw_clean_fix_refreshes_stats(tmp_path, monkeypatch):
    monkeypatch.setattr(raw_clean, "CATEGORIES_DIR", tmp_path)
    data = {"keywords": _keywords(), "stats": dict(STATS)}
    path = _write(tmp_path, "cat", data)
    result = {
        "added": [{"keyword": "gamma"}],
        "volume_changed": [{"keyword": "alpha", "csv_volume": 10}],
    }

    ok, _ = raw_clean.fix_clean_json("cat", data, [], result)

    assert ok
    assert _read(path)["stats"] == {"before": 9, "after": 2, "total_volume": 60}


def test_find_orphans_distribute_refreshes_stats(tmp_path, monkeypatch):
    monkeypatch.setattr(find_orphan_keywords, "CATEGORIES_DIR", tmp_path)
    path = _write(tmp_path, "cat", {"keywords": _keywords(), "stats": dict(STATS)})

    added = find_orphan_keywords.distribute_orphans(
        {"cat": [{"keyword": "delta", "volume": 5}]}, dry_run=False
    )

    assert added == 1
    assert _read(path)["stats"] == {"before": 9, "after": 4, "total_volume": 180}


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
