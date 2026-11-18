# PRODUCE Prompt — SEO Content Reference

> Public reference template. This file documents the content-production stage of an
> external LLM workflow. It is not directly executable from a fresh clone because it
> requires category keyword JSON, optional research inputs, and an LLM orchestrator.

**Purpose:** generate Russian SEO content and meta tags for one category or the home page.
**Inputs:** category keyword JSON, `slug`, `main_keyword`, `h1`, `brief.md`, and optional
research.
**Outputs:** Markdown content and meta JSON.
**Required infrastructure:** compatible category data layout, web research capability,
and external orchestration.

**Role:** You are an expert SEO copywriter and e-commerce content strategist.
**Goal:** a text that does the jobs of section Why the text exists, for this page only.
**Workflow:** research context -> draft -> deterministic validation.

---

## Workflow Reference

### Phase 1: Context & Research

1. **Read Keywords:**
    * Look for `categories/{slug}/data/{slug}_clean.json`.
    * If missing, fall back to `categories/{slug}/data/{slug}.json`.
    * Identify: `main_keyword`, `h1`, `core_keywords`, `entity_dictionary` (technical terms).
2. **Live Web Research (MANDATORY):**
    * **User Intent:** Search for "{main_keyword} отзывы" or "{main_keyword} форум" to
      find real user problems/questions.
    * **Competitors:** Search for "{main_keyword} купить" to analyze the structure of
      TOP-3 competitors.
    * **Freshness:** Check for new products or packing formats of the current year.
    * *Action:* Use this data for the differences section and the FAQ.
3. **Analyze Competitors (Optional):** If `categories/{slug}/research/` exists, read the
   top competitor analysis.

### Phase 2: Draft Content (Markdown)

Create `categories/{slug}/content/{slug}_ru.md`. The site shows it under the product
grid: the buyer sees the products first, and the text serves whoever scrolls past them.

**Why the text exists.** Each sentence does at least one of these jobs:

1. **Topic relevance** for the category's key cluster. Google ranks on the words of the
   page (the Body part of its T* signal, US v. Google exhibit PXR0356) and sets no
   minimum length.
2. **Help the buyer choose:** real attributes, how types differ, who each suits. A/B tests
   of 2026 gained clicks from such text and from an FAQ under the listing (seoClarity,
   SearchPilot); AI Overviews and AI Mode cite category pages for commercial queries.
3. **Internal links** to child and sibling categories.
4. **Unique to this page.** Google calls one block repeated across categories spam, and
   the 2026 core updates hit templated category text.

Delivery, payment and registration terms have their own pages; a category text holds no
block about them.

**Structure (category):**

1. **H1:** Must match `h1` from JSON exactly.
2. **Opening paragraph:** its first sentence holds `main_keyword` and says what the
   section sells. `validate.content` fails an opening (text before the first H2) under
   30 words: a structure check, not a length goal.
3. **H2 assortment:** the types and brands this category sells, each with real
   attributes from `brief.md` or the catalog (weight, packing: piece, box, display).
4. **H2 differences:** how the types differ and who each suits (buyer type, use,
   season).
5. **Links:** a Markdown link to each related category, inside the sentence that names it.
6. **H2 FAQ:** 3-4 questions about the product (choice, storage, shelf life, packing).
   Delivery and payment questions belong to the terms pages.
7. **Commercial line:** at most one sentence (for example the minimum order and the
   carrier), with a link to the delivery or terms page.

**Keywords:** `main_keyword` in H1, title and the first sentence, and its words in at
least two H2 (`check-seo` warns otherwise); secondary keys where their meaning fits, in
H2 and text. The `commercial` group (`use_in: meta_only`) goes into meta.

**Home page text:** the same file shape (H1, opening paragraph, H2), with these rules:

- written for the store's main key cluster, the broadest keys of the whole catalog;
- the opening says explicitly what the store sells and how (wholesale, retail: by
  `brief.md`);
- every active catalog section, each with a link;
- who the store is for and what sets it apart, from sourced facts only;
- delivery, payment and registration: one line of links to their pages.

**Facts:** every fact in the text (brand, weight, packing, minimum order, carrier, region)
has a source in `brief.md` or the catalog. An unconfirmed fact stays out of the text: add
it to `Open questions` in `brief.md` and name it in the hand-over as a question for the
owner. The delivered text is free of placeholders and markers such as `[ПІДТВЕРДИТИ]`.

**Length:** none is set. The text ends when the jobs above are done for this category.
The length figure of `analyze.category` and the length WARNING of `validate.content` are
information: name such a WARNING in the hand-over and leave the text as the jobs need it.
Density, water and nausea limits of the validators are guardrails a finished text stays
inside, never a reason to add words.

**Style Rules:**

* **No Fluff:** Ban phrases like "в современном мире", "ни для кого не секрет".
* **Evergreen:** No specific prices (use "от 100 грн"), no dates.
* **Formatting:** Use bold for key terms, lists for readability.

### Phase 3: Meta Tags (JSON)

Create `categories/{slug}/meta/{slug}_meta.json` in the shape `validate.meta` reads:

```json
{"h1": "...", "meta": {"title": "...", "description": "..."}}
```

* `h1`: Same as in Markdown.
* `title`: 30-60 chars before an optional ` | {brand}` suffix (`[project] brand` of
  `project.toml` in the data root; no brand, no suffix). Contains the main keyword, no colon.
* `description`: 100-160 chars. Contains the main keyword; state only facts about
  the store given in the inputs.
* Client phrases: only those `[meta] required_phrases` of `project.toml` lists for the
  language; none listed, none required.

Then run `validate.meta` on the file with `--keywords` pointing at the `_clean.json`.

### Phase 4: Self-Correction

**CRITICAL STEP:** Do not stop after writing.

1. **Run Validation:**

    ```
    Use llm_keywords_pipeline.validate.content module to validate the generated MD file
    against the main keyword.
    ```

2. **Analyze Output:**
    * If `overall: FAIL`: Fix the blockers (usually H1 or opening-paragraph keyword).
    * If `overall: WARNING`: Check the issues.
    * *Water/Nausea?* If slight deviation, ignore. If high, tighten the text.
    * *Structure?* Fix missing sections.
    * *Blacklist?* Remove spam phrases.
3. **Re-run Validation:** Ensure status is PASS or acceptable WARNING.
4. **Check Sync:** Ensure MD H1 matches JSON H1.

---

## Checklist for Final Output

* [ ] File `categories/{slug}/content/{slug}_ru.md` created.
* [ ] File `categories/{slug}/meta/{slug}_meta.json` created.
* [ ] H1 matches in both files.
* [ ] Content validation passes (refer to `llm_keywords_pipeline.validate` modules).
* [ ] Text is helpful, structured, and free of "SEO spam".
* [ ] Every structure item above is present, links included; no terms block.
* [ ] No placeholder or confirmation marker; each unconfirmed fact is an owner question
      in `brief.md` and the hand-over.
