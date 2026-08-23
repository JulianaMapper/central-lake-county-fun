# Verification: Crystal Lake Public Library (20) + Cook Memorial Public Library District (6)

Method: fetched each event's own URL directly with `curl` (Crystal Lake) and
`curl -L` (Cook, libnet redirects). "STILL-LIVE" = HTTP 200 and the page's own
date/title matches the row. No headless browser needed for verification itself —
only for diagnosing the root cause below.

## Crystal Lake Public Library — 20/20 STILL-LIVE

| Date | Name | Verdict |
|---|---|---|
| 2026-08-26 | Dream Riders Story Time | STILL-LIVE |
| 2026-09-14 | Baby Time | STILL-LIVE |
| 2026-09-15 | Family Story Time | STILL-LIVE |
| 2026-09-15 | Toddler Time | STILL-LIVE |
| 2026-09-16 | Family Story Time | STILL-LIVE |
| 2026-09-16 | Preschool Story Time | STILL-LIVE |
| 2026-09-17 | Virtual - Storytime with Ms. Karamy | STILL-LIVE |
| 2026-09-17 | Bilingual Story Time/Hora de Cuentos Bilingüe | STILL-LIVE |
| 2026-09-21 | Baby Time | STILL-LIVE |
| 2026-09-22 | Family Story Time | STILL-LIVE |
| 2026-09-22 | Toddler Time | STILL-LIVE |
| 2026-09-23 | Family Story Time | STILL-LIVE |
| 2026-09-23 | Preschool Story Time | STILL-LIVE |
| 2026-09-24 | Bilingual Story Time/Hora de Cuentos Bilingüe | STILL-LIVE |
| 2026-09-28 | Baby Play | STILL-LIVE |
| 2026-09-29 | Family Evening Story Time | STILL-LIVE |
| 2026-09-29 | Toddler Art Studio | STILL-LIVE |
| 2026-09-30 | Dream Riders Story Time | STILL-LIVE |
| 2026-10-01 | Sandy Oaks Farm Market Story Time | STILL-LIVE |
| 2026-10-03 | Crystal Lake Fire Rescue Department Open House | STILL-LIVE |

Every one of these is real, on the date shown, no cancellation notice. **All 20 are
scraper misses**, not removals. Recovered rows written to
`crystallake-recovered.ndjson` (20 lines).

## Cook Memorial Public Library District — 6 rows: 4 STILL-LIVE, 1 REMOVED, 1 out-of-scope

| Date | Name | Verdict |
|---|---|---|
| 2026-08-24 | Studio Workshop: How to Set Up A Recording Session | STILL-LIVE (scraper miss) |
| 2026-08-27 | The Library @ the Libertyville Farmers Market | STILL-LIVE (scraper miss) |
| 2026-08-29 | Family Maker @ Home! Flextangle | STILL-LIVE (scraper miss) |
| 2026-09-18 | DELAYED OPENING | REMOVED (404 — genuinely gone) |
| 2026-11-12 | LEGO Club | STILL-LIVE (scraper miss) |
| 2026-11-25 | CLOSING AT 5 PM FOR THANKSGIVING | STILL-LIVE, but **out of scope** — it's a holiday-hours notice, not an event. `SCHEMA.md` DROP rules explicitly exclude "Library closures, holiday hours, 'Closed' anything." Not written to NDJSON; should also never have been treated as a countable "live event" on the site in the first place (same rule applies to the 404'd "DELAYED OPENING" row — it was a closure notice too, so its removal is a non-issue either way).

Recovered rows written to `cook-recovered.ndjson` (4 lines — Studio Workshop,
Farmers Market, Flextangle, LEGO Club; Thanksgiving closing correctly excluded).

---

## ROOT CAUSE

### Crystal Lake (librarycalendar.com / Drupal "lc_calendar_theme") — confirmed structural defect, affects every librarycalendar.com source

