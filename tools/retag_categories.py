#!/usr/bin/env python3
"""Re-tag event types into the canonical 14-category taxonomy (2026-06-03).

Canonical categories:
  Storytime, Craft / Art, Nature / Outdoors, Animals, Music / Performance,
  Play / Drop-in, Movies, STEM / Discovery, Games & Clubs, Free Meals / Food,
  Festivals / Celebrations, Movement / Sports, Community Resources, Camps
  (+ Family Fun as the residual bucket, kept small)

Applies to:
  - index.html EVENTS array (rewrites "type" on each event line)
  - ../library_events_2026_summer.csv          (Type column)
  - ../library_events_2026_summer_CLOSE.csv    (Type column)
  - ../library_events_2026_summer_SHAREABLE.csv (Type column)

Run from the repo root:  python3 tools/retag_categories.py
"""
import csv, json, re, collections, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.dirname(ROOT)

# ---- direct type→category map (types that are already unambiguous) ----
TYPE_MAP = {
    'Storytime': 'Storytime', 'Book/Author': 'Storytime', 'Reading': 'Storytime',
    'Craft': 'Craft / Art', 'Craft/Art': 'Craft / Art', 'Art/Craft': 'Craft / Art',
    'Nature/Outdoors': 'Nature / Outdoors', 'Nature/Program': 'Nature / Outdoors',
    'Nature/Hike': 'Nature / Outdoors', 'Fishing': 'Nature / Outdoors',
    'Animals': 'Animals',
    'Concert': 'Music / Performance', 'Concert/Music': 'Music / Performance',
    'Concert/Performance': 'Music / Performance', 'Performance': 'Music / Performance',
    'Play/Drop-in': 'Play / Drop-in', 'Drop-in/Play': 'Play / Drop-in', 'Play': 'Play / Drop-in',
    'Movie': 'Movies', 'Movie/Show': 'Movies',
    'STEM': 'STEM / Discovery', 'STEAM': 'STEM / Discovery', 'Class/Education': 'STEM / Discovery',
    'Games': 'Games & Clubs', 'Game': 'Games & Clubs', 'Club': 'Games & Clubs',
    'Free Meal': 'Free Meals / Food',
    'Festival': 'Festivals / Celebrations', 'Festival/Fair': 'Festivals / Celebrations',
    'Festival/Fireworks': 'Festivals / Celebrations', 'Parade': 'Festivals / Celebrations',
    'Fireworks': 'Festivals / Celebrations', 'Halloween': 'Festivals / Celebrations',
    'Holiday': 'Festivals / Celebrations', 'Market': 'Festivals / Celebrations',
    'Community Event': 'Festivals / Celebrations', 'Community': 'Festivals / Celebrations',
    'Movement': 'Movement / Sports', 'Movement/Yoga': 'Movement / Sports',
    'Swim/Water': 'Movement / Sports', 'Bike': 'Movement / Sports',
    'Camp': 'Camps',
    'Library Outreach': 'Community Resources',
    'Meeting (skip)': 'Skip (adult/civic)', 'Civic Ceremony': 'Skip (adult/civic)',
}

