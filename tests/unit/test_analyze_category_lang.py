"""analyze.category honours --lang: no RU fallback for uk, --list per lang, argparse CLI (B21)."""

import json
import subprocess
import sys

import pytest

from llm_keywords_pipeline.analyze import category
from llm_keywords_pipeline.batch import generate

RU_CSV = "L3: Антибитум,,\nантибитум,,100\nочиститель битума,,50\n"


@pytest.fixture
def project(tmp_path, monkeypatch):
    csv_path = tmp_path / "semantics.csv"
    csv_path.write_text(RU_CSV, encoding="utf-8")
    monkeypatch.setattr(category, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(category, "SEMANTICS_CSV", csv_path)
    return tmp_path


def write_uk_raw(root, slug, keywords):
    data_dir = root / "uk" / "categories" / slug / "data"
    data_dir.mkdir(parents=True)
    payload = {"keywords": {"primary": [{"keyword": k, "volume": v} for k, v in keywords]}}
    (data_dir / f"{slug}.json").write_text(json.dumps(payload), encoding="utf-8")


def run_main(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["category", *args])
    with pytest.raises(SystemExit) as exc:
        category.main()
        raise SystemExit(0)
    return exc.value.code


def test_uk_without_uk_data_fails_naming_uk_file(project, monkeypatch, capsys):
    code = run_main(monkeypatch, "antibitum", "--lang", "uk", "--json")

    out = capsys.readouterr().out
    assert code not in (0, None)
    assert "uk/categories/antibitum/data/antibitum_clean.json" in out
    assert "очиститель битума" not in out


def test_ru_still_falls_back_to_csv(project, monkeypatch, capsys):
    code = run_main(monkeypatch, "antibitum", "--json")

    assert code in (0, None)
    result = json.loads(capsys.readouterr().out)
    assert result["meta"]["source"] == "csv"


@pytest.mark.parametrize(
    "args",
    [
        ("antybitum", "--lang", "uk", "--json"),
        ("--lang", "uk", "antybitum", "--json"),
        ("--json", "--lang", "uk", "antybitum"),
    ],
)
def test_slug_and_lang_parse_in_any_order(project, monkeypatch, capsys, args):
    write_uk_raw(project, "antybitum", [("антибітум", 70)])

    code = run_main(monkeypatch, *args)

    assert code in (0, None)
    result = json.loads(capsys.readouterr().out)
    assert result["meta"]["slug"] == "antybitum"
    assert result["meta"]["source"] == "raw_json"


def test_list_uk_lists_uk_categories(project, monkeypatch, capsys):
    write_uk_raw(project, "uk-only-slug", [("антибітум", 70)])

    code = run_main(monkeypatch, "--list", "--lang", "uk")

    out = capsys.readouterr().out
    assert code == 0
    assert "uk-only-slug" in out
    assert "antibitum" not in out
    assert "Total: 1 categories" in out


def test_list_ru_lists_csv_categories(project, monkeypatch, capsys):
    code = run_main(monkeypatch, "--list")

    out = capsys.readouterr().out
    assert code == 0
    assert "antibitum" in out


def test_missing_slug_is_a_usage_error(project, monkeypatch, capsys):
    assert run_main(monkeypatch) == 2


def test_run_analyze_call_form_still_parses(monkeypatch):
    """batch.generate.run_analyze calls `-m ... <slug> --json`; that argv must parse."""
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout='{"meta": {}}', stderr="")

    monkeypatch.setattr(generate.subprocess, "run", fake_run)
    ok, _ = generate.run_analyze("antibitum")
    assert ok

    argv = calls[0][calls[0].index("llm_keywords_pipeline.analyze.category") + 1 :]
    seen = {}
    monkeypatch.setattr(
        category,
        "analyze_category",
        lambda slug, lang: seen.update(slug=slug, lang=lang) or {"error": "stop"},
    )
    monkeypatch.setattr(sys, "argv", ["category", *argv])
    with pytest.raises(SystemExit):
        category.main()
    assert seen == {"slug": "antibitum", "lang": "ru"}
