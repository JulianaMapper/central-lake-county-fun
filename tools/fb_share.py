#!/usr/bin/env python3
"""Facebook share images (1080x1350) for the week's events.

  1. python3 tools/fb_share.py list  --start 2026-10-14 --end 2026-10-18
        Candidate events per day (free, close, kid-appropriate) with a first-draft
        picks file written to tools/fb_share_picks_<start>.json
  2. EDIT THE PICKS FILE -- this is the curation step. Read it, cut what a parent
     wouldn't drive for, fix emojis, rewrite the nature-center strip.
  3. python3 tools/fb_share.py render --picks tools/fb_share_picks_<start>.json [--out DIR]
        Writes fb-share-<start>-1.png, -2.png ... (default DIR: ~/Downloads)

Rules baked in (all learned 2026-10-06):
  * Free only. cost "Check website", blank, or a price is dropped.
  * Never "All day" items -- no time to show, and the user cut them.
  * Museums-type "Free Admission at X" rows are NOT listed; they go in the gold
    nature-center strip (hours vary by day -- verify on each site).
  * Times always carry am/pm. The first-draft times come from the site data; Juliana
    still spot-checks against each org's own site before posting.
  * Never more than 2 images (rule added 2026-10-07; was 3). Days are never split, the two
    images are balanced, and each holds at most PER_IMAGE (17) events -- so ~34 picks max.
    Over that, render refuses and tells you how many to cut.
  * The footer URL is fun.julianamapper.com.
"""
import argparse, json, re, subprocess, sys, html, math
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parent.parent
BANNED_ORGS = ("Wheaton Public Library", "Glen Ellyn Public Library")
SKIP_TYPES = {"Storytime", "Museums", "Community Resources", "Games & Clubs", "Camps"}
SKIP_NAME = re.compile(r"teen|adult|board|committee|registration (begins|opens)|book in a jar|foyer|resource table|social worker|lavender|quilt|writing workshop|tech talk|screening", re.I)
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
MAX_IMAGES = 2
PER_IMAGE = 17
EMOJI = [(r"farmers market", "🥕"), (r"pumpkin", "🎃"), (r"bat", "🦇"), (r"ghost|spooky|halloween|haunt", "👻"),
         (r"dog|canine|puppy", "🐶"), (r"hike|walk|trail", "🥾"), (r"lego|brick", "🧱"), (r"movie|film|flick", "🎬"),
         (r"music|concert|sing", "🎶"), (r"dance", "💃"), (r"paint|art|craft|canvas", "🎨"), (r"fish", "🎣"),
         (r"bird|owl|raptor", "🐦"), (r"museum", "🏛️"), (r"science|stem|lab", "🔬"), (r"festival|fest", "🍂"),
         (r"diwali|lights", "🪔"), (r"play", "🧸"), (r"escape|breakout|puzzle", "🧩"), (r"cook|bake|cookie", "🍪")]

def emoji_for(name):
    for pat, e in EMOJI:
        if re.search(pat, name, re.I): return e
    return "⭐"

def load_events():
    s = (ROOT / "index.html").read_text(encoding="utf-8")
    return json.loads(re.search(r"const EVENTS\s*=\s*(\[.*?\]);\s*\n?\s*const PARKS", s, re.S).group(1))

def start_time(t):
    """'6:30pm - 7:30pm' / '10:00AM' / '10:00 AM - 11 AM' -> '6:30pm'; None for all-day/unparseable."""
    m = re.search(r"(\d{1,2})(?::(\d{2}))?\s*([ap]m)", t or "", re.I)
    if not m: return None
    return f"{int(m.group(1))}:{m.group(2) or '00'}{m.group(3).lower()}"

def minutes(t):
    m = re.match(r"(\d+)(?::(\d+))?\s*([ap]m)", t, re.I)
    if not m: sys.exit(f"Can't read time {t!r} in picks -- use e.g. 9:30am")
    return (int(m.group(1)) % 12 + (12 if m.group(3).lower() == "pm" else 0)) * 60 + int(m.group(2) or 0)

def short_place(org):
    o = re.sub(r"\s*\(.*?\)", "", org)
    o = re.sub(r"Public Library District|Public Library|District Library|Area Library|Library District", "Library", o)
    o = re.sub(r"\bArea\b ", "", o)
    return o.replace("Lake County Forest Preserves", "Lake County Forest Preserves").strip()

