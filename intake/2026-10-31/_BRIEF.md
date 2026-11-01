# Sweep brief — 2026-10-31 (shared by all scraper agents)

Repo: central-lake-county-fun (cwd = this folder). Read, in this order: `intake/SCHEMA.md` (output format + age scope), then the
`../SOURCES.md` sections for your sources (endpoints, platform traps). `../CLAUDE.md` has the longer rules (SWEEP RUNBOOK at top).

**FULL sweep.** Window: 2026-10-31 through 2026-12-31. Skip anything outside it. Collect EVERYTHING in scope (regular storytimes,
STEM, crafts, teen, homeschool, nature, performances, holiday/Santa/tree-lighting/Thanksgiving/Veterans Day, new-year) — not one season.
Halloween (10/31 itself) is fine if still upcoming today.

**Output:** one file per source: `intake/2026-10-31/<source_id>.ndjson`, one JSON object per line, per SCHEMA.md. Use the same
`source_id` as the matching file in `intake/2026-10-10/` (or `intake/2026-10-24/`) where one exists, and copy the `org` string EXACTLY
from that file's rows (or from an existing EVENTS row in index.html for the same org). Org-string drift = double-adds and fake
"cancellations". Include `raw`. Set `scraped_at`. Do NOT edit index.html or anything outside `intake/2026-10-31/`. Use unique scratch
filenames under your own prefix. Give each source to exactly one agent (yours only: the list in your prompt).

**Rules that bite (CLAUDE.md):**
- Never default a cost. No price shown -> `cost: ""`. Write `Free` only if the page says free. Record real prices of paid events
  (they are removed later; under $10 stays). Libraries: blank cost = `Free` unless a fee is stated. Aggregators drop prices: open the host page.
- Multi-site agencies (Lake County Forest Preserves, IDNR, MCCD, Cook County FP): per-event `zip` = the site's real zip.
- Passive all-month items (scavenger hunts "Nov 1-30", Book of the Month displays, I-Spy, contests, "Begins/Ends" markers, drop-off periods) -> skip.
  Take-home craft kits (Grab & Go, Take & Make): keep, add normally. Closures, board meetings, senior-only, blood drives -> skip.
- Age scope: through high school + homeschool. Drop adult-only, EXCEPT adult maker/craft one-time classes (put `audience:"adult"`; they are parked for the workshops tab).
  Judge audience from title/description, not a keyword regex (`story` matches `history`). "with an adult" = family.
- Age-split sessions are separate rows. Multi-day = one row per day. Dedupe within your file on date|name|url, never across dates.
- Exclusions: Wheaton PL, Glen Ellyn PL, any DuPage forest preserve/nature center, Willowbrook Wildlife, Racine Zoo, MCCD `Camps`.
  Volo Museum and a "Hainesville library" are NOT sources. Free-admission-day museum rows are synthesized elsewhere: skip them.
- Event `url` must be event-specific, else "".
- Network works from bash (curl/python). Be gentle; no parallel bulk geocoders.
- Tribe: paginate (`per_page=50`, `start_date`, `end_date`, follow `next_rest_url`). libnet: `headless --dump-dom` with the range URL or the JSON the
  workshop fetcher uses (`tools/workshops/fetch_libnet.py` shows a working pattern). librarycalendar: UNION month grid + day feed (see SOURCES.md).
  Platforms move: if a documented URL fails, find the new one and say so in your reply.

**Final reply (short):** per source: row count, how fetched, anything that failed or looked wrong, new endpoints discovered. List events you are
unsure belong. Do not paste data back.
