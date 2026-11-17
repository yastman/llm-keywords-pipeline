<div align="center">

# LLM Keywords Pipeline

**[English](README.md) · [Русский](README.ru.md) · Українська**

**Пайплайн для кластеризації ключів і перевірки SEO-контенту українською та російською мовами.**

**Перетворює сирий список ключів на SEO-групи, LLM-ready briefs і вимірювані перевірки тексту: coverage, density, переспам, вода та нудота.**

<p>
  <img alt="Python" src="https://img.shields.io/badge/python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white">
  <img alt="uv" src="https://img.shields.io/badge/package%20manager-uv-6E56CF?style=for-the-badge">
  <img alt="Ruff" src="https://img.shields.io/badge/lint-ruff-46A758?style=for-the-badge">
  <img alt="Pytest" src="https://img.shields.io/badge/tests-pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white">
  <img alt="NLP" src="https://img.shields.io/badge/NLP-RU%20%2F%20UK-0E9F6E?style=for-the-badge">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-111111?style=for-the-badge">
</p>

</div>

```bash
uv sync --frozen
uv run ruff check src tests
uv run mypy
uv run pytest
uv build
```

---

## Яку проблему розв'язує

SEO-спеціаліст часто починає з брудного експорту семантики: дублікати, синоніми,
змішаний комерційний та інформаційний intent, частотності, нотатки щодо конкурентів і
текст, який треба перевірити на покриття ключів.

Вручну це працює лише на малому обсязі. Для каталогу з десятків або сотень категорій
потрібна повторювана система:

- завантажити або імпортувати список ключів;
- згрупувати ключі у зрозумілі SEO-кластери;
- відокремити primary, secondary, supporting і commercial keywords;
- використати TOP-10 SERP overlap і competitor research, якщо такий файл підготовлений;
- написати або згенерувати текст за кластеризованим brief;
- перевірити готовий текст на покриття ключів;
- знайти переспам, зайву воду та нудоту до публікації.

Цей репозиторій пакує такий workflow у Python-проєкт.

---

## Основний workflow

### 1. Адаптація списку ключів у JSON

Workflow починається з експорту ключів: CSV або структурованого списку семантики. Цей
сирий вхід адаптується в category JSON files, щоб увесь подальший pipeline працював не з
таблицями, а з одним зрозумілим контрактом даних.

У проєкті є кілька шляхів такого handoff:

- raw category JSON, наприклад `categories/{slug}/data/{slug}.json`: створюється поза
  цим пакетом (жоден модуль його не пише), pipeline лише читає його;
- кластеризований clean JSON, наприклад `categories/{slug}/data/{slug}_clean.json`;
- синхронізація master CSV у `_clean.json`;
- CSV restore/compare utilities для drift, missing keywords і змінених volumes.

D+E fallback pattern спочатку бере `_clean.json`, потім raw parsed JSON, потім CSV
fallback. На практиці `_clean.json` стає головним робочим артефактом для наступних
етапів.

### 2. Кластеризація ключів

Ключі розкладаються за практичними SEO-ролями:

| Група | Для чого потрібна |
| --- | --- |
| `primary` | Головні запити для H1, intro та основного intent сторінки. |
| `secondary` | Суміжні запити, що розширюють сторінку без зміни intent. |
| `supporting` | Long-tail і контекстні фрази для семантичної глибини. |
| `commercial` | "Купити", "ціна", "замовити" та схожі комерційні модифікатори, часто для meta або commercial signals. |

Утиліти synonym cleanup нормалізують близькі варіанти, обирають сильніший ключ за
частотністю та якістю фрази, а слабкі дублікати прибирають.

### 3. Підготовка research для категорії

В оригінальному workflow також підтримується окремий файл SERP TOP-10: ключі можна
перевіряти за перетином URL у видачі Google. Якщо два запити мають достатньо спільних
URL у TOP-10, вони можуть потрапити в один кластер або synonym group; якщо видача
помітно відрізняється, ключ вважається окремим пошуковим intent.

У повному workflow після кластеризації primary keyword, semantic
groups, entities, micro-intents і product insights використовувалися для генерації
`categories/{slug}/research/RESEARCH_PROMPT.md` під зовнішній web-research інструмент,
наприклад Perplexity Deep Research або LLM agent з web search. Результат дослідження
потім зберігався в `categories/{slug}/research/RESEARCH_DATA.md`.

