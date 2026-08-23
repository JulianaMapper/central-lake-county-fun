# Intake NDJSON schema

One JSON object per line. No wrapping array, no pretty-printing. UTF-8.
File path: `intake/YYYY-MM-DD/<source_id>.ndjson`

## Required on every line

| Field | Type | Notes |
|---|---|---|
| `date` | `YYYY-MM-DD` | Single day. A multi-day event = one line per day. |
| `time` | string | As printed, e.g. `10:00AM - 11:00AM`, `All Day`, `TBA` |
| `name` | string | Event title, verbatim from the page |
| `org` | string | Canonical org name (given to you — use it EXACTLY) |
| `location` | string | Room / branch / address as printed, else `""` |
| `age` | string | Age or grade text as printed, else `""` |
| `cost` | string | `Free` or the fee as printed |
| `reg` | string | `Yes` / `No` / `Recommended` |
| `url` | string | Event-specific link. Homepage is NOT acceptable — use `""` if none. |
| `audience` | enum | `kids` \| `family` \| `adult` — see rules |
| `raw` | string | The raw text block you parsed this from. **Required.** Lets us re-derive fields without re-scraping. |
| `source_id` | string | Given to you |
| `scraped_at` | ISO 8601 | e.g. `2026-07-31T14:22:00-05:00` |

Optional: `notes` (materials, indoor/outdoor, limited spots), `zip` (5-digit — set
this when the org has multiple locations).

**Do NOT set** `type`, `timeOfDay`, `ageGroup`, `drive`, `day`, `regStatus`. Those
are derived by the build step. Guessing them creates the drift we're fixing.

## Date window

**Whoever dispatches the sweep sets this — it is a parameter, not a constant.**
Convention: from the sweep date through the end of the horizon the sources
actually publish (a fall sweep should reach 2026-12-31 to catch Halloween and
holiday programming). State it in the scraper's instructions and skip anything
outside it.

*(This used to be hardcoded `2026-08-01`–`2026-10-31`, which silently became
wrong the moment a sweep ran outside that window.)*

## audience — how to classify

- `kids` — aimed at children only (`Ages 3-5`, `Preschool`, `Toddler`, `Youth`)
- `family` — `All ages`, `Families`, `with an adult`, `with caregiver`
- `teen` — middle/high school: grades 6–12, `Teens`, `Tweens`, `Young Adult`
- `homeschool` — labelled homeschool / home school, or daytime school-hours
  programming aimed at homeschool families
- `adult` — aimed at adults

"All ages with an adult" / "Ages 0-5 with an adult" is `family`, **not** `adult`.
The word "adult" there means supervision, not audience. Likewise an age tag of
`Early Childhood + Adults` is a caregiver-accompanied baby/toddler event —
`family`. Misreading these as `adult` was a real bug on the 2026-08-22 sweep.

## ⚠️ AGE SCOPE — widened 2026-08-04, and this file was the last holdout

This section used to say ages 0–5 only, and to drop grade 1+, ages 6+ and all
teen/tween programming. **That is no longer the policy** (`CLAUDE.md`, banner
dated 2026-08-04) and the stale copy here did measurable damage: the 2026-08-22
sweep found **1,935 events inside date ranges the site already covered**, and
35% of them were teen/tween rows earlier sweeps had thrown away under these
rules. Every scraper had to be handed a per-agent override to get around this
file.

**Current scope: through HIGH SCHOOL, plus homeschool.**

## KEEP

- Anything `kids` or `family`: all ages, family, families, baby, infant,
  toddler, littles, birth–5, ages 0–5 / 1–5 / 2–5, preschool, pre-K,
  kindergarten readiness, storytime
- **Elementary and school-age**: grades K–5, ages 6+, elementary
- **Teen / tween**: grades 6–12, ages 10+/12+, middle and high school, Young
  Adult. Teen nights, maker and STEM clubs, gaming, anime, teen volunteering
- **Homeschool**: anything labelled homeschool / home school / home-school, and
  daytime school-hours programming for homeschool families
- `adult` events **only if** they are maker / craft / DIY-learning: makerspace,
  3D printing, laser cutter, sewing, Cricut, embroidery, woodworking, pottery,
  screen printing, soldering, jewelry, canning, "learn to ___". These feed a
  planned separate maker page.

## COST

Free-only — **except `homeschool`, which is exempt** and keeps its real price.
Record the fee verbatim, with both tiers where they differ:
`"$6 resident / $8 nonresident"`. Homeschool programming is mostly paid, so a
free-only rule there guarantees an empty category.

⚠️ **Never default a cost you did not read.** If the listing shows no price,
leave `cost` empty rather than writing `"Free"` — a paid event labelled free
gets advertised as free AND survives the site's "Free only" filter. Detail pages
usually carry the real price and usually respond to plain curl; fetch them.

## DROP — do not emit a line

- **Library closures, holiday hours, "Closed" anything.** Explicitly unwanted.
- Board / commission / committee / trustee / zoning meetings
- Fundraisers, galas, golf outings, 21+ or bar events
- Senior programs, senior bus trips, blood drives
- Adults-only programming that is not maker/craft (book clubs, tax help, job
  fairs, ESL, Medicare/AARP sessions, adult fitness, lectures)
- Bookmobile stops named after apartment complexes or care facilities
- Paid registration classes / camps / multi-week sessions (non-homeschool)

### Superseded DROP rules — do NOT reinstate

These were correct under the ages-0–5 scope and are wrong now. Left visible on
purpose — a deleted rule tends to get "helpfully" reinvented:
- ~~School-age-only: grade 1+, grades K–5, ages 6+, elementary-only~~ — **KEEP**
- ~~Teen/tween-only (grades 6–12, ages 12+) unless tagged all-ages/family~~ — **KEEP**
- ~~All paid registration programming~~ — still dropped, **except homeschool**

## Example line

```
{"date":"2026-08-14","time":"10:30AM - 11:00AM","name":"Toddler Storytime","org":"Crystal Lake Public Library","location":"Youth Services Story Room","age":"Ages 18 months - 3 years","cost":"Free","reg":"No","url":"https://crystallake.librarycalendar.com/event/toddler-storytime-8-14","audience":"kids","raw":"Toddler Storytime | Thu Aug 14 | 10:30 - 11:00 am | Youth Services Story Room | Age Group: Toddler | No registration required","source_id":"crystallake-librarycalendar","scraped_at":"2026-07-31T14:22:00-05:00"}
```

## Quality bar

- Do not invent a field. Empty string beats a guess.
- If a page yields 0 events, still write the file with 0 lines and report why.
- **Dedupe within your own file on `date|name|url`, NOT `date|name`.** The old
  `date|name` wording was wrong twice over and cost real events on 2026-08-22:
  - **Same-day multi-session programs collapse.** Ela runs "Goofy Golf" five times
    in one day; a `date|name` key keeps one and silently deletes four.
  - **Never dedupe ACROSS dates.** A weekly storytime legitimately repeats the same
    title every week. Something collapsed those at Ela and deleted the whole series
    after its first occurrence — see `tools/recurrence_check.py`, which exists
    because that class of loss is invisible to every other check.
  When two rows share a date and title but have no distinct `url`, keep both if
  their `time` differs — that is a second session, not a duplicate.
- Report your line count. It will be checked against the file.
