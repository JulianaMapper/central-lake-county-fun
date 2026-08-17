#!/usr/bin/env node
/* Extracts the SITE'S OWN filter functions out of index.html and runs them against
 * the SITE'S OWN data, then prints one JSON blob of derived facts on stdout for
 * tools/qa_check.py to apply policy to.
 *
 * Why this exists: qa_check.py used to carry hand-written Python re-implementations
 * of ageBuckets() and eventDist(). That is the classic QA trap — the checker drifts
 * away from the thing it is checking, and then it passes while the site is broken,
 * which is worse than having no checker at all. There is exactly one copy of this
 * logic now, in index.html, and this file borrows it verbatim.
 *
 * The site is a single self-contained HTML file by design (GitHub Pages, no build
 * step), so there is no module to import — extraction by regex is the price of that,
 * and every extraction is asserted below rather than silently skipped.
 *
 * Usage:  node tools/qa_probe.js            (from anywhere; paths are resolved)
 * Output: {"ok":true, "events":[{i,org,age,type,buckets,dist,zip}], "counts":{...}}
 *         {"ok":false,"error":"..."}  on any extraction failure
 */
'use strict';
const fs = require('fs');
const path = require('path');

const ROOT = path.dirname(path.dirname(path.resolve(__filename)));
const INDEX = path.join(ROOT, 'index.html');
const HOME_ZIP = '60030';

function die(msg) {
  process.stdout.write(JSON.stringify({ ok: false, error: msg }) + '\n');
  process.exit(2);
}

let src;
try {
  src = fs.readFileSync(INDEX, 'utf8');
} catch (e) {
  die('cannot read ' + INDEX + ': ' + e.message);
}

// ── extract, asserting each one. A silent miss here would fake a pass. ──────────
function grab(re, label) {
  const m = src.match(re);
  if (!m) die('could not extract ' + label + ' from index.html — did it get renamed? '
              + 'Update tools/qa_probe.js to match.');
  return m[0];
}
function grabJSON(re, label) {
  const m = src.match(re);
  if (!m) die('could not extract ' + label + ' from index.html');
  try {
    return JSON.parse(m[1]);
  } catch (e) {
    die(label + ' is not valid JSON: ' + e.message);
  }
}
function grabObj(re, label) {
  const m = src.match(re);
  if (!m) die('could not extract ' + label + ' from index.html');
  try {
    // these literals use bare keys and/or single quotes
    return eval('(' + m[1] + ')');
  } catch (e) {
    die(label + ' did not evaluate: ' + e.message);
  }
}

const EVENTS = grabJSON(/const EVENTS = (\[[\s\S]*?\]);\n/, 'EVENTS');
const ZIP_CENTROIDS = grabObj(/const ZIP_CENTROIDS = (\{[\s\S]*?\});/, 'ZIP_CENTROIDS');
const ORG_ZIP = grabObj(/const ORG_ZIP = (\{[\s\S]*?\});/, 'ORG_ZIP');
const ORG_DRIVE = grabObj(/const ORG_DRIVE = (\{[\s\S]*?\});/, 'ORG_DRIVE');

// The real functions, verbatim. Evaluated together so their consts share scope.
const SNIPPETS = [
  grab(/const BUCKET_YEARS = \{[^}]*\};/, 'BUCKET_YEARS'),
  grab(/function addAgeSpan\(set, lo, hi\) \{[\s\S]*?\n\}/, 'addAgeSpan()'),
  grab(/function ageBuckets\(age\) \{[\s\S]*?\n  return out;\n\}/, 'ageBuckets()'),
  grab(/function matchesAudience\(e, want\) \{[\s\S]*?\n\}/, 'matchesAudience()'),
  grab(/function ageMatches\(e, want\) \{[\s\S]*?\n  return false;\n\}/, 'ageMatches()'),
  grab(/function haversineZip\([^)]*\)\{[\s\S]*?\n?\}/, 'haversineZip()'),
  grab(/function eventDist\(e\)\{[\s\S]*?\n?\}/, 'eventDist()'),
].join('\n');

let API;
try {
  // eventDist() closes over `userZipCoords`; the page sets it from the zip box.
  // null is the default (origin = 60030), which is what we want to audit against.
  API = eval('(function(){ var userZipCoords = null;\n' + SNIPPETS
             + '\nreturn {ageBuckets, ageMatches, eventDist, haversineZip}; })()');
} catch (e) {
  die('extracted functions failed to evaluate: ' + e.message
      + ' — the extraction regexes in tools/qa_probe.js are probably out of date.');
}
for (const fn of ['ageBuckets', 'ageMatches', 'eventDist', 'haversineZip']) {
  if (typeof API[fn] !== 'function') die('extracted ' + fn + ' is not a function');
}

// ── self-test: prove the borrowed logic behaves, so a regex that matched the
//    wrong block cannot quietly produce an all-clear. ───────────────────────────
const SELFTEST = [
  ['Teens, Kids, Family, Adults', ['elementary', 'family', 'preschool', 'teen']],
  ['Ages 0-1',                    ['baby']],
  ['Teens Grades 6th - 12th',     ['teen']],
  ['Grades 3-5',                  ['elementary']],
  ['ages 0-36 months',            ['baby']],
  ['All',                         ['family']],
];
for (const [input, want] of SELFTEST) {
  const got = [...API.ageBuckets(input)].sort();
  if (got.join(',') !== want.join(',')) {
    die('SELF-TEST FAILED on ' + JSON.stringify(input)
        + ': expected [' + want + '] got [' + got + ']. Either ageBuckets() changed '
        + 'behaviour (update the SELFTEST table in tools/qa_probe.js if that was '
        + 'deliberate) or the extraction grabbed the wrong code.');
  }
}
if (!ZIP_CENTROIDS[HOME_ZIP]) die('home zip ' + HOME_ZIP + ' missing from ZIP_CENTROIDS');

// ── derive the facts python needs ──────────────────────────────────────────────
const out = EVENTS.map((e, i) => {
  const zip = String(e.zip || ORG_ZIP[e.org] || '');
  return {
    i,
    org: e.org || '',
    name: e.name || '',
    date: e.date || '',
    type: e.type || '',
    age: e.age || '',
    cost: e.cost || '',
    time: e.time || '',
    zip: zip,
    zipKnown: !!(zip && ZIP_CENTROIDS[zip]),
    buckets: [...API.ageBuckets(e.age)].sort(),
    dist: Math.round(API.eventDist(e) * 100) / 100,
    // what her default four age boxes actually resolve to
    youngVisible: ['baby', 'preschool', 'elementary', 'family'].some(w => API.ageMatches(e, w)),
  };
});

const counts = {};
for (const r of [5, 7, 10, 15, 20, 30]) counts['within' + r] = out.filter(e => e.dist <= r).length;
counts.total = out.length;
counts.zipCentroids = Object.keys(ZIP_CENTROIDS).length;
counts.orgZip = Object.keys(ORG_ZIP).length;
counts.orgDrive = Object.keys(ORG_DRIVE).length;
counts.standout = EVENTS.filter(e => e.standout).length;

// zips referenced anywhere but absent from the centroid table
const referenced = new Set(Object.values(ORG_ZIP).map(String)
  .concat(EVENTS.filter(e => e.zip).map(e => String(e.zip))));
const missingZips = [...referenced].filter(z => z && !ZIP_CENTROIDS[z]).sort();

process.stdout.write(JSON.stringify({
  ok: true, counts, missingZips, events: out,
}) + '\n');