Цей файл не просто додається до категорії. Він стає brief для наступного етапу: факти
про продукт, структура конкурентів, intent користувача, content gaps, обов'язкові
блоки, ідеї для FAQ і ризики, які треба врахувати під час написання SEO-тексту.

Public package зберігає цей stage як prompt/checklist/reference material і pipeline
artifact, який перевіряється task generation. Зовнішні research runners і generated
research outputs навмисно винесені за межі репозиторію.

### 4. Написання SEO-тексту

Папка `prompts/` описує prepare/produce/deliver flow для LLM-assisted writing:
прочитати кластеризовані ключі, визначити primary keyword, врахувати entity dictionary,
content rules і optional research, потім підготувати або перевірити текст.

### 5. Перевірка готового тексту

Валідатори відповідають на головне питання: текст справді покриває brief чи лише
виглядає як SEO-текст?

Точки входу:

| Команда | Що перевіряє | Мова |
| --- | --- | --- |
| `uv run llm-keywords-check-seo <file.md> "<main_keyword>"` | Primary keyword в intro і H2, частота ключа. | За шляхом: шлях, що містить `/uk/` (наприклад `uk/categories/`) → uk, інакше ru. |
| `uv run llm-keywords-density <file.md>` | Щільність ключів, stem-групи, category substrings, spam/warning thresholds. | `--lang ru\|uk`, за замовчуванням ru. |
| `uv run llm-keywords-audit-brands <file.md>` | Blacklist брендів, згадки міст, NER-сутності. | За шляхом, як check-seo. |
| `uv run llm-keywords-audit-water <file.md>` | Вода, класична та академічна нудота. | `--lang ru\|uk`, за замовчуванням ru. |
| `uv run python -m llm_keywords_pipeline.validate.content <file.md> "<primary_keyword>"` | Структура H1/H2, primary keyword в H1 та intro, core і commercial coverage, вода/нудота, blacklist, довжина, content standards, markdown lint, FAQ. | `--lang ru\|uk`, за замовчуванням ru. |

