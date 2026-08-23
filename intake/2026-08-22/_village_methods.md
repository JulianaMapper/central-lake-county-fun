# Village sources — 2026-08-22 unblock sweep, method notes

For correcting SOURCES.md. All fetches done via bash `curl` (network access
confirmed working from the sandbox). Date window used: 2026-08-22 to
2026-12-31, per this task's explicit instruction (overrides SCHEMA.md's
default 08-01–10-31 window).

## 1. Village of Grayslake (`grayslake-village`) — PARTIALLY SOLVED

- `villageofgrayslake.com/calendar.aspx` confirmed still JS-widget-only, no
  markup to scrape — unchanged from prior sweep.
- **CivicEngage iCal feed exists and works**, but only two categories are
  populated at all: brute-forced `catID=0` through `60` against
  `https://www.villageofgrayslake.com/common/modules/iCalendar/iCalendar.aspx?catID=<N>&feed=calendar`.
  Only `catID=14` (holiday closures — Labor Day, Christmas, New Year's, all
  DROP) and `catID=21` (Heritage Center "Search & Share Genealogy" recurring
  program — adult, DROP) return any `VEVENT`s. **There is no Farmers Market
  or Movies Off Center category on this CivicEngage instance** — confirmed
  structurally, not just "looked empty."
- **Movies Off Center**: found on `grayslakevillagecenter.com/usa250-events`
  (Heritage Center's page, already a documented source, §34/§49). The 2026
  season's **final film was Friday Aug 7, 2026** ("Star Wars: A New Hope" —
  page says "It's the final film for this season's Movies Off Center!").
  That's before our window (2026-08-22 start), so **zero qualifying dates
  this sweep, correctly zero — not a fetch failure.**
