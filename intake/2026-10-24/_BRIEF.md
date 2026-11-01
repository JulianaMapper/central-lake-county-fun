# HOLIDAY-ONLY sweep brief — 2026-10-24 (shared by all scraper agents)

Repo: central-lake-county-fun (cwd). Read, in this order: `intake/SCHEMA.md` (output format + age scope), then the
`SOURCES.md` sections for your sources (endpoints, platform traps). `../CLAUDE.md` has the longer rules (SWEEP RUNBOOK at top).

**This is a TARGETED sweep, not a full calendar update.** Juliana wants only holiday events, found before they sell out / get forgotten.
**Window:** 2026-11-01 through 2027-01-03.
**In scope (holiday/seasonal only):** Santa / Mrs. Claus / cookies-with-Santa / breakfast-with-Santa (free ones), tree & menorah lightings,
holiday parades & walks, holiday markets / craft fairs with kid activity, Polar Express / pajama-and-hot-chocolate nights, Grinch / Elf / Frozen-style
character visits, holiday train shows & displays (open-to-public, free), Thanksgiving crafts / turkey events / friendsgiving kids events,
Veterans Day family ceremonies, Hanukkah, Kwanzaa, Diwali, Christmas, Winter Solstice, Winter Wonderland, ice/snow festivals, "Noon Year's Eve" / New Year's
countdowns for kids, holiday storytimes, holiday crafts, gingerbread events, holiday concerts/caroling/Nutcracker-type performances.
**Out of scope:** anything not holiday-themed (regular storytimes, ordinary STEM etc.), Halloween (already swept 10-10), passive all-month displays.

**Output:** one file per source: `intake/2026-10-24/<source_id>.ndjson`, one JSON object per line, per SCHEMA.md. Use the same `source_id` as the matching
file in `intake/2026-10-10/` where one exists, and copy the `org` string EXACTLY from that file's rows (or an existing EVENTS row in index.html for that org) —
org-string drift causes double-adds. Include `raw`. Set `scraped_at`. Do NOT edit index.html or any file outside `intake/2026-10-24/`. Use unique scratch
filenames under your own prefix.

**Rules that bite (from CLAUDE.md):**
- Never default a cost. No price shown -> `cost: ""`. Only write `Free` if the page says free. Record real prices of paid events (they get removed later; under $10 stays).
  Libraries: blank cost = `Free` unless a fee is stated. Aggregator listings drop prices: open the host's page.
- Multi-site agencies (Lake County Forest Preserves, IDNR, MCCD, Cook County FP): per-event `zip` = the site's real zip.
- Age scope: through high school + homeschool. Drop adult-only. Judge audience from title/description (`story` matches `history`).
- Age-split sessions are separate rows. Multi-day = one row per day. Santa visits with multiple time slots: one row per day with the full time span.
- Exclusions: Wheaton PL, Glen Ellyn PL, any DuPage forest preserve/nature center, Willowbrook, Racine Zoo, MCCD Camps. Volo Museum and a "Hainesville library" are not sources.
- Event `url` must be event-specific, else "".
- Network works from bash. Be gentle; no parallel bulk geocoders.
- Tribe: paginate (`per_page=50`, `start_date`, `end_date`). libnet: `headless --dump-dom` with range URL. librarycalendar: UNION month grid + day feed.
  Searching a site's own search for: santa, holiday, tree lighting, christmas, hanukkah, winter, thanksgiving, grinch, polar, cookies, cocoa, caroling, nutcracker, gingerbread, new year.

**Final reply (short):** per source: holiday row count, how fetched, anything that failed. List events you're unsure belong. Don't paste data back.
