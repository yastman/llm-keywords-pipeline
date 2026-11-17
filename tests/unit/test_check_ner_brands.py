import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from llm_keywords_pipeline.audit import ner_brands
from llm_keywords_pipeline.audit.ner_brands import (
    analyze_file,
    check_blacklist,
    clean_markdown,
    is_false_positive_location,
)
from llm_keywords_pipeline.core.project import ProjectConfig


class TestCheckNerBrands(unittest.TestCase):
    def test_is_false_positive_location(self):
        # "ровно" is in FALSE_POSITIVE_CITIES

        # 1. No preposition -> False Positive (True)
        self.assertTrue(is_false_positive_location("ровно", "отрезал ровно половину"))
        self.assertTrue(is_false_positive_location("Ровно", "Лежит Ровно посередине"))

        # 2. With preposition -> Real City (False)
        self.assertFalse(is_false_positive_location("ровно", "поехал в ровно на машине"))
        self.assertFalse(is_false_positive_location("Ровно", "из Ровно привезли"))
        self.assertFalse(is_false_positive_location("ровно", "до ровно пять километров"))

        # 3. "суми" (mistake for "суммы" or city)
        self.assertTrue(is_false_positive_location("суми", "большие суми денег"))
        self.assertFalse(is_false_positive_location("суми", "в суми отличная погода"))

        # 4. Word NOT in false positive list -> Always Real City (False)
        self.assertFalse(is_false_positive_location("киев", "просто киев стоит"))

    def test_check_blacklist_brands(self):
        # Test detection of banned brands
        text = "Мы продаем технику Karcher и химию Grass для авто."
        project = ProjectConfig(blacklist_brands=("karcher", "grass"))
        with patch.object(ner_brands, "get_project", return_value=project):
            results = check_blacklist(text)

        brands_found = [item["entity"] for item in results["brands"]]
        self.assertIn("karcher", brands_found)
        self.assertIn("grass", brands_found)
        self.assertEqual(len(results["brands"]), 2)

    def test_check_blacklist_cities(self):
        # Test detection of banned cities
        text = "Доставка в Киев, Харьков и Одессу возможна."
        results = check_blacklist(text)

        cities_found = [item["entity"] for item in results["cities"]]
        self.assertIn("киев", cities_found)
        self.assertIn("харьков", cities_found)
        # "одесса" is not a substring of "одессу"; the lemma pass catches it
        self.assertIn("одесса", cities_found)

        # Let's test exact match
        text2 = "Город Одесса красивый."
        results2 = check_blacklist(text2)
        self.assertIn("одесса", [item["entity"] for item in results2["cities"]])

    def test_city_parse_skips_language_without_morph(self):
        """A language whose analyzer has no `_morph` is skipped, not dereferenced."""
        from llm_keywords_pipeline.audit import ner_brands

        real = ner_brands.MorphAnalyzer

        class Stub:
            def __init__(self, lang):
                self._morph = None if lang == "uk" else real(lang)._morph

        ner_brands._city_parse.cache_clear()
        try:
            with patch.object(ner_brands, "MorphAnalyzer", Stub):
                self.assertIsNone(ner_brands._city_parse("києві"))
                self.assertEqual(ner_brands._city_parse("киеву")[0], "киев")
        finally:
            ner_brands._city_parse.cache_clear()

    def test_check_blacklist_ai_fluff(self):
        # Test AI fluff detection
        text = "В заключение, стоит отметить, что этот товар уникален."
        results = check_blacklist(text)

        fluff_found = [item["entity"] for item in results["ai_fluff"]]
        # expected matches based on patterns
        # "в заключение"
        # "стоит отметить"

        self.assertTrue(any("в заключение" in f for f in fluff_found))
        self.assertTrue(any("стоит отметить" in f for f in fluff_found))

    def test_clean_markdown(self):
        md_text = """
# Header
Some [link](url) here.
**Bold** text.
---
Frontmatter
---
* List item
"""
        cleaned = clean_markdown(md_text)
        self.assertNotIn("# Header", cleaned)  # Headers usually removed or hash removed
        self.assertNotIn("[link](url)", cleaned)  # Links simplified
        self.assertNotIn("**Bold**", cleaned)  # Formatting removed
        self.assertIn("Some link here", cleaned)
        self.assertIn("Bold text", cleaned)

    def test_analyze_file_safe_pass(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_file = Path(tmpdir) / "safe.md"
            temp_file.write_text(
                "Хороший текст про полировку автомобиля. Без брендов.", encoding="utf-8"
            )

            with patch("builtins.print"):
                exit_code = analyze_file(str(temp_file))

        self.assertEqual(exit_code, 0)

    def test_analyze_file_warning(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_file = Path(tmpdir) / "warning.md"
            temp_file.write_text("Мы продаем Karcher в Киеве. В заключение...", encoding="utf-8")

            with patch("builtins.print"):
                exit_code = analyze_file(str(temp_file))

        self.assertEqual(exit_code, 1)

    def test_check_blacklist_uk_lists(self):
        text = (
            "У цій статті ви дізнаєтеся, як мити авто. Варто зазначити: "
            "широкий асортимент є невід’ємною частиною магазину."
        )
        results = check_blacklist(text, "uk")

        fluff_found = [item["entity"] for item in results["ai_fluff"]]
        self.assertIn("у цій статті", fluff_found)
        self.assertIn("ви дізнаєтеся", fluff_found)
        self.assertIn("варто зазначити", fluff_found)
        strict_found = [item["entity"] for item in results["strict_phrases"]]
        self.assertEqual(strict_found, ["широкий асортимент", "є невід’ємною частиною"])

    def test_check_blacklist_ru_lists_unchanged(self):
        text = "В современном мире, стоит отметить, широкий ассортимент безусловно важен."
        results = check_blacklist(text)

        self.assertEqual(results, check_blacklist(text, "ru"))
        self.assertEqual(
            [item["entity"] for item in results["ai_fluff"]], ["стоит отметить", "безусловно"]
        )
        self.assertEqual(
            [item["entity"] for item in results["strict_phrases"]],
            ["в современном мире", "широкий ассортимент"],
        )
        # RU text is not checked against the UK lists.
        uk_results = check_blacklist(text, "uk")
        self.assertEqual(uk_results["ai_fluff"], [])
        self.assertEqual(uk_results["strict_phrases"], [])

    def test_analyze_file_uses_uk_lists_for_uk_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_file = Path(tmpdir) / "uk" / "categories" / "x" / "content.md"
            temp_file.parent.mkdir(parents=True)
            temp_file.write_text("Підбиваючи підсумки, засіб добре миє.", encoding="utf-8")

            with patch("builtins.print"):
                exit_code = analyze_file(str(temp_file))

        self.assertEqual(exit_code, 1)

    def test_check_blacklist_uk_fluff_both_reflexive_forms(self):
        for text in ("Ви дізнаєтеся все.", "Ви дізнаєтесь все."):
            fluff_found = [item["entity"] for item in check_blacklist(text, "uk")["ai_fluff"]]
            self.assertEqual(fluff_found, [text.lower().removesuffix(" все.")])

    def _analyze_uk_strict_only(self, output_json: bool) -> tuple[int, str]:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_file = Path(tmpdir) / "uk" / "categories" / "x" / "content.md"
            temp_file.parent.mkdir(parents=True)
            temp_file.write_text("Магазин пропонує широкий асортимент засобів.", encoding="utf-8")

            with patch("builtins.print") as mock_print:
                exit_code = analyze_file(str(temp_file), output_json=output_json)
        printed = "\n".join(str(c.args[0]) for c in mock_print.call_args_list if c.args)
        return exit_code, printed

    def test_analyze_file_uk_strict_only_json(self):
        exit_code, printed = self._analyze_uk_strict_only(output_json=True)

        summary = json.loads(printed)["summary"]
        self.assertEqual(exit_code, 1)
        self.assertEqual(summary["strict_count"], 1)
        self.assertEqual(summary["total_issues"], 1)
        self.assertEqual(summary["status"], "FAIL")

    def test_analyze_file_fluff_without_strict_is_warning(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_file = Path(tmpdir) / "ru.md"
            temp_file.write_text("В заключение, средство хорошо моет.", encoding="utf-8")

            with patch("builtins.print") as mock_print:
                exit_code = analyze_file(str(temp_file), output_json=True)
        summary = json.loads(mock_print.call_args.args[0])["summary"]

        self.assertEqual(exit_code, 1)
        self.assertEqual(summary["strict_count"], 0)
        self.assertEqual(summary["status"], "WARNING")

    def test_analyze_file_uk_strict_only_text(self):
        exit_code, printed = self._analyze_uk_strict_only(output_json=False)

        self.assertEqual(exit_code, 1)
        self.assertIn("STRICT-ФРАЗЫ (1)", printed)
        self.assertIn('"широкий асортимент"', printed)
        self.assertIn("FAIL", printed)
        self.assertNotIn("PASS", printed)


if __name__ == "__main__":
    unittest.main()
