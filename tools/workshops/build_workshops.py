"""Build the Grown-Up Workshops tab data and write it into index.html.

    python3 tools/workshops/build_workshops.py          # dry run: prints the rows
    python3 tools/workshops/build_workshops.py --write  # rewrites the WORKSHOPS block in index.html

Reads the pulls in tools/workshops/data/ (see README.md for how each was made), keeps the
hand-picked one-time adult workshops, attaches distance zip / card rule / seats / registration-
open date, and replaces everything between the WORKSHOPS-DATA-START/END markers in index.html.
"""
import datetime, json, html, os, re, sys, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
SP = os.path.join(HERE, 'data')
INDEX = os.path.join(HERE, '..', '..', 'index.html')
lib = json.load(open(f'{SP}/libnet_out.json'))
tri = json.load(open(f'{SP}/tribe_out.json'))

PICK = """Calavera Creations|Cricut Basics - RO|Fall Décor|Stamp Carving (Age 13-Adult)|Alcohol Ink Art|Intro to Diamond Art: Bookmark|
Sewing Basics:  Sunflower Pin Cushion|Bad Art: Watercolor Gone Wrong|Leather Bell Key Holder (Age 13-Adult)|DIY Key Chains|Pour Paint Snowflakes|
Christmas Tree Workshop|Sewing Machine Basics (Age 13-Adult)|Jewelry: Pearl Pendant (Age 18+)|Feel Good Art|Holiday Print Cards|
The Sybil van Antwerp Stationery Studio - RO|Egyptian Hieroglyphic Art Class - RO|Sewing: Bottle Gift Bag - RR|Álbum de Recortes con Fotos|
Wood and Resin Earrings (Age 13-Adult)|3D Printed Holiday Ornament - RO|Merry Hanger - RO|Crafting Herb Blends|
Monogrammed Throw Blankets|Happy Little Accidents|Collage Your Year in Books - RO|UV Resin Ornament|
Embroidered Cards Session 1|Gingerbread House Competition|Cake Decorating 101 - RO|Craftivism 101 - RO|Cards and Cookies|
Deck the Halls: Jumbo Ornament Workshop|Islamic Glass Painting Workshop|Winter Lights Book-Fold Candle|Let It Snow Wood Painting|
"Let It Snow" Sled - RO|Visible Mending Workshop|Crochet 101|Jewelry: Artisan Ring (Age 18+)|3D Printed Pocket Junk Tray - RO|
ArtWauk: Paint and Sip Cider|Ela Library Quilt Talks - FABRIC WORKSHOP DAY|Valentines Stack - RO|Jewelry: Hoop Earrings (Age 18+)|
Introduction to Brush Pen Calligraphy|Laser Etched Maps (Age 13-Adult)|Bordado sobre fotografía|Portraits at The Chalice - RO|
Handcrafted Cards - RR|Intro to Quilting - RR|Make @ Eastgate: Holiday Watercolors - RR|Make @ Eastgate: String Art Snowflake - RR|
Make @ Eastgate: Tea-Riffic Thank You Gift - RR|Sewing: Bottle Gift Bag - RO|Rustic Autumn Wreath|Felt Wreaths|Rangoli Art|
Crafternoon: Fall Themed Mini Cutting Board|Crafternoon: Holiday Wood Block Decoration|Crafting with Cricut: Napkin Rings or Placecards|
Crafting With Cricut: Garland or Gift Tags|Festive Throw Pillows|Holiday Napkins|Knitting for Beginners|Quality Watercolor Techniques|
Paint and Steep Tea|Glass Fusion: Lantern Panels (Age 13-Adult)|Water Marbling|Personaliza una Bolsa de Tela|Fall Quill Wreath|Sewing Basics|
Cricut for Beginners: Sticker Making|Learn to Sew"""
picks = {p.strip() for p in PICK.replace('\n', '').split('|')}
TPICK = {'Learn to Sew Workshop', 'BASE: Create', 'Natural Christmas Wreaths'}

def clean(n):
    n = html.unescape(n).strip()
    n = re.sub(r'\s+-\s+(RO|RR|NR)$', '', n)        # Algonquin branch codes
    n = n.replace('Session 1', '(2 sessions)')
    return re.sub(r'\s+', ' ', n)

# Library-wide registration rule: 'own' = must hold that library's card, 'open' = anyone can register.
# Filled from each library's own policy page; a library missing here shows "not stated".
LIB_RULE = json.load(open(os.path.join(HERE, 'lib_rules.json')))

