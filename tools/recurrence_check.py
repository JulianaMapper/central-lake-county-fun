#!/usr/bin/env python3
"""
Find recurring series that are probably TRUNCATED — the sweep caught some
occurrences and silently lost the rest.

  python3 tools/recurrence_check.py                 # audit index.html
  python3 tools/recurrence_check.py 2026-08-22      # audit an intake batch too

## Why this exists (the blind spot it closes)

`stale_check.py` compares the site against a sweep, so it can only ask
"is something on the site missing from the sweep?" It CANNOT ask
"is something missing from BOTH?"

If a weekly storytime runs 16 times and every sweep we have ever run caught
only 2 of them, then the site has 2, the sweep finds 2, they agree, and nothing
reports a problem. The other 14 dates were never in either list. They are
invisible to every check we own — not "probably fine", genuinely unmeasured.

That is not hypothetical. On 2026-08-22, verification found Warren-Newport was
missing events and **9 of 9 checked were still live on the source** — every one
a recurring/series program, no one-off affected. Those 9 were only the ones some
*earlier* sweep had happened to catch. Nobody could say how many more there were.

## How this detects it without a second source

It uses the calendar's own internal consistency. A weekly series leaves a
fingerprint: same title, same org, same weekday, evenly spaced dates. So:

  - group by (org, title, weekday)
  - if a group has >= MIN_OCCURRENCES dates and its gaps are a clean multiple
    of 7 days, treat it as a weekly series
  - then look for HOLES: weeks inside the series' own span with no event

A hole is not proof — libraries skip weeks for holidays and breaks. But a
series with 3 events across a 14-week span is not a series we captured properly,
and that is visible from our data alone, with nothing to compare against.

## ⚠️ Known limitation — it can be fooled by UNIFORM truncation

Cadence is inferred from our own data, so if a scraper drops occurrences
*evenly* the inference absorbs the loss. Capture weeks 1, 5 and 9 of a weekly
series and the gaps are 28-28: this reads it as a complete monthly series and
says nothing. It catches RAGGED loss (the common case, from render timing and
per-day slot caps) and misses PERIODIC loss.

Closing that hole needs an outside reference — one probe of the source for a
single known date, compared against what we hold for that date. Worth adding if
a source ever looks suspiciously tidy. Until then, treat a clean run as "no
ragged truncation found", not "capture is complete".

The first version of this check also assumed every multiple-of-7 cadence was
weekly, which reported a fully-captured monthly LEGO Club as 21% captured. It
found 84 "truncated" series on the live site; with cadence inferred properly
that fell to 3. **A checker that cries wolf gets ignored, which is worse than
having no checker** — so if you loosen a threshold here, re-measure the false
positives before trusting the output.

Reports, never edits.
"""
import json, re, sys, os, glob, collections, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, 'index.html')

MIN_OCCURRENCES = 3      # below this it isn't a series, it's a repeat
MIN_SPAN_WEEKS = 4       # ignore short runs; a 3-week series with 1 gap is noise
SUSPICIOUS_FILL = 0.60   # captured/expected below this = probably truncated


def load_events():
    s = open(INDEX, encoding='utf-8').read()
    i = s.index('const EVENTS = [')
    j = s.index('const PARKS')
    return json.loads(s[i + len('const EVENTS = '):j].rstrip().rstrip(';'))


def load_intake(stamp):
    rows = []
    d = os.path.join(ROOT, 'intake', stamp)
    for fn in sorted(glob.glob(os.path.join(d, '*.ndjson'))):
        if os.path.basename(fn).startswith('_'):
            continue
        for ln in open(fn, encoding='utf-8'):
            if ln.strip():
                rows.append(json.loads(ln))
    return rows


def norm(name):
    """Strip the varying tail so occurrences of one series group together."""
    n = name.lower()
    n = re.sub(r'\s*[-–—:]\s*\[[^\]]*\]', '', n)
    n = re.sub(r'\s*\([^)]*\)', '', n)
    # a trailing session/date/theme suffix varies per occurrence
    n = re.sub(r'\s*[-–—:]\s*(session|week|part|day|no\.?|#)\s*\d+.*$', '', n)
    n = re.sub(r'[^a-z0-9]+', ' ', n)
    return ' '.join(n.split())


