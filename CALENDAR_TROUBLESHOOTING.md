# Why the Calendar Sometimes Shows Nothing

## TL;DR
The site is a single `index.html` with one giant `<script>` block. **One JS syntax
error anywhere in that script wipes the entire calendar** — page loads, layout
renders, but no events appear. The most common culprit is an unescaped
apostrophe inside a single-quoted JS string (e.g., `name:'Children's Museum'`).

When you see the calendar blank, run the **2-second check** below before
anything else.

---

## The 2-Second Check (always run first)

```bash
cd "/Users/Juliana/Library/CloudStorage/OneDrive-FlourishandThriveLabs/Personal/Personal Process/Library Events/central-lake-county-fun"
python3 tools/check_syntax.py
```

- Output empty / "OK" = JS is valid; problem is elsewhere (cache, GH Pages
  build, filter state).
- Output with an error line + position = fix that line. The script tells you
  the line number AND the surrounding 80 characters of context.

You can also do it manually:

```bash
python3 -c "
import re
with open('index.html') as f: c = f.read()
m = list(re.finditer(r'<script[^>]*>(.*?)</script>', c, re.DOTALL))[1]
open('/tmp/check.js','w').write(m.group(1))
" && node --check /tmp/check.js
```

---

## How the Calendar Renders (so you know what can break)

```
[index.html loads]
        ↓
[main <script> block parses]
        ↓
   const EVENTS = [ … 2,400+ rows … ]       ← JSON-format objects, double quotes
   const PARKS = [ … ]                       ← JSON-format
   const BUCKET = [ … ]                      ← JSON-format
   const MAP_LOCATIONS = [ … ]               ← JS-format, single quotes ⚠
   …lots of functions…
        ↓
[DOMContentLoaded fires]
        ↓
   populateOrgs();
   applyFilters();      ← filters EVENTS by date >= today, builds filteredEvents
   initBucket();
   renderGridCal();
        ↓
   renderCal()          ← walks filteredEvents → builds list HTML → injects into #calContainer
```

**If any line in the script block has a syntax error, parsing aborts there.**
None of the functions ever get defined. `DOMContentLoaded` fires but
`applyFilters` doesn't exist, so the calendar stays blank.

The HTML chrome (tabs, hero, filter form, toolbar buttons) is **plain HTML**
and renders no matter what — that's why the page looks fine except the events
list is empty. **Empty page ≠ no events. Empty page = JS died.**

---

## Things That Have Broken the Calendar Before

### 1. Unescaped apostrophe in single-quoted MAP_LOCATIONS string ⚠ MOST COMMON

```js
{t:'mus', name:'Children's Museum', addr:'...'}
//                       ↑ this apostrophe closes the string early
```

**Fix:** escape with `\'`:
```js
{t:'mus', name:'Children\'s Museum', addr:'...'}
```

Why this keeps happening: when I add new museums to MAP_LOCATIONS from web
sources, names like *Children's*, *Women's*, *Yesterday's*, *St. James'* get
pasted in raw. The EVENTS / PARKS / BUCKET arrays use **double-quoted JSON** so
they're safe, but MAP_LOCATIONS uses single-quoted JS object literal syntax.

**Future fix:** when adding to MAP_LOCATIONS, use double quotes for the values
that might contain apostrophes:
```js
{t:'mus', name:"Children's Museum", addr:"301 N Washington"}
```

### 2. Trailing comma in EVENTS array
Browsers allow trailing commas, but if I ever run the data through
`JSON.parse` (some merge scripts do), it errors. Not currently a render-killer
for the live site, but it does mean `JSON.parse` checks fail.

### 3. Backslash-escape collision when adding via Python script
When I write Python code like:
```python
entries.append("{t:'mus', name:'Yesterday\\'s Farm', ...}")
```
the file ends up with literally `Yesterday\'s` — which is valid JS but reads
oddly. Better to use double quotes for the JS string when you know an
apostrophe is coming.

### 4. Smart quotes from copy-paste (`'` vs `'`)
If I paste a museum description from a website that uses curly quotes
(`'` U+2019, `'` U+2018) into a single-quoted JS string, the string still
parses (because those curly quotes aren't real apostrophes to the parser) —
BUT if the curly-quote pair gets mismatched somewhere else, you can break
parsing in odd ways. Hasn't bitten us yet; worth knowing.

### 5. HTML inside event names
If an event name contains `</script>`, the browser will close the script tag
early. None of the current event sources do this, but if a library ever names
an event something like *"Hour of Code – </script> demos"* it would nuke
everything. The escape would be `<\/script>`.

---

## When the Check Says JS Is Fine but Calendar Is Still Blank

Run through this list:

1. **Browser cache.** `Cmd+Shift+R` (hard refresh). Especially after a
   `?fbclid=...` URL — Facebook share links sometimes get cached.

2. **GitHub Pages still building.** A push usually deploys in 30–90 seconds.
   Check at https://github.com/JulianaMapper/central-lake-county-fun/actions
   — the latest "pages build and deployment" job should be green.

3. **Date filter excluded everything.** `applyFilters()` always drops events
   where `date < today`. If `today` (in the browser's local timezone) is past
   the latest event in `EVENTS`, the calendar will be legitimately empty.
   Check with:
   ```bash
   python3 -c "
   import re, json
   with open('index.html') as f: c = f.read()
   raw = c[c.find('const EVENTS = [')+15:c.find('];', c.find('const EVENTS = ['))+1]
   raw = raw.rstrip().rstrip(',') + ']'   # strip trailing comma
   events = json.loads(raw.replace(',]', ']'))
   from datetime import date
   future = [e for e in events if e['date'] >= str(date.today())]
   print(f'{len(future)} events on or after today ({date.today()})')
   print(f'Latest event: {max(e[\"date\"] for e in events)}')
   "
   ```

4. **Console errors.** Open DevTools (`Cmd+Opt+I`) → Console tab. A runtime
   error (different from a syntax error — would say something like
   `TypeError: Cannot read properties of undefined`) shows up there with a
   line number.

5. **`activeQuick` state stuck.** The quick filter buttons (Today / This Week
   / Free) set `activeQuick`. If the URL ever pre-loads with one of these and
   no events match, it'd show empty. Currently no URL-param handling, so this
   only happens after a user click.

---

## Pre-Commit Habit (the rule going forward)

Before every commit that touches `index.html`:

```bash
python3 tools/check_syntax.py && echo "✓ ready to commit"
```

If you forget and ship a broken commit, the calendar disappears for everyone
on the live site until you push a fix. There's no GitHub Action validating
this — yet.

**Future enhancement:** wire `tools/check_syntax.py` into a git pre-commit
hook in this repo so a commit physically can't be made with a broken script.

---

## Quick Reference: What File Lives Where

| Thing | Where it lives |
|---|---|
| The site itself | `index.html` (single file, everything embedded) |
| EVENTS data | `const EVENTS = [...]` inside `<script>` — JSON-format, ~2,460 rows |
| PARKS data | `const PARKS = [...]` — JSON-format |
| BUCKET data | `const BUCKET = [...]` — JSON-format |
| Map markers | `const MAP_LOCATIONS = [...]` — JS-format ⚠ (apostrophe danger) |
| Source CSVs | `../library_events_2026_*.csv` (one level up, OneDrive folder) |
| Site repo | `central-lake-county-fun/` |
| Live URL | https://julianamapper.github.io/central-lake-county-fun/ |
| Syntax check | `tools/check_syntax.py` |
