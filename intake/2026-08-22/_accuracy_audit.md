# Accuracy Audit — 2026-08-22 Intake Batch

Stratified random sample of 20 rows (seeded, reproducible), pulled from 5,036
total rows across the day's `*.ndjson` files. Each row's `url` was fetched
live and compared field-by-field against the recorded data. Where a fetch
failed (403 / JS-rendered), the row is marked UNVERIFIABLE rather than
guessed.

## Per-row results

| # | Source file | Date | Name | Verdict | What differs |
|---|---|---|---|---|---|
| 1 | mccd-calendar.ndjson | 2026-11-24 | Full Moon Hike and Campfire | **UNVERIFIABLE** | URL is a JS-driven calendar shell; fetch returned only nav/filter chrome, no event detail. Cannot confirm or refute anything. |
| 2 | fremont-libnet.ndjson | 2026-11-15 | Teens' Personal Reading Challenge | **WRONG** | Recorded `cost: "$100"`. Page: entry is free; "$100" is a **prize** ("participants compete for a $100 gift card"), not a fee. This is the exact failure mode the audit is watching for, inverted — a free event reads as a $100 event. Age recorded "Teen" vs. page's more precise "Grades 6-12" (minor). |
| 3 | crystal-lake-park-district.ndjson | 2026-11-06 | Elf Jr. The Musical | MINOR | Cost "$8" confirmed correct. But this is a multi-performance run — page also lists Sat Nov 7, 3PM and 7PM — only the Fri 7PM showing is captured. |
| 4 | ela-refetch.ndjson | 2026-09-15 | Family Rock (ages 1-5) | ACCURATE | Name/date/time/location/org all match. Blank cost matches page (no fee stated). |
| 5 | barrington-dayfeed.ndjson | 2026-08-27 | Art Play | MINOR | Matches for the 8/27 date, but page shows this is a weekly series (8/6, 8/20, 8/27, 9/3, 9/10, 9/17, 9/24) — only one occurrence captured. |
| 6 | caryarea-dayfeed.ndjson | 2026-10-17 | FOCAL Book Sale | MINOR | Location recorded as just "Cary Area Public Library" vs. page's full street address — truncated, not wrong. Cost blank is defensible (no price on page) but book sales often have unlisted per-item pricing. |
| 7 | vernonarea-dayfeed.ndjson | 2026-09-15 | Wiggling Ones (10:30am, Drop-in) | **WRONG** | Recorded `age: "Early Childhood"`. Page states a hard band: **"Ages 12-24 months."** A vague bucket masking a narrow eligibility window is a real error — a parent of a 4-year-old could show up and be turned away. Cost also should read "Free" (page confirms free) rather than blank. |
| 8 | foxlake-dayfeed.ndjson | 2026-10-16 | You're My Boo, Baby (Rave)! | MINOR | Name/date/time/location/age all confirmed exactly. Cost blank is consistent with the page (no fee stated), but page adds "drop-offs will not be permitted" — a logistics detail we don't capture, not a factual error. |
| 9 | grayslake-dayfeed.ndjson | 2026-12-03 | Explore Robotics in Lake County | MINOR | Content (date/time/age/location) all confirmed. URL slug ("build-drive-robots...") doesn't match displayed title, but the page itself is the correct, specific event — not a wrong-event link. |
| 10 | highlandpark-refetch.ndjson | 2026-09-26 | Imán de Mini Pan Dulce | MINOR | Accent dropped in recorded name ("Iman" vs "Imán"). Date/time/age/location match. Cost blank; page implies free ("all materials included") but doesn't say "Free" outright. |
| 11 | warrennewport-refetch.ndjson | 2026-10-12 | La Bella Catrina | MINOR | Date/time/name/location/age all match. Cost blank; page states no fee either way — ambiguous, not wrong. |
| 12 | cook-refetch.ndjson | 2026-10-13 | High School: Macramé Ghost | MINOR | Accent dropped ("Macrame" vs "Macramé"). Date/time/location/age match. Cost blank; page says "materials provided" but no price stated. |
| 13 | visitlakecounty-cvb.ndjson | 2026-08-28 | Elote Fest | **WRONG** | Recorded as a single day (2026-08-28) with `time: "TBA"`. Page: this is a **three-day festival, Fri Aug 28 – Sun Aug 30, 5-11 PM**. Cost "Free" is correct (page confirms "Free Admission"), and org attribution (venue/Village, not the CVB) is fine — but date/time materially understate the event. |
| 14 | visitlakecounty-cvb.ndjson | 2026-09-19 | Deerfield Harvest Fest | MINOR | Cost "Free" confirmed correct, date confirmed correct, org attribution correct (Village of Deerfield, co-hosted with Lions Club/Park District — not attributed to the CVB). Recorded `time: "All Day"` is misleading; page gives a specific window, **5-10:45 PM** (evening festival, not an all-day event). |
| 15 | lcfpd.ndjson | 2026-11-07 | Caminata en Espanol | **UNVERIFIABLE** | URL returned HTTP 403 on repeated attempts — could not verify any field. Consistent with lcfpd.org being a JS SPA that resists non-browser fetch. |
| 16 | lcfpd.ndjson | 2026-09-26 | Family Drop-In Nocturnal Animals | **UNVERIFIABLE** | Same as above — HTTP 403, no content retrievable. |
| 17 | grayslake-librarycalendar.ndjson | 2026-08-22 | Pop Up Exhibit: Votes For Women | MINOR | Page confirms this is a multi-day exhibit (Aug 17-31); the recorded date (8/22) is a legitimate day within that range, not an error, but pinning a multi-day exhibit to one day misrepresents it as a discrete single-occurrence event. Cost "Free" unverified — page doesn't state a price either way. |
| 18 | antioch-library.ndjson | 2026-09-23 | Drop-In Process Art | MINOR | Page's actual title is "Drop-In Process Art **In-Person**" — "In-Person" dropped from our record (minor truncation). Age recorded "Children's" vs. page's more specific "Children (Birth - 5th grade)" — vaguer, not wrong. Cost "Free" unverified (page doesn't state a price). |
| 19 | waukegan-libnet.ndjson | 2026-11-03 | Maker Space Open Hours | MINOR — content-fit flag | All fields (date/time/location/age "Adults & Seniors") confirmed accurate. But this is an adults-and-seniors program with zero family/child framing anywhere on the page — it likely doesn't belong on a parents'/kids' events site at all. Not a data error; a scope/inclusion error. |
| 20 | warrennewport-refetch.ndjson | 2026-11-18 | Dungeons and Dragons: Grades 6-8 | ACCURATE | Name/date/time/age/location all confirmed exactly. Cost blank matches page's "Cost: Not listed" — an honest blank, not a wrongly-claimed free. |

