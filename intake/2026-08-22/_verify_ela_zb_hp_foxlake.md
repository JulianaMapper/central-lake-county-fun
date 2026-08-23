# Verification: Ela / Zion-Benton / Highland Park / Fox Lake — 2026-08-22 sweep

## Ela Area Public Library (8 rows)

| Date | Name | Verdict |
|---|---|---|
| 2026-09-07 | Holiday Closing | STILL-LIVE (confirmed, but DROP per schema — closures are explicitly unwanted, not a recovery candidate) |
| 2026-09-08 | Crafternoon (grades K-5) | STILL-LIVE — scraper gap, recovered |
| 2026-09-24 | State Senator Darby Hills' Traveling Office Hours | STILL-LIVE — scraper gap, but DROP per schema (adult meeting, not maker/craft) |
| 2026-10-27 | Crafternoon (grades K-5) | STILL-LIVE — scraper gap, recovered |
| 2026-11-16 | Crafternoon (grades K-5) | STILL-LIVE — scraper gap, recovered |
| 2026-11-26 | Holiday Closing | STILL-LIVE (DROP per schema) |
| 2026-12-24 | Holiday Closing | STILL-LIVE (DROP per schema) |
| 2026-12-25 | Holiday Closing | STILL-LIVE (DROP per schema) |

**Root cause:** All 8 are genuinely still on the source (confirmed via headless
dump of `eapl.libnet.info/events?r=range&start=2026-08-22&end=2026-12-31`,
45s budget) with exact matching dates/times/IDs. This is **not** an artifact
of dropping the old `&a=Kids` filter — Crafternoon carries only a `Kids` age
tag and was still missed, and Holiday Closing/Darby Hills carry `Teens, Kids,
Adults` (all ages) tags, so age-filtering isn't the mechanism either. The
`.eelisttags`/`.eelistgroup` class assignment is also standard here (tags=age,
group=type) — no swap on this site.

Actual pattern: every missed row is a **repeat occurrence of a recurring
title** — "Crafternoon" appears 3x in the window, "Holiday Closing" 4x,
sharing the exact same title string each time. This strongly suggests the
parser (or a de-dupe step downstream of it) is collapsing same-titled
`.eelistevent` blocks and keeping only the first occurrence, silently
dropping the rest. "Darby Hills' Traveling Office Hours" is the one
one-off exception — its title contains a typographic apostrophe (`'`)
which may be breaking a regex/JSON step that assumes plain ASCII quotes;
worth checking separately.

Net: 3 of 8 are legitimate KEEP-worthy misses (Crafternoon, recovered below);
5 of 8 (4 Holiday Closing + 1 office-hours meeting) are correctly excluded
under current schema rules regardless of the scraper gap.

## Zion-Benton Public Library District (7 rows)

| Date | Name | Verdict |
|---|---|---|
| 2026-09-10 | Teens vs Procrastination | REMOVED (superseded — see below) |
| 2026-10-08 | Teens vs Procrastination | REMOVED (superseded) |
| 2026-10-13 | Paper Crafts | REMOVED (superseded) |
| 2026-11-10 | Paper Crafts | REMOVED (superseded) |
| 2026-11-12 | Teens vs Procrastination | REMOVED (superseded) |
| 2026-12-08 | Paper Crafts | REMOVED (superseded) |
| 2026-12-10 | Teens vs Procrastination | REMOVED (superseded) |

All 7 old event IDs return HTTP 404 on `zblibrary.libnet.info/event/<id>`.
This is a genuine source-side change, not a scraper artifact: the library
edited/re-created its recurring series under new IDs and slightly changed
titles/dates. Confirmed via headless dump of the full events range (511
event blocks rendered at 45s budget — an earlier 30s-budget attempt looked
truncated at 43 raw substring matches but that was a grep artifact, not an
actual render cutoff; the 45s dump reaches December 31 fine, so no HP-style
budget problem here):

- "Teens vs Procrastination" → now titled **"Teen VS Procrastination"**,
  new occurrences Wed Sep 09, Oct 14, Nov 11, Dec 09 (new IDs 17263230-33).
- "Paper Crafts" → now titled **"Junk Journals" / "Junk Journaling"**, new
  occurrences Tue Sep 08, Sep 15 (IDs 17163592, 17248571) — fewer occurrences
  found in-window than the old series had, so this series may also have been
  shortened, not just renamed.

Not added to recovered NDJSON: these are new identities (different title),
not a same-identity reschedule of the flagged rows, and out of scope for this
verification pass (they're a fresh scraper-normal capture, not a "gone" row
resurrection).

