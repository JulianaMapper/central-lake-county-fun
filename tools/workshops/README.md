# Grown-Up Workshops tab

The **05 Grown-Up Workshops** tab (`/workshops/`) lists ONE-TIME, hands-on classes for adults:
sewing, painting, jewelry, wreaths, needlepoint and so on. Started 2026-10-29 at Juliana's request.

## Rules (Juliana's)
- **One-time workshops only, "the special classes."** No weekly clubs, open studio, open makerspace,
  bring-your-own-project nights, take-home kits ("All day" + no registration), or multi-week series.
- **Mostly library events**, plus Michaels Gurnee (adult Hallmark workshops), needlepoint shops,
  Adler Arts Center one-day workshops, and park districts.
- **Paid classes stay, with their price.** This tab is NOT bound by the events calendar's free-only rule.
- Show, per class: distance, **when registration opens** (secondary, with "Remind me" calendar links),
  **Full as of <date>** / **Only N spots left as of <date>**, and **whether you need that library's card**.

## Refresh (each sweep)
```bash
python3 tools/workshops/fetch_libnet.py tools/workshops/data/libnet_out.json        # 13 libnet/Communico libraries
python3 tools/workshops/fetch_librarycalendar.py tools/workshops/data/lc_out.json   # Grayslake, Fox Lake, Wauconda
python3 tools/workshops/build_workshops.py            # dry run
python3 tools/workshops/build_workshops.py --write    # rewrites the WORKSHOPS block in index.html
python3 tools/qa_check.py
```
Then **read the new titles and update the picks in `build_workshops.py`** (`PICK`, `TPICK`, `APICK`,
the Michaels/needlepoint rows). The keyword filter in the fetchers only proposes candidates; a human
(or LLM) pass decides which are real one-time workshops.

⚠️ Pulls made by hand on 2026-10-29 that do not have a fetch script yet. Rebuild them next sweep:
- `data/tribe_out.json`: Tribe API for Gurnee PD, Brushwood Center, Waukegan PD, and others.
- `data/antioch_raw.json`: `apld.libcal.com/ajax/calendar/list?c=-1&date=0000-00-00&perpage=100&page=N`.
- `data/extra_libs.json`: Grayslake, Wauconda (rows built from `lc_out.json` + each event page's
  `og:description`) and North Chicago (Tribe `ncplibrary.org`, "STEAM Lab for Adults" only).
- Michaels: `michaels.com/events-and-services` needs Claude-in-Chrome (curl gets a maintenance page).
- Needlepoint shops: Shopify `/products.json` on velvetstitchhouse.com, thirdcoaststitches.com,
  thepepperpot.co, forestneedle.com. Shop list: `~/Developer/background-needlepoint/docs/LOCAL-SHOPS-AND-CLASSES.md`.

## Where each fact comes from
| Fact | libnet / Communico | Antioch LibCal | others |
|---|---|---|---|
| Registration opens | `reg_opens` | event page "Registrations open at …" (**the title's date can be stale**) | not published |
| Seats | `max_attendee` − `total_registrants`, `allow_waitlist` | `seatsleft_text` | none |
| Card rule | `sub_title` + `description` + `long_description` text | policy only | n/a |

**Card rules.** No nearby library limits ALL adult programs to its own cardholders (policies in
`lib_rules.json`, with sources). Restrictions are per class and written in the event text, often in the
**subtitle**: Northbrook "Card Required", Indian Trails "Reserved for Adult Indian Trails Library
cardholders only", Cook "Must be a CMPLD cardholder to attend". Algonquin's "*AAPLD card required" on
Cricut Basics is about checking out the machines, not the class (excluded in `card_rule()`).

**Park districts** register through Vermont Systems WebTrac, not their event calendars, e.g.
`ilgurneeweb.myvscloud.com/webtrac/web/search.html?module=ar&keyword=<activity#>`. Cloudflare blocks curl;
use Claude-in-Chrome + get_page_text. WebTrac has the real time, place and resident/non-resident price.

**Calendar links.** "Add to calendar" (the class) and "Remind me" (8 AM the day registration opens) each
offer Outlook (`outlook.office.com/.../deeplink/compose`, Microsoft 365 accounts), Google, and an .ics
for Apple Calendar. Times are sent as UTC so they land in the viewer's local time.

Every row's `zip` must exist in `ZIP_CENTROIDS` in index.html; the build fails loudly if not.