## Error rate

**2/20 ACCURATE, 12/20 MINOR, 3/20 WRONG, 3/20 UNVERIFIABLE**

- Hard errors (WRONG): 15%
- Unverifiable (no confidence either way): 15%
- Everything else has at least one small, non-misleading discrepancy

## Per-field reliability

| Field | Verdict | Notes |
|---|---|---|
| **url** | **Reliable** | 20/20 sampled URLs resolved to the correct, specific event page — no homepage redirects, no wrong-event links, even on the CVB and lcfpd rows. This is the strongest result in the audit. |
| **org** | Reliable | All checked rows (including both CVB rows) attributed to the correct real-world host, not to the aggregator. No errors found. |
| **location** | Reliable, sometimes truncated | Content always plausible/correct; occasionally missing the full street address the page gives (Cary Area Library). Never wrong, just less specific than available. |
| **name** | Mostly reliable | One systematic pattern: accented characters get dropped ("Iman" vs "Imán," "Macrame" vs "Macramé") — both in `*-refetch.ndjson` files. Cosmetic, not misleading, but consistent enough to flag. One title also dropped a qualifier ("In-Person"). |
| **date** | Mostly reliable, one real miss | 19/20 correct. The one failure (Elote Fest) undercounted a 3-day festival as 1 day — a CVB-sourced, multi-day-event problem. |
| **time** | **Weakest reliable field** | Two of two CVB rows had time problems (Elote Fest "TBA" when the page states 5-11PM; Deerfield Harvest Fest "All Day" when the page states 5-10:45PM). Both undersell evening events as either unknown or all-day. Library-source rows were time-accurate in every case sampled. |
| **age** | Mixed — worth distrust on vague buckets | One real error: "Early Childhood" masking a hard "12-24 months" eligibility window (Vernon Area) — this can cause a real turned-away-at-the-door outcome. Several other rows recorded a vaguer bucket than the page's precise language, always in the direction of "less specific," never contradictory. |
| **cost** ⚠️ | **Least trustworthy field — needs attention, but not in the direction you'd fear** | No sampled row falsely labeled a genuinely paid event as "Free." The one hard cost error (Fremont, "$100") is the opposite failure — a free program mislabeled as costing money, because a prize amount was captured as a fee. Separately, roughly half the sampled rows have a **blank** cost where the source page is ambiguous or (in at least 2 cases — Wiggling Ones, dropped-off caveat aside) implicitly free but never says the word "Free" — meaning blank cost is not reliably "confirmed free," it is more often "unconfirmed." Both sampled CVB "Free" rows were independently confirmed correct on their own pages. **Bottom line: no found instance of a truly paid event labeled Free or blank — the risk realized in this sample ran the safer direction — but the Fremont miss shows the capture logic can misread prize/incentive language as a fee, and blank cost cannot be read as a confirmed "free."** |

