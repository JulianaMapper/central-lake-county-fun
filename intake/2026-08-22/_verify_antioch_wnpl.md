# Verify: Antioch Public Library District (11) + Warren-Newport Public Library (9) — 2026-08-22

## Antioch Public Library District

| Date (on site) | Name | Verdict | Notes |
|---|---|---|---|
| 2026-09-04 | Nintendo Switch Play (Drop-In) | REMOVED | event/17111569 → HTTP 400 "Event not found." |
| 2026-09-08 | Family Movie Night | REMOVED | event/17153603 → HTTP 400 "Event not found." |
| 2026-09-10 | Special Needs Storytime | REMOVED | event/17253027 → HTTP 400 "Event not found." |
| 2026-09-10 | Cookies and Crafts | RESCHEDULED → 2026-09-17 | event/17093045 → HTTP 200, page's own Date field now Sept 17 |
| 2026-09-11 | Box Fun | RESCHEDULED → 2026-09-25 | event/17195146 → HTTP 200, Date field Sept 25 |
| 2026-09-12 | All Ages LEGO Club | REMOVED | event/16508144 → HTTP 400 "Event not found." |
| 2026-09-17 | Little Chefs | RESCHEDULED → 2026-09-24 | event/17093168 → HTTP 200, Date field Sept 24 |
| 2026-09-18 | Nintendo Switch Play (Drop-In) | RESCHEDULED → 2026-09-25 | event/17111570 → HTTP 200, Date field Sept 25 |
| 2026-10-22 | Little Chefs | RESCHEDULED → 2026-10-29 | event/17093169 → HTTP 200, Date field Oct 29 |
| 2026-11-05 | Open Workshop | STILL-LIVE | event/17098478 → HTTP 200, Date field confirms Nov 5, 2026 — scraper miss |
| 2026-11-05 | Minecraft Mania | STILL-LIVE | event/16902602 → HTTP 200, Date field confirms Nov 5, 2026 — scraper miss |

### ROOT CAUSE — Antioch

Two distinct, unrelated causes, cleanly separated by date:

1. **5 events genuinely rescheduled** (Cookies and Crafts, Box Fun, Little Chefs ×2, Nintendo Switch Play) — all originally in the Sept 10–18 window, all now sitting exactly **one week later** on the same event ID. This is a real source-side change (the library appears to have shifted a block of recurring weekly programs by a week), not a scraper bug — LibCal serves the *current* scheduled occurrence under the same event ID rather than the historical one we captured. No action needed on the scraper; these are legitimately different dates now and were correctly flagged as "gone" relative to the old date.
2. **3 events genuinely removed** (Special Needs Storytime, Family Movie Night, an earlier Nintendo Switch Play instance, All Ages LEGO Club) — return HTTP 400 "Event not found," i.e., deleted from LibCal, not a fetch/parse problem.
3. **2 events (Open Workshop, Minecraft Mania) are a real scraper gap**, and it lines up exactly with the flagged suspicion: **both sit at 2026-11-05, the known point where this sweep's iCal feed hit its 500-event cap** (iCal only reached ~Nov 5) and the JSON tail-fetch was supposed to pick up from there. These two fell in the seam between the two methods and were dropped by the stitch. **Fix: extend/verify the JSON tail-fetch start boundary is inclusive of the iCal feed's actual last-captured date, not an assumed cutoff** — confirm no off-by-one/date-boundary gap at the stitch point.

## Warren-Newport Public Library

| Date (on site) | Name | Verdict | Notes |
|---|---|---|---|
| 2026-08-25 | Project of the Week - Post-it-Notes Journal | STILL-LIVE | event/16119965 → HTTP 200, JSON-LD startDate 2026-08-25T10:00 matches exactly |
| 2026-08-26 | Project of the Week - Post-it-Notes Journal | STILL-LIVE | event/16119966 → startDate 2026-08-26T10:00 matches |
| 2026-08-26 | Dungeons and Dragons: Adults | STILL-LIVE | event/16547228 → startDate 2026-08-26T18:00 matches; subtitle "College and up" — adult, non-maker, out of site scope (DROP rule), not restored to NDJSON |
| 2026-09-08 | K-pop Club | STILL-LIVE | event/16474687 → startDate 2026-09-08T16:00 matches; teen/tween club — IN SCOPE since 2026-08-04. Stays live; no action |
| 2026-09-09 | Dungeons and Dragons: Grades 9-12 | STILL-LIVE | event/16959323 → startDate 2026-09-09T16:00 matches; teen program — IN SCOPE since 2026-08-04 (through high school). Stays live; no action |
| 2026-09-16 | Lotería Night | STILL-LIVE | event/16935478 → startDate 2026-09-16T18:30 matches; family game night — restored to NDJSON |
| 2026-09-21 | Café Spanglish | STILL-LIVE | event/16480312 → startDate 2026-09-21T18:30 matches; adult conversation group, non-maker (DROP rule), not restored |
| 2026-09-28 | Superhero Trivia Night | STILL-LIVE | event/16887589 → startDate 2026-09-28T18:00 matches; family trivia — restored to NDJSON |
| 2026-10-26 | Murder Mystery Night! | STILL-LIVE | event/16913885 → startDate 2026-10-26T17:30 matches; likely adult program, not restored pending age confirmation |

**All 9 rows are STILL-LIVE — zero real churn at Warren-Newport.** Every event's own JSON-LD `startDate` matches the date already on our site exactly.

### ROOT CAUSE — Warren-Newport

This is a pure scraper miss, not a source problem, and it matches the flagged suspicion about recurring/series items: **every one of the 9 missed rows is a recurring or series-style program** ("Project of the Week", "K-pop Club", "Dungeons and Dragons," "Café Spanglish," "Lotería Night") rather than a one-off. The static event pages here are served by a Communico/libnet JS front end — the `.eelistevent` list-view cards (what the scraper reads via headless Chrome `--dump-dom`) likely render recurring/series instances with a different DOM shape or timing than one-off events (e.g., depend on a client-side JS pass that runs after `--dump-dom` captures, or key off a different card class for series children). This looks like a **DOM-timing/selector gap for recurring items in the headless-Chrome capture**, not an audience filter — the events that came back via direct event-page fetch show no unusual audience/category markup that would explain a filter mis-read. Recommend: add a wait-for-selector or extra render delay before `--dump-dom` on the WNPL listing page, and diff a rendered page's DOM structure for a recurring vs. one-off card to confirm the exact selector mismatch.

## Recovered NDJSON

- `intake/2026-08-22/antioch-recovered.ndjson` — 2 lines (Open Workshop, Minecraft Mania — both 2026-11-05, both All Ages/maker-adult, cap-seam misses)
- `intake/2026-08-22/wnpl-recovered.ndjson` — 4 lines (Project of the Week ×2, Lotería Night, Superhero Trivia Night — clear family/all-ages fits)
- **Not restored** (STILL-LIVE and real; already live on the site so no action needed. Note K-pop Club and D&D: Grades 9-12 are TEEN programming, which IS in scope since 2026-08-04 — they were initially misjudged against the superseded ages-0-5 rules or age data unconfirmable from a static fetch of the JS-rendered WNPL page): Dungeons and Dragons: Adults, K-pop Club, Dungeons and Dragons: Grades 9-12, Café Spanglish, Murder Mystery Night!
