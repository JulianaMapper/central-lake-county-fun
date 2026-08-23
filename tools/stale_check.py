#!/usr/bin/env python3
"""
Find events that are LIVE on the site but no longer on the source's own calendar.

`merge_intake.py` answers "what's new?" — it dedupes intake against EVENTS and
reports the fresh rows. This answers the opposite question, which nothing else
asks: **what did the source drop?** An event that was real in July and is gone
from the library's calendar in August was cancelled, rescheduled, or renamed.
It stays on the site forever otherwise, because a sweep only ever adds.

  python3 tools/stale_check.py 2026-08-22

Only orgs present in the intake batch are judged. An org nobody re-swept tells
us nothing about its events, so its rows are never reported as missing.

## The confound this script exists to avoid (v1 fell straight into it)

**Intake files are POST-filter.** Every scraper has already dropped adult-only
programming, closures and board meetings before writing its NDJSON. So a naive
"live but not in intake" comparison cannot tell

    the source cancelled this        (real signal)

apart from

    our own filter refused to collect this   (noise)

The first version reported **513 "gone from source"** on the 2026-08-22 batch,
and the list was mostly `Library is Closed`, `Social Worker in the Library` and
adult film clubs — rows the sweep deliberately declined. Three orgs came out at
86–95% "missing", which is not a plausible cancellation rate. Useless as a
cancellation report, and actively misleading.

**The fix:** before calling a live event missing, ask whether today's policy
would even collect it. If it wouldn't, that event is out of scope for this
comparison — it gets reported separately as a **legacy row**, because it is a
different problem (old data predating the current scope) with a different
remedy (a cleanup pass, not a cancellation pull).

So the output has three sections, and they mean different things:
  1. CANCELLED   — the source's own text says so. Highest confidence.
  2. GONE        — in scope today, source no longer lists it. Real signal.
  3. LEGACY      — live but out of scope today. Cleanup list, NOT cancellations.

Output is a REPORT, not an edit. Removing a live event is a judgment call:
a renamed storytime looks identical to a cancelled one from here.
"""
import json, re, sys, os, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, 'index.html')

# A source that returned almost nothing is a broken scrape, not a mass
# cancellation. Below this many rows for an org, we refuse to judge it.
MIN_ROWS = 5
# ...and if a swept org lost more than this share of its live events, that is
# far likelier to be a parser regression than the library cancelling its fall.
# 0.50 rather than 0.60: Crystal Lake came in at 59% on the 2026-08-22 batch and
# was a partial scrape (the agent reported its Oct–Dec months as thin), so the
# first threshold sat just above a case it needed to catch.
SUSPICIOUS_LOSS = 0.50

CANCEL = re.compile(r'cancel|postpon|rescheduled|\bmoved to\b', re.I)

# ── Would today's sweep even collect this live event?
#
# These mirror the DROP rules the scrapers apply (CLAUDE.md SWEEP RUNBOOK step 5
# + intake/SCHEMA.md). They are deliberately conservative: a row only counts as
# out-of-scope on a POSITIVE match here. Anything ambiguous stays in scope, so
# the worst case is a false "gone" — visible and checkable — rather than
# silently excusing a real cancellation.
OUT_OF_SCOPE = re.compile(
    r'librar(?:y|ies) (?:is |are )?closed|\bclosed\b|closing early|late opening|'
    r'holiday hours|no school|'
    r'board (?:meeting|of trustees)|trustee|committee|commission|zoning|'
    r'friends of the library (?:meeting|book|drive)|book sale|'
    r'blood drive|fundrais|\bgala\b|golf outing|'
    r'social worker|notary|tax (?:help|assistance)|medicare|aarp|'
    r'job (?:fair|club)|r[ée]sum[ée]|\besl\b|citizenship|diploma|'
    r'senior|\b55\+|\b21\+|wine|beer|cocktail|'
    r'book club|book discussion|film discussion|great books|'
    r'genealogy|knitting circle|\bbunco\b',
    re.I)

# An age string that names ONLY adults. "Teens, Adults" is in scope (teens);
# "Early Childhood + Adults" is a caregiver event, also in scope.
ADULT_ONLY = re.compile(r'^\s*adults?(?:\s*\(?1[89]\+?\)?)?\s*$|^\s*adults? only\s*$', re.I)


# An age string that names a young audience. This OUTRANKS the title keywords
# below, because the title is a weak signal and the age tag is an explicit one.
YOUTH_AGE = re.compile(
    r'\bkids?\b|child|baby|babies|infant|toddler|preschool|pre-?k|'
    r'\bteens?\b|tween|young adult|\bya\b|grade|middle school|high school|'
    r'famil|all ages|everyone|youth|early childhood|elementary|homeschool', re.I)


