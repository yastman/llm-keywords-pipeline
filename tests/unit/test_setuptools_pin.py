"""TDD test: issue #2/#12 — setuptools<71 pin must be removed.

The <71 upper bound was a workaround to suppress pkg_resources DeprecationWarning
from pymorphy2 (pulled in by natasha). Since PR #25 already adds a targeted
filterwarnings entry for pymorphy2, the pin is no longer needed and blocks
future updates.
"""

from pathlib import Path

PYPROJECT = Path(__file__).parents[2] / "pyproject.toml"


class TestSetuptoolsPin:
    """pyproject.toml must not pin setuptools below version 71."""

    def test_no_setuptools_upper_pin(self):
        """setuptools<71 must not appear in pyproject.toml."""
        content = PYPROJECT.read_text()
        assert "setuptools<71" not in content, (
            "setuptools<71 is a workaround pin — remove it now that "
            "pkg_resources DeprecationWarning is handled via filterwarnings"
        )

    def test_audit_water_importable(self):
        """audit.water must import successfully (no ModuleNotFoundError)."""
        import llm_keywords_pipeline.audit.water  # noqa: F401

    def test_water_lemmatizes_without_pkg_resources(self, monkeypatch):
        """audit.water must not need pkg_resources (gone from setuptools>=81)."""
        import sys

        from llm_keywords_pipeline.audit import water

        monkeypatch.setitem(sys.modules, "pkg_resources", None)
        monkeypatch.setattr(water, "_NLP_CACHE", {})
        vocab = water.get_nlp_pipeline()["morph_vocab"]
        assert vocab("столы")[0].normal == "стол"