- **Grayslake Farmers Market**: `grayslakefarmersmarket.com` (Squarespace)
  has no `/calendar` page and no JSON collection endpoint — confirmed via
  `?format=json` returning the plain homepage, and no `/calendar` link in the
  nav. **But the homepage embeds a dated flyer image**
  (`GLFM-2026-fall.jpg`) that states: **Fall Market, Saturdays 10:00 AM –
  2:00 PM, September 26 – December 12, 2026.** That's a real dated schedule,
  not the vague recurring-pattern text the task briefing flagged — captured
  as 12 weekly lines. Location is "Downtown Grayslake" per the site's own
  branding; no more specific address is published, and no per-event URL
  exists (homepage isn't acceptable per SCHEMA, so `url` is `""`).
- **Result: 12 lines** (Farmers Market only). Movies Off Center is genuinely
  out of window, not missing data.
- **SOURCES.md fix**: add the working iCal catID=14/21 pattern (low value —
  both categories are DROP-only); document that Farmers Market dates live in
  a flyer image on the Squarespace homepage, not a calendar page, and must be
  re-checked each season (image filename `GLFM-2026-fall.jpg` will presumably
  become `GLFM-2027-fall.jpg` etc.).

## 2. Village of Lake Villa (`lakevilla-village`) — SOLVED, domain migrated

- **The village's domain changed from `lake-villa.org` to
  `villageoflakevilla.gov`.** The old domain now redirects
  (`www.lake-villa.org/...` → `www.villageoflakevilla.gov/...` — confirmed via
  the `Moved Permanently` response body when hitting the old iCal URL). This
  is the real root cause of the documented 404 — not a broken CivicEngage
  path, a domain change SOURCES.md doesn't know about yet.
- The CivicEngage iCal pattern from the task briefing works perfectly on the
  new domain: `https://www.villageoflakevilla.gov/common/modules/iCalendar/iCalendar.aspx?catID=<CID>&feed=calendar`.
  Tried all 7 given CIDs:
  | CID | VEVENTs | Content |
  |---|---|---|
  | 28 | 0 | (empty) |
  | 14 | 6 | Holiday closures + St. Patrick's Day Parade (out of window) |
  | 23 | 10 | PC/ZBA meetings — all DROP |
  | 26 | 5 | **Special events** — Holiday Parade & Tree Lighting, Halloween Trick-or-Treat Hours, Celebration of Fall (+2 out-of-window items) |
  | 22 | 13 | Village Board / Committee of the Whole meetings — all DROP |
  | 25 | 3 | Police Commission meetings — DROP |
  | 24 | 4 | Police Pension meetings — DROP |
- **CID 26 is the payload** — it's the village's actual special-events
  category. **Result: 3 lines** (Celebration of Fall Sept 12, Halloween
  Trick-or-Treat Hours Oct 31, Holiday Parade & Tree Lighting Nov 28).
- **SOURCES.md fix**: replace every `lake-villa.org` reference with
  `villageoflakevilla.gov`, and record CID 26 as "Special Events" (the other
  6 CIDs are meetings/closures, not worth re-polling every sweep).

## 3. Round Lake Beach (`rlb-village`) — SOLVED (retry, 2026-08-22 second pass)

**CRACKED IT. The Revize AJAX events endpoint (generalizes to every Revize
municipal site in the county):**

```
GET https://<domain>/_assets_/plugins/revizeCalendar/calendar_data_handler.php
    ?webspace=<webspace>
    &relative_revize_url=<protocolRelativeRevizeBaseUrl>
    &protocol=https:
```

For Round Lake Beach specifically:
```
https://www.roundlakebeachil.gov/_assets_/plugins/revizeCalendar/calendar_data_handler.php?webspace=roundlakebeach&relative_revize_url=//cms2.revize.com&protocol=https:
```

**How it was found:** WebFetch'd `cdn1-global.revize.com/plugins/revize_calendar/index.js`
directly (the prior attempt only pulled `core/main.min.js`, the generic vendor
FullCalendar bundle — the wiring is in `index.js`, a sibling file, not the core
lib). It contains:
```javascript
$.get('./_assets_/plugins/revizeCalendar/calendar_data_handler.php?webspace=' +
RZ.webspace + '&relative_revize_url=' + RZ.protocolRelativeRevizeBaseUrl +
'&protocol=' + window.location.protocol, ...)
```
The two `RZ.*` values are inline vars set on the page itself — pulled from
`curl`ing `calendar.php` raw and grepping for `protocolRelativeRevizeBaseUrl`
(`='//cms2.revize.com'`) and `RZ.revizeserverurl` (`.../revize/roundlakebeach`,
giving `webspace=roundlakebeach`). A first curl attempt with `webspace` set but
`relative_revize_url` blank returned the plain-text error `"Calendar handler
expected non empty values. Missing value for relative url"` — that error message
is what confirmed the param names before the working call.

**Response:** a flat JSON array, no auth, plain `curl` works — 202 events total,
spanning **2023-05-31 to 2026-10-30** (its whole cached history, not a
rolling window — don't assume it caps at "today + N months"). Each record:
`title`, `primary_calendar_name`, `calendar_displays` (list of numeric
calendar-ids — matches the `ACTIVE_CALENDAR_IDS` briefing note: `1`/`20`=Meetings,
`2`=Events, `3`=Village Hall Closings, `4`/`22`=Civic Center, `12`=Community
Events, `25`=Adjudication Hearings), `start`/`end` (ISO, local time — a "1pm-2pm"
printed event stores as `18:00`-`20:00`, i.e. UTC or a fixed CDT offset baked in;
treat `desc`'s printed times as ground truth over raw `start`/`end` clock digits),
`desc` (URL-decode it — it's `%XX`-escaped HTML with the real times/details),
`location`, `url` (empty on every record checked), `color`.

**Filtered for window 2026-08-22 → 2026-12-31:** only 3 events fall in range at
all (the calendar is sparsely populated past October) — two `Forever Young RLB`
lunches (adults 55+, **DROP** per age scope) and one qualifying event:
**Family Fun Friday - Day of the Dead Celebration**, 2026-10-30, 1:00PM-2:00PM,
free, Civic Center (2007 Civic Center Way). That's the sole line written to
`rlb-village.ndjson`.

**Not pursued further / not needed:** the `civic_center/upcoming_events.php`
second page — checked, it's static/manually-edited marketing copy (Reza
Illusionist, Summertime LIVE, BeachFest) with no parseable in-window dates; the
handler above is authoritative and supersedes it. Claude-in-Chrome was not
needed this pass — no browser contention issue to report.

**Generalization note for the county:** any Revize-CMS village site (this
runbook has flagged several) should be checked for the same
`_assets_/plugins/revizeCalendar/calendar_data_handler.php` path with its own
`webspace=` value — first curl `calendar.php` raw HTML and grep
`protocolRelativeRevizeBaseUrl` + `RZ.revizeserverurl` to get the two params.

---

## 3-OLD. Round Lake Beach (`rlb-village`) — NOT SOLVED, 0 events (superseded above)

- Confirmed the runbook's prior findings: `calendar.php?view=list&cat=Community+Events`
  is Revize CMS, hydrates via JS, no events in the raw HTML shell except an
  orphan `fc-event-dot` class (FullCalendar, as the briefing said).
- **Traced the FullCalendar wiring in the actual plugin JS** (not done in the
  prior attempt): pulled `/revize/plugins/revize_calendar/index.js`
  (redirects to `cdn1-global.revize.com/plugins/revize_calendar/core/main.min.js`,
  which is generic vendor FullCalendar code — no site-specific endpoint
  there). `index.js` itself references exactly one non-vendor data path:
  `./_assets_/plugins/revizeCalendar/cache/calendarimport.ics` — but that
  path **404s** on this site (confirmed with and without a calendar-id
  suffix). That code path exists in the plugin for sites that import an
  *external* Google/ICS calendar; Round Lake Beach's calendar is native, so
  it isn't populated.
- Guessed several plausible REST paths used by other Revize deployments
  (`getEvents.jsp`, `events.json`, `api/events`, `core/api.jsp`) — all
  redirect (302) to the site's catch-all page, i.e. don't exist.
- Tried the alternate page named in the brief,
  `/round_lake_beach_civic_center/upcoming_events.php` — this is a **static,
  manually-edited page**, not a calendar feed. It currently lists (no
  parseable dates for most): Reza Illusionist (no date given, Eventbrite
  link), Summertime LIVE "every other Thursday starting May 28 – Aug 6, 2026"
  (out of window), Family Fun Friday "throughout the summer" (no dates),
  Forever Young 55+ lunches (adult, DROP), and **BeachFest Independence Day,
  Friday & Saturday July 3–4, 2026** (out of window). Nothing on this page
  has a real date inside 2026-08-22–2026-12-31 — it reads as stale/pre-fall
  content that hasn't been refreshed for the season yet.
- **Escalated to Claude-in-Chrome per the runbook's escape hatch, but could
  not complete it this session**: the Chrome MCP tab group was actively being
  driven by a second, concurrent agent session the whole time (tabs kept
  jumping to `mccdistrict.org` — McHenry County Conservation District — under
  navigations I did not issue, and freshly-created tabs errored or vanished
  within one or two calls). Every attempt to get a stable tab of my own to
  poll `read_network_requests` or run `javascript_tool` against the live
  page failed on tab-ownership grounds, not a site block. **This needs a
  retry in a session that isn't sharing the browser**, watching Network
  during a real page load, to find the XHR the JS makes for its own events
  (which almost certainly exists — Revize wouldn't ship a JS calendar just to
  populate it with a 404 empty ICS import).
- **Result: 0 lines, file written empty as SCHEMA.md instructs.**
- **SOURCES.md fix**: note the domain migration risk is NOT the issue here
  (unlike Lake Villa) — the site is at the right URL, it's genuinely a
  client-hydrated calendar with an undiscovered backend. Flag for a
  Claude-in-Chrome-only retry, uncontended.

## 4. Village of Mundelein (`mundelein-village`) — SOLVED

- Brute-forced CivicEngage iCal `catID=0`–`40` against
  `https://www.mundelein.org/common/modules/iCalendar/iCalendar.aspx?catID=<N>&feed=calendar`,
  same method as Lake Villa. Three categories return events:
  | CID | VEVENTs | Content |
  |---|---|---|
  | 14 | 69 | **Everything** — meetings, closures, AND all real events (union of 24+25) |
  | 24 | 15 | Subset — Coffee w/ Mayor, Blood Drive, Community Connection events |
  | 25 | 14 | Same subset minus one item |
- CID 14 is the full feed; CID 24/25 look like narrower category views of
  the same underlying events (not extra content). Filtered CID 14 down to
  family-appropriate, in-window events, dropping: all Board of Trustees /
  Planning & Zoning / Historical / Arts / Fire Truck Committee / Economic
  Development / Pension board meetings, "Coffee with the Mayor" (civic,
  adult), and the Fire Dept blood drive.
- Kept: 2 remaining **Concerts in the Park** (Aug 23, Aug 30 — season runs
  through August, these two Sundays fall inside the window), 4 **Farmers
  Market** dates (Aug 29–Sep 19), **Park on Park** (Sep 9), 2-day
  **Mundelein Arts Festival** (Sep 19–20), **Winter Tree-Lighting Festival**
  (Dec 5), and 3 **Santa's Cottage** dates (Dec 5/12/19).
- This is a real fix, not just "featured events was already all of it" — the
  prior sweep's 2-event yield came from reading only the static "Featured
  Events" teaser on `/calendar.aspx`; the iCal feed underneath it carries the
  full season.
- **Result: 13 lines.**
- **SOURCES.md fix**: replace the "mostly empty calendar, Featured Events
  only" note with the iCal catID=14 pattern; note CID 24/25 are redundant
  subsets, not additional content.

## Summary

| Source | Lines written | Status |
|---|---|---|
| grayslake-village | 12 | Farmers Market solved via flyer image; Movies Off Center correctly 0 (season ended before window); village CivicEngage calendar confirmed structurally empty of anything else |
| lakevilla-village | 3 | Solved — domain migrated to villageoflakevilla.gov, CID 26 is the payload |
| rlb-village | 0 | Unsolved — needs an uncontended Claude-in-Chrome session to catch the live XHR |
| mundelein-village | 13 | Solved — iCal catID=14 carries the full season, not just Featured Events |

---

## ⚠️ CORRECTION (verified by the orchestrator, 2026-08-22) — the Revize endpoint does NOT generalize

The RLB writeup above recommends reusing
`/_assets_/plugins/revizeCalendar/calendar_data_handler.php?webspace=<site>&...`
on other Revize municipal sites. **Do not do that without a sanity check. It
silently serves the WRONG SITE'S DATA.**

Tested against two hosts:

```
https://www.roundlakebeachil.gov/_assets_/plugins/revizeCalendar/calendar_data_handler.php?webspace=roundlakebeach&...
https://www.mccdistrict.org/_assets_/plugins/revizeCalendar/calendar_data_handler.php?webspace=mccdistrict&...
```

Both returned **byte-identical** responses — same 205,719 bytes, same 202 events,
same 2023-05-31 → 2026-10-30 range, identical MD5. And the payload is **Round Lake
Beach's**: its `primary_calendar_name` values are `Civic Center` (91),
`Meetings` (64), `Community Events` (22), `Adjudication Hearings` (17),
`Village Hall Closings` (4) — RLB's own calendar names, served from the McHenry
County Conservation District's domain.

So the `webspace` parameter is ignored on this path. It is a shared/CDN-cached
asset route, not a per-tenant API.

**Why this matters more than a wasted request:** MCCD's real events came from
`window.jsonEvents` and total 43. If a future sweep had "generalized" this
endpoint to MCCD, it would have injected 202 Round Lake Beach rows — including
Adjudication Hearings and Village Hall closures — under the org name
`McHenry County Conservation District`. Wrong events, wrong town, wrong org, and
nothing downstream would have caught it: the rows are well-formed, the dates are
valid, and `qa_check.py` has no way to know a Round Lake Beach hearing isn't a
McHenry nature program.

**The rule:** the endpoint is correct for Round Lake Beach only, because that is
whose data it returns. For any other Revize site, read the `RZ.*` inline vars out
of *that site's own* `calendar.php`, and then **verify the payload belongs to that
site** — check `primary_calendar_name` values and one known event title against
the site's visible calendar — before writing a single row.

**General lesson worth keeping:** "this method should generalize" is a hypothesis,
not a finding. Two hosts returning the same byte count is the tell. Diff the
payloads before promoting a method to the registry.
