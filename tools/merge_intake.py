#!/usr/bin/env python3
"""
Merge intake/<date>/*.ndjson into the EVENTS array in index.html.

The intake files are what scrapers produce: what the page SAID, plus provenance.
This script owns every DERIVED field, so the canonical taxonomy and the
distance lookups cannot drift one scraper at a time.

  python3 tools/merge_intake.py 2026-07-31            # dry run, prints a full report
  python3 tools/merge_intake.py 2026-07-31 --write    # actually edit index.html

Adult-audience rows are NOT merged into EVENTS. They are written to
intake/<date>/_parked_adult.ndjson for the planned maker page.
"""
import json, re, sys, math, io, os, glob, collections, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, 'index.html')

# ── canonical taxonomy — MUST stay 1:1 with the .type-check chips in index.html
TYPES = ['Storytime','Craft / Art','Nature / Outdoors','Animals','Music / Performance',
         'Play / Drop-in','Movies','STEM / Discovery','Museums','Games & Clubs',
         'Free Meals / Food','Festivals / Celebrations','Movement / Sports',
         'Community Resources','Camps','Family Fun','Farmers Markets']

# first match wins — order is the rule, not an accident
TYPE_RULES = [
 ('Farmers Markets',      r'farmers?[ -]market|mercadito'),
 ('Free Meals / Food',    r'\blunch|\bmeals?\b|almuerzo|food pantry|breakfast|snack'),
 ('Storytime',            r'story\w*|\bstories\b|lapsit|\bbab(?:y|ies)\b|rhyme|cuento|'
                          r'hora del cuento|toddler time|bounce & books|\bsign with\b|'
                          r'\bread(?:ing)? (?:to|with)\b'),
 ('Movies',               r'\bmovies?\b|\bfilm\b|cinema|pel[íi]cula'),
 # Music BEFORE Festivals: "Sugar Skull! A Dia de Muertos Musical Adventure" is a
 # touring musical, not a festival.
 ('Music / Performance',  r'concert|\bmusic|\bband\b|\bsing\b|performance|theat(?:re|er)|musical|'
                          r'puppet|magic show|juggl|\bdrum|orchestra|symphony|\btunes?\b'),
 ('Festivals / Celebrations',
                          r'festival|\bfest\b|\bfair\b|celebrat|national night out|boo bash|'
                          r'trunk[ -]or[ -]treat|halloween|fireworks|parade|ofrenda|'
                          r'wicked wonderland|zinnia|anniversary party|\bparty\b'),
 ('Animals',              r'\banimals?\b|\bzoo\b|reptile|critter|\bbirds?\b|\bbugs?\b|insect|'
                          r'\bpets?\b|petting|llama|butterfl|dinosaur'),
 ('STEM / Discovery',     r'\bstem\b|science|scientist|robot|\blego\b|coding|tinkercad|tinker|'
                          r'3d print|engineer|experiment|\bmath\b|planetarium|telescope|'
                          r'fossil|\bspace\b|discovery (?:day|zone|lab)|little explorers'),
 ('Craft / Art',          r'\bcraft|\bart\b|\barts\b|maker|\bmake\b|painting|\bpaint\b|drawing|'
                          r'\bclay\b|pottery|\bsew|knit|crochet|granny square|macram|jewelry|'
                          r'manualidad|\bdiy\b|terracotta|\bcreate\b|collage|origami|workshop|'
                          r'\bcolor\b|colour'),
 ('Games & Clubs',        r'\bclub\b|\bgames?\b|chess|bingo|puzzle|trivia|pok[eé]mon|board game'),
 ('Movement / Sports',    r'\byoga\b|\bdance\b|fitness|\bsports?\b|\bswim|soccer|movement|zumba|'
                          r'\bfun run\b|\b5k\b|in motion|\bsteps?\b'),
 ('Nature / Outdoors',    r'\bnature\b|\bhike\b|\bwalk\b|\bgarden|\btrail|forest|\bbeach\b|'
                          r'outdoor|\bbees?\b|night sky|\bstars?\b|\bpark opening\b|'
                          r'muddy munchkins|al fresco|\bbay day\b'),
 ('Play / Drop-in',       r'\bplay\b|drop[- ]?in|open hours|open gym|playtime|sensory|stay & play|'
                          r'fine motor|open house|\btots?\b'),
 ('Community Resources',  r'resource|diaper|pantry|clinic|\bhealth\b|vaccin|legal|\bjob\b|'
                          r'community closet|sign up'),
 ('Camps',                r'\bcamps?\b'),
]

