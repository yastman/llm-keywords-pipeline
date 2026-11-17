# tests/unit/test_sync_semantics.py
"""Tests for sync_semantics.py"""

import json

from llm_keywords_pipeline.sync.semantics import (
    build_keywords_list,
    build_synonyms_list,
    find_clean_json_path,
    group_by_category,
    load_master_csv,
    sync_category,
)


class TestGroupByCategory:
    """Test grouping rows by category."""

    def test_groups_correctly(self):
        """Should group rows by category."""
        rows = [
            {"category": "cat1", "keyword": "a"},
            {"category": "cat2", "keyword": "b"},
            {"category": "cat1", "keyword": "c"},
        ]
        grouped = group_by_category(rows)

        assert len(grouped) == 2
        assert len(grouped["cat1"]) == 2
        assert len(grouped["cat2"]) == 1


class TestFindCleanJsonPath:
    """Test finding _clean.json path for category."""

    def test_finds_direct_path(self, tmp_path):
        """Should find _clean.json in direct category folder."""
        cat_dir = tmp_path / "categories" / "test-cat" / "data"
        cat_dir.mkdir(parents=True)
        clean_file = cat_dir / "test-cat_clean.json"
        clean_file.write_text("{}", encoding="utf-8")

        result = find_clean_json_path("test-cat", tmp_path / "categories")
        assert result == clean_file

    def test_finds_nested_path(self, tmp_path):
        """Should find _clean.json in nested category folder."""
        cat_dir = tmp_path / "categories" / "parent" / "child" / "data"
        cat_dir.mkdir(parents=True)
        clean_file = cat_dir / "child_clean.json"
        clean_file.write_text("{}", encoding="utf-8")

        result = find_clean_json_path("child", tmp_path / "categories")
        assert result == clean_file


class TestBuildKeywordsList:
    """Test building keywords list from rows."""

    def test_builds_sorted_list(self):
        """Should build list sorted by volume DESC."""
        rows = [
            {"keyword": "low", "volume": 10, "type": "keyword", "use_in": ""},
            {"keyword": "high", "volume": 100, "type": "keyword", "use_in": ""},
        ]
        result = build_keywords_list(rows)

        assert len(result) == 2
        assert result[0]["keyword"] == "high"
        assert result[0]["volume"] == 100

    def test_excludes_synonyms(self):
        """Should exclude synonym type."""
        rows = [
            {"keyword": "kw", "volume": 100, "type": "keyword", "use_in": ""},
            {"keyword": "syn", "volume": 50, "type": "synonym", "use_in": ""},
        ]
        result = build_keywords_list(rows)

        assert len(result) == 1
        assert result[0]["keyword"] == "kw"


class TestBuildSynonymsList:
    """Test building synonyms list from rows."""

    def test_builds_sorted_list(self):
        """Should build list sorted by volume DESC."""
        rows = [
            {"keyword": "syn1", "volume": 10, "type": "synonym", "use_in": ""},
            {"keyword": "syn2", "volume": 50, "type": "synonym", "use_in": "meta_only"},
        ]
        result = build_synonyms_list(rows)

        assert len(result) == 2
        assert result[0]["keyword"] == "syn2"
        assert result[0]["use_in"] == "meta_only"


class TestSyncCategory:
    """Test syncing single category."""

    def test_preserves_existing_fields(self, tmp_path):
        """Should preserve id, name, parent_id, entities, micro_intents."""
        cat_dir = tmp_path / "categories" / "test-cat" / "data"
        cat_dir.mkdir(parents=True)

        existing = {
            "id": "test-cat",
            "name": "Test Category",
            "parent_id": "parent",
            "entities": ["entity1"],
            "micro_intents": ["intent1"],
            "keywords": [{"keyword": "old", "volume": 1}],
            "synonyms": [],
        }
        clean_file = cat_dir / "test-cat_clean.json"
        clean_file.write_text(json.dumps(existing, ensure_ascii=False), encoding="utf-8")

        rows = [
            {"keyword": "new", "volume": 100, "type": "keyword", "use_in": ""},
        ]

        sync_category("test-cat", rows, tmp_path / "categories", dry_run=False)

        result = json.loads(clean_file.read_text(encoding="utf-8"))
        assert result["name"] == "Test Category"
        assert result["parent_id"] == "parent"
        assert result["entities"] == ["entity1"]
        assert result["micro_intents"] == ["intent1"]
        assert result["keywords"][0]["keyword"] == "new"

    def test_dry_run_no_changes(self, tmp_path):
        """Should not modify file in dry-run mode."""
        cat_dir = tmp_path / "categories" / "test-cat" / "data"
        cat_dir.mkdir(parents=True)

        existing = {"id": "test-cat", "keywords": [{"keyword": "old", "volume": 1}]}
        clean_file = cat_dir / "test-cat_clean.json"
        clean_file.write_text(json.dumps(existing), encoding="utf-8")
        original_content = clean_file.read_text()

        rows = [{"keyword": "new", "volume": 100, "type": "keyword", "use_in": ""}]

        sync_category("test-cat", rows, tmp_path / "categories", dry_run=True)

        assert clean_file.read_text() == original_content


class TestSyncStatsTotals:
    """stats totals follow the synced keyword entries."""

    def _sync(self, tmp_path, data, rows):
        cat_dir = tmp_path / "categories" / "test-cat" / "data"
        cat_dir.mkdir(parents=True)
        clean_file = cat_dir / "test-cat_clean.json"
        clean_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        sync_category("test-cat", rows, tmp_path / "categories", dry_run=False)
        return json.loads(clean_file.read_text(encoding="utf-8"))

    def test_grouped_keywords_recompute_total_volume(self, tmp_path):
        data = {
            "id": "test-cat",
            "keywords": {
                "primary": [{"keyword": "a", "volume": 10}],
                "secondary": [{"keyword": "b", "volume": 5}, {"keyword": "gone", "volume": 7}],
            },
            "stats": {"before": 3, "after": 3, "total_volume": 22},
        }
        rows = [
            {"keyword": "a", "volume": 100, "type": "keyword", "use_in": ""},
            {"keyword": "b", "volume": 5, "type": "keyword", "use_in": ""},
            {"keyword": "new", "volume": 30, "type": "keyword", "use_in": ""},
            {"keyword": "syn", "volume": 1000, "type": "synonym", "use_in": ""},
        ]
        result = self._sync(tmp_path, data, rows)
        assert result["stats"] == {"before": 3, "after": 3, "total_volume": 135}

    def test_no_stats_not_added(self, tmp_path):
        data = {"id": "test-cat", "keywords": {"primary": [{"keyword": "a", "volume": 10}]}}
        rows = [{"keyword": "a", "volume": 100, "type": "keyword", "use_in": ""}]
        assert "stats" not in self._sync(tmp_path, data, rows)


class TestLoadMasterCsv:
    """Test loading master CSV."""

    def test_empty_volume_reads_as_zero(self, tmp_path):
        """An empty volume cell should be read as 0, no crash."""
        csv_path = tmp_path / "master.csv"
        csv_path.write_text(
            "keyword,volume,category,type,use_in\na,,cat1,keyword,\nb,7,cat1,keyword,\n",
            encoding="utf-8",
        )

        rows = load_master_csv(csv_path)

        assert [r["volume"] for r in rows] == [0, 7]
