# tests/fixtures/real_data.py
"""Hand-written fixtures and samples for smoke, integration and unit tests."""

from pathlib import Path

# Hand-written UK fixture used when real UK data is absent
UK_FIXTURE_SLUG = "aktivnaya-pena"
UK_FIXTURE_DIR = Path(__file__).parent / "uk"
UK_FIXTURE_CONTENT = UK_FIXTURE_DIR / f"{UK_FIXTURE_SLUG}_uk.md"
UK_FIXTURE_META = UK_FIXTURE_DIR / f"{UK_FIXTURE_SLUG}_meta.json"
UK_FIXTURE_CLEAN = UK_FIXTURE_DIR / f"{UK_FIXTURE_SLUG}_clean.json"

# Real content samples for unit tests
SAMPLE_RU_MARKDOWN = """---
title: Активная пена
---

# Активная пена для бесконтактной мойки

Активная пена — современное моющее средство для бесконтактной мойки автомобиля.

## Как выбрать активную пену

При выборе активной пены обратите внимание на концентрацию и pH-уровень.

## Как правильно использовать

1. Разведите средство согласно инструкции
2. Нанесите на кузов снизу вверх
3. Подождите 2-3 минуты
4. Смойте водой

## Частые ошибки

Никогда не наносите пену на горячий кузов. Не давайте высохнуть.
"""

SAMPLE_UK_MARKDOWN = """---
title: Активна піна
---

# Активна піна для безконтактної мийки

Активна піна — сучасний миючий засіб для безконтактної мийки автомобіля.

## Як обрати активну піну

При виборі активної піни зверніть увагу на концентрацію та pH-рівень.

## Як правильно використовувати

1. Розведіть засіб згідно з інструкцією
2. Нанесіть на кузов знизу вгору
3. Зачекайте 2-3 хвилини
4. Змийте водою

## Часті помилки

Ніколи не наносьте піну на гарячий кузов. Не давайте висохнути.
"""
