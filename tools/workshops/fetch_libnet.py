import json, re, sys, urllib.request, urllib.parse, collections
from concurrent.futures import ThreadPoolExecutor

HOSTS = {
 'cooklib':'Cook Memorial PLD (Libertyville)','fremont':'Fremont PL (Mundelein)','wnpl':'Warren-Newport PL (Gurnee)',
 'lvdl':'Lake Villa District Library','rlalibrary':'Round Lake Area PL','events.waukeganpl.org':'Waukegan PL',
 'deerfield':'Deerfield PL','zblibrary':'Zion-Benton PL','eapl':'Ela Area PL (Lake Zurich)',
 'hplibrary':'Highland Park PL','northbrook':'Northbrook PL','indiantrails':'Indian Trails PL',
 'mppl':'Mount Prospect PL','aapld':'Algonquin Area PL',
}
CRAFT = re.compile(r'sew|quilt|knit|crochet|embroider|cross[- ]stitch|needle|paint|watercolor|acrylic|canvas|wreath|'
    r'pottery|clay|ceramic|candle|soap|macram|weav|felt|fiber|yarn|bead|jewel|resin|calligraph|letter|draw|sketch|'
    r'collage|journal|terrarium|succulent|floral|flower arrang|centerpiece|ornament|craft|diy|make (?:a|your)|maker|'
    r'cricut|laser|3d print|sublimat|screen print|printmak|block print|stamp|card making|gingerbread|decorat|'
    r'glass|mosaic|marbl|bolsa|tela\b|pillow|cutting board|wood block|placecard|napkin|gnome|etch|hand warmer|quill|woodwork|wood burn|pyrograph|leather|tie[- ]dye|dye|scrapbook|zentangle|art\b|artist', re.I)
NOT = re.compile(r'book (club|discussion)|writing group|writer|storytime|story time|esl|tax|medicare|'
    r'concert|film|movie|lecture|talk\b|author|trivia|game|bingo|yoga|tai chi|walk|tour|genealogy|computer|'
    r'open (studio|workshop|lab|hours)|drop[- ]?in|craft(ing)? (club|circle|night|group|corner)|knit(ting)? (club|circle|group)|'
    r'stitch(ers|ing)? (club|circle|group)|social|meetup|meet[- ]up', re.I)
ADULT = re.compile(r'adult|18\+|21\+|all ages|senior|grown', re.I)

def fetch(host):
    h = host if '.' in host else f'{host}.libnet.info'
    req = json.dumps({"private":False,"date":"2026-10-30","days":120,"locations":[],"ages":[],"types":[]})
    url = f'https://{h}/eeventcaldata?event_type=0&req=' + urllib.parse.quote(req)
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'}), timeout=60)
        return host, json.load(r)
    except Exception as e:
        return host, e

out, stats = [], {}
with ThreadPoolExecutor(8) as ex:
    for host, data in ex.map(fetch, HOSTS):
        if isinstance(data, Exception):
            stats[host] = f'ERR {data}'; continue
        # how many times does each title occur in the window -> recurrence signal
        # Recurrence signal = number of DISTINCT DATES a title runs on. (Bug fixed 2026-10-31: counting rows
        # made a one-time class offered as 2 sessions, e.g. Fremont 10am + 2pm, or on 2 dates look like a series.)
        dates = collections.defaultdict(set)
        for e in data:
            dates[re.sub(r'\W+',' ',e['title'].lower()).strip()].add(e['raw_start_time'][:10])
        cnt = {k: len(v) for k, v in dates.items()}
        keep = 0
        for e in data:
            ages = ' '.join(e.get('agesArray') or [])
            if not ADULT.search(ages): continue
            text = f"{e['title']} {e.get('sub_title','')} {e.get('description','')}"
            if not CRAFT.search(e['title'] + ' ' + e.get('description','')): continue
            if NOT.search(e['title']): continue
            key = re.sub(r'\W+',' ',e['title'].lower()).strip()
            if cnt[key] > 4: continue   # 5+ dates = a club/series; 2-4 dates = repeated one-time class, hand-review
            cost = e.get('registration_cost') or '0'
            # Indian Trails puts the rule in sub_title ("Reserved for Adult Indian Trails Library cardholders only")
            full = re.sub(r'<[^>]+>', ' ', ' . '.join(e.get(k) or '' for k in ('sub_title', 'description', 'long_description')))
            cardm = re.search(r'[^.]*\b(card ?holders? (only|to attend)|reserved for [^.]*card ?holders?|must (be|have) an? [\w-]* ?(library )?card ?holder|library card (is )?required|card required|residents only)\b[^.]*', full, re.I)
            out.append({
              'date': e['raw_start_time'][:10], 'time': e['time_string'], 'name': e['title'],
              'org': HOSTS[host], 'location': e.get('library') or e.get('location'),
              'ages': ages, 'cost': 'Free' if cost in ('0','0.00','') else f'${cost}',
              'reg': 'Yes' if e.get('allow_reg')=='1' or e.get('reg_url') else 'No',
              'reg_opens': (e.get('reg_opens') or '')[:10] if e.get('allow_reg')=='1' and e.get('open_registration_imidiatly')!='1' else '',
              'seats': f"{e.get('total_registrants')}/{e.get('max_attendee')}" if e.get('max_attendee') not in ('0',None) else '',
              'url': e['url'].replace('\\/','/'),
              'desc': re.sub(r'\s+',' ',re.sub('<[^>]+>',' ',e.get('description',''))).strip()[:300],
              'repeats_in_window': cnt[key],
              'max': int(e.get('max_attendee') or 0),
              'taken': int(e.get('total_registrants') or 0),
              'waitlist': e.get('allow_waitlist') == '1',
              'card_text': re.sub(r'\s+', ' ', cardm.group(0)).strip() if cardm else '',
            })
            keep += 1
        stats[host] = f'{len(data)} events, {keep} kept'
json.dump(out, open(sys.argv[1],'w'), indent=1)
for k,v in stats.items(): print(k, v)
print('TOTAL', len(out))