def audit(rows, label):
    groups = collections.defaultdict(list)
    for e in rows:
        try:
            d = datetime.date.fromisoformat(e['date'])
        except Exception:
            continue
        groups[(e['org'].strip(), norm(e['name']), d.weekday())].append((d, e['name']))

    findings = []
    for (org, title, wd), items in groups.items():
        dates = sorted({d for d, _ in items})
        if len(dates) < MIN_OCCURRENCES:
            continue
        span_days = (dates[-1] - dates[0]).days
        if span_days // 7 + 1 < MIN_SPAN_WEEKS:
            continue
        gaps = [(dates[k + 1] - dates[k]).days for k in range(len(dates) - 1)]
        if not gaps or any(g % 7 for g in gaps):
            continue                      # not on a fixed weekday cadence at all
        # ── Infer the series' OWN cadence from its most common gap.
        #
        # Do NOT assume weekly. A monthly-on-a-weekday series ("2nd Tuesday")
        # has 28-day gaps, which are also multiples of 7 — measuring it against a
        # weekly expectation reports a perfectly-captured monthly LEGO Club as
        # "21% captured, 11 weeks missing". That false positive is worse than no
        # check: it sends you rescraping a source that was already complete.
        cadence = collections.Counter(gaps).most_common(1)[0][0]
        if cadence not in (7, 14, 21, 28):
            continue
        expected = span_days // cadence + 1
        got = len(dates)
        if expected < MIN_OCCURRENCES:
            continue
        fill = got / expected
        if fill >= SUSPICIOUS_FILL:
            continue
        missing = []
        cur = dates[0]
        have = set(dates)
        while cur <= dates[-1]:
            if cur not in have:
                missing.append(cur.isoformat())
            cur += datetime.timedelta(days=cadence)
        findings.append({
            'org': org, 'title': items[0][1], 'got': got, 'expected': expected,
            'fill': fill, 'span': f"{dates[0]} .. {dates[-1]}", 'missing': missing,
            'cadence': cadence,
        })

    findings.sort(key=lambda f: (f['fill'], -len(f['missing'])))
    print(f"\n{'='*72}\n{label}: {len(findings)} probably-truncated recurring series\n{'='*72}")
    if not findings:
        print("  none — every weekly series looks fully captured.")
        return findings

    per_org = collections.Counter(f['org'] for f in findings)
    print("\n  worst orgs (likely a parser defect, not a library's schedule):")
    for org, n in per_org.most_common(10):
        print(f"    {n:3}  {org}")

    print("\n  detail:")
    for f in findings[:30]:
        print(f"\n  {f['org']} — {f['title'][:52]}")
        every = {7:'weekly',14:'biweekly',21:'every 3 wks',28:'monthly'}[f['cadence']]
        print(f"    {every}: captured {f['got']}/{f['expected']} ({f['fill']*100:.0f}%) over {f['span']}")
        gap = ', '.join(f['missing'][:8]) + (' ...' if len(f['missing']) > 8 else '')
        print(f"    missing dates: {gap}")
    if len(findings) > 30:
        print(f"\n  ... and {len(findings) - 30} more series")
    return findings


def main():
    ev = load_events()
    f1 = audit(ev, "LIVE SITE (index.html)")

    if len(sys.argv) > 1:
        rows = load_intake(sys.argv[1])
        f2 = audit(rows, f"INTAKE BATCH {sys.argv[1]}")
        # A series truncated in BOTH is the invisible case this tool exists for.
        live = {(f['org'], norm(f['title'])) for f in f1}
        both = [f for f in f2 if (f['org'], norm(f['title'])) in live]
        print(f"\n{'='*72}")
        print(f"TRUNCATED IN BOTH — {len(both)} series")
        print("  These are the ones no other check can see: the site and the sweep")
        print("  agree with each other, and both are missing the same weeks.")
        print(f"{'='*72}")
        for f in both[:20]:
            print(f"  {f['org'][:34]:34} {f['title'][:34]:34} {f['got']}/{f['expected']}")

    print("\nHoles are evidence, not proof — libraries do skip holiday weeks.")
    print("A series at 20-30% fill over a long span is a parser defect; check the")
    print("source's own calendar for one missing week before rescraping.")


if __name__ == '__main__':
    main()
