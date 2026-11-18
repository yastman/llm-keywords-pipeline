# DELIVER Prompt — Validation & Packaging

> Public reference template. This file documents the validation/packaging stage of an
> external LLM workflow. It is not directly executable from a fresh clone because it
> expects generated category artifacts and an LLM orchestrator.

**Purpose:** validate generated content and prepare delivery artifacts.
**Inputs:** `slug`, `tier`, `main_keyword`, generated content Markdown, and meta JSON.
**Outputs:** validation results and deliverable files.
**Required infrastructure:** compatible category data layout, validation modules, and
external orchestration.

**Этап:** 3/3 (DELIVER)
**Задача:** Валидировать контент и упаковать deliverables

## ⚡ D+E Pattern

Валидатор автоматически определяет JSON:

```
1. {slug}_clean.json (12 kw) ← preferred
2. {slug}.json (52 kw)       ← fallback
```

**Adaptive Thresholds:**

> **Note:** These are the thresholds enforced by `validate/density.py`
> (`SPAM_THRESHOLD`, `WARNING_THRESHOLD`, `OPTIMAL_RANGE`), the same for any keyword count.
> The values in the code are the ground truth for the validator.

| Density Spam | Density Warning | Density Optimal |
|--------------|-----------------|-----------------|
| >3.0% | >2.5% | 1.0-2.5% |

---

## Input Parameters

- `slug`: {slug}
- `tier`: {tier} (A/B/C)
- `main_keyword`: {keyword}
- `content_ru`: categories/{slug}/content/{slug}_ru.md
- `meta`: categories/{slug}/meta/{slug}_meta.json

---

## Steps

### Step 1: Run Quality Checks (5 проверок)

Запустить полную валидацию. В текущей структуре пакета используйте модули из
`llm_keywords_pipeline.validate`:

```bash
uv run python -m llm_keywords_pipeline.validate.content \
  categories/{slug}/content/{slug}_ru.md \
  "{main_keyword}"
```

**5 Checks:**

Диапазоны ниже — ограничители валидаторов: готовый текст остаётся внутри них, но слова
ради них не добавляются. Цели по длине или числу знаков нет.

1. **Markdown Structure**
   - Разделы по `prompts/produce.md`: ассортимент, различия и кому подходит, ссылки на
     соседние категории, FAQ из 3-4 вопросов о товаре (для главной — её правила там же)
   - H1 = название категории (если есть, должен совпадать с главным keyword)
   - Не больше одной коммерческой строки со ссылкой на страницу условий; блока об
     условиях доставки, оплаты, регистрации нет
   - Нет маркеров вроде `[ПІДТВЕРДИТИ]`; каждый неподтверждённый факт есть в
     `Open questions` в `brief.md` и в отчёте как вопрос владельцу

2. **LLM Proofreading (вычитка; валидатор грамматику не проверяет)**
   - Перечитай текст целиком и исправь сам:
   - Орфография и опечатки
   - Согласование (род, число, падеж)
   - Пунктуация
   - Synonym rotation (max 2 повтора/параграф): тоже вычиткой

3. **Water/Nausea**
   - Water: 40-65%
   - Classic Nausea: ≤3.5
   - Academic Nausea (доля топ-леммы среди повторяющихся значимых лемм): 7-9.5%

4. **Keyword Density**
   - Main keyword: 1.0-2.5% (warning >2.5%, spam >3.0%)
   - Равномерное распределение (не кластеры)

5. **NER & Blacklist**
   - Нет запрещённых AI-fluff фраз
   - Нет брендов конкурентов (`[blacklist] brands` в `project.toml`)
   - Нет брендов (если не в каталоге)

**Exit Codes:**

- 0 = PASS ✅
- 1 = WARNING ⚠️ (можно продолжать)
- 2 = FAIL ❌ (требуется fix)

### Step 2: Fix Issues (если FAIL)

Если проверка вернула FAIL:

1. Определить проблемные секции по выводу валидатора
2. Исправить контент
3. Перезапустить Step 1

**Типичные ошибки:**

| Ошибка | Fix |
|--------|-----|
| Water >70% | Убрать вводные слова, сократить параграфы |
| Nausea >4.0 | Synonym rotation, разнообразить предложения |
| Density <1.0% | Заменить синоним главным keyword в H2 или тексте, не добавляя текст |
| Competitor found | Убрать бренд или заменить названием вида товара |

### Step 3: Package Deliverables

Создать папку: `categories/{slug}/deliverables/`