MUSEUM_ORG = r'museum|botanic garden|aquarium|planetarium|zoo\b|trolley|cantigny|art institute'

# A staged production at a performing-arts venue is Music / Performance, whatever
# its title says. "The True Story of the 3 Little Pigs" is a play, not a storytime.
VENUE_PERF = r'james lumber|mainstage|main stage|theat(?:re|er)|auditorium|civic center|performing arts'

def derive_type(name, notes='', org='', location=''):
    if re.search(VENUE_PERF, f"{location} {notes}".lower()):
        return 'Music / Performance'
    # Museums is an ORG-level call. "Burpee Museum Presents: Fossils" hosted at a
    # library is STEM, not Museums.
    if re.search(MUSEUM_ORG, (org or '').lower()):
        if re.search(r'free admission|admission day|free wednesday|open house|all aboard', name.lower()):
            return 'Museums'
    hay = f"{name} {notes}".lower()
    for t, pat in TYPE_RULES:
        if re.search(pat, hay):
            return t
    return 'Family Fun'          # residual bucket — keep it small

EMOJI = re.compile(r'[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F]')
def strip_emoji(s):
    return re.sub(r'\s{2,}', ' ', EMOJI.sub('', s)).strip(' -–—:')

def derive_time_of_day(time_str):
    t = (time_str or '').strip().lower()
    if not t or t in ('tba','tbd'): return 'All Day'
    if t.startswith('all day'):     return 'All Day'
    m = re.search(r'(\d{1,2})(?::(\d{2}))?\s*([ap])', t)
    if not m: return 'All Day'
    h = int(m.group(1)) % 12
    if m.group(3) == 'p': h += 12
    return 'Morning' if h < 12 else ('Afternoon' if h < 17 else 'Evening')

def derive_age_group(age, audience, name=''):
    a = f"{age} {name}".lower()
    if re.search(r'\bbab(?:y|ies)\b|\binfant|0-1|birth ?[-–] ?1|lapsit|0-12 ?month|newborn', a): return 'baby'
    if re.search(r'\btoddler|1-2|18 ?month|2-3\b|wiggl', a):                                     return 'toddler'
    if re.search(r'preschool|pre-?k|3-5|2-5|4-5|\bages? 3\b',  a):                               return 'preschool'
    if audience == 'family' or re.search(r'all ages|famil', a):                                   return 'family'
    return 'youth'

REG_MAP = {'yes':'Yes','no':'No','recommended':'Recommended','':'No',
           'check website':'Check website','required':'Yes','no registration':'No registration'}
def derive_reg(reg):
    return REG_MAP.get((reg or '').strip().lower(), 'Check website')

# ── distance wiring. Without these every new event falls back to 99 miles and
#    becomes invisible at every filter setting except "Any distance".
NEW_ZIP_CENTROIDS = {                     # Census geocoder, Public_AR_Current benchmark
    '60090': [42.133062, -87.946432],     # Wheeling
    '60050': [42.338848, -88.274682],     # McHenry
    '60071': [42.465082, -88.300060],     # Richmond
    '53168': [42.546464, -88.106279],     # Salem, WI
}
# org -> (zip, drive-time minutes). Drive times marked EST are estimates from
# straight-line distance; the others reuse a same-town value already in ORG_DRIVE.
NEW_ORG_ZIP = {
    'College of Lake County':                ('60030',  8),   # EST, Grayslake campus
    'Lake Bluff Park District':               ('60044', 20),   # EST
    'Zion Park District':                     ('60099', 22),   # EST
    'McHenry Public Library District':        ('60050', 25),   # EST
    'Cary Area Public Library':               ('60013', 28),   # EST
    'Highwood Public Library':                ('60040', 28),   # EST
    'Deerfield Park District':                ('60015', 30),   # matches Deerfield PL
    'Johnsburg Public Library District':      ('60051', 28),   # EST
    'Indian Trails Public Library District':  ('60090', 30),   # EST
    'Community Library (Salem Lakes, WI)':    ('53168', 28),   # EST
    'Palatine Public Library District':       ('60067', 30),   # EST
    'Crystal Lake Public Library':            ('60014', 32),   # EST
    'Nippersink District Library':            ('60071', 32),   # EST
    'Glencoe Public Library':                 ('60022', 35),   # EST
    # NOTE: these two strings must match the scrapers' `org` byte-for-byte.
    # "and" vs "&" here is what tripped the distance gate on the first run.
    'City of Lake Forest Parks and Recreation': ('60045', 25),  # matches Lake Forest Library
    'Village of Lincolnshire Parks & Recreation': ('60069', 22),  # EST
}
# pre-existing bug: this org resolves to no zip and no drive, so its events are
# hidden at the 10-mile default despite being in Grayslake.
FIX_ORG_ZIP = {'Grayslake Feed Sales': ('60030', 5)}


