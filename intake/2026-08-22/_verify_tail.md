# Verify tail — small-count orgs (2026-08-22)

Orgs owned by this pass: Waukegan PL, Deerfield Park District, Round Lake Area PL,
Village of Mundelein, Barrington Area Library, Crabtree Nature Center, Highwood PL,
Grayslake Area PLD, Village of Fox Lake, Deerfield PL, Northbrook Park District.

## Verdicts

| Org | Date | Name | Verdict |
|---|---|---|---|
| Waukegan Public Library | 2026-08-24 | Toddler Storytime - Ages 18 months - 3 years | STILL-LIVE |
| Waukegan Public Library | 2026-08-31 | Toddler Storytime - Ages 18 months - 3 years | REMOVED (event page 404) |
| Deerfield Park District | 2026-08-27 | Summer Sampler Concert | STILL-LIVE (matched via calendar EID, startDate 2026-08-27T18:15) |
| Deerfield Park District | 2026-09-22 | Discovery Learning Center Preschool Open House | REMOVED — not found in day view, month view, or site search; no URL was ever captured |
| Round Lake Area Public Library | 2026-10-12 | Alebrijes | STILL-LIVE |
| Round Lake Area Public Library | 2026-10-16 | Emoji Galaxy Paint Workshop | STILL-LIVE |
| Village of Mundelein | 2026-08-22 | Mundelein Farmers Market | STILL-LIVE |
| Village of Mundelein | 2026-08-29 | Mundelein Farmers Market | STILL-LIVE |
| Barrington Area Library | 2026-08-25 | Teaching Garden Workshop: Rocking Painting | REMOVED — no URL captured, not found on current calendar, month view, or search on either balibrary.org or balibrary.librarycalendar.com |
| Crabtree Nature Center (Forest Preserves of Cook County) | 2026-08-27 | Sunset Photography Meetup | STILL-LIVE |
| Highwood Public Library | 2026-08-29 | iSpy Pouches • Bolsitas Sensoriales | STILL-LIVE |
| Grayslake Area Public Library District | 2026-09-04 | Pokémon Club | STILL-LIVE |
| Village of Fox Lake | 2026-12-03 | Florence Fischer Turkey Luncheon | STILL-LIVE |
| Deerfield Public Library | 2026-12-12 | Celtic Winter Medley | STILL-LIVE |
| Northbrook Park District | 2026-08-23 | Northbrook Community Center Grand Opening Celebration | STILL-LIVE |

**12 STILL-LIVE (recovered to NDJSON), 3 REMOVED.** Normal single-digit churn for this batch — no systemic breakage in the fetch/parse layer for these orgs, with one notable exception below.

## Notes — systemic findings

**Village of Mundelein — genuinely under-scraped, not a broken fetch.** The
source URL (`mundelein.org/calendar.aspx`) loads fine and the 2 Farmers Market
rows in `_GONE_to_verify.md` are both confirmed live at the stated dates. BUT
the page's "Featured Events" sidebar — which the earlier sweep apparently
never parsed — actually lists at least 6 real, current, non-recurring events:
Concert in the Park (Aug 23, Aug 30), Coffee with Mayor Meier and Trustee
Juarez (Sep 5), Mundelein Community Connection - Park on Park (Sep 9), and
more. None of these made it into any sweep. This is a real coverage gap for a
CivicPlus-calendar org — the page defaults to a single-day view
(`day=22&month=8&year=2026`, i.e. "today") plus a separate "Featured Events"
`<div id="featured">` block that the scraper isn't reading. Worth a follow-up
scrape pass targeting `#featured` specifically, or paging through
`Calendar.aspx?month=N&year=2026` for full-month coverage. Not resolved here —
out of scope for a verify-only pass — but flagging since it's likely to
recur on other CivicPlus-based org sites in the corpus.

**Grayslake Area Public Library District (0.0 mi from home)** — the single
row (Pokémon Club, 2026-09-04) checked out clean: live, correct date, correct
URL. No indication of a broader problem with this source; the "missing" row
was simply one event correctly flagged by the stale-check and it turned out
still to be there. No action needed beyond the recovery already appended.

**Deerfield Park District** is also CivicPlus-based (same platform pattern as
Mundelein) and one of its two rows (Discovery Learning Center Preschool Open
House) is genuinely gone — no URL was ever captured for it and it doesn't
appear anywhere on the current calendar or site search. Given the Mundelein
finding, it's plausible some Deerfield events are similarly hidden in a
"featured/upcoming" widget outside the day-view scrape path, but nothing
findable pointed to this specific event still existing — treating as REMOVED
rather than under-scraped.

## Files written
- 10 new `<org-slug>-recovered.ndjson` files in this directory (one Mundelein
  file carries both rows; Round Lake carries both rows).
- This report.
