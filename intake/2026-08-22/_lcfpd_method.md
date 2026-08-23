# Lake County Forest Preserves — method that finally worked (2026-08-22)

**Result: 32 events written to `lcfpd.ndjson`** (from 55 unique detail pages
fetched, 23 dropped as adult/paid/out-of-scope). Previous sweeps got 0.

## The blocker, and what actually broke it

Both the list page and every event detail page 403 to plain `curl`, even with
a real `User-Agent` header set. This is **not** solved by headers — it needs
an actual browser engine (Cloudflare/bot-check style gate, confirmed by a
`cf-chl` / `__CF$cv$params` bootstrap script visible in the rendered detail
page HTML).

Headless Chrome clears the block completely, on both the list and detail
pages. The fix that had eluded prior attempts was **not** about getting past
the 403 — that part already worked in prior sweeps for the list page. The
detail pages specifically needed a much larger time budget:

```
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless --disable-gpu --dump-dom \
  --virtual-time-budget=60000 \
  --run-all-compositor-stages-before-draw \
  --user-agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36" \
  "https://www.lcfpd.org/calendar/<event-slug>/<yyyymmdd>/"
```

- **10s and 12s budgets (prior attempts) were too short** — the detail page
  renders in two passes: an AngularJS 1.x app (`angular.module('MainApp', ...)`,
  not a router-based SPA as previously assumed) that fires XHRs for a
  `RequestVerificationToken`-signed request, then a Cloudflare challenge
  bootstrap script, then the real event body. At 10-12s the DOM dump lands
  mid-render and only nav/footer boilerplate exists yet.
- **60,000ms (60s) virtual time + `--run-all-compositor-stages-before-draw`
  reliably renders the full event body** — Date/Time/Location/Age/Pricing
  table/Description text all present. Real (wall-clock) run time per page was
  only ~7-8 seconds, so the cost of the larger budget is cheap — it does not
  actually wait 60 real seconds, it just gives the virtual clock enough
  ticks to let Angular's digest cycle and the async data calls settle.
- One page (`sunday-stroll-/20261018/`) came back as a **504 Gateway
  Timeout** on the first attempt — a flaky upstream response, not a rendering
  problem. A second attempt with the identical command succeeded. **Retry
  once on a 504** before concluding a page is unreachable.

No JSON/XHR API endpoint was found in the JS bundles (checked for `/api/`,
`/umbraco/`, `/sitecore/`, `?format=json`) — this app calls its own
Angular-legacy endpoints with a rotating anti-forgery token
(`RequestVerificationToken` + a per-load `s` value), which is not a stable,
scrapable API. **The dump-dom approach above is the durable method** — no
Claude-in-Chrome interactive session was needed.

## Step-by-step for the next sweep

1. Fetch the list page: `https://www.lcfpd.org/calendar/?F_a=All` with
   headless Chrome, `--dump-dom --virtual-time-budget=15000` (this budget was
   already sufficient here — it's a static-content slider, not the same
   render-timing problem as the detail pages). User-Agent header required
   (bare curl 403s regardless of UA).
2. Extract every `/calendar/<slug>/<yyyymmdd>/` href from that dump
   (`grep -o 'href="/calendar/[^"]*/202[0-9]*/[^"]*"'`, strip `?F_c=` query
   suffixes, dedupe). This is the full "Featured Events" slider content — all
   slides are present in the static DOM, no clicking/pagination needed. Got
   55 unique event/date URLs this way, spanning through Nov 2026.
3. Fetch each detail URL with the 60s-budget command above. ~8s wall-clock
   each — 55 pages took about 7 minutes total.
4. Strip `<script>`/`<style>`, collapse tags to text, find the **last**
   occurrence of "Upcoming Events" in the text (it also appears in the site
   nav and possibly a related-events widget — the last occurrence is the
   actual event body), and cut off at "The District occasionally takes
   photographs" (start of the shared photo-release boilerplate that follows
   every event body).
5. Parse Date / Time / Location / Age tag / Pricing table / description /
   registration status out of that block. All of it is present as plain text
   — no further JS execution needed once you have the dumped DOM.

## Filtering applied (per this project's rules)

- **Free-only except homeschool.** 3 events tagged "for Homeschoolers" were
  kept WITH their real price ($6 resident/$8 nonresident in all 3 cases).
  Every other paid event (historic home tours, guided walks/talks with a
  "Pricing:" table, senior series, sketching hour, guided paddle, etc.) was
  dropped — LCFPD runs far more paid adult/family programming than free
  programming, which is why the drop count (23) is so much higher than the
  keep count (32 kept out of 55 fetched).
- **Senior programs dropped** (standing rule) — 3 "Senior Series" events.
- **Adult-only, non-maker/craft dropped** — Beer Garden Trivia Night, Local
  History Author Series, Pop/Pride/GlenRock Story talk, Sunset Guided Hike
  (adult-tagged even though free/registration-only).
- Two Spanish-language walks and events (`Caminata en Espanol` x3,
  `Caminata a Traves de la Historia`) kept — family-tagged, free, in scope.
- `GlenRock Pop at the Dunn Museum` and `Bess Bower Dunn Day` are the same
  day/venue but distinct slider entries (one centers on the soda-brand
  promo, one on the museum's free-admission day) — kept both since both are
  genuinely separate listed events, not a dedupe case.

## Things that did NOT need trying, in the end

- Claude-in-Chrome interactive `get_page_text` — the plain headless-Chrome
  dump-dom with the longer budget was sufficient and is far cheaper to run
  55 times.
- iCal/RSS/print views — never found one; not needed since dump-dom worked.
- Older `/calendar/` list/month views — not needed; the `?F_a=All` slider
  already surfaced every event in the Aug 22–Nov 2026 window in one page.

## Recommendation for `SOURCES.md`

Update the LCFPD row's note from **"403s to curl — needs headless + UA"** to:

> 403s to curl (bot-check gate) even with UA — headless Chrome clears it.
> List page: `--dump-dom --virtual-time-budget=15000` is enough. **Detail
> pages need `--virtual-time-budget=60000 --run-all-compositor-stages-before-draw`**
> — shorter budgets (10-12s) return nav/footer only. No JSON API exists (it's
> legacy AngularJS 1.x with a rotating anti-forgery token, not a real REST
> endpoint). ~8s wall-clock per detail page; retry once on an occasional 504.
