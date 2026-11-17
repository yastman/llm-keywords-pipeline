# tests/unit/test_merge_to_master.py
"""Tests for merge_to_master.py"""

import json

from llm_keywords_pipeline.sync.merge_master import (
    collect_from_clean_json,
    find_clean_json_files,
    load_excel_keywords,
    merge_keywords,
    save_master_csv,
)


class TestFindCleanJsonFiles:
    """Test finding _clean.json files."""

    def test_finds_nested_files(self, tmp_path):
        """Should find _clean.json in nested structure."""
        # Create nested structure
        cat1 = tmp_path / "cat1" / "data"
        cat1.mkdir(parents=True)
        (cat1 / "cat1_clean.json").write_text("{}", encoding="utf-8")

        cat2 = tmp_path / "cat1" / "sub" / "data"
        cat2.mkdir(parents=True)
        (cat2 / "sub_clean.json").write_text("{}", encoding="utf-8")

        files = find_clean_json_files(tmp_path)
        assert len(files) == 2


class TestCollectFromCleanJson:
    """Test collecting keywords from _clean.json."""

    def test_collects_keywords_list_format(self, tmp_path):
        """Should collect keywords from list format."""
        data = {
            "id": "test-cat",
            "keywords": [
                {"keyword": "ключ1", "volume": 100},
                {"keyword": "ключ2", "volume": 50},
            ],
            "synonyms": [
                {"keyword": "синоним", "volume": 30},
                {"keyword": "meta", "volume": 20, "use_in": "meta_only"},
            ],
        }
        clean_file = tmp_path / "test-cat" / "data" / "test-cat_clean.json"
        clean_file.parent.mkdir(parents=True)
        clean_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        rows = collect_from_clean_json(clean_file)

        assert len(rows) == 4
        assert rows[0] == {
            "keyword": "ключ1",
            "volume": 100,
            "category": "test-cat",
            "type": "keyword",
            "use_in": "",
        }
        assert rows[3] == {
            "keyword": "meta",
            "volume": 20,
            "category": "test-cat",
            "type": "synonym",
            "use_in": "meta_only",
        }

    def test_collects_keywords_dict_format(self, tmp_path):
        """Should collect keywords from dict format (legacy)."""
        data = {
            "id": "test-cat",
            "keywords": {
                "primary": [{"keyword": "primary", "volume": 100}],
                "secondary": [{"keyword": "secondary", "volume": 50}],
            },
        }
        clean_file = tmp_path / "test-cat" / "data" / "test-cat_clean.json"
        clean_file.parent.mkdir(parents=True)
        clean_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        rows = collect_from_clean_json(clean_file)

        assert len(rows) == 2


class TestLoadExcelKeywords:
    """Test loading keywords from Excel."""

    def test_loads_excel_with_standard_columns(self, tmp_path):
        """Should load Excel with 'Ключевое слово' and 'Точное вхождение'."""
        # Create test Excel using pandas
        import pandas as pd

        df = pd.DataFrame(
            {
                "Ключевое слово": ["тест1", "тест2"],
                "Точное вхождение": [100, 200],
            }
        )
        excel_path = tmp_path / "test.xlsx"
        df.to_excel(excel_path, index=False)

        keywords = load_excel_keywords(excel_path)

        assert keywords == {"тест1": 100, "тест2": 200}

    def test_keeps_original_keyword_form(self, tmp_path):
        """Excel keywords keep case, ё and ’ (only surrounding spaces stripped)."""
        import pandas as pd

        df = pd.DataFrame({"Ключевое слово": [" Пам’ять Ёлки "], "Точное вхождение": [7]})
        excel_path = tmp_path / "test.xlsx"
        df.to_excel(excel_path, index=False)

        assert load_excel_keywords(excel_path) == {"Пам’ять Ёлки": 7}


