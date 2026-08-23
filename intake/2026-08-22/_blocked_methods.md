# Blocked-source unblock methods — 2026-08-22

## 1. McHenry County Conservation District (`mccd-calendar`) — 43 lines, UNBLOCKED

**Working method: read the calendar's own in-page JS data array, then cross-reference the Amilia SmartRec store for cost/category.**

1. Navigate (Claude-in-Chrome) to `https://www.mccdistrict.org/calendar.php?view=list&month=08&day=01&year=2026`.
   Plain curl and `--dump-dom` still fail here as documented (revize CMS, JS-rendered) — but you don't need either.
2. The page's own script exposes `window.jsonEvents` — a JS array of **every event on the calendar, past and future** (1,918 entries as of this sweep), each with `title`, `primary_calendar_name` (the calendar bucket: `Programs` / `Special Events` / `Board Meetings` / `Holidays/Office Closures`), `start`, `end`, `location`, and a URL-encoded HTML `desc`. Pull it directly with the `javascript_tool`:
   ```js
   window.jsonEvents.filter(e => new Date(e.start) >= START && new Date(e.start) <= END
     && e.primary_calendar_name !== 'Board Meetings' && e.primary_calendar_name !== 'Holidays/Office Closures')
   ```
   `desc` decodes with `decodeURIComponent()` then strip tags; it carries the printed age text ("For ages 14 and up", "For ages 2-6 with an Adult") and whether registration is required, but **never a price**.
3. **This is also the correct `Type` field for the Camps exclusion** — `primary_calendar_name` is the site's own bucket, not a name guess. In the 2026-08-22 through 2026-12-31 window, zero events carry `Programs`/`Special Events` AND look like a multi-day registration camp — MCCD's actual `Camps` inventory (Time Travelers Camp, Young Explorers Camp Session 3) all falls in Aug 3–14, before this window, so nothing needed excluding this round. Confirmed the trap is real: **"Hike with Mike: Camp Lakota"** and **"Full Moon Hike and Campfire"** both contain "Camp" as a substring and are NOT camps — a name-substring filter would have wrongly dropped/kept the wrong ones.
4. **Cost**: the calendar modal (day-detail view, `calendar.php?view=day&...&id=<N>`) never shows a price — confirmed on multiple events by screenshot; it has description, age, a generic (non-per-activity) "Registration is required" link, and a map, and that's all. The real per-activity price and category live in the **Amilia SmartRec** storefront:
   ```
   https://app.amilia.com/store/en/mccdistrict/api/Activity/Search?textCriteria=<url-encoded event title>
   ```
   This is a plain same-origin GET once you're on `app.amilia.com` (no antiforgery token required for read access) and returns a full HTML results page. Fetch it with `fetch()` inside `javascript_tool` (much faster than navigating per event) and regex out the block between `"Search Results"` and `"You can see"` — it contains the exact price range (e.g. `$0.00 - $5.00`, meaning resident/nonresident) and the category breadcrumb (e.g. `Guided Hikes & Walks | Fall 2026 | Day Hikes | Adults 14+`). Search on a short distinctive substring of the title if the full title returns 0 results (Amilia's search is fairly literal).
   The category breadcrumb's age tag (`Adults 14+`, `Youth 8-13`, `All Ages`, etc.) is Amilia's own age-floor bucket, not "adults-only" branding — cross-checked against the calendar's plain-English age text and they agree everywhere except one case (see below).
5. **Exclusions applied this sweep** (age/audience judgment calls, not camps): dropped `Great Outdoors Beer Trail` (Amilia confirms "Ages 21+"), `Introduction to Volunteering` (calendar text says "ages 18 and up," adult civic training), `Grounding Yoga & Meditation` ×3 sessions (adult fitness/wellness class — DROP rule explicitly names fitness classes), and `Nature Journal Hike for Adults` (explicitly "for Adults," paired with a separate "...for Kids" version that was kept). Everything else tagged `Adults 14+` was kept and classified `audience: kids`, consistent with the "through high school" age scope — that tag means age floor 14, not adult-only, per the plain-English "For ages 14 and up" text on the same events.

No further approach needed — this source is fully unblocked going forward with this method.

## 2. Wheeling Park District (`wheeling-pd`) — 18 lines, PARTIALLY UNBLOCKED

**Working method: skip the EventOn AJAX calendar entirely — use the curated `/special-events/` page instead, which is plain server-rendered HTML.**