def in_scope_today(e):
    """True if the CURRENT collection policy would still gather this event."""
    age = e.get('age', '') or ''
    if ADULT_ONLY.match(age):
        return False
    # ⚠️ Age tag beats title keywords. "Panel to Panel: A Graphic Novel Book Club"
    # tagged `Kids`, "High School Book Club" and "In the Middle Book Club
    # (grades 6-8)" are all IN SCOPE since 2026-08-04 — but `book club` is in the
    # out-of-scope pattern below because ADULT book clubs are the common case.
    # Without this precedence rule the checker mislabels real kids' and teen
    # programming as legacy cruft and quietly recommends deleting it.
    if YOUTH_AGE.search(age):
        return True
    if OUT_OF_SCOPE.search(e.get('name', '')):
        return False
    # A paid event is only collected when it's homeschool programming
    # (the 2026-08-04 fee exemption). Everything else is free-only.
    cost = (e.get('cost', '') or '').strip()
    if cost and not re.search(r'free', cost, re.I):
        if e.get('audience') != 'homeschool' and \
           not re.search(r'homeschool', e.get('name', ''), re.I):
            return False
    return True


def load_events():
    s = open(INDEX, encoding='utf-8').read()
    i = s.index('const EVENTS = [')
    j = s.index('const PARKS')
    blob = s[i + len('const EVENTS = '):j].rstrip().rstrip(';')
    return json.loads(blob)


def key(date, name, org):
    return (date, name.strip().lower(), org.strip().lower())


# ── Title drift: the THIRD confound, found on the 2026-08-22 batch.
#
# Exact-title matching claimed Deerfield had cancelled 95% of its fall calendar.
# It hadn't — this sweep's scrapers fold the age/grade text into the name:
#
#     live "Screen Printing"   vs  intake "Screen Printing (Makerspace)"
#     live "Perler Beads"      vs  intake "Perler Beads & Snow Cones"
#     live "Kids Taste Test"   vs  intake "Kids Taste Test: Jelly Belly"
#
# Same event, different label. So a live event counts as STILL LISTED when its
# normalized token set is a subset of some intake title on the same date+org
# (or vice versa). Requires >= 2 tokens so a one-word title can't match
# everything.
def norm_title(n):
    n = n.lower()
    n = re.sub(r'\s*[-–—]\s*\[[^\]]*\]', '', n)   # "- [In Person]"
    n = re.sub(r'\s*\([^)]*\)', '', n)            # "(Makerspace)"
    n = re.sub(r'[^a-z0-9]+', ' ', n)
    return tuple(sorted(set(n.split())))


def still_listed(live_name, intake_titles):
    """intake_titles: list of token-tuples for the same date+org."""
    lt = set(norm_title(live_name))
    if not lt:
        return False
    for cand in intake_titles:
        ct = set(cand)
        if lt == ct:
            return True
        if len(lt) >= 2 and lt <= ct:
            return True
        if len(ct) >= 2 and ct <= lt:
            return True
    return False