def candidates(start, end, drive):
    out = []
    for e in load_events():
        if not (start <= e["date"] <= end): continue
        if e["org"] in BANNED_ORGS: continue
        if not re.match(r"\s*free\b", str(e.get("cost", "")), re.I): continue
        if e.get("type") in SKIP_TYPES or SKIP_NAME.search(e["name"]): continue
        if (e.get("drive") or 99) > drive: continue
        st = start_time(e["time"])
        if not st: continue
        out.append({"date": e["date"], "time": st, "emoji": emoji_for(e["name"]), "name": e["name"].strip(),
                    "place": short_place(e["org"]), "_standout": bool(e.get("standout")), "_drive": e.get("drive") or 99})
    return out

def cmd_list(a):
    c = candidates(a.start, a.end, a.drive)
    byday = {}
    for e in c: byday.setdefault(e["date"], []).append(e)
    draft = []
    for d in sorted(byday):
        rows = sorted(byday[d], key=lambda e: (not e["_standout"], e["_drive"]))
        print(f"\n== {d} ({date.fromisoformat(d):%A}) -- {len(rows)} candidates")
        for i, e in enumerate(sorted(rows, key=lambda e: minutes(e["time"]))):
            print(f"  {'*' if e['_standout'] else ' '} {e['time']:>7}  {e['name'][:58]:58} {e['place'][:30]:30} {e['_drive']}min")
        draft += rows[:a.per_day]
    for e in draft: e.pop("_standout"); e.pop("_drive")
    out = ROOT / "tools" / f"fb_share_picks_{a.start}.json"
    out.write_text(json.dumps({
        "kicker": "FREE FAMILY FUN · LAKE COUNTY & NEARBY", "title": ["What’s Happening", "This Week"],
        "nature_title": "🌲 Free nature centers, open most days:",
        "nature": "FILL IN: names + hours from each center's own site. Hours can change, so check the site.",
        "footer_line": "Hundreds more events, plus a 🗺️ park map & playgrounds ⭐ and indoor play areas", "footer_url": "fun.julianamapper.com",
        "events": draft}, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\nFirst-draft picks ({len(draft)}) -> {out}\n* = standout. NOW CURATE THAT FILE, then run render.")

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{width:1080px;height:1350px;background:#f0e6d0;color:#1a1612;font-family:'Public Sans',sans-serif;display:flex;flex-direction:column}
.top{background:#1f3a6b;color:#f0e6d0;padding:22px 50px 16px;border-bottom:10px solid #e8a92c;text-align:center}
.kick{font-family:'Special Elite';font-size:26px;letter-spacing:3px;color:#e8a92c}
h1{font-family:'DM Serif Display';font-weight:400;font-size:62px;line-height:1;margin:4px 0 6px}
.sub{font-size:28px;font-weight:700}.pg{font-family:'Special Elite';font-size:24px;color:#e8a92c;margin-top:6px}
.list{flex:1;padding:14px 36px 0;display:flex;flex-direction:column}
.day{flex:1;display:flex;gap:16px;margin-bottom:12px}.day:last-child{margin-bottom:0}
.d{width:128px;flex:none;background:#c1342a;color:#fff;border-radius:14px;text-align:center;display:flex;flex-direction:column;justify-content:center}
.d span{font-size:32px;font-weight:800}.d b{font-family:'DM Serif Display';font-weight:400;font-size:44px;line-height:1.05}
ul{flex:1;list-style:none;background:#fff8e8;border:3px solid #1a1612;border-radius:14px;padding:8px 16px;display:flex;flex-direction:column;justify-content:space-around}
li{display:flex;gap:12px;font-size:24px;line-height:1.2;padding:3px 0;border-bottom:1px dashed #b9a98a}li:last-child{border:0}
li i{flex:none;width:100px;font-style:normal;font-weight:800;color:#c1342a;text-align:right;white-space:nowrap}
li b{font-weight:800}li small{font-size:20px;font-weight:500;color:#3a332b}li small:before{content:"· "}
.nc{margin:12px 36px 0;background:#e8a92c;border:3px solid #1a1612;border-radius:14px;padding:10px 18px;font-size:23px;line-height:1.3}
.foot{margin-top:14px;background:#1a1612;color:#f0e6d0;text-align:center;padding:12px 0 14px}
.foot p{font-size:24px;font-weight:700}.foot h2{font-family:'DM Serif Display';font-weight:400;font-size:46px;color:#e8a92c;margin-top:2px}
"""
FONTS = '<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Public+Sans:wght@500;700;800&family=Special+Elite&display=swap" rel="stylesheet">'
e_ = lambda s: html.escape(s, quote=False)

def day_label(d):
    dt = date.fromisoformat(d); return f"{dt:%A} {dt:%b} {dt.day}", f"{dt:%a}".upper(), f"{dt:%b} {dt.day}"

def paginate(days):
    """Split whole days into at most MAX_IMAGES balanced pages of <= PER_IMAGE events each."""
    total = sum(len(v) for _, v in days)
    if total <= PER_IMAGE: return [days]
    best = None
    for k in range(1, len(days)):  # split between days k-1 and k
        a, b = sum(len(v) for _, v in days[:k]), sum(len(v) for _, v in days[k:])
        if a <= PER_IMAGE and b <= PER_IMAGE and (best is None or abs(a - b) < best[0]): best = (abs(a - b), k)
    if best is None:
        sys.exit(f"{total} picks across {len(days)} days won't fit in {MAX_IMAGES} images (max {PER_IMAGE} each, days never split). "
                 f"Cut ~{max(1, total - MAX_IMAGES * PER_IMAGE)} or more picks and re-run.")
    return [days[:best[1]], days[best[1]:]]

def page_html(cfg, pg, i, total, last):
    names = [day_label(d)[0] for d, _ in pg]
    sub = " &amp; ".join(e_(x) for x in names) if len(names) <= 2 else f"{e_(names[0])} – {e_(names[-1])}"
    days = ""
    for d, evs in pg:
        _, dn, dt = day_label(d)
        li = "".join(f"<li><i>{e_(e['time'])}</i><span>{e_(e['emoji'])} <b>{e_(e['name'])}</b> <small>{e_(e['place'])}</small></span></li>" for e in evs)
        days += f'<div class="day"><div class="d"><span>{dn}</span><b>{dt}</b></div><ul>{li}</ul></div>'
    nature = f'<div class="nc"><b>{e_(cfg["nature_title"])}</b><br>{e_(cfg["nature"])}</div>' if last and cfg.get("nature") else ""
    counter = f'<div class="pg">{i} of {total}</div>' if total > 1 else ""
    return (f'<!doctype html><html><head><meta charset="utf-8">{FONTS}<style>{CSS}</style></head><body>'
            f'<div class="top"><div class="kick">{e_(cfg["kicker"])}</div><h1>{"<br>".join(e_(t) for t in cfg["title"])}</h1>'
            f'<div class="sub">{sub}</div>{counter}</div><div class="list">{days}</div>{nature}'
            f'<div class="foot"><p>{e_(cfg["footer_line"])}</p><h2>{e_(cfg["footer_url"])}</h2></div></body></html>')

def cmd_render(a):
    cfg = json.loads(Path(a.picks).read_text(encoding="utf-8"))
    if "FILL IN" in cfg.get("nature", ""): sys.exit("Picks file still has the nature-center placeholder. Fill it in (or set it to \"\" to omit).")
    byday = {}
    for e in cfg["events"]: byday.setdefault(e["date"], []).append(e)
    days = [(d, sorted(v, key=lambda e: minutes(e["time"]))) for d, v in sorted(byday.items())]
    pages = paginate(days); first = days[0][0]
    out = Path(a.out).expanduser(); out.mkdir(parents=True, exist_ok=True)
    tmp = Path("/tmp") if False else out / ".fb_share_tmp"; tmp.mkdir(exist_ok=True)
    for i, pg in enumerate(pages, 1):
        h = tmp / f"p{i}.html"; h.write_text(page_html(cfg, pg, i, len(pages), i == len(pages)), encoding="utf-8")
        png = out / f"fb-share-{first}-{i}.png"
        subprocess.run([CHROME, "--headless", "--disable-gpu", "--hide-scrollbars", "--virtual-time-budget=8000",
                        "--window-size=1080,1350", f"--screenshot={png}", f"file://{h}"], capture_output=True, check=True)
        print(f"{png}  ({sum(len(v) for _, v in pg)} events, {len(pg)} days)")
    for f in tmp.iterdir(): f.unlink()
    tmp.rmdir()
    print("Check each image for text overflow before posting (a long title can wrap and push the footer).")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    l = sub.add_parser("list"); l.add_argument("--start", required=True); l.add_argument("--end", required=True)
    l.add_argument("--drive", type=int, default=30, help="max drive minutes (default 30)"); l.add_argument("--per-day", type=int, default=5)
    r = sub.add_parser("render"); r.add_argument("--picks", required=True); r.add_argument("--out", default="~/Downloads")
    a = ap.parse_args(); {"list": cmd_list, "render": cmd_render}[a.cmd](a)
