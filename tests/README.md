# Test Suite

Automated tests for `llm-keywords-pipeline` use `pytest`.

The source of truth for test strategy and commands is [../docs/testing.md](../docs/testing.md).

Default checks:

```bash
uv sync --frozen
uv run ruff check src tests
uv run mypy
uv run pytest
uv build
```

Git hooks (`.pre-commit-config.yaml`, the only gate; no remote CI): install with
`uv run pre-commit install --hook-type pre-commit --hook-type pre-push`. Pre-commit runs
ruff check, ruff format and file hygiene on staged files; pre-push runs `uv lock --check`,
`uv run ruff check src tests`, `uv run mypy` and `uv run pytest -q --cov-fail-under=20`.

Test layout:

```text
tests/
├── unit/          # isolated function tests
├── integration/   # file and pipeline interactions
├── e2e/           # end-to-end scenarios when available
├── smoke/         # broad sanity checks
├── fixtures/      # public synthetic test data
├── helpers/       # test utilities
└── conftest.py    # shared fixtures
```

Some tests are data-required and may skip when private category/content datasets are not
available. Public tests should prefer fixtures and `tmp_path`.
