# PREPARE Prompt — Category Initialization

> Public reference template. This file documents the category-initialization stage of an
> external LLM workflow. It is not directly executable from a fresh clone because it
> requires project category data and an LLM orchestrator.

**Purpose:** create the folder/data scaffold for one SEO category.
**Inputs:** `slug`, category `name`, and priority `tier`.
**Outputs:** category folders plus task/keyword JSON artifacts.
**Required infrastructure:** compatible project data layout and external orchestration.

**Этап:** 1/3 (PREPARE)
**Задача:** Подготовить структуру и данные для категории

---

## Input Parameters

- `slug`: {slug}
- `name`: {name}
- `tier`: {tier} (A/B/C)

---

## Steps

### Step 1: Init Folders

Создать структуру категории:

```bash
categories/{slug}/
├── content/
├── meta/
├── data/
├── deliverables/
└── .logs/
```

### Step 2: Create Task File

Создать `task_{slug}.json`:

```json
{
  "slug": "{slug}",
  "tier": "{tier}",
  "keywords_count": 0,
  "created_at": "ISO8601",
  "current_stage": "prepare",
  "stages": {
    "prepare": "completed",
    "produce": "pending",
    "deliver": "pending"
  },
  "paths": {
    "data": "categories/{slug}/data/{slug}.json",
    "content_ru": "categories/{slug}/content/{slug}_ru.md",
    "meta": "categories/{slug}/meta/{slug}_meta.json",
    "deliverables": "categories/{slug}/deliverables/"
  }
}
```

### Step 3: Generate Keywords JSON

Получить файл внешним парсингом выгрузки ключей: ни один модуль `llm_keywords_pipeline`
его не пишет, пакет только читает его.

**Output:** `categories/{slug}/data/{slug}.json`

**Формат JSON:**

```json
{
  "slug": "{slug}",
  "name": "{name}",
  "tier": "{tier}",
  "main_keyword": "...",
  "main_keyword_volume": 1234,
  "keywords": [
    {"keyword": "...", "volume": 123, "type": "exact"},
    ...
  ],
  "total_keywords": 52,
  "total_volume": 12345
}
```

### Step 4: CLEAN Keywords (Рекомендуется)

Кластеризация 52 ключей → 12 уникальных:

```
# Используйте модули package для кластеризации
# Input: {slug}.json (52 kw)
# Output: {slug}_clean.json (12 kw)
```

Ключ убирается только по правилу из `brief.md` (`prompts/intake.md`): каждый убранный ключ
записывается в `excluded` файла `_clean.json` с причиной, которая ссылается на бриф.
Дубли и сливаемые в кластер ключи сюда не относятся.

**D+E Pattern:** Все скрипты автоматически используют `_clean.json` если существует.

**Преимущества:**

- 100% coverage вместо ~40%
- Оптимальная density 1.0-2.5%
- Без дубликатов ключей

---

## Output Report

Вернуть краткий отчёт:

```
✅ PREPARE завершён для {slug}

Структура:
- Папки созданы: categories/{slug}/
- Task file: task_{slug}.json
- Keywords JSON: categories/{slug}/data/{slug}.json

Keywords Stats:
- Main keyword: "{main_keyword}" (volume: {volume})
- Total keywords: {count}
- Total volume: {total_volume}

Статус: stage=prepare completed
Следующий этап: PRODUCE
```

---

## Error Handling

### Если CSV не найден

```
❌ ERROR: CSV file not found
Path: data/keywords.csv
Action: Check file path or download CSV
```

---

## Success Criteria

- [ ] Папки созданы
- [ ] task_{slug}.json существует
- [ ] categories/{slug}/data/{slug}.json создан
- [ ] **(Рекомендуется)** categories/{slug}/data/{slug}_clean.json создан
- [ ] JSON содержит min 3 keywords (12 в _clean.json)
- [ ] Stage "prepare" = "completed" в task file

---

**Version:** 6.0 — public packaging update
**D+E Pattern:** Includes CLEAN step for _clean.json
**Model:** haiku (fast init)
