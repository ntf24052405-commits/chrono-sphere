#!/usr/bin/env python3
"""Collects Indian tax / GST / company-law deadline news into data/feed.json.
Standard library only. Run by GitHub Actions every ~15 minutes.
  python scripts/fetch_feeds.py                      -> refresh data/feed.json
  python scripts/fetch_feeds.py --stamp FILE.json    -> add a "checked" time to FILE.json
"""
import hashlib, json, re, sys, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

OUT = Path('data/feed.json')
KEEP_DAYS, MAX_ITEMS, TIMEOUT = 120, 700, 25
UA = 'Mozilla/5.0 (compatible; ChronoSphereBot/1.0)'

# Google News RSS searches, India edition (free, no key). Add or remove topics freely.
TOPICS = [
    'income tax due date extended', 'ITR due date extension CBDT', 'tax audit report due date',
    'advance tax due date', 'TDS due date extended', 'form 3CEB due date',
    'GST due date extended', 'GSTR-3B due date', 'GSTR-1 GSTR-9 due date extension',
    'GST amnesty last date', 'CBIC circular extension', 'CBDT circular extension',
    'state GST due date extended flood', 'MCA last date extended companies',
    'ROC filing due date extended LLP', 'MSME-1 DPT-3 due date', 'ICAI extension deadline',
    'SEBI extends deadline', 'RBI extends deadline', 'EPFO ESIC due date extended',
    'customs notification extended till',
]
def gnews(q):
    return ('https://news.google.com/rss/search?q=' + urllib.parse.quote(q + ' when:14d') +
            '&hl=en-IN&gl=IN&ceid=IN:en')
DIRECT_RSS = [('https://taxguru.in/feed/', 'taxguru.in')]            # publisher feeds (best effort)
LEGACY_PAGE = 'https://ntf24052405-commits.github.io/ca-news/'       # your original CA Live Update page

RELEVANT = re.compile(r'tax|gst|itr\b|tds|tcs|sebi|rbi\b|icai|icsi|icmai|chartered|\bmca\b|nclt|\broc\b|llp|customs|'
    r'duty|cbdt|cbic|compan|compliance|audit|return|filing|\bform\b|circular|nfra|kyc|\bibc\b|insolvency|\bexam|'
    r'registration|portal|income|refund|e-?invoice|penalty|annual|dgft|epfo|esic|msme|ibbi|scheme|debt|deadline|'
    r'due date|extend', re.I)

CATS = [
    ('GST', r'\bgst|gstr|cbic|e-?invoice|e-?way'),
    ('Income Tax', r'income[- ]tax|\bitr\b|\btds\b|\btcs\b|cbdt|advance tax|tax audit|form 26as|\b3c[abde]+\b'),
    ('Companies Act', r'\bmca\b|companies act|\broc\b|\bllp\b|nclt|aoc-?4|mgt-?7|dir-?3|adt-?1|dpt-?3|msme-?1|\bibc\b|insolvency'),
    ('Markets & Regulators', r'sebi|\brbi\b|fema|\bfla\b|icai|icsi|icmai|epfo|esic|customs|dgft'),
]
def categorize(t):
    for name, rx in CATS:
        if re.search(rx, t, re.I): return name
    return 'Other'

def key_of(t): return re.sub(r'\W+', '', t.lower())[:80]

def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': '*/*'})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read()

def parse_rss(data, default_src):
    out = []
    for it in ET.fromstring(data).iter('item'):
        title = (it.findtext('title') or '').strip()
        link = (it.findtext('link') or '').strip()
        if not title or not link: continue
        el = it.find('source')
        src = (el.text or '').strip() if el is not None and el.text else default_src
        try: dt = parsedate_to_datetime(it.findtext('pubDate')).astimezone(timezone.utc)
        except Exception: dt = datetime.now(timezone.utc)
        if src and title.endswith(' - ' + src): title = title[:-(len(src) + 3)].strip()
        out.append({'t': title, 'u': link, 's': src, 'c': categorize(title),
                    'd': dt.strftime('%Y-%m-%d'), 'ts': int(dt.timestamp())})
    return out

def parse_legacy(data):
    m = re.search(r'var D=(\[[\s\S]*?\]),cat=', data.decode('utf-8', 'replace'))
    if not m: raise ValueError('legacy format changed')
    return json.loads(m.group(1).replace('<\\/', '</'))

def load():
    try: return json.loads(OUT.read_text(encoding='utf-8'))
    except Exception: return {}

def main():
    if len(sys.argv) >= 3 and sys.argv[1] == '--stamp':
        p = Path(sys.argv[2]); j = json.loads(p.read_text(encoding='utf-8'))
        j['checked'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
        p.write_text(json.dumps(j, ensure_ascii=False, separators=(',', ':')), encoding='utf-8'); return

    prev = load(); fresh = []; ok = 0; bad = 0
    jobs = [(gnews(q), 'Google News', parse_rss) for q in TOPICS] + \
           [(u, s, parse_rss) for u, s in DIRECT_RSS] + [(LEGACY_PAGE, 'CA Live Update', None)]
    for url, name, parser in jobs:
        try:
            data = get(url)
            fresh += parser(data, name) if parser else parse_legacy(data)
            ok += 1
        except Exception as e:
            bad += 1; print('skip', name, str(e)[:80])
        time.sleep(0.4)
    print('sources ok:', ok, 'failed:', bad, 'items fetched:', len(fresh))
    if not ok:
        print('No source reachable - keeping the previous feed.'); return

    now = datetime.now(timezone.utc); cutoff = (now - timedelta(days=KEEP_DAYS)).timestamp()
    merged = {}
    for x in (prev.get('items') or []) + fresh:                 # fresh items overwrite older copies
        t = (x.get('t') or '').strip()
        if not t or not RELEVANT.search(t): continue
        x['ts'] = int(x.get('ts') or now.timestamp())
        if x['ts'] < cutoff: continue
        merged[key_of(t)] = x
    items = sorted(merged.values(), key=lambda x: x['ts'], reverse=True)[:MAX_ITEMS]
    sig = hashlib.sha1('|'.join(sorted(key_of(x['t']) for x in items)).encode()).hexdigest()
    if sig == prev.get('sig'):
        print('No new headlines - file unchanged.'); return
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({'updated': now.isoformat(timespec='seconds'), 'sig': sig, 'count': len(items), 'items': items},
                              ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print('Wrote', len(items), 'items')

if __name__ == '__main__':
    main()