1. `https://www.wheelingparkdistrict.com/events/` still errors client-side ("Please select an event archive page in eventON Settings") and its EventOn AJAX/REST routes are not worth chasing.
2. `https://www.wheelingparkdistrict.com/special-events/` loaded cleanly via Claude-in-Chrome with **no 403 and no Cloudflare interstitial** — the earlier "403 to Tribe API guess and plain homepage" finding in SOURCES.md was about the wrong path, not real bot-blocking on this domain. Plain `curl` was not retried here, so it's unconfirmed whether the block is Claude-in-Chrome-only or lifted entirely — worth a quick curl check next sweep.
3. The visible list (dates + times) is real server HTML. Each event's full detail (fee, location, description) lives in an already-in-DOM `.eventon_list_event` → `.event_description` block that EventOn shows in a lightbox on click — you don't need to click at all, the text is present in the DOM from page load:
   ```js
   document.querySelectorAll('.eventon_list_event') // 25 cards, one per session-instance
   ```
   Extract `.event_description`'s `textContent`; it duplicates itself (title snippet + full block), so slice from the second occurrence of `"Event Details"`. Fee ("FeeR $50/ NR $60"), Location, and the full description are all in that text.
4. **No stable per-event URL exists** — cards open a same-page lightbox, not a permalink, so `url` is `""` for all Wheeling rows.
5. **One event's detail never populated in the DOM** even after a JS `.click()`: "Day of the Dead 5k" (Oct 25). Its `.event_description` stayed empty — possibly lazy-loaded only on a real (not synthetic) click. Recorded with blank cost/location rather than guessing; worth a manual visit + real click next time.
6. Dropped as adult-not-maker/craft (per house rules) rather than "blocked": `End of Summer BBQ`, `Sound Bath Meditation with Goats` ×2, `Chicago's Most Haunted Lunch & Show`, `Dink or Treat Pickleball Tournament`, `Fall Fling` (country club brunch). Kept `Paint a Pot with Goats` ×2 as `audience: adult` under the maker/craft exception (pottery painting).

## 3. Volo Museum / Jurassic Gardens (`volo-museum`) — 10 lines, UNBLOCKED (but thin)

**Working method: don't fight `volocars.com` — its events content actually lives on a separate, unprotected domain, `volofun.com`.**

1. `https://www.volocars.com/` itself loads fine via Claude-in-Chrome (no 403 seen this sweep, contrary to the prior "403 at WAF/TLS layer to curl and browser UA" note — that may have been curl-specific or since resolved). `volocars.com/events` 404s and its sitemap lists no events/calendar page at all — the museum's events microsite is fully split off onto **`volofun.com`**, findable via the "Volo Auto Museum News" sitemap link → `volofun.com/volo-news/` → `volofun.com/events/`.
2. `https://volofun.com/events/` is plain server-rendered HTML (get_page_text works directly, no JS extraction needed) and lists "All Upcoming Events by Date" plus a separate "Past Events by Date" section (each with its own "Load More"). **As of this scrape (Aug 22), the upcoming list runs out at September 20 — there is nothing dated in October, November, or December posted yet.** This reads as the org genuinely not having published fall/Halloween/holiday programming yet, not a scraping gap: the "Load More" under Past Events, when clicked, only ever expands further into the past, and no second "Load More" exists under the upcoming section.
3. Two of the upcoming items are **stated recurring monthly programs**, not one-offs: "Live Interactive Reptile Meet & Greet" ("usually every 2nd Sunday") and "Sensory Sunday at Jurassic Gardens" ("every 3rd Sunday of the month"). Per the "never invent a date" rule, only the explicitly-listed September occurrences were emitted — **do not** project Oct/Nov/Dec 2nd-/3rd-Sunday dates without re-checking the live page closer to those months, since the Sept Reptile Meet & Greet was itself already moved off its usual Sunday.
4. **Admission cost**: `https://volofun.com/plan-your-visit-to-volo-museum/` gives the real current price ladder — Platinum (all 3 attractions, next-day free) $59.95–$69.95, two-attraction $45.95–$59.95, single-attraction à la carte $17.95–$39.95, **kids 4 & under free** always. Individual events don't carry their own ticket price — they're included with whichever general admission the visitor already bought — so every Volo row's `cost` field states that range rather than "Free," per the task's "record real admission prices" instruction for this paid attraction.
5. Recommend a follow-up pass in October (before Halloween) and again in late November (before the holiday season) specifically to re-check `volofun.com/events/` for newly-posted fall/holiday dates — the method is proven, the content just isn't live yet.

## Line counts
- `mccd-calendar.ndjson`: 43
- `wheeling-pd.ndjson`: 18
- `volo-museum.ndjson`: 10