# ---- name-based rules for ambiguous types (Program, Other, Family*, Social) ----
# Ordered: first match wins.
NAME_RULES = [
    ('Skip (adult/civic)', r'board meeting|board committee|committee of the whole|park board|trustee|brews\s*&\s*views|will run for beer|snap focus|seed library|civic minded|homeschooling: where do i begin|legal services'),
    ('Camps',              r'\bcamp\b(?!fire)'),
    ('Community Resources', r'vision screening|diaper|resource exchange|recycling|library on the go|biblioteca en movimiento|birth to five|focus group|blood drive'),
    ('Storytime',          r'story|wonderful ones|super babies|babies, books|bounce\s*&\s*books|books and bounces|kinder ready|wondertime|dual language|little kids, big feelings|early learners|friday family fun|family rock|tots on the loose|baby|toddler'),
    ('Animals',            r'animal|zoo|reptile|critter|bird|butterfly|insect|\bbug\b|petting|wildlife|read to a dog|good boy|bow wow|\bdogs?\b|dino|t-?rex|frogs'),
    ('Games & Clubs',      r'bingo|trivia|pok[eé]mon|chess|escape room|gaming|lotería|loteria|game night'),
    ('STEM / Discovery',   r'stem|science|lego|robot|code|engineer|3d print|kohl|museum|space|telescope|virtual tour|discovery|planetarium'),
    ('Music / Performance', r'music|concert|sing|drum|band|magic|juggler|hoofer|puppet|dance party|performer'),
    ('Free Meals / Food',  r'lunch|meal|snack|breakfast|food truck|cookout|pastry|ice cream'),
    ('Festivals / Celebrations', r'fest|fair|carnival|parade|celebration|firework|touch[ -]a[ -]truck|night out|kick[ -]?off|neighborhood nights|expo|car fun|birthday bash|memorial day|juneteenth|night live'),
    ('Movement / Sports',  r'yoga|skate|sports|swim|lazy river|triathlon|waterpark|movement|zumba|kickin|bobbers'),
    ('Nature / Outdoors',  r'nature|hike|trail|garden|outdoor|preserve|\bbee\b|web of life|fish|seed|flower|stroll|campfire'),
    ('Craft / Art',        r'craft|\bart\b|paint|tie dye|mural|jewelry|bookmark|cards|make[ -]?and|project of the week'),
    ('Play / Drop-in',     r'play|drop-in|open gym|sensory|mud kitchen'),
    ('Movies',             r'movie|film'),
]

CANONICAL = ['Storytime', 'Craft / Art', 'Nature / Outdoors', 'Animals',
             'Music / Performance', 'Play / Drop-in', 'Movies', 'STEM / Discovery',
             'Museums', 'Games & Clubs', 'Free Meals / Food', 'Festivals / Celebrations',
             'Movement / Sports', 'Community Resources', 'Camps', 'Family Fun']


def classify(ev_type, name):
    t = (ev_type or '').strip()
    if t in TYPE_MAP:
        return TYPE_MAP[t]
    if t in CANONICAL:
        return t
    n = (name or '').lower()
    for cat, rx in NAME_RULES:
        if re.search(rx, n):
            return cat
    return 'Family Fun'


def retag_html(path):
    out, counts, skips = [], collections.Counter(), []
    with open(path) as f:
        lines = f.readlines()
    for line in lines:
        s = line.strip().rstrip(',')
        if s.startswith('{"date"'):
            try:
                e = json.loads(s)
            except Exception:
                out.append(line)
                continue
            new = classify(e.get('type'), e.get('name'))
            if new == 'Skip (adult/civic)':
                skips.append(f"{e['date']}  {e['name']}  [{e['org']}]")
            counts[new] += 1
            if new != e.get('type') and new != 'Skip (adult/civic)':
                e['type'] = new
                trail = ',' if line.rstrip().endswith(',') else ''
                indent = line[:len(line) - len(line.lstrip())]
                line = indent + json.dumps(e, ensure_ascii=False, separators=(', ', ': ')) + trail + '\n'
        out.append(line)
    with open(path, 'w') as f:
        f.writelines(out)
    return counts, skips


def retag_csv(path):
    if not os.path.exists(path):
        return None
    with open(path, newline='') as f:
        rdr = csv.reader(f)
        rows = list(rdr)
    hdr = rows[0]
    ti, ni = hdr.index('Type'), hdr.index('Event Name')
    counts = collections.Counter()
    for r in rows[1:]:
        if len(r) <= max(ti, ni):
            continue
        new = classify(r[ti], r[ni])
        counts[new] += 1
        r[ti] = new
    with open(path, 'w', newline='') as f:
        csv.writer(f).writerows(rows)
    return counts


if __name__ == '__main__':
    print('=== index.html ===')
    counts, skips = retag_html(os.path.join(ROOT, 'index.html'))
    for c in CANONICAL:
        if counts[c]:
            print(f'  {counts[c]:4d}  {c}')
    if skips:
        print(f'\n  {len(skips)} adult/civic events flagged (NOT removed — pending approval):')
        for s in skips:
            print('   ', s)
    for name in ['library_events_2026_summer.csv',
                 'library_events_2026_summer_CLOSE.csv',
                 'library_events_2026_summer_SHAREABLE.csv']:
        p = os.path.join(LIB, name)
        c = retag_csv(p)
        if c is not None:
            print(f'\n=== {name} ===')
            for cat in CANONICAL + ['Skip (adult/civic)']:
                if c[cat]:
                    print(f'  {c[cat]:4d}  {cat}')
