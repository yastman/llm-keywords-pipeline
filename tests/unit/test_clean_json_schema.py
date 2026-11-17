"""_clean.json keywords: dict of groups is canonical, flat list still reads (lkp-ftg).

Also lkp-euc: master/volume sources combine by keyword_key.
"""

import copy
import json
import sys
from pathlib import Path

from llm_keywords_pipeline.analyze import duplicates as analyze_duplicates
from llm_keywords_pipeline.analyze import order as analyze_order
from llm_keywords_pipeline.core.clean_json import keyword_entries, keyword_groups
from llm_keywords_pipeline.extract import all_keywords, ru_keywords_list, uk_keywords
from llm_keywords_pipeline.fix import keywords_order
from llm_keywords_pipeline.generate.all_meta import get_primary_keyword
from llm_keywords_pipeline.sync import merge_master, update_volume
from llm_keywords_pipeline.sync.semantics import group_by_category, load_master_csv, sync_category

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_clean.json"

DICT_DATA = {
    "id": "cat",
    "keywords": {
        "primary": [{"keyword": "главный", "volume": 100, "intent": "commercial"}],
        "secondary": [{"keyword": "второй", "volume": 50}],
    },
}
FLAT_DATA = {
    "id": "cat",
    "keywords": [{"keyword": "главный", "volume": 100}, {"keyword": "второй", "volume": 50}],
}


def write_clean(root: Path, data: dict, slug: str = "cat") -> Path:
    path = root / "categories" / slug / "data" / f"{slug}_clean.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class TestHelper:
    def test_dict_of_groups(self):
        assert list(keyword_groups(DICT_DATA)) == ["primary", "secondary"]
        assert keyword_entries(DICT_DATA) == [
            {"keyword": "главный", "volume": 100, "intent": "commercial"},
            {"keyword": "второй", "volume": 50},
        ]

    def test_flat_list(self):
        assert keyword_entries(FLAT_DATA) == FLAT_DATA["keywords"]

    def test_missing_and_non_list_group(self):
        assert keyword_entries({}) == []
        assert keyword_entries({"keywords": {"primary": [{"keyword": "a"}], "x": "y"}}) == [
            {"keyword": "a"}
        ]


class TestMasterRoundTrip:
    """merge_master -> master CSV -> semantics keeps groups, intent and meta."""

    def _round_trip(self, tmp_path: Path, data: dict) -> dict:
        clean = write_clean(tmp_path, data, slug=data["id"])
        rows = merge_master.merge_keywords(merge_master.collect_from_clean_json(clean), {})
        csv_path = tmp_path / "master.csv"
        merge_master.save_master_csv(rows, csv_path)
        for category, cat_rows in group_by_category(load_master_csv(csv_path)).items():
            sync_category(category, cat_rows, tmp_path / "categories", dry_run=False)
        return read(clean)

    def test_dict_in_same_dict_out(self, tmp_path):
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        assert self._round_trip(tmp_path, copy.deepcopy(data)) == data

    def test_flat_in_same_flat_out(self, tmp_path):
        data = {**FLAT_DATA, "synonyms": [{"keyword": "син", "volume": 5, "use_in": "content"}]}
        assert self._round_trip(tmp_path, copy.deepcopy(data)) == data


class TestSemanticsSync:
    def _sync(self, tmp_path: Path, data: dict, rows: list[dict]) -> dict:
        clean = write_clean(tmp_path, data)
        sync_category("cat", rows, tmp_path / "categories", dry_run=False)
        return read(clean)

    def test_csv_volume_and_membership_applied_in_groups(self, tmp_path):
        rows = [
            {"keyword": "Главный", "volume": 300, "type": "keyword", "use_in": ""},
            {"keyword": "новый", "volume": 7, "type": "keyword", "use_in": ""},
        ]
        result = self._sync(tmp_path, copy.deepcopy(DICT_DATA), rows)
        assert result["keywords"] == {
            "primary": [{"keyword": "Главный", "volume": 300, "intent": "commercial"}],
            "secondary": [],
            "supporting": [{"keyword": "новый", "volume": 7}],
        }

    def test_new_keyword_in_flat_file_stays_flat(self, tmp_path):
        rows = [
            {"keyword": "главный", "volume": 100, "type": "keyword", "use_in": ""},
            {"keyword": "новый", "volume": 200, "type": "keyword", "use_in": ""},
        ]
        result = self._sync(tmp_path, copy.deepcopy(FLAT_DATA), rows)
        assert result["keywords"] == [
            {"keyword": "новый", "volume": 200},
            {"keyword": "главный", "volume": 100},
        ]

    def test_new_file_is_dict_of_groups(self, tmp_path):
        (tmp_path / "categories").mkdir()
        rows = [{"keyword": "a", "volume": 1, "type": "keyword", "use_in": ""}]
        sync_category("cat", rows, tmp_path / "categories", dry_run=False)
        result = read(tmp_path / "categories" / "cat" / "data" / "cat_clean.json")
        assert result["keywords"] == {"supporting": [{"keyword": "a", "volume": 1}]}

    def test_csv_use_in_wins_over_file(self, tmp_path):
        data = {
            "id": "cat",
            "keywords": {"primary": [{"keyword": "a", "volume": 1, "use_in": "x"}]},
        }
        rows = [{"keyword": "a", "volume": 1, "type": "keyword", "use_in": ""}]
        result = self._sync(tmp_path, data, rows)
        assert result["keywords"] == {"primary": [{"keyword": "a", "volume": 1}]}


