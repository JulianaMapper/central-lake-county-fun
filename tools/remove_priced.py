#!/usr/bin/env python3
"""
Enforce the FREE-ONLY rule on the live EVENTS array (Juliana, 2026-10-10: "if there's a
price then we remove it").

  python3 tools/remove_priced.py            # dry run: counts + sample, nothing written
  python3 tools/remove_priced.py --write    # remove them, saving the list for revert

Removes upcoming events whose `cost` states a price, EXCEPT:
  * homeschool events (CLAUDE.md 2026-08-04: homeschool keeps its real price)
  * anything whose cost STARTS with "Free" (free entry with optional paid extras, "Free for
    residents / $5 non-resident", "Free (Early Bird $10 or a new toy)") — the event is free
  * blank / "Check website" costs (price unknown is not a price)
Past events are left alone. The removed rows are written to
intake/<date>/_removed_priced.json so a mistake is one `git checkout` / re-add away.

Run it AFTER every merge_intake --write: scrapers legitimately record the price of paid
events, and this is the step that keeps them off the calendar. It does not touch the
Fall Fun tab (FALL_PLACES — paid venues are intended there) or the PARKS map.
"""
import datetime, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, 'index.html')
PRICE = re.compile(r'\$\s?\d|\b(paid|fee|admission|ticket)\b|\d+\s*/\s*\d+', re.I)


def is_priced(e):
    c = (e.get('cost') or '').strip()
    if not c or re.match(r'free\b', c, re.I):
        return False
    return bool(PRICE.search(c))


def is_homeschool(e):
    t = ' '.join([e.get('name', ''), e.get('age', ''), e.get('notes', '')]).lower()
    return 'homeschool' in t or 'home school' in t or e.get('audience') == 'homeschool'


def main(write):
    s = open(INDEX, encoding='utf-8').read()
    m = re.search(r'(const EVENTS\s*=\s*\[)(.*?)(\];\s*\n?\s*const PARKS)', s, re.S)
    today = datetime.date.today().isoformat()
    gone = []

    def sub(x):
        try:
            o = json.loads(x.group(0))
        except Exception:
            return x.group(0)
        if o.get('date', '') >= today and is_priced(o) and not is_homeschool(o):
            gone.append(o)
            return '\x00'
        return x.group(0)

    body = re.sub(r'\{[^{}]*\}', sub, m.group(2))
    print(f'{len(gone)} upcoming priced (non-homeschool) events {"removed" if write else "would be removed"}')
    by = {}
    for o in gone:
        by[o['org']] = by.get(o['org'], 0) + 1
    for org, n in sorted(by.items(), key=lambda kv: -kv[1])[:15]:
        print(f'   {n:4} {org}')
    if not write:
        print('DRY RUN — nothing written. Re-run with --write.')
        return
    body = re.sub(r'\s*\x00\s*,', '', body)
    body = re.sub(r',\s*\x00', '', body)
    body = body.replace('\x00', '')
    open(INDEX, 'w', encoding='utf-8').write(s[:m.start(2)] + body + s[m.end(2):])
    out = os.path.join(ROOT, 'intake', today, '_removed_priced.json')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    prev = json.load(open(out, encoding='utf-8')) if os.path.exists(out) else []
    seen = {(o['org'], o['date'], o['name']) for o in prev}
    prev += [o for o in gone if (o['org'], o['date'], o['name']) not in seen]   # append, never overwrite
    json.dump(prev, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print('saved', out)


if __name__ == '__main__':
    main('--write' in sys.argv)
