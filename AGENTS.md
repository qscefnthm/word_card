# Word Card maintenance rules

## Scope and source of truth

- This is a static vocabulary site for `qscefnthm/word_card`. Preserve the fixed Pages URL and the existing night-card design.
- Vocabulary source of truth: `data/catalog.json` + `data/decks/*.json`. Never duplicate vocabulary in HTML or JavaScript.
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
- No automatic study-time accounting and no minimum-time pressure.

## Verification and deployment

1. Read the current remote commit/files before editing; preserve unrelated changes.
2. Run `python3 tools/validate.py` and `node --check assets/app.js`.
3. Check desktop and mobile rendering, flip/rate/search, refresh/resume, export/import, and vocabulary updates without progress loss.
4. Use project-relative asset paths to work under `/word_card/`.
5. Commits, Pages enablement, deployment success, and live HTTP verification are separate states. Report only what is verified.
6. Never bypass connector safety blocks. If writes are blocked, leave the remote untouched and provide the prepared source and exact blocker.

## Content audit guard (2026-09-27)

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

Before adding, supplementing, correcting, or publishing vocabulary cards, read and follow [WORD_CARD_UPDATE_WORKFLOW.md](WORD_CARD_UPDATE_WORKFLOW.md). This is the canonical end-to-end maintenance workflow: source review, headword/phrase/example alignment, book references, stable IDs and progress, audio, validation, and deployment evidence.

Do not silently change its content standards or teaching approach. Changes to the workflow require the user's explicit request or approval. A routine vocabulary update must not rewrite this workflow.
