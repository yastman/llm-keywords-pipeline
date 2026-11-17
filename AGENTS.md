# AGENTS.md

Guide for an LLM agent that uses this repo to turn a keyword export into category SEO
texts and meta for an RU/UK e-commerce catalog.

## Roles

You do the content work: read the keyword CSV, map keywords to categories, cluster them,
write the brief, texts and meta. The package is the data format plus deterministic checks:
it moves keywords between CSV and JSON, computes the brief, and validates what you wrote.
A text is done when the validators pass, not when it reads well.

## Data stays out of git

The repository is public. Real keyword exports, `_clean.json` files, client texts and meta
never go into a commit. `.gitignore` covers `categories/`, `uk/`, `data/*.csv`,
`data/*.xlsx`, `key_all.csv` and `Структура _Ultimate.csv` at the repo root; tests use
`tests/fixtures/` only. Before a commit, `git status` lists no data file.

## Where data lives

Keep data in a directory outside the clone and point the package at it:

```bash
export LLM_KEYWORDS_PROJECT_ROOT=/path/to/project-data
```

Unset, the root is the repo itself (`src/llm_keywords_pipeline/core/config.py`). Layout
the code reads under that root (`{slug}` is the category slug):

```text
categories/{slug}/data/{slug}_clean.json     clustered keywords (RU)
categories/{slug}/content/{slug}_ru.md       category text (RU)
categories/{slug}/meta/{slug}_meta.json      meta (RU)
uk/categories/{slug}/...                     same for UK; text is content/{slug}_uk.md
data/ru_semantics_master.csv                 master CSV: keyword,volume,category,type,use_in
key_all.csv                                  volume export: columns "Ключевое слово","Показов в месяц"
Структура _Ultimate.csv                      legacy semantics CSV, read by analyze.category --list
```

`_clean.json` keeps `keywords` as a dict of groups `primary`, `secondary`, `supporting`,
`commercial` (`core/clean_json.py`); `primary[0]` is the main keyword, `commercial` entries
carry `"use_in": "meta_only"` and go into meta, not the text. Synonyms sit in a top-level
`synonyms` list. Example: `tests/fixtures/sample_clean.json`.

Meta file shape read by the validator: `{"h1": "...", "meta": {"title": "...", "description": "..."}}`.

## Workflow

Run commands from the repo root with `uv run`; data paths are absolute or under the data root.

1. **Keywords in.** Read the owner's keyword CSV. Assign each keyword a category slug and
   a type (`keyword` or `synonym`); write `data/ru_semantics_master.csv`.
2. **Per-category JSON.** Push the master CSV into `_clean.json` files; review the dry run
   first. The CSV decides which keywords a file holds: an entry the CSV lacks is dropped,
   a new one lands in `supporting`.

   ```bash
   uv run python -m llm_keywords_pipeline.sync.semantics [--categories a,b]         # dry run
   uv run python -m llm_keywords_pipeline.sync.semantics --apply [--categories a,b]
   ```

   Then cluster: move each file's keywords into `primary` / `secondary` / `supporting` /
   `commercial` in the JSON.
   Related commands, RU only (they scan `categories/`, never `uk/`):
   `sync.merge_master [--excel f.xlsx ...]` rebuilds the master CSV from the RU
   `_clean.json` files; `sync.update_volume` (no flags) rewrites their volumes from
   `key_all.csv`, in place.

   UK has no CSV and no sync: you make each UK file yourself by translating and adapting
   the RU `_clean.json` into `uk/categories/{slug}/data/{slug}_clean.json` (same shape).
3. **Brief.** `uv run python -m llm_keywords_pipeline.analyze.category <slug> [--lang uk] [--json]`
   prints the keyword groups, recommended length, coverage target and structure.
4. **Text and meta.** Write the text by `prompts/produce.md` (RU); prepare and delivery
   steps are in `prompts/prepare.md` and `prompts/deliver.md`. The meta has the shape
   above; a client phrase is required only when `project.toml` in the data root lists it
   under `[meta] required_phrases` for the language (regexes, e.g.
   `required_phrases = { uk = ["опт\\b"], ru = [] }`); `[meta] recommended_phrases`
   gives a WARNING when missing; `[project] brand` is the title suffix ` | {brand}` of
   the meta generators.
5. **Validate and fix.** Run every validator below on the file; fix the text and rerun
   until each exits 0; a WARNING you leave in place is named, with the reason, in the hand-over.
6. **Hand over** the files under the data root. Nothing from steps 1-5 is committed.

## Validators

| Command | Checks | Language |
| --- | --- | --- |
| `uv run llm-keywords-check-seo <file.md> "<main_keyword>"` | Main keyword in intro and H2, keyword frequency | from the path: a `uk/` segment (`uk/categories/...` or `.../uk/...`) → uk, else ru |
| `uv run llm-keywords-density <file.md> [--slug SLUG]` | Keyword density, stem groups, spam | `--lang ru\|uk`, default ru |
| `uv run llm-keywords-audit-brands <file.md>` | Brands, cities, strict phrases, AI fluff | from the path |
| `uv run llm-keywords-audit-water <file.md>` | Water, classic and academic nausea | `--lang ru\|uk`, default ru |
| `uv run python -m llm_keywords_pipeline.validate.content <file.md> "<primary_keyword>" --with-analysis <slug>` | H1/H2 structure, keyword in H1 and intro, core and commercial coverage, water, blacklist, length, markdown lint, FAQ | `--lang ru\|uk`, default ru; also picks the RU or UK `_clean.json` for `<slug>` |
| `uv run python -m llm_keywords_pipeline.validate.meta <meta.json> --keywords <_clean.json>` | Title and description length, primary keyword, `[meta] required_phrases` (FAIL) and `recommended_phrases` (WARNING) of `project.toml` | `--lang ru\|uk` if given, else the meta's `"language"` key, else the path as check-seo, else ru (also under `--all`) |

Pass the keyword source every time: without `--with-analysis` validate.content has no
category keywords and reports coverage PASS on zero keywords; without `--keywords`
validate.meta skips the primary-keyword check ("No keywords to check").

Exit codes: 0 PASS, 1 WARNING, 2 FAIL, except audit-brands (1 for any hit, WARNING or
FAIL) and audit-water (0 PASS or WARNING, 1 BLOCKER). `validate.meta --all` scans
`./categories` and `./uk/categories` of the current directory, so run it from the data
root (`uv run --project <repo> ...`).

Niche rules come only from `project.toml` in the data root: category slugs (else
slugify), synonyms, extra commercial markers, brand blacklist, city check on/off,
allowed strict phrases, density substrings, L2-forbidden patterns, content standards
(Safety block, расход, warnings: off unless switched on) and the brief's editorial tone.
No file means none of them applies; the generic UA/RU city check stays on. Keys and examples: the docstring of
`src/llm_keywords_pipeline/core/project.py`; `tests/fixtures/project_ultimate.toml` is a
full car-care example.

Thresholds (water, nausea, title/description length, keyword frequency, word counts) live
in `QUALITY_THRESHOLDS` in `src/llm_keywords_pipeline/core/config.py`; read them there,
never from a prompt or this file. No validator checks grammar or spelling: proofread by
`prompts/deliver.md`.

## Changing the code

Tests and hooks: `docs/testing.md`. Package map and public surface: `docs/architecture.md`.
