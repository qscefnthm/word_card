# Quick review update — 2026-10-06.1

Scope: quick overview UI only. Vocabulary, catalog version, audio, formal flashcard source, maintenance workflow and existing storage keys remain unchanged.

## Features

- Both list overview and the last card/completion screen expose an explicit next-deck button.
- Next deck uses catalog order, preserves view/core filter and resumes the destination deck's saved card position. It clears search, scrolls to the top, never auto-wraps, and keeps current content on a failed fetch.
- List view has bilingual and English-recall sections. Recall shows the English headword and an optional area to write a Chinese meaning; original forms, notes and Chinese usage cues are not exposed before revealing answers.
- Reveal one meaning or the whole filtered set, then hide again. Headword meaning and phrase meaning stay separate. There is no automatic grading.
- Drafts and the list preference use only the new `word-card-recall-v1` localStorage key, scoped by deck/card and checked against the headword. Drafts are local to the browser; they are not added to the existing export or cloud-synced. Read/write failures are disclosed. Answers are concealed on restart/deck change even when drafts survive.
- Existing `word-card-site-v2` ratings/runs and `word-card-quick-v1` indices are preserved. List filtering no longer resets saved paged positions.
- Page footer reports `速览界面 2026-10-06.1`; the vocabulary version remains `2026-09-28.1`.

## Verification at the baseline

Baseline commit: `34b216c6d61b50e9821ba561701e7f6cebbb61f8`. Relevant local source blobs were checked against that remote tree before editing.

- `python3 tools/validate.py`: PASS, 7 decks / 226 cards, including existing audio metadata.
- Node syntax checks for app.js, quick.js and quick-extras.js: PASS.
- Existing `tools/test_components.py`: 25 PASS (formal card component/import-export regression).
- New `tools/test_quick_review.py`: 40 PASS, including all current deck terms/meanings, explicit reveal, input escaping, draft serialization, core/search/mode switching, next-deck and terminal-deck behavior, failed fetch/retry, mock storage failure, saved ratings/runs/indices, desktop and 390px/320px layout, and existing MP3 blob playback.
- Static HTML IDs/resources checked; no duplicate element IDs.
- Vocabulary, catalog, all audio files, index.html and app.js are byte-identical to baseline.

The runtime environment blocked local HTTP browser navigation with ERR_BLOCKED_BY_ADMINISTRATOR. No policy settings were changed. Browser checks therefore use offline DOM with mock JSON fetch, Storage and history; serialized reloads are simulated. They do not verify native persistence, live HTTP/CSP or HarmonyOS hardware. MP3 playback was exercised from in-memory existing audio, not listening-quality verification. Deployment and public-site verification must be reported separately.

Tests use synthetic records only; no learner records, book scans or private history are committed.