## Systematic errors identified

1. **`lcfpd.ndjson` (32 rows) — unverifiable as a class.** Both sampled rows returned HTTP 403 to a non-browser fetch, consistent with lcfpd.org being a JS SPA. This audit could not confirm or refute a single lcfpd row. Recommend a headless-browser (claude-in-chrome) spot-check pass on this file specifically before trusting it, since 2/2 came back with zero signal either way.
2. **`mccd-calendar.ndjson` — same failure mode**, at least for the one detail-page URL sampled (JS calendar, no static event content served).
3. **`visitlakecounty-cvb.ndjson` — time/date under-capture on multi-day or evening events, 2/2 sampled.** Elote Fest (3-day festival compressed to 1 day + "TBA") and Deerfield Harvest Fest ("All Day" for what's actually a 5-10:45PM evening event) both understated the real schedule. Org attribution was correct in both cases, so this isn't a host-misattribution problem — it's specifically date/time capture on multi-day festival listings. Small file (44 rows) — worth a manual pass on any other multi-day/festival-named entries in this file specifically.
4. **`*-refetch.ndjson` files — diacritics dropped from titles** (Highland Park, Cook). Cosmetic only, but consistent enough across the "new method, unproven" refetch files to flag for a normalization fix.
5. **Recurring/multi-session events captured as a single row** (Elf Jr. the Musical, Art Play, Pop Up Exhibit) — not wrong for the specific date shown, but incomplete; readers relying on the site for "when is this happening" won't see the other dates.
6. **Fremont-libnet prize-vs-fee confusion** — worth a spot check of other fremont-libnet rows containing gift-card/prize/raffle language, since the same capture pattern that turned a prize into a "$100 cost" here could recur elsewhere in that file.

## Recommendation: is this batch safe to publish?

**Conditionally yes — with two targeted fixes and one file held back for re-verification, not a full-batch hold.**

- **Fix before publish:** Fremont-libnet "Teens' Personal Reading Challenge" cost field ($100 → blank/Free), and the Elote Fest date/time (single day/TBA → Aug 28-30, 5-11PM). Both are confirmed, specific, low-effort corrections.
- **Hold and re-verify:** `lcfpd.ndjson` (32 rows) and, if feasible, the single `mccd-calendar.ndjson` detail-page pattern — both came back completely unverifiable via fetch in this audit, which means this audit has zero evidence either way for those sources, not a clean bill of health. A headless-browser pass on a small sample from each would resolve this before publish.
- **Spot-check, don't block:** `visitlakecounty-cvb.ndjson` for other multi-day/evening festivals with similarly vague times ("TBA," "All Day") — 44 rows, worth a manual skim given the 2/2 hit rate found here.
- **Everything else in the sample — the bulk of it: library `*-libnet`, `*-librarycalendar`, and `*-dayfeed` sources — held up well.** No WRONG verdicts among those 14 rows, no false "Free" labels on paid events (the audit's top concern), and no wrong-event URLs anywhere in the sample. The core capture pipeline for library calendar sources appears sound; the risk is concentrated in newer/harder-to-scrape sources (lcfpd, mccd JS calendars) and in the CVB aggregator's handling of multi-day date ranges — not in the batch broadly.
