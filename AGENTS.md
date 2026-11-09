# Reading Review and Word Card maintenance rules

## Scope and source of truth

- This static site for `qscefnthm/word_card` primarily supports exam-reading vocabulary review. Daily vocabulary memorization returns to the user's vocabulary software. Preserve the fixed Pages URL and the existing night-card design.
- `index.html` puts reading review first and retains the original card DOM as a collapsible auxiliary area. Existing card deep links must still open the correct card; `quick.html` keeps its address. Do not delete the old card library or replace old scripts/audio in this transition.
- Reading-review source of truth: `data/review/catalog.json` + batch files such as `data/review/2014-e1.json`, rendered by `review.html`. Legacy-card source of truth remains `data/catalog.json` + `data/decks/*.json`. Never duplicate vocabulary in HTML or JavaScript.
- The first reading-review batch is 2014 English I Texts 1–4: 129 entries (117 highlight review groups, 12 supplemental). Support each Text and Text 1+2 / Text 3+4 groups. These are target counts, not evidence that source review or deployment has passed.
- Show English first; reveal contextual meaning, source location and the supplied 红宝书 original definition on demand. No new audio is required for this batch. Do not publish full exam papers or private handwriting.
- Do not upload the full vocabulary PDFs, exam scans, private learning logs, personal timetable, tokens, or passwords.
- Do not change repository visibility without explicit owner authorization. Pages public access must not be described as private access.

## Content

- Prioritize words highlighted in the provided reading, then answer-option words that caused mistakes. Do not silently inject a large unrelated word list.
- Yellow = unfamiliar term; red wave = user's proposed answer evidence; other red notes = corrections. Do not invent marked evidence.
- Preserve `book` word, number, page, englishPage and definition from the supplied source. Keep contextual meaning, translation, and explanatory note separately labeled.
- Inflected forms link to their lemma; phrases or derived forms link to relevant entries without claiming independent inclusion.
- The initial 32 cards are migrated from the provided 2010 English I Text 4 HTML, not recreated from memory.

## Stable progress and updates

- Do not change existing card IDs or the localStorage key `word-card-site-v2` for routine updates.
- Same ID across decks means same lexical item/sense and shared familiarity. Use different IDs for genuinely different senses.
- Add/update deck files; update catalog count, date, and version. Keep the running review round as a snapshot; new cards appear when starting a new round.
- Keep import support for original `night-vocab-2010t4` v1 and site `word-card` v2 exports. Merge by timestamp; old imports must not erase newer ratings.
- No login or automatic cross-device progress synchronization exists. Do not claim one. Export/import is a manual transfer, not cloud sync.
- No automatic study-time accounting and no minimum-time pressure. Do not add scheduled tasks for this transition.
- Reading-review progress uses only `exam-reading-review-v1`, a long-term namespace for multiple batches, not just 2014. Keep entry IDs stable and scope progress by batch and entry; changing the selected Text must not overwrite another batch.
- New review/home code must not migrate, write or clear `word-card-site-v2`, `word-card-quick-v1`, `word-card-recall-v1` or the legacy `zhou-night-vocab-2010t4-v1` key. Legacy modules retain their existing behavior; new import/export must remain independent and must not accept old card backups as review backups.

## Verification and deployment

1. Read the current remote commit/files before editing; preserve unrelated changes.
2. Run legacy checks: `python3 tools/validate.py`, `python3 tools/test_components.py`, `python3 tools/test_quick_review.py`, and `node --check` for `assets/app.js`, `assets/quick.js`, `assets/quick-extras.js`. Also run `python3 tools/validate_review.py`, `python3 tools/test_review.py`, `node --check assets/review.js`, and `node --check assets/home.js` for reading review. Missing dependencies or scripts mean checks are pending, not passed.
3. Check desktop and mobile rendering, flip/rate/search, refresh/resume, export/import, and vocabulary updates without progress loss.
4. Use project-relative asset paths to work under `/word_card/`.
5. `.github/workflows/validate-reading-review.yml` is the permanent read-only regression workflow for both modules. It never writes source files or learning records back. A successful run must correspond to the exact revision being published.
6. Commits, Pages enablement, deployment success, and live HTTP verification are separate states. Report only what is verified.
7. Never bypass connector safety blocks. If writes are blocked, leave the remote untouched and provide the prepared source and exact blocker.

## Reading-review content guard (2026-11-09)

- Review entries use their own schema and validation, not the legacy full-example-card schema. Preserve actual source words, contextual meanings and reliable locations; never invent a complete sentence just to satisfy a legacy validator.
- A short excerpt must be labeled “原文定位片段（非完整例句）”; a location without an excerpt is “原文位置”. Only a complete checked source sentence may be labeled “真题正文原句”. Assistant-written text is “补充例句（助手编写，非真题原句）”. Do not mix these provenance labels.
- “黄标” versus “补充” describes selection provenance, not whether the quoted text is original. Preserve this distinction and all independently verified book/source fields.
- 红宝书 comparison is required. Distinguish exact entries, inflection/lemma links, related entries and confirmed absence from unresolved source access. Never label an unverified mapping as checked.
- Read the review workflow in `WORD_CARD_UPDATE_WORKFLOW.md` before adding later years/batches. Do not apply legacy audio-generation requirements to this audio-free module.

## Legacy-card content audit guard (2026-09-27)

The following complete-sentence schema and pronunciation rules remain mandatory for legacy cards. They do not force reading-review entries into that schema.

- `meaning` describes the displayed `term`. Do not silently include a negation, comparison, subject or object found only in the example.
- Keep the example's exact phrase in `collocation` and translate that phrase separately in `collocationMeaning`.
- Every `quote` must be a complete example sentence, not a standalone option, headword or unfinished question stem.
- Preserve negation, conditions, attribution and scope. Do not turn uncertainty or a rejected claim into an asserted fact by clipping its context.
- `exampleType: original` uses `quoteType: 真题正文原句` only for a complete sentence checked against the supplied reading. Newly written examples use `exampleType: supplemental` and `quoteType: 补充例句（助手编写，非真题原句）`; they cannot be marked as original answer evidence.
- Both card views must show example provenance and distinguish headword meaning from phrase meaning.
- Preserve stable IDs and source-book records during repairs. Shared IDs must have agreeing headword meanings.
- Regenerate pronunciation after any headword or `spokenText` change. Audio `terms` and `spokenTexts` must match the card.
- Run `python3 tools/validate.py`, including `check_card_content.py`, plus syntax checks for both page scripts. Mechanical checks do not replace source/content review.

## Required update workflow

Before adding, supplementing, correcting, or publishing reading-review entries or legacy vocabulary cards, read and follow [WORD_CARD_UPDATE_WORKFLOW.md](WORD_CARD_UPDATE_WORKFLOW.md). This is the canonical end-to-end maintenance workflow: source review, headword/phrase/example alignment, book references, stable IDs and progress, audio, validation, and deployment evidence.

Do not silently change its content standards or teaching approach. Changes to the workflow require the user's explicit request or approval. A routine vocabulary update must not rewrite this workflow.