def card_rule(e):
    t = e.get('card_text', '')
    if t and not re.search(r'check (it )?out|bring home', t, re.I):   # Algonquin's "*AAPLD card required" is for Cricut checkout
        return 'own', t
    for k, (rule, quote) in LIB_RULE.items():
        if e['org'].startswith(k):
            return rule, quote
    return 'unknown', ''

rows = []
for e in lib:
    if e['name'].strip() in picks:
        rule, note = card_rule(e)
        left = e['max'] - e['taken'] if e.get('max') else None
        rows.append(dict(date=e['date'], time=e['time'], name=clean(e['name']), org=e['org'],
                         where=e['location'], cost=e['cost'], reg=e['reg'], opens=e['reg_opens'],
                         url=e['url'], desc=e['desc'], card=rule, cardNote=note,
                         left=max(left, 0) if left is not None else None, waitlist=e.get('waitlist', False)))
for e in tri:
    if any(e['name'].startswith(k) or html.unescape(e['name']).startswith(k) for k in TPICK):
        rows.append(dict(date=e['date'], time='', name=clean(e['name']), org=e['org'], where='',
                         cost=html.unescape(e['cost']) or 'Cost unconfirmed – check website',
                         reg='Yes', opens='', url=e['url'], desc=html.unescape(e['desc'])[:300]))
MICH = 'https://www.michaels.com/events-and-services'
def m(date, time, name, desc, cost='Free'):
    return dict(date=date, time=time, name=name, org='Michaels Gurnee', where='Stonebrook Commons, 6635 Grand Ave',
                cost=cost, reg='No', opens='', url=MICH, desc=desc)
