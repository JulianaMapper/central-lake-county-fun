# visitlakecounty.org (Lake County CVB) — sweep method, 2026-08-22 → 2026-12-31

## Working request — the actual breakthrough

The plain `/events` page and its `?&print` variant are both **dead ends** — they
only render a rolling "next ~30-40 days" widget (37-40 events, whatever falls in a
default 1-month window), no matter how many times you hit them or in what order.

The real feed is a **hidden POST form** on `/events` itself:

```html
<form action="/events#eventlist32" name="MoreEvents" method="post">
  <input type="Hidden" name="newemaxrws" value="64">
  <input type="Hidden" name="StartDate" value="08/22/2026">
  <input type="Hidden" name="EndDate" value="{ts '2026-09-22 00:00:00'}">
  <input type="submit" value="Load More Events">
</form>
```

`POST /events` with `StartDate`, `EndDate` (both `MM/DD/YYYY`), and `newemaxrws`
(the result-window size — the page's own default is 64) returns the full event
list for that range in one response, unpaginated. Working call used for this sweep:

```bash
curl -s -A "<normal browser UA>" -X POST \
  -d "StartDate=08/22/2026&EndDate=12/31/2026&newemaxrws=500" \
  "https://www.visitlakecounty.org/events" -o events_postmax.html
```

`newemaxrws=500` (also tried 5000, same result) returned **275 unique event
detail links** — that's the true ceiling for this date range, not a page-size
cap; raising the window further changed nothing. Every event link matches
`href="/<slug>-YYYY-MM-DD"` and is a real detail page.

## Detail pages — structured data confirmed at scale

All 275 detail pages were fetched (`xargs -P 8` + plain curl, ~30s total). 274 of
275 carried the documented `<script type="application/ld+json">` `@type: Event`
block (`name`, `startDate`/`endDate` as `"Weekday, Month D, YYYY"` strings,
`location.address` with `postalCode`, `description` as an HTML-escaped blob).
One page (`Sails-Unfurled…-2020-01-13`, a long-past/orphaned listing) had none.

**Cost is NOT reliably in the JSON-LD** (`offers`/`isAccessibleForFree` were null
on every page checked, confirming the brief's warning). The real signal is a
plain-text **"Additional Information"** block in the rendered page body,
immediately followed by one of two fixed tags before "For more information":
`Free Admission` or `Admission Cost` (sometimes with a dollar figure attached,
e.g. `Admission Cost Adult Admission: $48.00`). This tag was extracted for all
217 events that fell inside the date window and used as the primary free/paid
gate — far more reliable than guessing from description text. Example:
`Additional Information Free Admission For more information, call 847...`

One event (Honey Harvest Festival, Highland Park) carried the `Free Admission`
tag but its own description said "children must be accompanied by a **paid**
registered adult" — a direct contradiction. Treated as paid and dropped; the
site's own tag isn't perfectly trustworthy and the body text should win when
they conflict.

## Category pages — low yield, not worth scraping again

Checked `/Family-Fun-Guide`, `/il250`, `/flavor-festival` and their `?&print`
variants per the brief. All three are static guide/FAQ content (a JS
accordion of "family fun" tips, an Illinois 250 landing page, a Flavor
Festival explainer) with **zero dated event links** — none of the
`/<slug>-YYYY-MM-DD` pattern anywhere in their HTML. They don't add coverage
beyond `/events`; skip them in future sweeps unless the CVB restructures the
site.

## Funnel: 275 → 217 → 58 → 33 kept lines (44 ndjson lines after expanding multi-day/recurring)

1. **275** unique event detail links returned by the POST for 08/22–12/31/2026.
2. **217** had a `startDate` that actually falls inside the sweep window (many
   returned links carry stale years like `2025-07-09` or `2020-01-13` in the
   slug/original posting — the true `startDate` in the JSON-LD is what was
   trusted, not the slug's year).
3. **58** of those 217 carried the `Free Admission` tag.
4. Applying this project's DROP rules to those 58 (fundraisers/galas, 21+/bar/
   beer/wine events, business & tourism promotions, adult-only concerts and
   nightlife, vendor/craft markets with no kid focus, one cost contradiction)
   left **33 distinct events**, which expand to **44 ndjson lines** once
   multi-day festivals (Elote Fest, Harbor Days, Irish Days, Mundelein Fine
   Arts Festival) and the recurring Grayslake Fall Farmers Market (12 Saturdays,
   Sept 26–Dec 12) are written one line per date.

Notable drops and why, since several looked close: **Cruisin' on Center
Grayslake Car Show** is an explicit 501c3 fundraiser (scholarships, food
pantries) despite free admission — dropped under the fundraiser rule, not the
cost rule. **Ray Bradbury Birthday Bash** is a free evening electronic-dance
multimedia show, not family-oriented despite being free. **ArtWauk /
HolidayWauk / ZombieWauk** (recurring monthly) are explicitly framed as
"grab dinner" gallery-and-bar crawls — adult. **First Friday on MainStreet
Libertyville** (x4 dates) is a downtown shopping/wine-tasting promotion, not a
dated public event for kids. **Vintage Holidays in Long Grove** spans
Nov 20–Dec 24 with no fixed single-day program described — a season-long
shopping promotion, not a dated event — dropped rather than invented a date.
**Honey Harvest Festival** — see cost contradiction above.

## Strategic finding — what this source surfaced that direct scraping missed

**Every one of the 33 kept events is new to the calendar** — a text search of
`SOURCES.md` for each event name (Pumpkin Jubilee, Venetian Night, Festival of
Lights, Halloween Howl, Elote Fest, Harbor Days, Irish Days, Deerfield Harvest
Fest, Wauconda Big Bang, Mini Comic Con, Nature Discovery Day, Salute in Song,
Bangin' BBQ, Mundelein Fine Arts Festival, Trick or Treat) returned zero hits.
None of these are duplicates of anything already documented as a source or
event in this project.

This confirms the brief's hypothesis directly: **the CVB recovered exactly the
class of event that defeats direct municipal scraping** —
- **Village of Fox Lake**: 6 of the kept events (Fall Festival, Halloween Howl,
  Pumpkin Jubilee, Santa's Workshop/Kris Kringle Market, Venetian Night,
  Festival of Lights Parade) came through the CVB. `CLAUDE.md` §36 already
  documents Fox Lake's own `/121/Events` page as a *partial* curated source —
  the CVB caught several the village's own page evidently doesn't carry (or
  wasn't re-checked for this cycle).
- **Village of Deerfield**, **City of Highland Park**, **Village of
  Winthrop Harbor**, **Village of Lincolnshire**, **Village of Wauconda**
  (the fireworks show, distinct from Wauconda Park District's own calendar),
  and **Historic Downtown Long Grove**'s Halloween/holiday programming (Trick
  or Treat, Pet Costume Parade) have **no dedicated source entry in
  `SOURCES.md` at all** — this is the structural fix the brief predicted: a
  commercial aggregator surfacing exactly the town-run festivals that have no
  clean CivicEngage/Tribe/libnet feed of their own.
- **Vernon Area Public Library's Mini Comic Con** is a one-off library special
  event that a routine libnet.info calendar scrape (source #19 in `CLAUDE.md`)
  would likely have caught anyway if it ran in-window during a normal sweep —
  but it's confirmation the CVB also duplicates library-hosted specials, which
  is fine (dedup handles it) and useful as a cross-check.

## Recommendation for `SOURCES.md`

**Add `visitlakecounty.org` as a standing source**, tagged with the POST
method above (not the plain `/events` GET, which badly undercounts). Given the
33-of-217 hit rate (~15% of in-range events pass this project's filters) and
zero overlap with existing sources on this sweep, it's worth a full re-run each
season alongside the library/park-district sweep, using the same POST
technique with the season's date range.

## Counts

- 275 unique event URLs returned by the site for 08/22–12/31/2026
- 217 fell inside the requested window
- 58 tagged "Free Admission"
- 33 distinct events kept after DROP-rule triage
- **44 lines written to `visitlakecounty-cvb.ndjson`** (33 events, expanded for
  multi-day festivals and the recurring farmers market), including the
  pre-existing balloon-glow line that was preserved unchanged.
