"""TDD test: issue #13 — mypy scope and coverage floor must be honest.

- mypy is scoped to core/text.py and must not claim the full package.
- The pre-push hook's cov-fail-under must not flip on minor changes (20, not 24).
"""

from pathlib import Path

ROOT = Path(__file__).parents[2]
PYPROJECT = ROOT / "pyproject.toml"
PRE_COMMIT_CONFIG = ROOT / ".pre-commit-config.yaml"


class TestMypyConfig:
    """pyproject.toml mypy config must honestly scope to core/text.py."""

    def test_mypy_files_lists_core_text(self):
        """mypy files must include core/text.py."""
        content = PYPROJECT.read_text()
        assert "core/text.py" in content

    def test_mypy_does_not_claim_full_package(self):
        """mypy files must NOT list the full src package as the only source."""
        content = PYPROJECT.read_text()
        # The misleading pattern would be files = ["src/llm_keywords_pipeline"]
        # without any module names — current config is core/text.py, that's fine.
        assert 'files = ["src/llm_keywords_pipeline"]' not in content


class TestCoverageGate:
    """The pre-push hook's coverage floor must leave headroom."""

    def test_coverage_gate_not_equal_to_actual(self):
        """cov-fail-under must not be equal to current coverage (fragile gate).

        Current coverage is ~24%. A gate of 24 is fragile — set to 20 to give
        headroom while still catching large regressions.
        """
        content = PRE_COMMIT_CONFIG.read_text()
        assert "--cov-fail-under=20" in content
        # 24 is the fragile value — we need something below current coverage
        assert "--cov-fail-under=24" not in content, (
            "Coverage gate --cov-fail-under=24 equals actual coverage; "
            "lower to 20 for a stable floor"
        )