The month-grid page (`/events/month/{Y}/{M}`) does **not** render the full list of
a day's events into the initial DOM. Each day cell caps at a small number of
"sparse" `article.event-card` blocks (verified: 2 slots per day in the September
grid), and any events beyond that are hidden behind a **"View All Events on
MM/DD/YY"** button:

```html
<a href="/events/feed/html?_wrapper_format=lc_calendar_feed&current_date=2026-09-15&ongoing_events=hide"
   data-ajax-http-method="GET" data-dialog-type="modal" class="... use-ajax">
  View All<span class="visually-hidden"> Events on 09/15/26</span>
</a>
```

That link fires an AJAX request that opens a modal with the true day feed. A
`--dump-dom` capture of the month grid only ever sees what's already in the
initial 2-slot-per-day markup — it never clicks "View All" and never issues that
follow-up request, so it never sees the modal's contents.

**Verified directly:** for 2026-09-15, the month-grid dump shows only 2 events
(Take-and-Make Crafts placeholder + Family Story Time). Fetching the day's own
feed URL (`/events/feed/html?current_date=2026-09-15`) returns `data-count="7"`
and includes **Toddler Time** plus 4 other events the grid never showed.

**Why it hits recurring storytimes specifically:** the 2 visible slots per day
get filled by whatever renders first in DOM order — closures, board/committee
meetings, and the always-present all-day "Take-and-Make Crafts" placeholder
routinely occupy both slots on days that also have 2-3 storytimes stacked
(Family Story Time + Toddler Time + Preschool Story Time all fall on the same
Tue/Wed slate). The storytimes lose the slot race and never make it into the
static DOM at all — they're not paginated, filtered, or in a collapsed
"recurring" wrapper; they're just excluded from what few slots render.

**Fix:** don't scrape the month grid at all. For each date in range, fetch
`https://{subdomain}.librarycalendar.com/events/feed/html?_wrapper_format=lc_calendar_feed&current_date=YYYY-MM-DD&ongoing_events=hide`
directly (plain `curl` works — confirmed, no JS needed for this endpoint) and
parse every `article.event-card` in that response. This is the same Drupal theme
across every librarycalendar.com source in `SOURCES.md` (Grayslake, Wauconda, Fox
Lake, Glen Ellyn, Wheaton, Barrington, Lake Forest, Vernon Area, McHenry) — **all
of them are very likely under-counting recurring children's programming the same
way**, and should be re-swept with the per-day feed endpoint instead of the month
grid.

### Cook Memorial (libnet.info) — likely a render-timing gap, not a structural one

Re-running the exact swept URL
(`cooklib.libnet.info/events?r=range&start=2026-08-22&end=2026-12-31`) through
headless Chrome with a generous 10s `--virtual-time-budget` **did** surface 5 of
the 6 missing events (everything except the genuinely-404'd row) inside the
`.eelistevent` list — no hidden modal, no pagination wall, no age-group filter
excluding them. A plain `curl` (no JS) returns 0 events, confirming the page is
fully JS-rendered via AJAX.

That means the sweep's dump most plausibly ran with too short a
`--virtual-time-budget` (or fired the dump before the 3-month-range AJAX call
resolved) and caught a partially-populated DOM. A 3-month range is a heavier
query than the single-month librarycalendar.com pages, so it plausibly takes
longer to finish loading — worth re-sweeping with a longer wait/budget (10s+)
or by polling for the expected event count before dumping, and checking whether
other libnet.info sources swept with a similarly wide date range (Cook only
has a small in-scope population so the 55% miss rate here is a handful of rows,
but the same timing risk applies to any libnet source hit with a multi-month
range).

## Bottom line
Both "suspicious" flags were correct: **no real removals except one closure
notice that was never a countable event anyway.** Crystal Lake's gap is a
structural parser defect (month grid truncates to ~2 slots/day; the rest lives
behind an unfetched AJAX modal) that likely affects every librarycalendar.com
source in the registry. Cook's gap looks like a render-timing issue specific to
wide date-range libnet queries.
