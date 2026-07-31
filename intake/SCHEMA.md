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

`2026-08-01` through `2026-10-31` inclusive. Skip anything outside it.

## audience — how to classify

- `kids` — aimed at children only (`Ages 3-5`, `Preschool`, `Toddler`, `Youth`)
- `family` — `All ages`, `Families`, `with an adult`, `with caregiver`
- `adult` — aimed at adults

"All ages with an adult" / "Ages 0-5 with an adult" is `family`, **not** `adult`.
The word "adult" there means supervision, not audience.

## KEEP

- Anything `kids` or `family` that fits ages 0–5: all ages, family, families,
  baby, infant, toddler, littles, birth–5, ages 0–5 / 1–5 / 2–5, preschool,
  pre-K, kindergarten readiness, storytime
- `adult` events **only if** they are maker / craft / DIY-learning: makerspace,
  3D printing, laser cutter, sewing, Cricut, embroidery, woodworking, pottery,
  screen printing, soldering, jewelry, canning, "learn to ___". These feed a
  planned separate maker page.

## DROP — do not emit a line

- **Library closures, holiday hours, "Closed" anything.** Explicitly unwanted.
- Board / commission / committee / trustee / zoning meetings
- Fundraisers, galas, golf outings, 21+ or bar events
- Senior programs, senior bus trips, blood drives
- School-age-only: grade 1+, grades K–5, ages 6+, elementary-only,
  teen/tween-only (grades 6–12, ages 12+) — unless also tagged all-ages/family
- Adult events that are NOT maker/craft (book clubs, tax help, job fairs,
  fitness classes, lectures)
- Bookmobile stops named after apartment complexes or care facilities
- Paid registration classes / camps / multi-week sessions

## Example line

```
{"date":"2026-08-14","time":"10:30AM - 11:00AM","name":"Toddler Storytime","org":"Crystal Lake Public Library","location":"Youth Services Story Room","age":"Ages 18 months - 3 years","cost":"Free","reg":"No","url":"https://crystallake.librarycalendar.com/event/toddler-storytime-8-14","audience":"kids","raw":"Toddler Storytime | Thu Aug 14 | 10:30 - 11:00 am | Youth Services Story Room | Age Group: Toddler | No registration required","source_id":"crystallake-librarycalendar","scraped_at":"2026-07-31T14:22:00-05:00"}
```

## Quality bar

- Do not invent a field. Empty string beats a guess.
- If a page yields 0 events, still write the file with 0 lines and report why.
- Dedupe within your own file on `date|name`.
- Report your line count. It will be checked against the file.
