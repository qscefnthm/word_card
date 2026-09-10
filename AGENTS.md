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
