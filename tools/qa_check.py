#!/usr/bin/env python3
"""Pre-push QA gate for index.html. Run this before every commit.

    python3 tools/qa_check.py

Why this exists: three separate classes of bug have shipped to the live site, and
all three were SILENT — the page rendered fine and the numbers looked plausible,
so nothing revealed them until someone noticed an event missing by hand:

  1. 2026-06-09  orphan `type` values      → 25 events unreachable by any type chip
  2. 2026-08-17  first-match-wins classAge → 221 events hidden from the age filter
  3. 2026-08-17  missing ORG_ZIP entries   →  54 events stuck at 99 mi, hidden at
                                              every distance except "Any"

The shape is always the same: an event is IN the data, looks correct on its card,
and is invisible because some lookup table doesn't know about it. A human reading
the calendar cannot see that. These checks can.

HOW THE AGE AND DISTANCE CHECKS WORK — this matters if you edit this file.
They do NOT reimplement the site's logic. `tools/qa_probe.js` extracts the real
ageBuckets() / ageMatches() / eventDist() out of index.html and runs them under
node, and this script only applies policy to the facts it returns. An earlier
version of this file carried Python copies of those functions; that is the classic
QA trap, where the checker drifts from the thing it checks and then passes while
the site is broken. Do not reintroduce a copy. If node is unavailable the age and
distance checks FAIL loudly rather than falling back to a stale duplicate.

FAIL blocks the push. WARN is informational — read it, then decide.

Exit codes: 0 = clean (warnings allowed), 1 = at least one FAIL, 2 = probe error.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, "index.html")
PROBE = os.path.join(ROOT, "tools", "qa_probe.js")
HOME_ZIP = "60030"

# The canonical taxonomy from CLAUDE.md. An event whose type is off this list
# silently vanishes whenever any type chip is checked.
CANON_TYPES = {
    "Storytime", "Craft / Art", "Nature / Outdoors", "Animals",
    "Music / Performance", "Play / Drop-in", "Movies", "STEM / Discovery",
    "Museums", "Games & Clubs", "Free Meals / Food", "Festivals / Celebrations",
    "Movement / Sports", "Community Resources", "Camps", "Family Fun",
    "Farmers Markets",
}

# Orgs that must never reach the live site (DuPage / out of scope).
BANNED_ORGS = {
    "Wheaton Public Library",
    "Glen Ellyn Public Library",
    "Forest Preserve District of DuPage County",
}

# Age strings that are legitimately unclassifiable — don't nag about these.
AGE_EXEMPT = {"", "not specified", "n/a", "-", "tba", "tbd"}

fails, warns = [], []


def fail(msg):
    fails.append(msg)


def warn(msg):
    warns.append(msg)


def run_probe():
    """Run the site's own logic via node. Returns dict, or None if unavailable."""
    if not shutil.which("node"):
        fail("`node` is not on PATH, so the age and distance checks cannot run.\n"
             "      They deliberately have no Python fallback — a second copy of the\n"
             "      site's logic would drift and give false confidence. Install node\n"
             "      (or `fnm use 22`) and re-run.")
        return None
    if not os.path.exists(PROBE):
        fail("tools/qa_probe.js is missing — the age and distance checks need it.")
        return None
    r = subprocess.run([shutil.which("node"), PROBE], capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        fail("qa_probe.js failed (exit %d):\n      %s"
             % (r.returncode, (r.stdout + r.stderr).strip()[:1200]))
        return None
    try:
        d = json.loads(r.stdout)
    except Exception as e:
        fail("qa_probe.js emitted invalid JSON: %s" % e)
        return None
    if not d.get("ok"):
        fail("qa_probe.js: %s" % d.get("error", "unknown error"))
        return None
    return d


def main():
    txt = io.open(INDEX, encoding="utf-8").read()

    # ── 0. the existing syntax gate, so this is the only command you need ──────
    chk = os.path.join(ROOT, "tools", "check_syntax.py")
    if os.path.exists(chk):
        r = subprocess.run([sys.executable, chk], capture_output=True, text=True)
        if r.returncode != 0:
            fail("check_syntax.py FAILED — the calendar will render blank:\n"
                 + (r.stdout + r.stderr).strip())
    else:
        warn("tools/check_syntax.py not found; skipped the syntax gate")

    # ── 1. the site's own logic, via node ─────────────────────────────────────
    probe = run_probe()
    if probe:
        c = probe["counts"]
        print("index.html: %d events, %d zips, %d org→zip, %d org→drive"
              % (c["total"], c["zipCentroids"], c["orgZip"], c["orgDrive"]))
        EV = probe["events"]

        # 1a. distance reachability. eventDist() returns 99 for anything it cannot
        # place, which hides it at every radius except "Any distance".
        stranded = Counter(e["org"] or "(blank)" for e in EV if not e["zipKnown"])
        if stranded:
            fail("%d orgs (%d events) have NO usable zip → eventDist() returns 99 mi, "
                 "hidden at every radius:\n%s"
                 % (len(stranded), sum(stranded.values()),
                    "\n".join("      %4d  %s" % (n, o) for o, n in stranded.most_common())))
        if probe["missingZips"]:
            fail("zips referenced but absent from ZIP_CENTROIDS (→ 99 mi): %s"
                 % ", ".join(probe["missingZips"]))
        at99 = [e for e in EV if e["dist"] >= 99]
        if at99:
            fail("%d events still resolve to >=99 mi: %s"
                 % (len(at99), sorted({e["org"] for e in at99})))
        veryfar = [e for e in EV if 60 < e["dist"] < 99]
        if veryfar:
            warn("%d events resolve to >60 mi (fine if intentional, e.g. Chicago museums): %s"
                 % (len(veryfar), sorted({e["org"] for e in veryfar})))

        # 1b. age reachability, using the site's real ageBuckets()/ageMatches().
        unreachable = Counter()
        for e in EV:
            if (e["age"] or "").strip().lower() in AGE_EXEMPT:
                continue
            if not e["buckets"] and e["type"] != "Storytime":
                unreachable[e["age"]] += 1
        if unreachable:
            fail("%d age strings (%d events) match NO age bucket → hidden whenever any "
                 "age box is ticked:\n%s"
                 % (len(unreachable), sum(unreachable.values()),
                    "\n".join("      %4d  %r" % (n, a) for a, n in unreachable.most_common(15))))

        print("   standout: %d (%.1f%%)   within 10 mi: %d   reachable by the four "
              "young age boxes: %d"
              % (c["standout"], 100.0 * c["standout"] / c["total"],
                 c["within10"], sum(1 for e in EV if e["youngVisible"])))
        print("   by radius: " + "  ".join("<=%s:%d" % (r, c["within" + r])
                                           for r in ("5", "7", "10", "15", "20", "30")))
    else:
        # Fall through to the data-only checks so the run is still useful.
        m_ev = re.search(r"const EVENTS = (\[.*?\]);\n", txt, re.S)
        EV = json.loads(m_ev.group(1)) if m_ev else []
        EV = [{"org": e.get("org", ""), "type": e.get("type", ""), "age": e.get("age", ""),
               "date": e.get("date", ""), "name": e.get("name", ""), "time": e.get("time", ""),
               "cost": e.get("cost", ""), "location": e.get("location", ""), "ownZip": bool(e.get("zip"))}
              for e in EV]

    if not EV:
        fail("no events could be read from index.html")
        report()
        return

    # ── 2. type taxonomy ──────────────────────────────────────────────────────
    orphan_types = Counter(e["type"] or "(blank)" for e in EV if e["type"] not in CANON_TYPES)
    if orphan_types:
        fail("off-taxonomy `type` values → invisible when any type chip is checked:\n%s"
             % "\n".join("      %4d  %r" % (n, t) for t, n in orphan_types.most_common()))

    # ── 3. out-of-scope orgs ──────────────────────────────────────────────────
    banned = Counter(e["org"] for e in EV if e["org"] in BANNED_ORGS)
    if banned:
        fail("out-of-scope orgs present on the live site: %s" % dict(banned))
    camps = [e for e in EV if e["org"].startswith("McHenry County Conservation")
             and e["type"] == "Camps"]
    if camps:
        fail("%d McHenry County Conservation District `Camps` events must be excluded"
             % len(camps))

    # ── 4. required fields + date sanity ──────────────────────────────────────
    for field in ("date", "name", "org", "type"):
        n = sum(1 for e in EV if not e.get(field))
        if n:
            fail("%d events missing required field `%s`" % (n, field))
    baddate = [e["date"] for e in EV if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(e.get("date", "")))]
    if baddate:
        fail("%d events with a malformed date, e.g. %r" % (len(baddate), baddate[:3]))

    dupes = [k for k, n in Counter(
        (e.get("date"), e.get("name"), e.get("org"), e.get("time")) for e in EV).items() if n > 1]
    if dupes:
        warn("%d exact duplicate rows (date+name+org+time), e.g. %r" % (len(dupes), dupes[:2]))

    # Passive month-long items (self-guided scavenger hunts, Book of the Month
    # displays) aren't events: they repeat on every date and crowd the calendar.
    passive = sorted({e["name"] for e in EV
                      if re.search(r"scavenger hunt|i-?spy board|dino hunt|book of the month", e.get("name", ""), re.I)
                      and re.match(r"all day", str(e.get("time", "")), re.I)})
    if passive:
        fail("%d passive all-day items (not events; remove): %r" % (len(passive), passive[:5]))

    # ── 5. intake rules (added 2026-10-02 after a cleanup pass) ────────────────
    import datetime
    today = datetime.date.today().isoformat()
    soon = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
    upcoming = [e for e in EV if e.get("date", "") >= today]

    def span_mins(t):
        m = re.match(r"^(\d{1,2})(?::(\d\d))?\s*(am|pm)\s*[-–]\s*(\d{1,2})(?::(\d\d))?\s*(am|pm)", str(t), re.I)
        if not m:
            return 0
        f = lambda h, mi, ap: (int(h) % 12 + (12 if ap.lower() == "pm" else 0)) * 60 + int(mi or 0)
        return f(m.group(4), m.group(5), m.group(6)) - f(m.group(1), m.group(2), m.group(3))
    all_day_ish = lambda e: re.match(r"all day", str(e.get("time", "")), re.I) or span_mins(e.get("time")) >= 300

    # 5a. month-long passive items ("Spooky Scavenger Hunt - October 1-31").
    MONTHS = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*"
    month_long = sorted({e["name"] for e in upcoming if all_day_ish(e) and re.search(
        MONTHS + r"\s+\d{1,2}\s*[-–]\s*(" + MONTHS + r"\s+)?\d{1,2}\b|\ball month\b|\bmonth[- ]long\b",
        e.get("name", ""), re.I)})
    if month_long:
        fail("%d month-long passive items (not events; remove): %r" % (len(month_long), month_long[:5]))

    # 5b. take-home kits the Crafts tab didn't catch. KIT_RE mirrors the one in
    # index.html (search "const KIT_RE") — keep the two in sync.
    KIT_RE = re.compile(r"(grab|reg)\s*(and|&|'n'|n)\s*go|craft bags?|pick[\s-]?up period|take\s*(and|&|-)?\s*make|take\s*home craft|"
                        r"to[\s-]go\b|stem kit|little play box|\bkit\b", re.I)
    kitish = re.compile(r"\bkits?\b|\bbags?\b|to[\s-]?go|take[\s-]?home|grab|pick[\s-]?up", re.I)
    missed = sorted({"%s @ %s" % (e["name"], e["org"]) for e in upcoming
                     if all_day_ish(e) and e.get("type") != "Museums"
                     and kitish.search(e.get("name", "")) and not KIT_RE.search(e.get("name", ""))})
    if missed:
        warn("%d all-day kit-like items NOT on the Crafts tab (extend KIT_RE in index.html + here, or leave):\n%s"
             % (len(missed), "\n".join("      " + m for m in missed[:15])))

    # 5c. multi-site agencies: the org fallback zip is just their office, which
    # put Ryerson (Riverwoods) at 0 mi from Grayslake. Each event needs its own zip.
    MULTI_SITE = {"Lake County Forest Preserves", "Illinois Department of Natural Resources",
                  "McHenry County Conservation District", "Forest Preserves of Cook County"}
    if "ownZip" in (EV[0] if EV else {}):
        nozip = Counter("%s — %s" % (e["org"], (e.get("location") or "?").split(",")[0])
                        for e in upcoming if e["org"] in MULTI_SITE and not e.get("ownZip"))
        if nozip:
            fail("%d multi-site-agency events have no zip of their own (add \"zip\" for the actual site):\n%s"
                 % (sum(nozip.values()), "\n".join("      %4d  %s" % (n, k) for k, n in nozip.most_common(15))))

    # 5d. free museum / nature-center days must carry real hours for the band.
    RANGE = re.compile(r"^\d{1,2}(:\d\d)?\s*(AM|PM)\s*-\s*\d{1,2}(:\d\d)?\s*(AM|PM)$", re.I)
    nohours = Counter("%s (%s)" % ((e.get("location") or e["org"]).split(",")[0], e.get("time"))
                      for e in upcoming if e.get("type") == "Museums" and re.search("free", e.get("cost", ""), re.I)
                      and not RANGE.match(str(e.get("time", ""))))
    if nohours:
        fail("%d free museum/nature days without a clean 'H:MM AM - H:MM PM' time:\n%s"
             % (sum(nohours.values()), "\n".join("      %4d  %s" % (n, k) for k, n in nohours.most_common(15))))

    # 5e. recurring free-day venues about to run out of dates.
    last = {}
    for e in EV:
        if e.get("type") == "Museums" and re.search("free", e.get("cost", ""), re.I):
            v = (e.get("location") or e["org"]).split(",")[0]
            n, d = last.get(v, (0, ""))
            last[v] = (n + 1, max(d, e.get("date", "")))
    # Where to look up each venue's next free days (official pages only).
    FREE_DAY_SOURCES = {
        "Museum of Science and Industry": "https://www.griffinmsi.org/zipcode-validation",
        "Field Museum": "https://www.fieldmuseum.org/our-events/free-wednesdays",
        "Shedd Aquarium": "https://www.sheddaquarium.org/plan-a-visit/get-tickets/discounts-and-free-hours/illinois-resident-free-hours",
        "Adler Planetarium": "https://www.adlerplanetarium.org/tickets/",
        "Art Institute of Chicago": "https://www.artic.edu/events/6437/uniqlo-third-thursdays",
        "Museum of Contemporary Art Chicago": "https://mcachicago.org/Visit",
        "Chicago History Museum": "http://www.chicagohistory.org/visit-us/",
        "Peggy Notebaert Nature Museum": "https://naturemuseum.org/plan-your-visit",
        "Chicago Botanic Garden": "https://www.chicagobotanic.org/visit/free-admission-opportunities",
        "Lizzadro Museum of Lapidary Art": "https://lizzadromuseum.org/",
    }
    ending = sorted((d, v) for v, (n, d) in last.items() if n >= 4 and today <= d < soon)
    if ending:
        warn("%d recurring free-day venues run out of dates within 30 days — look up the next month:\n%s"
             % (len(ending), "\n".join("      last %s  %s%s" % (d, v, ("  → " + FREE_DAY_SOURCES[v]) if v in FREE_DAY_SOURCES else "")
                                       for d, v in ending)))

    # Near-duplicates: same date+org+start time, one title a word-superset of the
    # other ("DIY Stuffies" vs "DIY Stuffies - Grades K-5"). A parent sees the same
    # event twice. Fix with `python3 tools/dedupe_events.py --write`.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from dedupe_events import find_duplicates
    near = find_duplicates(EV)
    if near:
        fail("%d near-duplicate events (run tools/dedupe_events.py), e.g. %r"
             % (len(near), [EV[i]["name"] for i in near[0]]))

    report()


def report():
    print()
    for m in warns:
        print("WARN  %s" % m)
    for m in fails:
        print("FAIL  %s" % m)
    print()
    if fails:
        print("QA FAILED — %d failure(s), %d warning(s). Do not push." % (len(fails), len(warns)))
        sys.exit(1)
    print("QA PASSED — 0 failures, %d warning(s)." % len(warns))
    sys.exit(0)


if __name__ == "__main__":
    main()