rows += [
    m('2026-11-01', '1:00pm - 3:00pm', 'Hand-Stitched Holiday Card', 'Use yarn and foam to make an embroidered holiday card. Free, in-store.'),
    m('2026-11-07', '10:00am - 12:00pm', 'Hallmark Holiday Workshop: Vintage Ornaments', 'Part 1 of Michaels x Hallmark "Countdown to Craftsmas". Free, in-store.'),
    m('2026-11-07', '1:00pm - 3:00pm', 'Hallmark Holiday Workshop: Paint-Scraped Greeting Cards', 'Part 2: custom holiday card with masking tape and paint-scraping. Free, in-store.'),
    m('2026-11-08', '1:00pm - 3:00pm', 'Hallmark-Inspired Holiday Ornament', 'Free, in-store.'),
    m('2026-11-15', '1:00pm - 3:00pm', 'Cookie Cutter Clay Ornaments', 'Custom clay ornaments with cookie cutters, paint and foliage for texture. Free, in-store.'),
    m('2026-12-06', '1:00pm - 3:00pm', 'Handknit Yarn Muff', 'Pick out and buy a skein, then learn to make a cozy muff in under 10 minutes.', 'Free class (you buy the yarn)'),
    m('2026-12-13', '1:00pm - 3:00pm', 'Holiday Junk Journal', 'Basic supplies provided; bring or buy anything you want to add.'),
    dict(date='2026-11-07', time='8:30am - 11:00am', name='Needlepoint Decorative Stitch Class: Chicago Angel',
         org='Third Coast Stitches (Old Town Chicago, ~65 min)', where='1365 N Wells St', cost='$190', reg='Yes', opens='',
         url='https://www.thirdcoaststitches.com/products/decorative-stitch-class-chicago-angel',
         desc='Learn 4-way continental, criss-cross Hungarian, beading with sequins, satin stitch, French knots and turkey work. Canvas and threads included.'),
    dict(date='2026-11-11', time='6:00pm - 8:00pm', name='Beginner Needlepoint Class with Ellen',
         org='Velvet Stitch House (Evanston, ~45 min)', where='2114 Central St', cost='$90', reg='Yes', opens='',
         url='https://velvetstitchhouse.com/products/beginner-class-with-ellen-11-11-26',
         desc='First needlepoint piece from threading the needle on. Beginner canvas, thread and needle included.'),
    dict(date='2026-11-17', time='10:00am - 12:00pm', name='Beginner Needlepoint Class with Ellen',
         org='Velvet Stitch House (Evanston, ~45 min)', where='2114 Central St', cost='$90', reg='Yes', opens='',
         url='https://velvetstitchhouse.com/products/beginner-class-with-ellen-11-17-26',
         desc='First needlepoint piece from threading the needle on. Beginner canvas, thread and needle included.'),
    dict(date='2026-12-08', time='10:00am - 12:00pm', name='Beginner Needlepoint Class with Ellen',
         org='Velvet Stitch House (Evanston, ~45 min)', where='2114 Central St', cost='$90', reg='Yes', opens='',
         url='https://velvetstitchhouse.com/products/beginner-class-with-ellen-12-8-26-daytime',
         desc='First needlepoint piece from threading the needle on. Beginner canvas, thread and needle included.'),
    dict(date='2026-12-09', time='6:00pm - 7:00pm', name='Holiday Candle Making Class with Betsy Jane Candles',
         org='Velvet Stitch House (Evanston, ~45 min)', where='2114 Central St', cost='$50', reg='Yes', opens='',
         url='https://velvetstitchhouse.com/products/holiday-candle-making-class-with-betsy-jane-candles',
         desc='One-hour candle-making evening. Ticket includes all materials. RSVP required.'),
    dict(date='2027-01-16', time='9:00am - 12:00pm', name='The Finishing Fairy: Rounds & Rectangle Ornaments Class',
         org='Velvet Stitch House (Evanston, ~45 min)', where='2114 Central St', cost='$165', reg='Yes', opens='',
         url='https://velvetstitchhouse.com/products/the-finishing-fairy-rounds-rectangle-ornaments-class',
         desc='Finish your own needlepoint ornament with a no-glue lacing technique. No finishing experience needed. Bring a completed needlepoint piece.'),
]
# Antioch PLD (LibCal, not libnet). Registration-open date lives in the title: "… Registration begins Oct 15 at 6PM".
MON = {m: i for i, m in enumerate('Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split(), 1)}
APICK = re.compile(r'Paint N Sip|Sewing Machine 101|Cricut 101|DIY Soap|Mini Planters', re.I)
for e in json.load(open(f'{SP}/antioch_raw.json')):
    if not APICK.search(e['title']) or 'CANCELLED' in e['title'].upper():
        continue
    # The title's date can be stale (Candy Cane title says Oct 27; page says Nov 5) -- trust the event page.
    page = urllib.request.urlopen(urllib.request.Request(e['url'], headers={'User-Agent': 'Mozilla/5.0 Chrome/124'}), timeout=40).read().decode('utf8', 'ignore')
    m = re.search(r'Registrations open at\s+[\d:apm]+\s+\w+,\s+(\w+)\s+(\d+),\s+(\d{4})', page)
    if m:
        opens = f"{m.group(3)}-{MON[m.group(1)[:3]]:02d}-{int(m.group(2)):02d}"
    else:   # already open: the page no longer shows it, fall back to the title
        m = re.search(r'Registration (?:begins|opens) (\w{3}) (\d+)', e['title'], re.I)
        opens = f"2026-{MON[m.group(1).title()]:02d}-{int(m.group(2)):02d}" if m else ''
    seats = e.get('seatsleft_text') or ''
    desc = html.unescape(re.sub(r'\s+', ' ', re.sub('<[^>]+>', ' ', e['description']))).strip()
    desc = re.sub(r'\s*Please fill out this waiver.*$', '', desc)
    rows.append(dict(date=e['startdt'][:10],
                     time=f"{e['fromTime'].split()[0]} - {e['toTime'].split()[0]}",
                     name=re.sub(r'\s*-?\s*Registration (begins|opens).*$', '', e['title'], flags=re.I).strip(),
                     org='Antioch PLD', where='The Workshop', cost='Free', reg='Yes', opens=opens,
                     url=e['url'], desc=desc,
                     left=int(m2.group(1)) if (m2 := re.match(r'(\d+) seats? left', seats)) else None, waitlist=False,
                     card='priority', cardNote='Policy: "All Library programs are open to the public"; for limited programs, Antioch residents may be given priority. The sign-up form asks only name, email and phone (checked 10/29).'))

# Tribe rows were pulled without times; add them (from each org's Tribe API, 2026-10-29).
TRIBE_FIX = {'BASE: Create': dict(time='7:00pm - 9:00pm', where='Brushwood Center at Ryerson Woods, 21850 Riverwoods Rd'),
             'Natural Christmas Wreaths': dict(time='6:00pm - 7:00pm', where='Bevier Park, 2255 W Yorkhouse Rd')}
for r in rows:
    for k, v in TRIBE_FIX.items():
        if r['name'].startswith(k):
            r.update(v)

# Libraries within 10 mi on other platforms (librarycalendar.com day feed; North Chicago Tribe API) -- see maker_lc.py
rows += [r for r in json.load(open(f'{SP}/extra_libs.json')) if 'November Crafts' not in r['name']]


# Added 2026-10-31 from the sweep's parked adult rows (intake/2026-10-31/_parked_adult.ndjson): libraries on platforms the
# fetchers do not cover (Palatine, Highwood, Cary, Lake Bluff, McHenry, Vernon Area, Kenosha, Community Library WI, Fox Lake)
# and park districts / farms with paid classes. 'left': 0 = the event page said Full on 2026-10-31.
def h(date, time, name, org, where, cost, url, desc, reg='Yes', left=None, card='unknown', note=''):
    return dict(date=date, time=time, name=name, org=org, where=where, cost=cost, reg=reg, opens='', url=url, desc=desc,
                card=card, cardNote=note, left=left, waitlist=False)
CU = 'Cost unconfirmed – check website'
# One-time adult classes found by web search (Antioch Art Center etc.): intake/2026-10-31/websearch2-adult-workshops.ndjson
_ws = os.path.join(HERE, '..', '..', 'intake', '2026-10-31', 'websearch2-adult-workshops.ndjson')
if os.path.exists(_ws):
    for _l in open(_ws):
        if not _l.strip(): continue
        _r = json.loads(_l)
        _p = _r.get('price') or _r.get('cost') or CU
        rows.append(h(_r['date'], re.sub(r'(AM|PM)', lambda m_: m_.group(1).lower(), _r['time']), re.sub(r'\s*\(.*?\)\s*$', '', _r['name']),
                      _r['org'], _r['location'].split(',')[0],
                      _p.split(' (')[0] if _p.startswith('$') else _p, _r['url'],
                      (_r['raw'] + ' ' + _r.get('who_may_attend', '') + '. ' + _r.get('register_how', '')).strip()[:300]))
rows += [
    h('2026-12-21', '3:00pm - 4:00pm', 'Gnome for the Holidays', 'Fox Lake District Library', 'Large Meeting Room', 'Free', 'https://www.fllib.org/event/gnome-holidays-5339',
      'Paint and decorate a wood triangle into a winter gnome to bring home. Registration required, space limited.'),
    h('2026-11-03', '11:00am - 11:30am', 'Cricut Activity: Seasonal Potholders', 'Palatine PL', 'Rand Road Branch', 'Free', 'https://www.palatinelibrary.org/event/cricut-activity-seasonal-potholders-cricut-activity-agarradores-de-ollas-para-la-temporada', 'Cricut project, adults. Registration required.', left=0),
    h('2026-11-09', '11:00am - 1:00pm', 'Laser Activity: Etched Pint Glasses', 'Palatine PL', 'Workshop Lab, Main Library', 'Free', 'https://www.palatinelibrary.org/event/laser-activity-etched-pint-glasses-234937', 'Laser-etch a pint glass in the Workshop Lab. Registration required.', left=0),
    h('2026-11-09', '3:00pm - 5:00pm', 'Laser Activity: Etched Pint Glasses', 'Palatine PL', 'Workshop Lab, Main Library', 'Free', 'https://www.palatinelibrary.org/event/laser-activity-etched-pint-glasses-234937', 'Laser-etch a pint glass in the Workshop Lab. Registration required.', left=0),
    h('2026-11-20', '11:00am - 1:00pm', 'Cricut Activity: Holiday Cards', 'Palatine PL', 'Workshop Lab, Main Library', 'Free', 'https://www.palatinelibrary.org/event/cricut-activity-holiday-cards-234941', 'Make holiday cards with the Cricut. Registration required.'),
    h('2026-11-20', '2:00pm - 4:00pm', 'Cricut Activity: Holiday Cards', 'Palatine PL', 'Workshop Lab, Main Library', 'Free', 'https://www.palatinelibrary.org/event/cricut-activity-holiday-cards-234941', 'Make holiday cards with the Cricut. Registration required.'),
    h('2026-12-02', '1:00pm - 3:00pm', 'Snowman Hand Warmer', 'Palatine PL', 'Rand Road Room, Rand Road Branch', 'Free', 'https://www.palatinelibrary.org/event/snowman-hand-warmer-242831', 'Sew a snowman hand warmer. Registration required.'),
    h('2026-12-04', '11:00am - 1:00pm', 'Snowman Hand Warmer', 'Palatine PL', 'Workshop Lab, Main Library', 'Free', 'https://www.palatinelibrary.org/event/snowman-hand-warmer-238877', 'Sew a snowman hand warmer. Registration required.'),
    h('2026-12-08', '1:00pm - 3:00pm', 'Snowman Hand Warmer', 'Palatine PL', 'Palatine Public Library', 'Free', 'https://www.palatinelibrary.org/event/snowman-hand-warmer-242832', 'Sew a snowman hand warmer. Registration required.'),
    h('2026-11-07', '10:30am - 11:30am', 'Art Workshop for Adults: Felt Pies', 'Highwood PL', 'Highwood Library & Community Center, 102 Highwood Ave', 'Free', 'https://highwoodlibrary.org/events/art-workshop-for-adults-felt-pies-taller-de-arte-para-adultos-tartas-de-fieltro', 'Free hands-on art workshop, all experience levels. Registration required. Bilingual (English/Spanish).'),
    h('2026-11-11', '6:00pm - 7:30pm', 'Art Workshop for Adults: Crochet (guided instruction)', 'Highwood PL', 'Highwood Library & Community Center, 102 Highwood Ave', 'Free', 'https://highwoodlibrary.org/events/art-workshop-for-adults-crochet-taller-de-arte-para-adultos-tejido-con-gancho-7', 'Free hands-on art workshop, all experience levels. Registration required. Bilingual (English/Spanish).'),
    h('2026-11-17', '5:15pm - 6:15pm', 'Art Workshop for Adults: Glass Pebble Magnets', 'Highwood PL', 'Highwood Library & Community Center, 102 Highwood Ave', 'Free', 'https://highwoodlibrary.org/events/art-workshop-for-adults-glass-pebble-magnets-taller-de-arte-para-adultos-imanes-con-piedras-de-vidrio', 'Free hands-on art workshop, all experience levels. Registration required. Bilingual (English/Spanish).'),
    h('2026-11-23', '7:00pm - 8:00pm', 'Create Your Own Thanksgiving Centerpiece with Peggy Garvin', 'Cary Area PL', 'Meeting Room', '$30', 'https://caryarea.librarycalendar.com/event/create-your-own-thanksgiving-centerpiece-43239', 'Hands-on workshop. Payment required at registration.', left=0),
    h('2026-12-14', '7:00pm - 8:00pm', 'Duct Tape Scalloped Ornaments', 'Cary Area PL', 'Flex Zone', 'Free', 'https://caryarea.librarycalendar.com/event/duct-tape-scalloped-ornaments-44506', 'Learn to make ornaments out of duct tape. Registration required.'),
    h('2026-12-19', '10:00am - 11:30am', '3D Printing Pens', 'Cary Area PL', 'Flex Zone', 'Free', 'https://caryarea.librarycalendar.com/event/3d-printing-pens-44421', 'Create 3D art by hand with 3D pens. Registration required.'),
    h('2026-11-07', '10:30am - 11:30am', 'Table Centerpieces with Lake Forest Flowers', 'Lake Bluff PL', 'Spruth Room', 'Free', 'https://lakeblufflibrary.libcal.com/event/17185164', 'Lake Forest Flowers shows how to craft a floral table centerpiece; participants leave with their own.'),
    h('2026-12-02', '5:30pm - 7:00pm', 'Winter Wreaths / Corona de Invierno', 'McHenry PL', 'Meeting Rooms East and West', 'Free', 'https://mchenry.librarycalendar.com/event/placeholder-bilingual-craft-34282', 'Bilingual wreath-making craft. Registration required.', left=0),
    h('2026-12-12', '10:00am - 12:00pm', 'Stamping with Mallory', 'McHenry PL', 'Meeting Rooms East and West', 'Free', 'https://mchenry.librarycalendar.com/event/stamping-mallory-35656', 'Card/stamping craft class. Registration required.', left=0),
    h('2026-11-12', '6:30pm - 8:30pm', 'Maker Class: Alcohol Ink', 'Vernon Area PL', 'Meeting Room', 'Free', 'https://calendar.vapld.info/event/copy-maker-class-104865', 'Using alcohol ink, create organic forms. Registration required.'),
    h('2026-12-08', '10:00am - 11:30am', 'Adults & Crafts: Tea Blends', 'Kenosha PL', 'KPL Northside Neighborhood Library', 'Free', 'https://mykpl.bibliocommons.com/events/6967cd6739996c13d3d010d5', 'Learn about different teas and blend your own to take home. Adults, registration required.'),
    h('2026-12-14', '5:30pm - 7:00pm', 'Adults & Crafts: Tea Blends', 'Kenosha PL', 'KPL Northside Neighborhood Library', 'Free', 'https://mykpl.bibliocommons.com/events/6967cd6739996c13d3d010d5', 'Learn about different teas and blend your own to take home. Adults, registration required.'),
    h('2026-11-04', '1:30pm - 3:00pm', 'Book Page Pumpkin', 'Community Library (Salem Lakes, WI)', 'Twin Lakes Meeting Room', 'Free', 'https://communitylib.libcal.com/event/17663290', 'Turn a book into a rustic pumpkin centerpiece.'),
    h('2026-11-09', '6:00pm - 7:00pm', 'Thankful by Design', 'Community Library (Salem Lakes, WI)', 'Salem Meeting Room', 'Free', 'https://communitylib.libcal.com/event/17620899', 'Make coordinated fall thank-you cards with acrylic paint markers.'),
    h('2026-11-16', '6:00pm - 7:00pm', 'A Banner of Gratitude', 'Community Library (Salem Lakes, WI)', 'Salem Meeting Room', 'Free', 'https://communitylib.libcal.com/event/17467404', 'Guided gratitude meditation, then paint your own canvas banner.'),
    h('2026-12-08', '6:00pm - 7:00pm', 'Deck the Table: A Holiday Decorating Workshop', 'Community Library (Salem Lakes, WI)', 'Salem Meeting Room', 'Free', 'https://communitylib.libcal.com/event/17623306', 'Learn to build a festive Christmas tablescape.'),
    h('2026-12-09', '1:30pm - 3:00pm', 'Felted Winter Farm Scene with Pop Up Art School', 'Community Library (Salem Lakes, WI)', 'Twin Lakes Meeting Room', 'Free', 'https://communitylib.libcal.com/event/17389273', 'Needle felting: "paint with wool" on felt inside an embroidery hoop.'),
    h('2026-12-10', '6:00pm - 7:00pm', 'Red and White Fluff Ornament', 'Community Library (Salem Lakes, WI)', 'Salem Meeting Room', 'Free', 'https://communitylib.libcal.com/event/17670818', 'Make yarn "candy cane" snowball ornaments.'),
    h('2026-12-14', '6:00pm - 7:00pm', 'Word of the Year Art', 'Community Library (Salem Lakes, WI)', 'Salem Meeting Room', 'Free', 'https://communitylib.libcal.com/event/17467550', 'Guided meditation, then paint your word on a mini canvas fridge magnet.'),
    # Park districts, forest preserves and farms (paid unless noted)
    h('2026-11-12', '6:00pm - 8:00pm', 'Cookie Decorating: Cozy Fall (Adult)', 'Deerfield Park District', 'Patty Turner Center, 375 Elm St', '$60 resident / $65 nonresident', 'https://www.deerfieldparks.org/calendar.aspx?EID=1297', 'Adult (18+) cookie decorating class.'),
    h('2026-12-17', '6:00pm - 8:00pm', 'Cookie Decorating: Cozy Winter Cottage (Adult)', 'Deerfield Park District', 'Patty Turner Center, 375 Elm St', '$60 resident / $65 nonresident', 'https://www.deerfieldparks.org/calendar.aspx?EID=1298', 'Adult (18+) cookie decorating class.'),
    h('2026-12-03', '6:30pm - 7:30pm', 'Winter Containers', 'Deerfield Park District', 'Patty Turner Center, 375 Elm St', '$55 resident / $65 nonresident', 'https://www.deerfieldparks.org/calendar.aspx?EID=1307', 'Make a winter planter. Ages 21+.'),
    h('2026-11-08', '3:00pm - 5:00pm', 'Fall Embroidery Sampler', 'Skokie Park District', 'Skokie Heritage Museum', '$40 resident / $50 nonresident', 'https://www.skokieparks.org/events/fall-embroidery-sampler/', 'Beginner-friendly embroidery sampler class.'),
    h('2026-11-12', '7:00pm - 8:30pm', 'Tabletop Terrariums', 'Skokie Park District', 'Emily Oaks Nature Center', '$37 resident / $46 nonresident', 'https://www.skokieparks.org/events/tabletop-terrariums26/', 'Build a tabletop terrarium.'),
    h('2026-11-22', '3:00pm - 5:00pm', 'Intro to Crochet: Granny Squares', 'Skokie Park District', 'Skokie Heritage Museum', '$40 resident / $50 nonresident', 'https://www.skokieparks.org/events/intro-to-crochet-granny-squares/', 'Learn to crochet granny squares.'),
    h('2026-11-29', '2:00pm - 4:00pm', 'Intro to Nålbinding', 'Skokie Park District', 'Skokie Heritage Museum', CU, 'https://www.skokieparks.org/events/intro-to-nalbinding/', 'Intro to the ancient Scandinavian needle-looping craft.'),
    h('2026-12-02', '7:00pm - 8:30pm', 'Evergreen Wreaths', 'Skokie Park District', 'Emily Oaks Nature Center', '$37 resident / $46 nonresident', 'https://www.skokieparks.org/events/evergreen-wreaths-1/', 'Make an evergreen wreath.'),
    h('2026-12-03', '7:00pm - 8:30pm', 'Evergreen Wreaths', 'Skokie Park District', 'Emily Oaks Nature Center', '$37 resident / $46 nonresident', 'https://www.skokieparks.org/events/evergreen-wreaths-1/', 'Make an evergreen wreath.'),
    h('2026-11-21', '1:00pm - 2:00pm', 'Natural Dyes', 'Heller Nature Center (Park District of Highland Park)', 'Heller Nature Center, 2821 Ridge Rd', '$20', 'https://www.pdhp.org/event/natural-dyes/', 'Natural dyeing class at Heller Nature Center.'),
    h('2026-11-12', '10:00am - 2:00pm', 'Tiny Tree Treasures (basket-weaving mini tree skirt)', 'Vernon Hills Park District', 'Sullivan Community Center, 635 N Aspen Dr', CU, 'https://www.vhparkdistrict.org/event/tiny-tree-treasures/', 'Hands-on basket-weaving workshop: make a mini tree skirt. No experience needed.'),
    h('2026-11-21', '10:00am - 12:00pm', 'Buckthorn Dyeing Workshop', 'Forest Preserves of Cook County', 'Crabtree Nature Center, 3 Stover Rd, Barrington Hills', 'Free', 'https://fpdcc.com/event/buckthorn-dyeing-workshop/', 'Cut buckthorn and dye fabric with it, with Chicago artist Katelyn Patton.', reg='No'),
    h('2026-11-17', '10:00am - 11:30am', 'Wreath Making Workshop', 'Elawa Farm', 'Elawa Farm, 1401 Middlefork Dr, Lake Forest', CU, 'https://elawafarm.org/classes-programs', 'Hands-on with Eileen Weber of Lake Forest Flowers; all supplies provided. Tickets through Elawa Farm.'),
    h('2026-11-20', '6:00pm - 8:00pm', 'Thanksgiving Cookie Centerpieces with Folklorica Bakery', 'Elawa Farm', 'Elawa Farm, 1401 Middlefork Dr, Lake Forest', CU, 'https://elawafarm.org/classes-programs', 'Hands-on cookie decorating workshop, materials provided.'),
    h('2026-12-11', '9:00am - 12:30pm', 'Holiday Baking Workshop: Bûche de Noël', 'Elawa Farm', 'Elawa Farm, 1401 Middlefork Dr, Lake Forest', CU, 'https://elawafarm.org/classes-programs', 'Hands-on baking class with Pastry Chef Maggie Logan.'),
    h('2026-12-18', '9:00am - 12:30pm', 'Holiday Baking Workshop: Bûche de Noël', 'Elawa Farm', 'Elawa Farm, 1401 Middlefork Dr, Lake Forest', CU, 'https://elawafarm.org/classes-programs', 'Hands-on baking class with Pastry Chef Maggie Logan.'),
]
# Deerfield PL runs Felt Wreaths as a registration lottery (max 1, 8-9 on the waitlist): not "Full", just a lottery.
for r in rows:
    if r['org'].startswith('Deerfield PL') and r['name'].startswith('Felt Wreaths'):
        r['left'] = None
        r['desc'] += ' Registration is by lottery: join the waitlist to enter.'
# drop exact duplicates (same date, time, name, org)
_seen, _u = set(), []
for r in rows:
    k = (r['date'], r['time'], re.sub(r'\W+', '', r['name'].lower()), r['org'][:8])
    if k not in _seen:
        _seen.add(k); _u.append(r)
rows = _u

# Gurnee PD registers through WebTrac ("save your spot"), which also carries the real time/place/price.
for r in rows:
    if r['org'] == 'Gurnee PD' and r['name'].startswith('Learn to Sew'):
        r.update(time='9:00am - 12:00pm', where='Hunt Club Community Center', cost='$45 resident / $56 non-resident',
                 url='https://ilgurneeweb.myvscloud.com/webtrac/web/search.html?module=ar&keyword=214445',
                 desc='Learn to sew a placemat and napkin set. Ages 14+. Register on the Gurnee Park District WebTrac page.')
rows.sort(key=lambda r: (r['date'], r['time']))

# zip per row, so the distance filter is branch-accurate
ORG_ZIP = {'Grayslake': '60030', 'Wauconda': '60084', 'Fox Lake': '60020', 'North Chicago': '60064', 'Fremont PL': '60060', 'Warren-Newport': '60031', 'Lake Villa': '60046', 'Round Lake Area PL': '60073',
           'Waukegan': '60085', 'Zion-Benton': '60099', 'Ela Area': '60047', 'Highland Park': '60035',
           'Northbrook': '60062', 'Indian Trails': '60090', 'Mount Prospect': '60056', 'Michaels Gurnee': '60031',
           'Gurnee PD': '60031', 'Deerfield PL': '60015', 'Deerfield Park': '60015', 'Palatine': '60067', 'Highwood': '60040', 'Cary': '60013', 'Lake Bluff': '60044', 'McHenry PL': '60050', 'Vernon Area': '60069', 'Community Library': '53168', 'Skokie': '60077', 'Heller': '60035', 'Vernon Hills': '60061', 'Forest Preserves of Cook': '60010', 'Elawa': '60045', 'Brushwood': '60015', 'Third Coast': '60610', 'Velvet Stitch': '60201'}
def zip_for(r):
    o, w = r['org'], r['where'] or ''
    if o.startswith('Antioch'):
        return '60002'
    if o.startswith('Kenosha'):
        return '53140'
    if o.startswith('Community Library') and 'Twin Lakes' in w:
        return '53181'
    if o.startswith('Cook Memorial'):
        return '60061' if 'Aspen' in w else '60048'
    if o.startswith('Algonquin'):
        return '60156' if 'Eastgate' in w else '60102'
    for k, z in ORG_ZIP.items():
        if o.startswith(k):
            return z
    raise SystemExit(f'no zip for {o}')
for r in rows:
    r['zip'] = zip_for(r)
    if len(r['desc']) >= 290:   # scraper cut at 300 chars; end on a whole sentence
        r['desc'] = r['desc'][:r['desc'].rfind('.') + 1] or r['desc']
    else:
        r['desc'] = re.sub(r'\s+\S{1,2}$', '', r['desc'])   # stray "R" from "Registration…" cut-offs

today = datetime.date.today().isoformat()
rows = [r for r in rows if r['date'] >= today]   # past classes drop off on every rebuild

# Every row's zip must be in the site's ZIP_CENTROIDS, or the miles filter can't place it.
site = open(INDEX).read()
zips = json.loads(re.search(r'const ZIP_CENTROIDS\s*=\s*(\{.*?\});', site, re.S).group(1))
missing = {r['zip'] for r in rows} - set(zips)
if missing:
    raise SystemExit(f'FAIL: zips not in ZIP_CENTROIDS (add them to index.html first): {sorted(missing)}')

block = ('// WORKSHOPS-DATA-START (written by tools/workshops/build_workshops.py; do not hand-edit)\n'
         f'const WS_ASOF = {json.dumps(today)};\n'
         f'const WORKSHOPS = {json.dumps(rows, ensure_ascii=False)};\n'
         '// WORKSHOPS-DATA-END')
print(len(rows), 'workshops;', sum(1 for r in rows if r['opens'] > today), 'with registration not open yet;',
      sum(1 for r in rows if r.get('left') == 0), 'full as of', today)
if '--write' in sys.argv:
    new, n = re.subn(r'// WORKSHOPS-DATA-START.*?// WORKSHOPS-DATA-END', lambda _: block, site, flags=re.S)
    if n != 1:
        raise SystemExit('FAIL: WORKSHOPS-DATA markers not found exactly once in index.html')
    open(INDEX, 'w').write(new)
    print('wrote', os.path.normpath(INDEX))
