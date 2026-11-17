"""TDD test: issue #15 — prompts must reflect actual code thresholds.

Confirmed discrepancies:
1. seo.py docstring says "100 символов" but limit=150.
2. deliver.md uses density values that don't match SPAM/WARNING_THRESHOLD in density.py.
Fix: update seo.py docstring to 150; add a note in deliver.md that thresholds come from code.
"""

import re
from pathlib import Path

from llm_keywords_pipeline.core.config import QUALITY_THRESHOLDS as Q
from llm_keywords_pipeline.validate.density import (
    OPTIMAL_RANGE,
    SPAM_THRESHOLD,
    WARNING_THRESHOLD,
)

ROOT = Path(__file__).parents[2]
SEO_PY = ROOT / "src" / "llm_keywords_pipeline" / "validate" / "seo.py"
DELIVER_MD = ROOT / "prompts" / "deliver.md"
DENSITY_PY = ROOT / "src" / "llm_keywords_pipeline" / "validate" / "density.py"


class TestCodeThresholdsConsistency:
    """Code constants must be self-consistent across modules."""

    def test_seo_intro_limit_in_docstring(self):
        """seo.py docstring must not claim 100 chars when code uses 150."""
        content = SEO_PY.read_text()
        # The docstring incorrectly says "в первых 100 символах"
        assert "в первых 100 символах" not in content, (
            "seo.py docstring claims 100-char intro limit but code uses 150"
        )

    def test_density_thresholds_documented(self):
        """density.py must have SPAM_THRESHOLD and WARNING_THRESHOLD as named constants."""
        content = DENSITY_PY.read_text()
        assert "SPAM_THRESHOLD" in content
        assert "WARNING_THRESHOLD" in content

    def test_deliver_md_acknowledges_code_thresholds(self):
        """deliver.md must note that actual thresholds come from code, not the table."""
        content = DELIVER_MD.read_text()
        # After fix: deliver.md should note SPAM/WARNING come from density.py
        assert "density.py" in content or "SPAM_THRESHOLD" in content or "код" in content.lower(), (
            "deliver.md must reference that density thresholds come from code constants"
        )


PROMPTS = ROOT / "prompts"
_NUM = r"(\d+(?:\.\d+)?)"
_RANGE = re.compile(_NUM + r"-" + _NUM + r"%")


def _lines(name: str, marker: str) -> list[str]:
    lines = [ln for ln in (PROMPTS / name).read_text(encoding="utf-8").splitlines() if marker in ln]
    assert lines, f"{name}: no line with {marker!r}"
    return lines


def _ranges(lines: list[str]) -> set[tuple[float, float]]:
    return {(float(a), float(b)) for ln in lines for a, b in _RANGE.findall(ln)}


class TestPromptNumbersMatchCode:
    """Threshold numbers in prompts equal core/config.py and validate/density.py."""

    def test_deliver_water_range(self):
        lines = _lines("deliver.md", "Water")
        water = (Q["water_target_min"], Q["water_target_max"])
        assert _ranges(lines) == {water}
        maxes = {float(m) for ln in lines for m in re.findall(r"max " + _NUM + "%", ln)}
        assert maxes <= {Q["water_target_max"]}

    def test_deliver_nausea(self):
        classic = _lines("deliver.md", "Classic Nausea")
        assert all(f"≤{Q['nausea_classic_target']:g}" in ln for ln in classic)
        academic = _lines("deliver.md", "Academic Nausea")
        expected = f"{Q['nausea_academic_min']:g}-{Q['nausea_academic_max']:g}%"
        assert all(expected in ln for ln in academic)

    def test_density_numbers(self):
        optimal = (float(OPTIMAL_RANGE[0]), float(OPTIMAL_RANGE[1]))
        deliver = (PROMPTS / "deliver.md").read_text(encoding="utf-8")
        assert f"| >{SPAM_THRESHOLD}% | >{WARNING_THRESHOLD}% | {optimal[0]}-{optimal[1]}% |" in (
            deliver
        )
        assert _ranges(_lines("deliver.md", "Density:")) == {optimal}
        main_kw = _lines("deliver.md", "Main keyword:")
        assert _ranges(main_kw) == {optimal}
        assert all(
            f"warning >{WARNING_THRESHOLD}%" in ln and f"spam >{SPAM_THRESHOLD}%" in ln
            for ln in main_kw
        )
        assert _ranges(_lines("prepare.md", "density")) == {optimal}

    def test_produce_meta_lengths(self):
        title = _lines("produce.md", "`title`:")
        assert f"{Q['title_min']}-{Q['title_max']} chars" in title[0]
        desc = _lines("produce.md", "`description`:")
        assert f"{Q['description_min']}-{Q['description_max']} chars" in desc[0]