class TestMergeKeywords:
    """Test merging keywords."""

    def test_updates_volume_from_excel(self):
        """Should update volume from Excel data."""
        existing = [
            {"keyword": "ключ", "volume": 50, "category": "cat1", "type": "keyword", "use_in": ""},
        ]
        excel = {"ключ": 100}

        result = merge_keywords(existing, excel)

        assert result[0]["volume"] == 100

    def test_adds_new_keywords_as_uncategorized(self):
        """Should add new keywords from Excel as uncategorized."""
        existing = []
        excel = {"новый": 200}

        result = merge_keywords(existing, excel)

        assert len(result) == 1
        assert result[0]["category"] == "uncategorized"
        assert result[0]["type"] == "keyword"

    def test_case_yo_apostrophe_variants_match(self):
        """Excel 'пам'ять елки' updates the existing 'Пам’ять Ёлки' row, no new row."""
        existing = [
            {
                "keyword": "Пам’ять Ёлки",
                "volume": 5,
                "category": "cat1",
                "type": "keyword",
                "use_in": "",
            },
        ]

        result = merge_keywords(existing, {"пам'ять елки": 40})

        assert len(result) == 1
        assert result[0]["volume"] == 40
        assert result[0]["keyword"] == "Пам’ять Ёлки"

    def test_dedups_case_yo_variants_in_category(self):
        """Two spellings of one keyword in one category and type collapse to one row."""
        existing = [
            {"keyword": "Ёлка", "volume": 5, "category": "c", "type": "keyword", "use_in": ""},
            {"keyword": "елка", "volume": 9, "category": "c", "type": "keyword", "use_in": ""},
        ]

        result = merge_keywords(existing, {})

        assert len(result) == 1
        assert result[0]["volume"] == 9

    def test_new_keyword_written_in_original_form(self, tmp_path):
        """A new Excel keyword reaches the master CSV unchanged."""
        result = merge_keywords([], {"Пам’ять Ёлки": 3})
        csv_path = tmp_path / "master.csv"

        save_master_csv(result, csv_path)

        lines = csv_path.read_text(encoding="utf-8").strip().split("\n")
        assert lines[1].startswith("Пам’ять Ёлки,3,")

    def test_updates_volume_for_every_row_of_keyword(self):
        """Excel volume should apply to the keyword in every category and type."""
        existing = [
            {"keyword": "ключ", "volume": 50, "category": "cat1", "type": "keyword", "use_in": ""},
            {"keyword": "Ключ", "volume": 60, "category": "cat2", "type": "keyword", "use_in": ""},
            {"keyword": "ключ", "volume": 70, "category": "cat1", "type": "synonym", "use_in": ""},
        ]

        result = merge_keywords(existing, {"ключ": 100})

        assert len(result) == 3
        assert [r["volume"] for r in result] == [100, 100, 100]

    def test_deduplicates_within_category_and_type(self):
        """Should keep keyword with higher volume on duplicate in the same category and type."""
        existing = [
            {"keyword": "ключ", "volume": 50, "category": "cat1", "type": "keyword", "use_in": ""},
            {"keyword": "Ключ", "volume": 100, "category": "cat1", "type": "keyword", "use_in": ""},
        ]

        result = merge_keywords(existing, {})

        assert len(result) == 1
        assert result[0]["volume"] == 100

    def test_dedup_treats_null_volume_as_zero(self):
        """A null volume on a duplicate should lose to a real volume, no crash."""
        existing = [
            {
                "keyword": "ключ",
                "volume": None,
                "category": "cat1",
                "type": "keyword",
                "use_in": "",
            },
            {"keyword": "ключ", "volume": 10, "category": "cat1", "type": "keyword", "use_in": ""},
            {
                "keyword": "ключ",
                "volume": None,
                "category": "cat1",
                "type": "keyword",
                "use_in": "",
            },
        ]

        result = merge_keywords(existing, {})

        assert len(result) == 1
        assert result[0]["volume"] == 10

    def test_keeps_same_phrase_in_two_categories(self):
        """The same phrase in two categories should yield one row each."""
        existing = [
            {"keyword": "ключ", "volume": 50, "category": "cat1", "type": "keyword", "use_in": ""},
            {"keyword": "ключ", "volume": 100, "category": "cat2", "type": "keyword", "use_in": ""},
        ]

        result = merge_keywords(existing, {})

        assert sorted((r["category"], r["volume"]) for r in result) == [("cat1", 50), ("cat2", 100)]

    def test_keeps_phrase_as_keyword_and_synonym(self):
        """The same phrase as keyword and synonym in one category should yield both rows."""
        existing = [
            {"keyword": "ключ", "volume": 100, "category": "cat1", "type": "keyword", "use_in": ""},
            {"keyword": "ключ", "volume": 50, "category": "cat1", "type": "synonym", "use_in": ""},
        ]

        result = merge_keywords(existing, {})

        assert sorted(r["type"] for r in result) == ["keyword", "synonym"]


class TestSaveMasterCsv:
    """Test saving master CSV."""

    def test_saves_sorted_csv(self, tmp_path):
        """Should save CSV sorted by category, then volume DESC."""
        rows = [
            {"keyword": "b", "volume": 50, "category": "cat2", "type": "keyword", "use_in": ""},
            {"keyword": "a", "volume": 100, "category": "cat1", "type": "keyword", "use_in": ""},
            {"keyword": "c", "volume": 200, "category": "cat1", "type": "keyword", "use_in": ""},
        ]
        csv_path = tmp_path / "master.csv"

        save_master_csv(rows, csv_path)

        content = csv_path.read_text(encoding="utf-8")
        lines = content.strip().split("\n")
        assert len(lines) == 4  # header + 3 rows
        assert "cat1" in lines[1]  # cat1 first (alphabetically)
        assert "200" in lines[1]  # highest volume first

    def test_null_volume_sorts_as_zero(self, tmp_path):
        """A null volume from _clean.json should sort as 0, no crash."""
        rows = [
            {"keyword": "a", "volume": None, "category": "cat1", "type": "keyword", "use_in": ""},
            {"keyword": "b", "volume": 5, "category": "cat1", "type": "keyword", "use_in": ""},
        ]
        csv_path = tmp_path / "master.csv"

        save_master_csv(rows, csv_path)

        lines = csv_path.read_text(encoding="utf-8").strip().split("\n")
        assert lines[1].startswith("b,5,")
        assert lines[2].startswith("a,,")
