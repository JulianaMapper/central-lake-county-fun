# librarycalendar.com — per-day feed scraping method (verified 2026-08-22)

## The defect this replaces

`<host>/events/month/{Y}/{M}` (the month grid) is **not a static page for this
purpose**. Confirmed by direct curl (no JS execution): the grid HTML ships
with **zero** `article.event-card` elements per day — every day cell is a
loading spinner (`lc-spinner`) plus a hidden AJAX link
(`/events/feed/html?...&current_date=YYYY-MM-DD`) that Drupal's JS fires on
render. A plain `curl`/static-DOM read of the grid therefore returns nothing
per day; a headless `--dump-dom` render (what the original sweep used) waits
long enough to pick up **some** of that AJAX population — apparently capped
around 2 slots/day in practice — but not all of it, and a "View All Events on
MM/DD/YY" modal exists specifically because the grid's own per-day AJAX call
is itself display-limited. Busy days (7000+ event calendars, holidays,
multi-program days) lose everything past that cap, and recurring low-priority
items (storytimes) lose the slot race to board meetings/closures/the
always-present Take-and-Make placeholder.

## The fix: call the day-feed endpoint directly, once per day

```
GET https://<host>/events/feed/html?_wrapper_format=lc_calendar_feed&adjust_range=1&current_date=YYYY-MM-DD&ongoing_events=hide
```

This is the exact URL the month grid's own per-day AJAX call and the "View
All Events" modal both hit — confirmed by reading the `href` Drupal embeds on
each day cell of the static grid HTML. It returns a **complete, ready-to-parse
HTML fragment** for that single day (a `<section class="calendar calendar--month">`
wrapper containing one `div.calendar__day` with `data-count="N"` and N
`article.event-card` elements) — no wrapping page chrome, so it's cheaper to
parse than a full page.

- **No headless browser needed.** Plain `curl` (or Python
  `urllib.request`) with a standard desktop User-Agent returns HTTP 200 and
  the full fragment. Confirmed on all three hosts below.
- Iterate one request per day across the sweep window — there is no
  multi-day/range variant; `current_month` params were tried on 2026-07-31
  and rejected by the endpoint (that dead-end note in `CLAUDE.md` is now
  corrected), but `current_date` (single ISO date) is accepted and is the
  only supported grain.
- Per-event fields available directly in the feed fragment: title, event URL
  (`/event/<slug>-<id>`), display time, registration status label
  (Open/Upcoming/Closed), and audience-category tags (Kids, Families, Tween,
  Adults, etc. — from the `lc-event-info__item--colors` block).
- Fields NOT in the feed fragment, requiring one `curl` to the event's own
  detail page (`/event/<slug>-<id>`, also plain-curl-able, no headless):
  age group text, full location/address, and any stated fee amount
  (`field--name-description` under a "...Fee" heading). Cost defaults to
  empty when no fee text exists on the detail page — never inferred as Free.

## Confirmed on all 3 target hosts

| host | feed endpoint responds | sample day (2026-09-15) `data-count` |
|---|---|---|
| grayslake.librarycalendar.com | yes, HTTP 200, plain curl | 3 |
| www.wauclib.org | yes, HTTP 200, plain curl | 3 |
| www.fllib.org | yes, HTTP 200, plain curl | 3 |

## Grid-count vs day-feed-count comparison

Static-grid `curl` read (no JS): **0** `article.event-card` per day on every
day inspected (2026-09-14, 09-15, 09-16) on grayslake — the grid ships empty
and relies entirely on the client-side AJAX call this method replicates
directly. This is a stronger version of the defect than "loses the slot
race": a non-headless grid scrape loses 100% of events, and even a headless
`--dump-dom` render only recovers whatever the grid's own capped AJAX
population manages before the DOM is captured.

Day-feed `data-count` values pulled directly (ground truth, matches the
number of `article.event-card` nodes returned):

| org | date | day-feed `data-count` | events kept after DROP filters |
|---|---|---|---|
| Grayslake Area Public Library District | 2026-09-14 | 2 | 2 |
| Grayslake Area Public Library District | 2026-09-15 | 3 | 1 (sewing dropped: adult, paid) |
| Grayslake Area Public Library District | 2026-09-16 | 4 | 4 |

Whole-window yield comparison (2026-08-22–2026-12-31, 132 days), day-feed
method vs the earlier same-day month-grid sweep, both after the same
KEEP/DROP/cost filters:

| source | month-grid sweep (earlier today) | day-feed method | delta |
|---|---|---|---|
| grayslake-librarycalendar.ndjson → grayslake-dayfeed.ndjson | 85 | **120** | **+35 (+41%)** |
| wauconda-librarycalendar.ndjson → wauconda-dayfeed.ndjson | 116 | **95** | **-21 (-18%)** |
| foxlake-librarycalendar.ndjson → foxlake-dayfeed.ndjson | 184 | **150** | **-34 (-18%)** |

Grayslake — the single most important org on the site (0.0 mi) — is the one
that mattered most and it gained 35 events (+41%), consistent with the
verified defect: the grid loses the slot race on busy days and this org runs
the most programming.

Wauconda and Fox Lake came out *lower* under the day-feed method despite the
method being structurally more complete per day. Two likely, non-exclusive
causes, not yet fully disentangled:
1. The day-feed method also applies the corrected COST filter (paid
   non-homeschool events dropped even when the grid/AJAX copy showed no
   price and the earlier sweep may have defaulted them to "Free" and kept
   them — the one thing SCHEMA.md now explicitly forbids).
2. The two methods classify `audience` slightly differently (this method
   derives it from the feed's color-coded category tags + detail-page age
   group text; the grid sweep may have used different signals), which
   changes which rows pass the age-scope KEEP/DROP filters.

This is a real discrepancy worth a follow-up pass — recommend diffing
title+date sets between the two files for Wauconda/Fox Lake before trusting
either total as "the" count. It does not undermine the core finding: the
day-feed endpoint returns strictly more raw events per day than the grid
(proven below), independent of how the two runs then filtered them.

### Per-day raw event count: day-feed vs static grid (ground truth)

| org | date | static month-grid `article.event-card` count (plain curl, no JS) | day-feed `data-count` |
|---|---|---|---|
| Grayslake Area Public Library District | 2026-09-14 | 0 | 2 |
| Grayslake Area Public Library District | 2026-09-15 | 0 | 3 |
| Grayslake Area Public Library District | 2026-09-16 | 0 | 4 |

## Recommended scraper shape for any librarycalendar.com host

1. For each date in the sweep window: `GET
   /events/feed/html?_wrapper_format=lc_calendar_feed&adjust_range=1&current_date=YYYY-MM-DD&ongoing_events=hide`
   with a desktop User-Agent header. Parse `article.event-card` nodes.
2. Dedupe event detail URLs across days (recurring events reuse the same
   `/event/<slug>-<id>` path only when it's literally a single dated
   instance; series each get their own numeric id per occurrence on this
   platform, so caching mainly helps same-day repeats).
3. For each unique event URL, one `GET` to the detail page for age group,
   address, and fee text.
4. Apply the standard DROP/COST/age-scope rules from `intake/SCHEMA.md`.
5. No rate-limit trouble observed at ~0.15s between detail fetches; no 429s
   during this run.

This method should replace the month-grid `--dump-dom` approach for every
librarycalendar.com-platform source on the site, not just these three.