def main(stamp):
    intake_dir = os.path.join(ROOT, 'intake', stamp)
    if not os.path.isdir(intake_dir):
        sys.exit(f"no intake dir: {intake_dir}")

    rows = []
    for fn in sorted(os.listdir(intake_dir)):
        if not fn.endswith('.ndjson') or fn.startswith('_'):
            continue
        with open(os.path.join(intake_dir, fn), encoding='utf-8') as f:
            for ln in f:
                if ln.strip():
                    rows.append(json.loads(ln))

    if not rows:
        sys.exit("intake batch is empty — nothing to compare against")

    swept = collections.Counter(r['org'].strip().lower() for r in rows)
    seen = {key(r['date'], r['name'], r['org']) for r in rows}
    # date+org -> normalized titles, for drift-tolerant matching
    by_day = collections.defaultdict(list)
    for r in rows:
        by_day[(r['date'], r['org'].strip().lower())].append(norm_title(r['name']))
    # (org, YYYY-MM) actually covered by this sweep — the FOURTH guard. A scraper
    # that only reached October cannot testify about November: several sources
    # publish a few months at a time, and an org's later months coming back thin
    # is a coverage limit, not the library cancelling its winter.
    swept_months = {(r['org'].strip().lower(), r['date'][:7]) for r in rows}
    dates = [r['date'] for r in rows]
    lo, hi = min(dates), max(dates)
    print(f"intake {stamp}: {len(rows)} rows, {len(swept)} orgs, window {lo}..{hi}\n")

    # ── 1. explicit cancellations the sources are announcing
    flagged = [r for r in rows if CANCEL.search(r['name']) or CANCEL.search(r.get('notes', ''))]
    if flagged:
        print(f"CANCELLED / MOVED — {len(flagged)} intake rows say so in their own text.")
        print("  These should NOT be injected; if a matching event is already live, pull it.")
        for r in sorted(flagged, key=lambda x: x['date']):
            live = " [ALREADY LIVE]" if key(r['date'], r['name'], r['org']) in \
                {key(e['date'], e['name'], e['org']) for e in load_events()} else ""
            print(f"  {r['date']}  {r['org'][:34]:34}  {r['name'][:52]}{live}")
        print()
    else:
        print("CANCELLED / MOVED — no intake row announces a cancellation.\n")

    # ── 2. live events the source no longer lists, split by whether today's
    #       policy would even collect them. See the confound note in the docstring.
    ev = load_events()
    per_org_live = collections.Counter()
    missing = collections.defaultdict(list)      # in scope today -> real signal
    legacy = collections.defaultdict(list)       # out of scope   -> cleanup list

    for e in ev:
        org = e['org'].strip().lower()
        if org not in swept:
            continue                      # not re-swept — we know nothing
        if not (lo <= e['date'] <= hi):
            continue                      # outside what the sweep even looked at
        if (org, e['date'][:7]) not in swept_months:
            continue                      # that month wasn't covered — no testimony
        if key(e['date'], e['name'], e['org']) in seen:
            continue                      # still listed — fine
        if still_listed(e['name'], by_day.get((e['date'], org), [])):
            continue                      # listed under a drifted title
        if in_scope_today(e):
            per_org_live[org] += 1
            missing[org].append(e)
        else:
            legacy[org].append(e)

    # in-scope live totals, for an honest denominator
    for e in ev:
        org = e['org'].strip().lower()
        if org not in swept or not (lo <= e['date'] <= hi) or not in_scope_today(e):
            continue
        if (org, e['date'][:7]) not in swept_months:
            continue
        if key(e['date'], e['name'], e['org']) in seen or \
                still_listed(e['name'], by_day.get((e['date'], org), [])):
            per_org_live[org] += 1

    total_missing = sum(len(v) for v in missing.values())
    print(f"GONE FROM SOURCE — {total_missing} live events in {lo}..{hi} that are "
          f"in scope today but their own org no longer lists.\n"
          f"  (rows the current policy wouldn't collect are excluded here and "
          f"reported as LEGACY below)\n")

    for org in sorted(missing, key=lambda o: -len(missing[o])):
        gone, live = len(missing[org]), per_org_live[org]
        name = missing[org][0]['org']
        if swept[org] < MIN_ROWS:
            print(f"  ~ {name}: {gone}/{live} missing — SKIPPED, sweep only "
                  f"returned {swept[org]} rows (likely a broken scrape)")
            continue
        share = gone / max(live, 1)
        warn = "  ⚠️ SUSPICIOUS — check the parser before deleting anything" \
            if share >= SUSPICIOUS_LOSS else ""
        print(f"  {name}: {gone}/{live} missing ({share*100:.0f}%){warn}")
        for e in sorted(missing[org], key=lambda x: x['date'])[:12]:
            print(f"      {e['date']}  {e['name'][:60]}")
        if gone > 12:
            print(f"      ... and {gone - 12} more")
        print()

    # ── 3. legacy rows: live, but the current scope wouldn't collect them
    total_legacy = sum(len(v) for v in legacy.values())
    print(f"\nLEGACY / OUT-OF-SCOPE — {total_legacy} live events in {lo}..{hi} that "
          f"today's policy would not collect.\n"
          f"  These are NOT cancellations. They predate the current scope "
          f"(closures, board meetings,\n  adult-only programming, paid non-homeschool "
          f"events). Separate cleanup decision.\n")
    for org in sorted(legacy, key=lambda o: -len(legacy[o]))[:12]:
        rows_ = legacy[org]
        print(f"  {rows_[0]['org']}: {len(rows_)}")
        for e in sorted(rows_, key=lambda x: x['date'])[:5]:
            print(f"      {e['date']}  {e['name'][:60]}")
        if len(rows_) > 5:
            print(f"      ... and {len(rows_) - 5} more")
    if len(legacy) > 12:
        print(f"  ... and {len(legacy) - 12} more orgs")

    print("\nNothing was modified. Renames and cancellations look identical from here,\n"
          "so deciding what to pull from index.html is a human call.")


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