Morphology-aware для української та російської (леми pymorphy3): matching ключів у
check-seo, підрахунок ключів у density (ключі рахуються за n-грамами лем) і core coverage
у validate.content. Не morphology-aware: commercial coverage (exact match), category
substrings у density (російські підрядки, лише ru) і stem-групи density для ru (Snowball;
для uk групування за лемою). Вода й нудота беруть леми natasha для ru і pymorphy3 для uk;
метрики визначені в розділі [Можливості](#можливості).

Markdown lint працює через pymarkdownlnt і повертає `SKIPPED`, якщо пакет не
встановлено. Жоден валідатор не перевіряє граматику й орфографію: це крок LLM-вичитки
в [prompts/deliver.md](prompts/deliver.md).

---

## Чому це корисно

### Для SEO-спеціаліста

Проєкт перетворює семантику на керований checklist: які ключі брати в текст, які
залишати для meta, де бракує coverage і де текст уже переоптимізований.

### Для LLM-контенту

LLM може швидко написати чернетку, але пайплайн перевіряє результат детерміновано:
ключі, структура, density, вода, нудота та ознаки SEO-спаму.

### Для RU/UK каталогів

Перевірки враховують українську та російську мову: tokenization, stopwords, stemming,
lemmatization і morphology-aware matching, а не лише exact string match. Спільний
токенізатор (`core/text`) і water audit для української лишають слова з апострофом
(`м'який`, з `'`, `’` або `ʼ`) одним токеном; токени лем у check-seo і density та
matching ключів (coverage у validate.content) розбивають їх по апострофу. NER і
морфологія natasha працюють лише для російської; для української audit-brands
пропускає NER, а water audit лематизує через pymorphy3.

---

## Можливості

| Блок | Що робить |
| --- | --- |
| Keyword JSON adaptation | Перетворює CSV/master/raw keyword data на category JSON і `_clean.json`, з якими працює весь pipeline. |
| Keyword clustering | Будує clean keyword groups із raw/CSV/category data і розділяє intent roles. |
| SERP TOP-10 overlap | Використовує перетин URL у пошуковій видачі, щоб зрозуміти: ключі в один кластер чи це різні intents. |
| Synonym cleanup | Знаходить near-duplicates і нормалізує конкуруючі варіанти ключів. |
| Research prompt workflow | Перетворює clustered keywords/entities/product insights на research prompt contract; public docs зберігають workflow `RESEARCH_PROMPT.md` → `RESEARCH_DATA.md` → brief. |
| Content validation | Перевіряє H1, intro, headings, keyword coverage, meta sync і мовні правила. |
| Density and spam | Рахує ключі за n-грамами лем (exact) і окремими лемами (partial), плюс stem-групи та category substrings, проти warning/spam thresholds. |
| Water and nausea | Рахує воду (частка стоп-слів, калібрована), класичну нудоту (√ частоти топ-леми), академічну нудоту (частка топ-леми серед повторюваних значущих лем) і повтор лем. |
| Generation | Генерує meta artifacts, SQL exports, semantic review files, catalog JSON і checklists. |
| Repair and sync | Оновлює volumes, відновлює `_clean.json` із CSV, merge master keyword data (один рядок на категорію, тип і фразу; перемагає більший volume) і виправляє misplaced terms. |

---

## Структура проєкту

```text
src/llm_keywords_pipeline/
  analyze/      аналіз категорії та metadata для LLM briefs
  audit/        water, nausea, coverage, blacklist, H1 і quality audits
  core/         keyword matching, morphology, SEO rules, text utilities
  generate/     meta, checklist, semantic review, catalog і export tools
  validate/     content, meta, heading, density, language і data validators
  sync/         CSV/master-data synchronization і _clean.json repair
  fix/          сфокусовані cleanup utilities
  compare/      keyword distribution і dataset comparison helpers
  automation/   orchestrator prepare→produce→validate→deliver, batch runner, LLM client (бібліотека, без CLI)
tests/          pytest suite і public fixtures
prompts/        prepare/produce/deliver LLM workflow templates
docs/           architecture, testing і public-version notes
```

---

## Швидкий старт

Потрібно: Python 3.12+ і [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/yastman/llm-keywords-pipeline.git
cd llm-keywords-pipeline

uv sync --frozen
uv run pre-commit install --hook-type pre-commit --hook-type pre-push
uv run ruff check src tests
uv run mypy
uv run pytest
```

Pre-commit hook запускає ruff (check і format) і file hygiene checks на staged files;
pre-push hook запускає `uv lock --check`, `uv run ruff check src tests`, `uv run mypy` і
`uv run pytest -q --cov-fail-under=20`. Remote CI немає: ці hooks єдиний gate.

`uv sync` ставить default groups `nlp`, `dev` і `test`. Група `nlp`: pymorphy3 з
російським і українським словниками, natasha, snowballstemmer і pymarkdownlnt. Якщо
словника pymorphy3 для мови немає, лематизація один раз видає `RuntimeWarning` і
відкочується на російський stemming, тож українські леми будуть неправильними.

Запуск public fixture через packaged CLI:

```bash
uv run llm-keywords-audit-brands tests/fixtures/valid_content.md --json
```

Coverage:

```bash
uv run pytest --cov=src/llm_keywords_pipeline --cov-report=term-missing
```

Опційний локальний database demo:

```bash
cp .env.example .env
docker compose up
```

Compose піднімає MariaDB і Adminer на localhost. Це локальний demo, не production
deployment recipe.

---

## Документація

| Документ | Що всередині |
| --- | --- |
| [Architecture](docs/architecture.md) | Package map, workflow boundaries і supported public surface. |
| [Testing](docs/testing.md) | Test tiers, default commands, local git hooks, data-required skips. |
| [Research Workflow](docs/research-workflow.md) | Як clustered keywords перетворювались на `RESEARCH_PROMPT.md`, `RESEARCH_DATA.md` і content brief. |
| [Public Version](docs/public-version.md) | Що включено, що виключено і навіщо залишені prompts. |
| [Prompt Templates](prompts/README.md) | Prepare/produce/deliver LLM workflow templates. |

---

## Публічна межа

Репозиторій зберігає інженерну структуру, тести, fixtures і prompt workflow.
Production datasets, generated reports, SERP TOP-10 exports і external LLM orchestration
навмисно виключені; data-layout dependent modules залишені як reference implementations
для сумісних SEO-проєктів.

---

## Ліцензія

MIT. Див. [LICENSE](LICENSE).

---

Сирий список ключів легко експортувати. Цей проєкт перетворює його на кластеризовану
SEO-роботу, яку можна написати, перевірити й покращити.