class TestReadersAcceptDict:
    def test_merge_master_collects_every_group(self, tmp_path):
        rows = merge_master.collect_from_clean_json(write_clean(tmp_path, DICT_DATA))
        assert [r["keyword"] for r in rows] == ["главный", "второй"]

    def test_analyze_duplicates_finds_across_groups(self, tmp_path):
        data = copy.deepcopy(DICT_DATA)
        data["keywords"]["secondary"].append({"keyword": "Главный", "volume": 1})
        result = analyze_duplicates.analyze_category(write_clean(tmp_path, data))
        assert result is not None
        assert len(result["duplicates"]) == 1
        assert len(result["all_keywords"]) == 3

    def test_all_meta_primary_keyword(self):
        assert get_primary_keyword(DICT_DATA) == "главный"
        assert get_primary_keyword(FLAT_DATA) == "главный"

    def test_analyze_order_checks_each_group(self, tmp_path, monkeypatch):
        monkeypatch.setattr(analyze_order, "ROOT", tmp_path)
        result = analyze_order.analyze_category(write_clean(tmp_path, DICT_DATA))
        assert result["keywords_order_wrong"] is False
        data = copy.deepcopy(DICT_DATA)
        data["keywords"]["secondary"].append({"keyword": "больше", "volume": 70})
        result = analyze_order.analyze_category(write_clean(tmp_path, data))
        assert result["keywords_order_wrong"] is True

    def test_keywords_order_fix_keeps_groups(self, tmp_path):
        data = copy.deepcopy(DICT_DATA)
        data["keywords"]["secondary"] += [
            {"keyword": "ноль", "volume": 0},
            {"keyword": "больше", "volume": 70},
        ]
        clean = write_clean(tmp_path, data)
        stats = keywords_order.fix_category(clean)
        assert stats["keywords_removed"] == 1
        assert stats["keywords_sorted"] is True
        assert read(clean)["keywords"] == {
            "primary": [{"keyword": "главный", "volume": 100, "intent": "commercial"}],
            "secondary": [{"keyword": "больше", "volume": 70}, {"keyword": "второй", "volume": 50}],
        }

    def test_keywords_order_fix_flat_stays_flat(self, tmp_path):
        data = {"keywords": [{"keyword": "a", "volume": 1}, {"keyword": "b", "volume": 5}]}
        clean = write_clean(tmp_path, data)
        keywords_order.fix_category(clean)
        assert read(clean)["keywords"] == [
            {"keyword": "b", "volume": 5},
            {"keyword": "a", "volume": 1},
        ]

    def test_extractors(self, tmp_path):
        clean = write_clean(tmp_path, DICT_DATA)
        expected = {"главный": "главный", "второй": "второй"}
        assert uk_keywords.extract_keywords_from_file(clean) == expected
        assert ru_keywords_list.extract_keywords_from_file(clean) == expected
        rows = all_keywords.extract_from_file(clean)
        assert [(r["keyword"], r["source_type"]) for r in rows] == [
            ("главный", "keyword"),
            ("второй", "synonym"),
        ]
        flat_rows = all_keywords.extract_from_file(write_clean(tmp_path, FLAT_DATA))
        assert [r["source_type"] for r in flat_rows] == ["keyword", "keyword"]


class TestSourcePrecedence:
    """lkp-euc: Excel/CSV volume sources resolve by keyword_key."""

    def _run_merge(self, tmp_path, monkeypatch, sources: list[dict], clean: dict | None) -> list:
        categories = tmp_path / "categories"
        categories.mkdir()
        if clean is not None:
            write_clean(tmp_path, clean)
        names = [f"s{i}.xlsx" for i in range(len(sources))]
        by_name = dict(zip(names, sources, strict=True))
        monkeypatch.setattr(merge_master, "load_excel_keywords", lambda p: by_name[p.name])
        out = tmp_path / "master.csv"
        argv = ["merge", "--excel", *names, "--output", str(out), "--categories", str(categories)]
        monkeypatch.setattr(sys, "argv", argv)
        merge_master.main()
        return [(r["keyword"], r["volume"]) for r in load_master_csv(out)]

    def test_last_source_wins_whatever_spelling(self, tmp_path, monkeypatch):
        clean = {"id": "cat", "keywords": {"primary": [{"keyword": "КЛЮЧ", "volume": 1}]}}
        sources = [{"ключ": 10}, {"Ключ": 20}, {"ключ": 30}]
        assert self._run_merge(tmp_path, monkeypatch, sources, clean) == [("КЛЮЧ", 30)]

    def test_new_keyword_keeps_first_spelling(self, tmp_path, monkeypatch):
        sources = [{"Новый": 1}, {"новый": 2}]
        assert self._run_merge(tmp_path, monkeypatch, sources, None) == [("Новый", 2)]

    def _load_volumes(self, tmp_path, monkeypatch, capsys, lines: list[str]):
        csv_file = tmp_path / "key_all.csv"
        csv_file.write_text("Ключевое слово,Показов в месяц\n" + "\n".join(lines) + "\n", "utf-8")
        monkeypatch.setattr(update_volume, "CSV_FILE", csv_file)
        volumes = update_volume.load_csv_volumes()
        return volumes, capsys.readouterr().out

    def test_update_volume_keys_once_and_warns(self, tmp_path, monkeypatch, capsys):
        volumes, out = self._load_volumes(tmp_path, monkeypatch, capsys, ["Ёлка,10", "елка,20"])
        assert volumes == {"елка": 20}
        assert "'Ёлка'" in out
        assert "'елка'" in out

    def test_update_volume_same_volume_no_warning(self, tmp_path, monkeypatch, capsys):
        volumes, out = self._load_volumes(tmp_path, monkeypatch, capsys, ["Ёлка,10", "елка,10"])
        assert volumes == {"елка": 10}
        assert out == ""
