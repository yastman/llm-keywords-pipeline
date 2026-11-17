"""Smoke tests for the llm-keywords-audit-brands CLI (ner_brands.main)."""

import pytest

from llm_keywords_pipeline.audit.ner_brands import main


def test_help_prints_usage_and_exits_0(capsys):
    assert main(["--help"]) == 0
    out = capsys.readouterr().out
    assert "Usage" in out
    assert "Файл не найден" not in out


def test_short_help_exits_0(capsys):
    assert main(["-h"]) == 0
    assert "Usage" in capsys.readouterr().out


def test_missing_file_exits_2(tmp_path, capsys):
    assert main([str(tmp_path / "missing.md")]) == 2
    assert "Файл не найден" in capsys.readouterr().out


def test_uk_city_case_forms_exit_nonzero(tmp_path, capsys):
    f = tmp_path / "uk_city.md"
    f.write_text("Доставка по Києву, Харкову та Тернополю.", encoding="utf-8")
    assert main([str(f)]) != 0


def test_uk_locative_city_exits_nonzero(tmp_path, capsys):
    f = tmp_path / "kyiv.md"
    f.write_text("Доставка у Києві.", encoding="utf-8")
    assert main([str(f), "--json"]) != 0
    assert '"київ"' in capsys.readouterr().out


def test_uk_lowercase_city_after_preposition_exits_nonzero(tmp_path, capsys):
    f = tmp_path / "kyiv_lower.md"
    f.write_text("доставка у києві", encoding="utf-8")
    assert main([str(f), "--json"]) != 0
    assert '"київ"' in capsys.readouterr().out


@pytest.mark.parametrize(
    "text",
    [
        "Рівним шаром нанесіть засіб.",
        "Нанесіть рівним шаром",
        "У сумах до 1000 грн",
        "різних сумах",
    ],
)
def test_uk_common_word_homograph_exits_0(tmp_path, capsys, text):
    f = tmp_path / "homograph.md"
    f.write_text(text, encoding="utf-8")
    assert main([str(f), "--json"]) == 0
    assert '"CITY"' not in capsys.readouterr().out


def test_uk_city_after_po_exits_nonzero(tmp_path, capsys):
    f = tmp_path / "rivne.md"
    f.write_text("Доставка по Рівному.", encoding="utf-8")
    assert main([str(f), "--json"]) != 0
    assert '"рівне"' in capsys.readouterr().out
