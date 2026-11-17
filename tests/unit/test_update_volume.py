"""Tests for update_volume.py"""

import json

from llm_keywords_pipeline.sync.update_volume import update_category


class TestUpdateCategory:
    """Test category update."""

    def test_updates_keyword_volumes(self, tmp_path):
        """Should update keyword volumes from volumes dict."""
        clean_file = tmp_path / "test_clean.json"
        data = {
            "keywords": [{"keyword": "тест", "volume": 0}, {"keyword": "проверка", "volume": 50}]
        }
        clean_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        volumes = {"тест": 100, "проверка": 50}  # проверка unchanged
        updated, total = update_category(clean_file, volumes)

        assert total == 2
        assert updated == 1  # only тест changed

        # Verify file was updated
        result = json.loads(clean_file.read_text(encoding="utf-8"))
        assert result["keywords"][0]["volume"] == 100

    def test_updates_synonym_volumes(self, tmp_path):
        """Should also update synonym volumes."""
        clean_file = tmp_path / "test_clean.json"
        data = {"keywords": [], "synonyms": [{"keyword": "синоним", "volume": 0}]}
        clean_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        volumes = {"синоним": 200}
        updated, total = update_category(clean_file, volumes)

        assert total == 1
        assert updated == 1

    def test_no_update_when_volume_unchanged(self, tmp_path):
        """Should not count as updated when volume is same."""
        clean_file = tmp_path / "test_clean.json"
        data = {"keywords": [{"keyword": "тест", "volume": 100}]}
        clean_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        volumes = {"тест": 100}  # Same value
        updated, total = update_category(clean_file, volumes)

        assert updated == 0

    def test_returns_zero_for_missing_keywords(self, tmp_path):
        """Should return 0 updated when keywords not in volumes dict."""
        clean_file = tmp_path / "test_clean.json"
        data = {"keywords": [{"keyword": "нет в словаре", "volume": 0}]}
        clean_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        volumes = {"другой ключ": 100}
        updated, total = update_category(clean_file, volumes)

        assert updated == 0
        assert total == 1

    def test_updates_dict_grouped_keywords_and_keeps_shape(self, tmp_path):
        """Should update volumes when keywords is a dict of groups and keep the dict."""
        clean_file = tmp_path / "test_clean.json"
        data = {
            "keywords": {
                "primary": [{"keyword": "a", "volume": 0}],
                "secondary": [{"keyword": "b", "volume": 5}],
                "supporting": [],
                "commercial": [{"keyword": "c", "volume": 0}],
            }
        }
        clean_file.write_text(json.dumps(data), encoding="utf-8")

        updated, total = update_category(clean_file, {"a": 10, "b": 5, "c": 30})

        assert (updated, total) == (2, 3)
        result = json.loads(clean_file.read_text(encoding="utf-8"))
        assert result["keywords"]["primary"] == [{"keyword": "a", "volume": 10}]
        assert result["keywords"]["secondary"] == [{"keyword": "b", "volume": 5}]
        assert result["keywords"]["supporting"] == []
        assert result["keywords"]["commercial"] == [{"keyword": "c", "volume": 30}]


class TestStatsTotalVolume:
    """stats.total_volume follows updated keyword volumes (both keyword shapes)."""

    def _run(self, tmp_path, data, volumes):
        clean_file = tmp_path / "x_clean.json"
        clean_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        update_category(clean_file, volumes)
        return json.loads(clean_file.read_text(encoding="utf-8"))

    def test_flat_keywords_recompute_total_volume(self, tmp_path):
        data = {
            "keywords": [{"keyword": "a", "volume": 10}, {"keyword": "b", "volume": 5}],
            "synonyms": [{"keyword": "s", "volume": 1}],
            "stats": {"before": 2, "after": 2, "total_volume": 15},
        }
        result = self._run(tmp_path, data, {"a": 100, "s": 7})
        assert result["stats"] == {"before": 2, "after": 2, "total_volume": 105}

    def test_grouped_keywords_recompute_total_volume(self, tmp_path):
        data = {
            "keywords": {
                "primary": [{"keyword": "a", "volume": 10}],
                "secondary": [{"keyword": "b", "volume": 5}],
            },
            "stats": {"total_volume": 15},
        }
        result = self._run(tmp_path, data, {"b": 50})
        assert result["stats"]["total_volume"] == 60

    def test_no_stats_not_added(self, tmp_path):
        data = {"keywords": [{"keyword": "a", "volume": 10}]}
        assert "stats" not in self._run(tmp_path, data, {"a": 20})
