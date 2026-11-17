"""UK lookups prefer real data under PROJECT_ROOT and fall back to the hand-written fixture."""

import importlib

import pytest

from tests.fixtures.real_data import UK_FIXTURE_CLEAN, UK_FIXTURE_CONTENT, UK_FIXTURE_SLUG

MODULES = [
    "tests.smoke.test_validators_smoke",
    "tests.smoke.test_text_utils_smoke",
    "tests.integration.test_validation_pipeline",
]


@pytest.mark.parametrize("module_name", MODULES)
def test_real_uk_content_wins_over_fixture(module_name, tmp_path, monkeypatch):
    module = importlib.import_module(module_name)
    real = tmp_path / "uk" / "categories" / UK_FIXTURE_SLUG / "content" / f"{UK_FIXTURE_SLUG}_uk.md"
    real.parent.mkdir(parents=True)
    real.write_text("# real", encoding="utf-8")
    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)

    assert module.find_uk_content(UK_FIXTURE_SLUG) == real


@pytest.mark.parametrize("module_name", MODULES)
def test_fixture_used_when_real_uk_content_absent(module_name, tmp_path, monkeypatch):
    module = importlib.import_module(module_name)
    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)

    assert module.find_uk_content(UK_FIXTURE_SLUG) == UK_FIXTURE_CONTENT
    assert module.find_uk_content("no-such-slug") is None


def test_uk_clean_fixture_used_when_real_data_absent(tmp_path, monkeypatch):
    module = importlib.import_module("tests.integration.test_validation_pipeline")
    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)

    assert module.find_uk_clean(UK_FIXTURE_SLUG) == UK_FIXTURE_CLEAN
