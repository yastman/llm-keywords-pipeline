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
project.toml                                 client rules, see New client below
<[paths] semantics_csv>                      structure CSV (L1:/L2:/L3: rows), see New client
```

`_clean.json` keeps `keywords` as a dict of groups `primary`, `secondary`, `supporting`,
`commercial` (`core/clean_json.py`); `primary[0]` is the main keyword, `commercial` entries
carry `"use_in": "meta_only"` and go into meta, not the text. Synonyms sit in a top-level
`synonyms` list. Example: `tests/fixtures/sample_clean.json`.

Meta file shape read by the validator: `{"h1": "...", "meta": {"title": "...", "description": "..."}}`,
plus an optional `"language": "ru"` or `"uk"` that sets its language when `--lang` is not
given.

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
| `uv run llm-keywords-check-seo <file.md> "<main_keyword>"` | Main keyword in intro and H2, keyword frequency | from the path: a path starting with `uk/categories/` or containing `/uk/` → uk, else ru |
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
slugify), synonyms, extra commercial words (one key for the brief's intent split, another
for `core.synonyms`), the audit brand blacklist, brands all_meta skips as product types,
city check on/off, allowed strict phrases, density substrings, L2-forbidden patterns,
content standards (Safety block, расход, warnings: off unless switched on) and the
brief's editorial tone. Each module reads its own key. No file means none of them
applies; the generic UA/RU city check stays on. Keys and an example: section New client;
`tests/fixtures/project_ultimate.toml` is a full car-care example.

Thresholds (water, nausea, title/description length, keyword frequency, word counts) live
in `QUALITY_THRESHOLDS` in `src/llm_keywords_pipeline/core/config.py`; read them there,
never from a prompt or this file. No validator checks grammar or spelling: proofread by
`prompts/deliver.md`.

## New client

1. Make a data root outside the clone, set `LLM_KEYWORDS_PROJECT_ROOT` to it and keep the
   layout of section Where data lives. UK texts stay under `uk/categories/`.
2. Put `project.toml` in the data root (`src/llm_keywords_pipeline/core/project.py` reads
   it). No file is an empty config: no client rule applies and generic rules stay on. An
   invalid file raises `ProjectConfigError` naming the file and the key.
3. Set only the keys the client needs. A command that cannot run without a key stops
   before it writes anything, with `<root>/project.toml: <key> is not set; this command
   needs it`: `[paths] semantics_csv` for `batch.generate`, `[opencart]` for
   `generate.sql` (ru) and `generate.plural_sql` (uk and ru).

Every section, commented (a B2B sweets shop as the example):

```toml
[project]
brand = "Genesis"             # meta title suffix " | Genesis"; unset = no suffix
site = "shop.example"         # read into the config; no command uses it yet
languages = ["uk", "ru"]      # read into the config; no command uses it yet

[paths]
# Structure CSV, relative to the data root. batch.generate needs it; analyze.category
# and extract.export_uk_texts use it when set, else the category folders.
semantics_csv = "data/structure.csv"

[meta]
required_phrases = { uk = ["опт\\b"], ru = [] }  # validate.meta: regexes, FAIL if missing
recommended_phrases = { uk = ["роздріб"] }       # validate.meta: regexes, WARNING if missing
# generate.all_meta description per language; placeholders {keyword} {name} {types} {brand}
description_template = { uk = "{name} оптом від {brand}. {types}." }
type_skip_brands = ["roshen"]  # generate.all_meta: entities with one are not product types

[slugs.ru]                    # category name -> slug; a name not listed = slugify(name)
"Шоколадные конфеты" = "shokoladnye-konfety"
[slugs.uk]
"Шоколадні цукерки" = "shokoladnye-konfety"

[markers]
commercial = { uk = ["оптом"], ru = ["оптом"] }  # core.seo / analyze.category intent split

[synonyms]
strip_terms = ["солодощі"]     # core.synonyms: dropped from a keyword before comparing
stems = { "шоколадн" = "шоколад" }  # core.synonyms: word prefix -> stem
map = { "цукерки" = "конфеты" }    # analyze.duplicates: substring -> replacement
commercial_markers = ["киев"]  # core.synonyms (RU): added to its generic commercial markers

[blacklist]
brands = ["haribo"]           # audit.ner_brands: competitor brands reported in the text
cities = true                 # audit.ner_brands city check; false = off
phrases_allow = ["широкий асортимент"]  # strict phrases not checked

[density.category_substrings.ru]  # validate.density (ru): substrings per slug
shokoladnye-konfety = { primary = ["конфет", "шоколад"], anti = ["печень"] }

[structure.l2_forbidden]      # validate.structural: regexes an L2 text must not contain
konditerskie-izdeliya = ["шоколадн.*конфет"]

[content_standards]           # validate.content quality mode; each false when not set
safety_block = false
howto_steps = true
evergreen_math = false
warnings = false

[niche]
tone = "эксперт по оптовым поставкам сладостей"  # analyze.category: brief editorial tone

[opencart]                    # generate.sql, generate.plural_sql; no default
table_prefix = "oc_"          # table <prefix>category_description
language_ids = { uk = 1, ru = 3 }  # language_id of each language in the shop database
```

## Changing the code

Tests and hooks: `docs/testing.md`. Package map and public surface: `docs/architecture.md`.
