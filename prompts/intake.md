# INTAKE: client brief before keyword filtering

Step 0 of the workflow in `AGENTS.md`. Collect the facts about the shop that decide which
keywords stay and what a text may claim, before any keyword is grouped or dropped.

**Output:** `<data root>/brief.md` and the `project.toml` keys listed in Output below.
**Done when:** every question below has an answer with a source in `brief.md` or sits
under `Open questions`, and every collected item below is filled or marked unavailable.

A fact counts only with its source: the owner's words with a date, a site URL, or a file
path. Texts and keyword choices may rely only on sourced facts; an open question means
the keyword or the claim stays out until the owner answers.

## 1. Collect without asking

Gather these first, so the questions to the owner cover only what the site cannot tell.

- **Categories:** each category of the site with its URL and product count; empty and
  near-empty categories marked. A keyword is kept only for a category that sells it.
- **Info pages:** about, delivery, payment, terms, contacts. Copy the facts they state:
  addresses, warehouses, pickup points, min order, payment and delivery terms, who may buy.
- **Current meta:** title, description and H1 of the home page and each category, so new
  texts keep what is true and replace what is not.
- **Brands:** brands the catalog actually lists.
- **Client documents:** files the owner put in the data root or the repo (price lists,
  contracts, earlier briefs).

A page that needs a login or returns an error: record it as unavailable, with the URL.

## 2. Ask the owner

Send only questions the collected facts leave open; quote what the site says and ask to
confirm it where it is ambiguous. Each answer decides keywords or text:

| Question | Decides |
| --- | --- |
| Business type: producer, official distributor, importer, reseller, retailer? | «від виробника» / «от производителя» only for a producer; «офіційний дистриб'ютор» only with the owner's confirmation |
| Wholesale, retail or both? | Keep or drop «опт», «роздріб», «купити 1 шт» keys; `[meta] required_phrases` |
| Who buys: legal entities, ФОП, private persons; is registration needed to see prices or order? | Keys like «для магазину», «для ФОП»; the access terms stay on the info pages, linked from the home text |
| Regions served, warehouses, pickup points, delivery carriers? | City keys only where a warehouse or pickup point is confirmed; «доставка по Україні» only if confirmed |
| Min order, payment methods, deferral, prices shown to guests? | Keys with «мінімальне замовлення», «відтермінування», «ціна»; the terms themselves stay on the info pages, linked from the home text |
| Assortment: which categories and brands are sold; which competitor brands are never named? | Trademark keys only for brands the shop sells; `[blacklist] brands` |
| Phrases the owner bans or requires? | Required: `[meta] required_phrases`, `recommended_phrases`. Banned: listed in `brief.md` only, no key checks them |
| Languages, and which is primary? | `[project] languages`; which texts come first |
| Tone and audience of the texts? | `[niche] tone` |

## 3. Output

`<data root>/brief.md`, one fact per line with its source:

```markdown
# Brief: <shop>
Site: <url>. Collected: <date>.

## Facts
- Business type: official distributor of X. Source: owner, 2026-11-17, «...».
- Min order: 3000 грн. Source: https://shop.example/oplata
- Pickup: Kyiv, вул. ... Source: https://shop.example/contacts

## Categories
| Category | URL | Products |

## Keyword rules
- Drop city keys except Київ (pickup point confirmed above).
- Drop «від виробника» keys (not a producer).

## Open questions
- Deferral for new clients? Asked 2026-11-17.
```

`project.toml` keys the brief fills (shape and comments: `AGENTS.md`, section New client):

- `[project] brand`, `site`, `languages`
- `[meta] required_phrases`, `recommended_phrases` from required phrases and the
  wholesale/retail answer
- `[blacklist] brands` from the competitor brands, `cities` (false only when the texts
  will name a confirmed warehouse or pickup city), `phrases_allow` (required phrases the
  strict-phrase audit would flag; it turns their check off)
- `[niche] tone`

## 4. Excluding keywords

Each keyword dropped because of the brief goes out of `data/ru_semantics_master.csv` (a key
left there comes back into `supporting` on the next sync) and into a top-level `excluded`
list of the category's `_clean.json` with a reason that cites the brief (UK has no CSV:
the UK file gets only the `excluded` entry):

```json
"excluded": [
  {"keyword": "цукерки від виробника", "volume": 90, "reason": "brief: not a producer"}
]
```

Sync keeps top-level keys it does not own, and no command reads `excluded`, so the list
stays as written. `sync.merge_master --excel f.xlsx` adds every Excel keyword missing from
the `_clean.json` files back to the master CSV as an `uncategorized` row (sync skips such
rows): delete the rows of excluded keys, so none is given a category again.
