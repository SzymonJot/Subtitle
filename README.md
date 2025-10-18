# Subtitle

*Automated subtitle processing → vocabulary extraction → spaced‑repetition decks.*

This project ingests subtitle files (e.g., `.srt` / `.vtt`), performs NLP to extract useful vocabulary in context, and builds language‑learning decks (Anki/Quizlet‑ready). It’s the backbone behind an MVP for Swedish (and other languages) vocabulary learning from real shows.

> **Status:** Early public WIP. Interfaces and file paths may change.

---

## Features

* **Subtitle ingestion & cleaning** – normalize whitespace, split into sentences/words, handle edge cases.
* **NLP pipeline** – lemma/POS extraction, per‑lemma frequency & coverage metrics, context examples.
* **Candidate selection & ranking** – choose the most useful items to learn (by coverage / frequency / custom score).
* **Deck builder** – export flashcards with example sentences and (optionally) translations.
* **Batchable pipeline** – process episodes/file sets; designed to run locally or as background jobs.
* **Test suite** – unit tests for critical text/ID routines (see `test/`).

---

## Project layout

```
Subtitle/
├─ api/            # (optional) service endpoints (e.g., FastAPI) to orchestrate builds
├─ common/         # constants, helpers shared across modules
├─ core/           # core domain logic (selection, scoring, ranking)
├─ deck/           # deck formats, card schema, exporters (Anki/Quizlet)
├─ infra/          # integration glue (e.g., storage, cache, queues)
├─ nlp/            # text cleaning, tokenization, lemma/POS tagging
├─ pipeline/       # end‑to‑end orchestration (analysis → build → export)
├─ worker/         # background job runner (e.g., RQ/Redis)
├─ test/           # unit tests
└─ requirements.txt
```

> See also: `decisions.md` for design notes and trade‑offs.

---

## Quickstart

### 1) Create a virtual environment

```bash
python -m venv .venv
. .venv/bin/activate   # Windows: .venv\\Scripts\\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2) Prepare input subtitles

Put one or more `.srt`/`.vtt` files in an input folder, for example `data/input/`.

### 3) Run the analysis → deck build pipeline

> The exact entry point may change while the project evolves. A typical pattern is:

```bash
python -m pipeline.run \
  --input "data/input/*.srt" \
  --lang sv \
  --export anki \
  --out data/output/
```

Parameters you can expect:

* `--input`: glob of subtitle files to process
* `--lang`: ISO code, e.g., `sv` (Swedish), `en`, `pl`
* `--export`: `anki` | `quizlet` | `json`
* `--out`: output directory

### 4) Import into Anki / Quizlet

* For Anki: import the generated `.apkg` or `.csv` according to your preference.
* For Quizlet: import the exported `.csv`.

---

## Configuration

Create a `.env` (or use env vars) for optional integrations:

```
DEEPL_AUTH_KEY=...        # if using DeepL translations
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
REDIS_URL=redis://localhost:6379/0
```

Additional knobs are usually exposed via CLI flags or config files under `pipeline/`.

---

## How it works (high level)

```
[SRT/VTT files]
      │
      ▼
 [nlp.cleaning]  → normalize, dedupe whitespace, split to sentences/words
      │
      ▼
 [nlp.tagging]   → lemma/POS, per‑token metadata
      │
      ▼
 [core.metrics]  → frequency & coverage per lemma; attach example sentences
      │
      ▼
[core.selection] → choose candidates (filters, known‑words exclusion)
      │
      ▼
 [core.ranking]  → score by coverage/frequency/custom heuristics
      │
      ▼
  [deck.build]   → render cards (front/back, example, translation*)
      │
      └──────────→ *translation optional via provider (e.g., DeepL)
```

---



## Roadmap (short)
* [ ] Configurable selection strategies (coverage‑driven vs frequency‑driven)
* [ ] Caching layer for context translations (surface + sentence key)
* [ ] Export presets for Anki/Quizlet
* [ ] Minimal web API to kick off builds 

---

## License

MIT (unless noted otherwise in submodules/assets).