Скопировать файлы:

- `{slug}_ru.md` (из content/)
- `{slug}_meta.json` (из meta/)

Создать дополнительно:

**1. README.md**

```markdown
# {Name} — Deliverables

**Tier:** {tier}
**Status:** Validated ✅
**Date:** {ISO8601}

## Files

| File | Description |
|------|-------------|
| {slug}_ru.md | Контент RU |
| {slug}_meta.json | Meta tags RU |
| QUALITY_REPORT.md | Отчёт валидации |

## Metrics (RU)

- Words: {words}
- H2: {h2_count}
- FAQ: {faq_count}
- Water: {water}%
- Nausea: {nausea}
- Density: {density}%

## Validation

✅ All 5 checks passed
- Markdown structure: OK
- LLM proofreading: done
- Water/Nausea: OK
- Keyword density: OK
- NER/Blacklist: OK

## Next Steps

1. Импорт в CMS
2. Настройка URL: /category/{slug}
3. Публикация
```

**2. QUALITY_REPORT.md**

```markdown
# Quality Report — {slug}

**Date:** {ISO8601}
**Tier:** {tier}
**Validator:** pipeline validation suite

---

## Summary

| Check | Status | Details |
|-------|--------|---------|
| Markdown | ✅ PASS | H2={count}, FAQ={count} |
| LLM proofreading | ✅ DONE | Spelling, agreement, punctuation |
| Water/Nausea | ✅ PASS | Water={X}%, Nausea={X} |
| Density | ✅ PASS | Main={X}%, Distribution OK |
| NER | ✅ PASS | No competitors |

---

## Metrics

### Content (RU)

- Words: {words}
- H2: {h2_count}
- FAQ: {faq_count}

### SEO

- Keyword Density: {density}% (target: 1.0-2.5%)
- Water: {water}% (target: 40-65%)
- Classic Nausea: {nausea} (target: ≤3.5)
- Academic Nausea: {academic}% (target: 7-9.5%)

### Owner questions

- {unconfirmed fact left out of the text}

---

## Logs

Full logs: categories/{slug}/.logs/ (generated by validator run)
```

### Step 4: Update Task File

Обновить `task_{slug}.json`:

```json
{
  "status": "completed",
  "current_stage": "deliver",
  "stages": {
    "prepare": "completed",
    "produce": "completed",
    "deliver": "completed"
  },
  "metrics": {
    "words": 340,
    "water": 56.9,
    "nausea": 2.45,
    "density": 1.5,
    "h2": 4,
    "faq": 4
  },
  "validation": {
    "passed": true,
    "checks": {
      "markdown": "pass",
      "proofreading": "done",
      "water": "pass",
      "density": "pass",
      "ner": "pass"
    }
  },
  "completed_at": "ISO8601"
}
```

---

## Output Report

Вернуть Orchestrator:

```
✅ DELIVER завершён для {slug}

Validation:
- All 5 checks: PASSED ✅
- Exit code: 0

Deliverables:
- Path: categories/{slug}/deliverables/
- Files: 4 (content RU, meta, README, QUALITY_REPORT)

Metrics:
- Words: 340
- Water: 56.9% / 40-65% ✓
- Nausea: 2.45 / ≤3.5 ✓
- Density: 1.5% / 1.0-2.5% ✓

Owner questions: {list or none}

Task Status: COMPLETED ✅

Ready for:
1. CMS Import
2. URL: /category/{slug}
3. Publication
```

---

## Error Handling

### Если валидация провалена (exit code 2)

```
❌ VALIDATION FAILED

Failed checks:
- Water/Nausea: Water 75% (max 65%)
- Nausea: 4.2 (max 3.5)

Action Required:
1. Reduce water by removing intro phrases
2. Apply synonym rotation to reduce nausea
3. Re-run PRODUCE step

Do not proceed to packaging.
```

### Если файлы не найдены

```
❌ ERROR: Content files not found
Missing:
- categories/{slug}/content/{slug}_ru.md

Action: Run PRODUCE first
```

---

## Success Criteria

- [ ] Validation returned PASS
- [ ] Все 5 проверок пройдены
- [ ] Deliverables созданы (4 файла)
- [ ] README.md содержит метрики
- [ ] QUALITY_REPORT.md содержит детали
- [ ] Task file updated: status="completed"

---

**Version:** 6.0 — public packaging update
**D+E Pattern:** Auto-detects _clean.json with adaptive thresholds
**Model:** sonnet (quality audit)
