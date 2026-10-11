# Sweep brief — 2026-10-10 (shared by all scraper agents)

Repo: central-lake-county-fun (cwd). Read, in this order: `intake/SCHEMA.md` (output format + age scope), then the
`SOURCES.md` sections for your sources (endpoints, platform traps). `../CLAUDE.md` has the longer rules.

**Window:** 2026-10-10 through 2026-12-31. Skip anything outside it.
**Priority tonight: Halloween / fall events** (trick-or-treat, trunk-or-treat, boo bashes, costume parades, haunted
trails, pumpkin/harvest/fall fests, spooky storytimes, Halloween crafts) — but collect EVERYTHING in scope, not just those.

**Output:** one file per source: `intake/2026-10-10/<source_id>.ndjson`, one JSON object per line, per SCHEMA.md. `source_id` and `org`:
use the same `source_id` as the matching file in `intake/2026-09-11/` where one exists, and copy the `org` string EXACTLY from
that file's rows (or from an existing EVENTS row in index.html for the same org). Include `raw`. Set `scraped_at`.
Do NOT edit index.html or any file outside `intake/2026-10-10/`. Use unique scratch filenames under your own prefix.

**Rules that bite (from CLAUDE.md):**
- Never default a cost. No price shown -> `cost: ""`. Only write `Free` if the page says free. Homeschool events keep real price.
- Multi-site agencies (Lake County Forest Preserves, IDNR, MCCD, Cook County FP): set per-event `zip` to the site's real zip.
- Passive all-month items (scavenger hunts "Oct 1-31", Book of the Month displays, I-Spy) -> skip. Take-home kits: keep, add normally.
- Age-split sessions are separate rows. Multi-day event = one row per day.
- Exclusions: Wheaton PL, Glen Ellyn PL, any DuPage forest preserve/nature center, Willowbrook, Racine Zoo, MCCD Camps.
- Judge audience from title/description, not a keyword regex (`story` matches `history`). Drop adult-only (except maker/craft/DIY).
- Event `url` must be event-specific, else "".
- Network works from bash (curl/python). Be gentle: don't hammer; do not run parallel bulk geocoders.
- Tribe sites: paginate (`per_page=50` truncates). libnet: `headless --dump-dom` with the range URL. librarycalendar: UNION month grid + day feed.

**Final reply (short):** per source: row count, how fetched, anything that failed or looked wrong. List any Halloween events
you found that you are unsure belong. Do not paste the data back.
