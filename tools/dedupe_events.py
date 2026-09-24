#!/usr/bin/env python3
"""
Collapse near-duplicate rows already live in the EVENTS array of index.html.

  python3 tools/dedupe_events.py            # dry run, lists every pair it would merge
  python3 tools/dedupe_events.py --write    # actually edit index.html

Why this exists: merge_intake.py dedupes an incoming batch against what is live,
but nothing ever checked the live array against ITSELF. Rows that arrived by other
paths (hand edits, older sweeps) sat side by side as the same event twice:

  "DIY Stuffies"          5:30 PM - 6:30 PM   Waukegan PL   (type Animals)
  "DIY Stuffies - Grades K-5"  5:30pm - 6:30pm   Waukegan PL   (type Craft / Art)

Two rows are the SAME event when they share date + org + start time AND one
title's words are a subset of the other's (the longer one just adds an age band,
room, or subtitle). A shared URL alone is NOT enough — Fox Lake, Wauconda, Lake
Forest and Home Depot reuse one generic calendar link for many different events.
A shared URL only relaxes the subset rule to allow a one-word title
("Alebrijes" vs "Alebrijes - Ages 6-14 | Edades 6-14").

Parenthetical text is deliberately KEPT in the title tokens: "Jedi Training
(Pre-K–Grade 2)" and "Jedi Training (Grades 3-5)" are two sessions, not one.

qa_check.py imports find_duplicates() and fails the push if any remain.
"""
import collections, io, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, 'index.html')


def title_tokens(name):
    n = (name or '').lower()
    n = re.sub(r'\[[^\]]*\]', '', n)          # "[In Person]" is venue noise
    n = n.replace('’', "'")
    return frozenset(re.sub(r'[^a-z0-9]+', ' ', n).split())


def start_minute(t):
    t = (t or '').lower().strip()
    if not t or 'all day' in t:
        return 'allday'
    m = re.match(r'(\d{1,2})(?::(\d\d))?\s*([ap])?', t)
    if not m:
        return t
    h, mi, ap = int(m.group(1)), int(m.group(2) or 0), m.group(3)
    if not ap:                                 # "5:30 - 6:30 PM" -> take the later am/pm
        m2 = re.search(r'([ap])\.?m', t)
        ap = m2.group(1) if m2 else None
    if ap == 'p' and h < 12:
        h += 12
    if ap == 'a' and h == 12:
        h = 0
    return h * 60 + mi


def is_same(x, y, url_count):
    a, b = title_tokens(x['name']), title_tokens(y['name'])
    if not a or not b:
        return False
    if a == b:
        return True
    small, big = (a, b) if len(a) <= len(b) else (b, a)
    if not small <= big:
        return False
    if len(small) >= 2:
        return True
    # one-word title: only when the two rows point at the same, event-specific URL
    u = x.get('url')
    return bool(u) and u == y.get('url') and url_count[(x['date'], u)] == 2


def find_duplicates(EV):
    """Return clusters (lists of indexes into EV), each cluster = one real event."""
    url_count = collections.Counter((e['date'], e.get('url')) for e in EV if e.get('url'))
    groups = collections.defaultdict(list)
    for i, e in enumerate(EV):
        groups[(e['date'], e['org'].strip().lower(), start_minute(e.get('time')))].append(i)
    clusters = []
    for idx in groups.values():
        if len(idx) < 2:
            continue
        parent = {i: i for i in idx}
        def root(i):
            while parent[i] != i:
                i = parent[i]
            return i
        for p in range(len(idx)):
            for q in range(p + 1, len(idx)):
                if is_same(EV[idx[p]], EV[idx[q]], url_count):
                    parent[root(idx[q])] = root(idx[p])
        by_root = collections.defaultdict(list)
        for i in idx:
            by_root[root(i)].append(i)
        clusters += [c for c in by_root.values() if len(c) > 1]
    return clusters


def merge_cluster(rows):
    """Keep the most descriptive title as the base; fill its blanks from the others.

    The longer-titled row is the newer merge_intake row in practice, so its
    derived fields (type, ageGroup) come from the canonical taxonomy — e.g. it
    files DIY Stuffies under Craft / Art, where the older row had Animals.
    """
    rows = sorted(rows, key=lambda r: (-len(title_tokens(r['name'])), -len(r['name'])))
    base = dict(rows[0])
    for other in rows[1:]:
        for k, v in other.items():
            if v not in (None, '') and base.get(k) in (None, ''):
                base[k] = v
    return base


def main():
    write = '--write' in sys.argv
    txt = io.open(INDEX, encoding='utf-8').read()
    m = re.search(r'(const EVENTS = )(\[.*?\])(;\n)', txt, re.S)
    EV = json.loads(m.group(2))

    clusters = find_duplicates(EV)
    drop, replace = set(), {}
    for c in sorted(clusters, key=lambda c: EV[c[0]]['date']):
        keep = min(c)                          # keep the row's original position
        replace[keep] = merge_cluster([EV[i] for i in c])
        drop.update(i for i in c if i != keep)
        print(f"{EV[keep]['date']}  {EV[keep]['org'][:26]:26}  -> {replace[keep]['name'][:60]}")
        for i in c:
            print(f"      x {EV[i]['name'][:60]:60}  {EV[i].get('time', '')}")

    out = [replace.get(i, e) for i, e in enumerate(EV) if i not in drop]
    print(f"\n{len(clusters)} duplicate clusters, {len(drop)} rows removed: EVENTS {len(EV)} -> {len(out)}")
    if not write:
        print("DRY RUN — nothing written. Re-run with --write to apply.")
        return
    txt = txt[:m.start(2)] + json.dumps(out, ensure_ascii=False, separators=(',', ':')) + txt[m.end(2):]
    io.open(INDEX, 'w', encoding='utf-8').write(txt)
    print("index.html written.")


if __name__ == '__main__':
    main()
