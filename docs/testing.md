# Testing

The project uses `pytest` with `pytest.ini` as the source of truth for test discovery and
default options. Coverage settings live in `.coveragerc`.

## Default Checks

These are the commands used by the README:

```bash
uv sync --frozen
uv run ruff check src tests
uv run mypy
uv run pytest
uv build
```

To inspect collection:

```bash
uv run pytest --collect-only -q
```

Coverage:

```bash
uv run pytest --cov=src/llm_keywords_pipeline --cov-report=term-missing
```

## Test Tiers

| Tier | Location | Purpose |
| --- | --- | --- |
| Unit | `tests/unit/` | Fast checks for isolated functions and deterministic behavior. |
| Integration | `tests/integration/` | File and pipeline interactions using fixtures or temporary paths. |
| Smoke | `tests/smoke/` | Broad sanity checks for important modules. |
| E2E | `tests/e2e/` | End-to-end scenarios when available. |
| Fixtures | `tests/fixtures/` | Synthetic public data used by tests. |

## Data-Required Tests

Some tests can run against production category/content datasets when they are available.
The public repository does not include those datasets. Such tests should either use
public fixtures or skip with an explicit reason when production data is absent.

Skips caused by missing production data are acceptable only when they are intentional and
documented. They should not hide failures in the default fixture-backed suite.

## Git Hooks

There is no remote CI: the local git hooks in `.pre-commit-config.yaml` are the only
gate. Install them once per clone:

```bash
uv run pre-commit install --hook-type pre-commit --hook-type pre-push
```

The pre-commit hook runs on staged files:

```bash
uv run ruff check --fix --exit-non-zero-on-fix --unsafe-fixes
uv run ruff format
# plus file hygiene: check-json/toml/yaml, merge markers, large files,
# private keys, trailing whitespace, end-of-file newline
```

The pre-push hook runs on the whole repository:

```bash
uv lock --check
uv run ruff check src tests
uv run mypy
uv run pytest -q --cov-fail-under=20
```

`uv build` is not part of any hook; run it by hand when packaging changes.

If local commands change, update README, this file, `tests/README.md`, and
`.pre-commit-config.yaml` together.
