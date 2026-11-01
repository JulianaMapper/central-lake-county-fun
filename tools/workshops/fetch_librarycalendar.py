"""Adult maker workshops from librarycalendar.com libraries (day feed, one request per day)."""
import datetime, html, json, re, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor

HOSTS = {'grayslake.librarycalendar.com': 'Grayslake Area PL', 'www.fllib.org': 'Fox Lake District Library',
         'www.wauclib.org': 'Wauconda Area PL'}
UA = {'User-Agent': 'Mozilla/5.0 (Macintosh) Chrome/124'}
START, END = datetime.date(2026, 10, 30), datetime.date(2027, 2, 28)
CRAFT = re.compile(r'sew|quilt|knit|crochet|embroider|stitch|paint|watercolor|wreath|pottery|clay|candle|soap|macram|weav|'
                   r'felt|bead|jewel|resin|calligraph|draw|sketch|collage|terrarium|succulent|floral|centerpiece|ornament|'
                   r'gnome|marbl|pillow|cutting board|craft|diy|make (?:a|your)|maker|cricut|laser|3d print|screen print|block print|stamp|card making|'
                   r'gingerbread|glass|mosaic|wood|leather|tie[- ]dye|scrapbook|art\b|journal', re.I)
NOT = re.compile(r'book (club|discussion)|club\b|circle|group|meetup|social|open (studio|lab)|drop[- ]?in|'
                 r'take (&|and) make|grab (&|and) go|kit\b|storytime|film|movie|lecture|author', re.I)

def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read().decode('utf8', 'ignore')

def day(args):
    host, d = args
    try:
        t = get(f'https://{host}/events/feed/html?_wrapper_format=lc_calendar_feed&adjust_range=1'
                f'&current_date={d}&ongoing_events=show')
    except Exception as e:
        return host, d, [], str(e)
    out = []
    for art in re.findall(r'(?s)<article class="event-card.*?</article>', t):
        groups = re.findall(r'This event is in the "([^"]+)" group', art)
        a = re.search(r'aria-label="View Details - &quot;(.*?)&quot; on (.*?)" href="([^"]+)"', art)
        if a:
            out.append(dict(title=html.unescape(a.group(1)), label=html.unescape(a.group(2)), href=a.group(3), groups=groups, date=str(d)))
    return host, d, out, None

jobs = [(h, START + datetime.timedelta(n)) for h in HOSTS for n in range((END - START).days + 1)]
seen, cards, errs = set(), [], 0
with ThreadPoolExecutor(12) as ex:
    for host, d, evs, err in ex.map(day, jobs):
        errs += bool(err)
        for e in evs:
            k = (host, e['href'])
            if k not in seen:
                seen.add(k); e['host'] = host; cards.append(e)

# title counts per library -> recurrence signal
cnt = {}
for e in cards:
    cnt[(e['host'], e['title'].lower())] = cnt.get((e['host'], e['title'].lower()), 0) + 1

cand = [e for e in cards if 'Adults' in ' '.join(e['groups']) and CRAFT.search(e['title']) and not NOT.search(e['title'])
        and cnt[(e['host'], e['title'].lower())] <= 4]

def detail(e):
    t = get(f"https://{e['host']}{e['href']}")
    txt = html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', re.sub(r'(?s)<(script|style).*?</\1>', '', t))))
    body = re.search(r'(?s)<div class="lc-event__body[^"]*">(.*?)</div>\s*</div>', t)
    desc = html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', body.group(1)))).strip() if body else ''
    e['desc'] = desc[:300]
    e['full_text'] = txt
    return e

with ThreadPoolExecutor(8) as ex:
    cand = list(ex.map(detail, cand))
json.dump([{k: v for k, v in e.items()} for e in cand], open(sys.argv[1], 'w'), indent=1)
print(f'{len(cards)} events scanned, {errs} day errors, {len(cand)} adult craft candidates')
for e in sorted(cand, key=lambda x: x['date']):
    print(e['date'], '|', HOSTS[e['host']][:12], '|', e['title'], '|', e['label'][-60:], '|', ','.join(e['groups']))