**Root cause:** legitimate upstream edit to the recurring series (title +
ID churn). Nothing for the scraper to fix.

## Highland Park Public Library (5 rows)

| Date | Name | Verdict |
|---|---|---|
| 2026-09-05 | Game Club | STILL-LIVE — recovery skipped (age unverifiable) |
| 2026-11-25 | Early Closing | STILL-LIVE (DROP per schema — closure) |
| 2026-12-05 | Game Club | STILL-LIVE — recovery skipped (age unverifiable) |
| 2026-12-24 | Early Closing | STILL-LIVE (DROP per schema) |
| 2026-12-31 | Early Closing | STILL-LIVE (DROP per schema) |

All 5 confirmed live via direct detail-page fetch (`hplibrary.org/event/<id>`,
200, JSON-LD `startDate` matches exactly).

**Root cause — bigger than the flagged virtual-time-budget issue:**
`hplibrary.libnet.info/events` (the URL this sweep used) renders **zero**
event blocks at any budget tested (20s/30s/45s) — the DOM dump contains only
the widget's CSS, no `.eelistevent` content at all. This isn't "the tail got
cut off," it's a dead listing: Highland Park's live calendar has moved to
**`hplibrary.org`** (Communico platform; `hplibrary.libnet.info` individual
event pages 404, confirming the libnet backend is retired for this org).
However, `hplibrary.org/events` *also* failed to render any event blocks in
headless dump (same empty output, tested 30s/45s) — its listing appears to
fetch via a separate JS API call to `api.communico.co` that either needs
longer than 45s, blocks headless/automated requests, or needs a differently
shaped URL than the libnet `r=range&start=&end=` pattern. Individual detail
pages (`hplibrary.org/event/<id>`) work fine via plain curl (server-rendered
JSON-LD), so a page-by-page approach could work as a stopgap, but there's no
month/range listing endpoint confirmed working yet for discovery of *new*
events — only for re-verifying already-known IDs.

**Action needed beyond this pass:** the next sweep needs a working
Highland Park listing method (right domain + a listing endpoint proven to
populate in headless mode, or a `sitemap`/API contract) before it can find
new HP events at all — this pass could only reconfirm known ones.

## Fox Lake District Library (3 rows)

| Date | Name | Verdict |
|---|---|---|
| 2026-08-22 | Play-Doh Playdates (Ages 2-7) | STILL-LIVE — scraper gap, recovered |
| 2026-08-22 | Awkward Family Photos | STILL-LIVE — scraper gap, recovered |
| 2026-09-07 | Foxy's Spice-sations! Turmeric | RESCHEDULED → 2026-09-14 (also DROP-eligible: adult, non-maker) |

**Root cause:** Rows 1–2 fall on 2026-08-22 itself, the sweep's own run
date/window start — a month-grid scraper that treats "start" as exclusive,
or a same-day-events filter, would drop exactly these two and nothing else.
Both are confirmed present via `fllib.org/event/...` detail pages with exact
matching date/time. Row 3 is a genuine one-week reschedule at source (site
shows a recurring "first Monday" spice series; Sept 7 was dropped from the
schedule, Sept 14 is the live occurrence) — not a scraper issue, and it's
also excluded from recovery regardless because it's an adult grab-and-go
sampling program, not maker/craft.

## Recovered NDJSON

- `intake/2026-08-22/ela-recovered.ndjson` — 3 lines (Crafternoon x3)
- `intake/2026-08-22/fox-lake-district-library-recovered.ndjson` — 2 lines
  (Play-Doh Playdates, Awkward Family Photos)

No recovery file created for Zion-Benton (superseded events are a different
identity, out of scope) or Highland Park (Game Club age could not be
confirmed without fabricating a field — schema says empty beats a guess, but
`audience` is a required enum, so it was left out entirely rather than
guessed).

## Summary — why these were missed

1. **Ela:** parser/de-dupe appears to collapse repeat occurrences of a
   recurring title, keeping only the first (Crafternoon, Holiday Closing).
   One likely-separate cause: a typographic apostrophe in a title (Darby
   Hills'). The dropped `&a=Kids` filter is **not** the cause.
2. **Zion-Benton:** not a scraper bug — the library renamed/rebuilt these
   recurring series upstream; old IDs are genuinely gone.
3. **Highland Park:** wrong/dead domain (`hplibrary.libnet.info` has an
   empty events widget) plus the replacement domain's listing page also
   fails to render in headless mode — this is a bigger gap than the
   previously-known virtual-time-budget issue; HP needs a new discovery
   method, not just a longer budget.
4. **Fox Lake:** likely an off-by-one on the sweep's start date, dropping
   same-day events; one row is a genuine reschedule.
