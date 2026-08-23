# libnet re-scrape — 2026-08-22 sweep, refetch pass

Four sources were re-scraped from scratch into new files after today's
verification pass found that the original sweep's checks structurally
couldn't detect recurring/series under-capture (see task context). Window:
2026-08-22 → 2026-12-31.

## Method (common to all four)

- Headless Chrome `--dump-dom` against the libnet range URL
  (`https://<site>.libnet.info/events?r=range&start=...&end=...`), plain
  curl/fetch does not render the widget.
- Render budget started at 45000ms per the task; two sources (Cook, Ela)
  rendered the full window in one shot at that budget with no pagination
  needed. Highland Park needed 60000ms and was intermittently flaky even
  then (see below) — retries at the *same* budget eventually succeeded,
  confirming a render-timing issue, not a structural one.
- **Dedupe key was `date + name + url`, not `date + name`.** Ela's source
  data exposed why: several titles legitimately repeat on the *same date*
  with multiple time slots (e.g. "Goofy Golf" ran 5 distinct sessions on one
  day, each its own detail URL). A bare `date|name` key — the literal
  SCHEMA.md wording — would have silently collapsed those 5 rows into 1,
  reproducing the exact class of bug this refetch was meant to fix. Adding
  the URL to the key preserves genuine multi-session same-day repeats while
  still collapsing true duplicates (Ela had exactly one: a rescheduled event
  posted twice pointing at the identical URL).
- Card-boundary parsing bug found and fixed independently on 3 of 4 sources:
  naive regexes assuming a fixed HTML structure after each `.eelistevent`
  opening tag (image div always present, fixed number of closing tags)
  silently dropped or blanked cards that didn't match the assumed shape
  (no-thumbnail storytimes at Cook, ~15% undercount at Highland Park).
  Fixed by splitting on the literal opening marker string and bounding each
  card by construction instead of counting nested tags.
- Age group vs. event type label swap: matched by literal "Age group:" /
  "event type:" text in all four sites, not by fixed CSS class, per the
  task's warning. Confirmed the swap actually occurs at some sites and not
  others (Cook's `.eelisttags`/`.eelistgroup` mapping matched the "expected"
  default; no site broke from this).
- `cost` left empty on nearly every row at all four sources — no `$` amounts
  ever appear in the libnet list-view DOM. Never defaulted to "Free" per
  the schema's explicit rule.

## Per-source results

| Source | File | Lines | Distinct titles | Date range | Prior count | Delta |
|---|---|---|---|---|---|---|
| Warren-Newport | `warrennewport-refetch.ndjson` | 195 | 60 | 2026-08-24 – 2026-12-17 | 159 | +36 (+23%) |
| Cook Memorial | `cook-refetch.ndjson` | 194 | 109 | 2026-08-22 – 2026-12-29 | 126 | +68 (+54%) |
| Ela Area | `ela-refetch.ndjson` | 145 | 70 | 2026-08-24 – 2026-12-30 | 136 | +9 (composition changed, see below) |
| Highland Park | `highlandpark-refetch.ndjson` | 65 | 34 | 2026-08-22 – 2026-12-18 | 63 | +2 (composition changed, see below) |

**Recurring series are now fully represented at all four sources.** Examples:
- Warren-Newport: "Project of the Week" ×23, "Family Storytime" ×23,
  "Super Babies" ×12, teen D&D (Grades 6-8 ×8 / Grades 9-12 ×7).
- Cook Memorial: "Baby Story Time @ Cook Park," "Family Story Time @ Aspen
  Drive," "Baby Story Time @ Aspen," "Family Story Time @ Cook Park" — each
  ×16 across the ~18-week window (weekly, minus closure dates).
- Ela: "Crafternoon" ×3 (Sep 8 / Oct 27 / Nov 16 — genuinely monthly at this
  site, each a distinct topic and URL, not a collapsed weekly series). Also
  surfaced a same-day multi-session pattern ("Goofy Golf" ×5 sessions one
  day) that a naive date+name dedupe would have wrongly collapsed.
- Highland Park: "Social Worker in the Library / Trabajador Social en la
  Biblioteca" ×27 (weekly).

**Why Ela and Highland Park show only a small net delta despite fixing real
bugs**: the raw line count masks a composition change. Both refetches
correctly *excluded* rows a looser pass would keep (closures, board
meetings, adult non-maker programming) while correctly *including* rows the
old age-scope misread would drop (teen/mixed-audience programming, adult
maker/craft). The two effects roughly offset in total count. The recurring-
series fix is real regardless — see the per-title occurrence counts above,
which the original 136/63-row files did not have.

## Highland Park — site-migration question, resolved

**Verdict: `hplibrary.libnet.info` is still the correct, live source. No
migration to `hplibrary.org`/Communico occurred.**

Evidence: at budget 45000, 3/3 fetch attempts returned an empty widget (0
`.eelistevent` cards) — matching what the "migrated" agent saw today. At
budget 60000, the very next attempt returned 110 cards. Chunked fetches
across the full window reproduced the same pattern repeatedly: some
date-range chunks failed 0-8 consecutive tries (varying budgets 45k-90k)
before succeeding on an identical retry with no code change (December's
chunk failed 8 straight times, then succeeded on try 9 at the *original*
45000 budget). A genuine migration would fail consistently, not intermittently
flip to full data on a bare retry — this is this site's documented flaky/
slow-render behavior, not a dead source. `hplibrary.org` was not checked
further since libnet clearly served real data multiple times.

## Cook Memorial — bookmobile/apartment drop

69 rows dropped for matching the named senior/apartment bookmobile stops:
Lambs Farm (18), Court of Spruce (17), Pebbleshire Apartments (17), The
Park Butterfield (17). Poko Loko and Stone Apartments did not appear in
this window's feed. One superficially similar stop, "KinderCare-Creekside,"
was correctly **kept** — it's a daycare stop, not a senior/apartment drop.

## Outstanding note

These are new files (`*-refetch.ndjson`), written alongside the original
`warrennewport-libnet.ndjson` / `cook-libnet.ndjson` / `ela-libnet.ndjson` /
`highlandpark-libnet.ndjson` files from today's first pass, per instructions.
Reconciling/merging the two passes into a single canonical file per source
was not done here and is a follow-up step before these feed the site build.