def hav(a, b):
    R = 3958.8
    dla, dlo = math.radians(b[0]-a[0]), math.radians(b[1]-a[1])
    x = math.sin(dla/2)**2 + math.cos(math.radians(a[0]))*math.cos(math.radians(b[0]))*math.sin(dlo/2)**2
    return R*2*math.atan2(math.sqrt(x), math.sqrt(1-x))

def read_js_obj(txt, name):
    s = re.search(r'const %s\s*=\s*(\{.*?\});' % name, txt, re.S).group(1).replace("'", '"')
    return json.loads(re.sub(r'([{,\s])([A-Za-z_]\w*)\s*:', r'\1"\2":', s))


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    stamp = sys.argv[1]
    write = '--write' in sys.argv
    intake_dir = os.path.join(ROOT, 'intake', stamp)

    txt = io.open(INDEX, encoding='utf-8').read()
    m_ev = re.search(r'(const EVENTS = )(\[.*?\])(;\n)', txt, re.S)
    EV = json.loads(m_ev.group(2))
    ZC = read_js_obj(txt, 'ZIP_CENTROIDS')
    ORG_ZIP = read_js_obj(txt, 'ORG_ZIP')
    ORG_DRIVE = read_js_obj(txt, 'ORG_DRIVE')

    # Late drop net: library-service and adult-civic rows that slipped past the
    # scrapers' own filters. Logged, never silent.
    LATE_DROP = re.compile(r'book (?:&|and)? ?media (?:flash )?sale|used book|book sale|'
                           r'friends of the library|curbside|notary|proctor', re.I)

    rows, parked, late = [], [], []
    for f in sorted(glob.glob(os.path.join(intake_dir, '*.ndjson'))):
        if os.path.basename(f).startswith('_'): continue
        for ln in io.open(f, encoding='utf-8'):
            if not ln.strip(): continue
            r = json.loads(ln)
            if LATE_DROP.search(r['name']):
                late.append(r); continue
            (parked if r.get('audience') == 'adult' else rows).append(r)

    print(f"intake {stamp}: {len(rows)} to merge, {len(parked)} adult rows parked")
    if late:
        print(f"  late-dropped {len(late)} library-service rows:")
        for r in sorted({x['name'] for x in late}): print(f"     - {r[:56]}")

    # ── dedupe against what is already live
    have = {(e['date'], e['name'].strip().lower(), e['org'].strip().lower()) for e in EV}
    fresh, dupes = [], 0
    seen = set()
    for r in rows:
        k = (r['date'], r['name'].strip().lower(), r['org'].strip().lower())
        if k in have or k in seen:
            dupes += 1; continue
        seen.add(k); fresh.append(r)
    print(f"  {dupes} already present or intra-batch duplicates -> {len(fresh)} new")

    # ── distance wiring
    ZC.update({z: c for z, c in NEW_ZIP_CENTROIDS.items() if z not in ZC})
    for org, (z, mins) in {**NEW_ORG_ZIP, **FIX_ORG_ZIP}.items():
        ORG_ZIP[org] = z
        ORG_DRIVE[org] = mins

    origin = ZC['60030']
    def miles(org, zipc):
        z = zipc or ORG_ZIP.get(org)
        return round(hav(origin, ZC[z]), 1) if z and z in ZC else 99.0

    # ── build event objects
    out = []
    for r in fresh:
        org = r['org']
        zipc = r.get('zip') or ORG_ZIP.get(org, '')
        out.append({
            'date': r['date'],
            'day': datetime.date.fromisoformat(r['date']).strftime('%A'),
            'time': r['time'] or 'TBA',
            'timeOfDay': derive_time_of_day(r['time']),
            'name': strip_emoji(r['name']),
            'type': derive_type(r['name'], r.get('notes', ''), org, r.get('location', '')),
            'org': org,
            'location': r.get('location', ''),
            'age': r.get('age', '') or 'Youth/Family',
            'ageGroup': derive_age_group(r.get('age', ''), r['audience'], r['name']),
            'cost': r.get('cost') or 'Free',
            'reg': derive_reg(r.get('reg')),
            'regStatus': '',
            'url': r.get('url', ''),
            'notes': r.get('notes', ''),
            'drive': ORG_DRIVE.get(org, 30),
            **({'zip': zipc} if zipc else {}),
        })

    # ── HARD GATE: nothing may resolve to the 99-mile fallback
    bad = [(e['org'], e['name']) for e in out if miles(e['org'], e.get('zip')) >= 99]
    if bad:
        print("\nABORT — these resolve to no real distance and would be invisible:")
        for o, n in sorted(set(bad))[:20]: print(f"   {o} :: {n[:50]}")
        sys.exit(1)
    print("  distance gate: OK (every merged event resolves to a real distance)")

    # ── report
    print("\n=== derived TYPE distribution ===")
    for t, n in collections.Counter(e['type'] for e in out).most_common():
        ex = next(e['name'] for e in out if e['type'] == t)
        assert t in TYPES, f"non-canonical type {t!r}"
        print(f"  {n:4d}  {t:26s} e.g. {ex[:46]}")
    print("\n=== derived ageGroup / timeOfDay ===")
    print("  ", dict(collections.Counter(e['ageGroup'] for e in out)))
    print("  ", dict(collections.Counter(e['timeOfDay'] for e in out)))
    print("\n=== per-org, with distance and how many land inside 10 mi ===")
    for org, n in collections.Counter(e['org'] for e in out).most_common():
        d = miles(org, next((e.get('zip') for e in out if e['org'] == org), None))
        print(f"  {n:4d}  {d:5.1f} mi  {'IN ' if d <= 10 else 'out'}  {org[:44]}")
    inside = sum(1 for e in out if miles(e['org'], e.get('zip')) <= 10)
    print(f"\n  {inside} of {len(out)} new events visible at the 10-mile default ({inside*100//max(len(out),1)}%)")
    print(f"  EVENTS: {len(EV)} -> {len(EV)+len(out)}")

    if not write:
        print("\nDRY RUN — nothing written. Re-run with --write to apply.")
        return

    # ── write
    if parked:
        p = os.path.join(intake_dir, '_parked_adult.ndjson')
        io.open(p, 'w', encoding='utf-8').write(
            '\n'.join(json.dumps(x, ensure_ascii=False) for x in parked) + '\n')
        print(f"\nparked {len(parked)} adult rows -> {os.path.relpath(p, ROOT)}")

    EV2 = EV + out
    txt = txt[:m_ev.start(2)] + json.dumps(EV2, ensure_ascii=False) + txt[m_ev.end(2):]
    for name, obj in (('ZIP_CENTROIDS', ZC), ('ORG_ZIP', ORG_ZIP), ('ORG_DRIVE', ORG_DRIVE)):
        mo = re.search(r'(const %s\s*=\s*)(\{.*?\})(;)' % name, txt, re.S)
        txt = txt[:mo.start(2)] + json.dumps(obj, ensure_ascii=False) + txt[mo.end(2):]
    io.open(INDEX, 'w', encoding='utf-8').write(txt)
    print(f"wrote index.html — EVENTS now {len(EV2)}")
    print("NOW RUN: python3 tools/check_syntax.py")


if __name__ == '__main__':
    main()
