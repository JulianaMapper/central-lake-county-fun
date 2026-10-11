#!/usr/bin/env python3
"""
Find orgs that have upcoming events on the site but were NOT swept.

`stale_check.py` only judges orgs present in the intake batch ("an org nobody re-swept
tells us nothing"), so an org the sweep skipped entirely is invisible to it. That is
how Park District of Highland Park (55 live rows) and Highwood Public Library went
unswept on 2026-10-10 until Juliana asked. This is the complement: it asks "who did we
forget to look at?"

  python3 tools/coverage_check.py 2026-10-10

Reads intake/<stamp>/*.ndjson and EVENTS in index.html. Prints, per org, the number of
upcoming live events with zero intake rows. Nothing is modified.

How to read the output:
  * Free-day venues (Chicago museums, Botanic Garden, nature centers, Cook County FP)
    are NOT scraped — their rows come from museum_free_days_*.md / nature_center_hours_*.md.
    They always show up here; refresh them from those files.
  * "(community trick-or-treat hours)" rows are single static rows — refresh by hand.
  * Everything else is a real gap: find its calendar and sweep it.
  * Run it AFTER the scrapers finish and again after the gap-fill agents, until the
    remaining list is only the two groups above.
Org names are compared case-insensitively and exactly, so an org the scraper renamed
also shows up here — that is a feature (see the org-drift note in CLAUDE.md).
"""
import collections, glob, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import stale_check as s  # reuse load_events()

FREE_DAY = ('museum', 'planetarium', 'aquarium', 'botanic', 'art institute', 'field museum',
            'nature center', 'forest preserves of cook', 'department of natural resources',
            'kohl children', 'obama presidential')


def main(stamp):
    d = os.path.join(os.path.dirname(HERE), 'intake', stamp)
    swept = set()
    for f in glob.glob(os.path.join(d, '*.ndjson')):
        if os.path.basename(f).startswith('_'):
            continue
        for ln in open(f, encoding='utf-8'):
            if ln.strip():
                swept.add(json.loads(ln)['org'].strip().lower())
    if not swept:
        sys.exit('empty intake batch')
    today = stamp
    live = collections.Counter(e['org'] for e in s.load_events() if e['date'] >= today)
    gaps = sorted(((n, o) for o, n in live.items() if o.strip().lower() not in swept), reverse=True)
    groups = {'GAP': [], 'FREE-DAY / hours-file (not scraped)': [], 'static trick-or-treat rows': []}
    for n, o in gaps:
        if 'trick-or-treat hours' in o:
            groups['static trick-or-treat rows'].append((n, o))
        elif any(k in o.lower() for k in FREE_DAY):
            groups['FREE-DAY / hours-file (not scraped)'].append((n, o))
        else:
            groups['GAP'].append((n, o))
    print(f'{len(live)} orgs live; {len(gaps)} not in intake {stamp}\n')
    for g, items in groups.items():
        print(f'== {g}: {len(items)} orgs, {sum(n for n, _ in items)} events')
        if g != 'static trick-or-treat rows':
            for n, o in items:
                print(f'   {n:4} {o}')
        print()


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
