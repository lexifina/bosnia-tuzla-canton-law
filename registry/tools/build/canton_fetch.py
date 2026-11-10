"""Bosnian cantons: fetch a canton's official gazette (every issue as a PDF, from the canton's own site) into <src>.
Shared by the canton refresh runners (fetch_tk.py, fetch_zdk.py, fetch_sbk.py, fetch_bpk.py). Private.

    python -X utf8 fetch_<cc>.py list --src DIR       # re-read the gazette page: <src>/listing.json
    python -X utf8 fetch_<cc>.py pdfs --src DIR [--years 2022-2026] [--limit N]   # fetch listed PDFs not cached yet

listing.json: [{"url", "text" (the link text), "year" (from the link, when it names one)}] in page order.
by-url/<sha256(url)>: the bytes. requests.jsonl: one line per request. At most one request per --interval seconds
(default 0.6, under 2 a second). Stops on 403/429, two failures in a row, or a challenge page (writes <src>/STOP).
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import time
import urllib.parse
from pathlib import Path

import requests

UA = 'lexifina-watch/1.0 (+https://lexifina.com/watch; corpus@lexifina.com)'

CANTONS = {
    'tk': {'page': 'https://skupstinatk.gov.ba/sluzbene-novine-tk', 'base': 'https://skupstinatk.gov.ba/',
           'keep': r'(?i)/sl_novine/', 'drop': r'(?i)^$'},
    'zdk': {'page': 'https://zdk.ba/preuzimanja/sluzbene-novine', 'base': 'https://zdk.ba/',
            'advlisting': True, 'keep': r'(?i)slzdk', 'drop': r'(?i)-hr(-\d)?\s*$'},  # the Bosnian edition (bs, or bs-hr before 2003)
    'sbk': {'page': 'https://sbk-ksb.gov.ba/index.php/dokumenti', 'base': 'https://sbk-ksb.gov.ba/',
            'keep': r'(?i)novine|SN%20|/sluzbene/', 'drop': r'(?i)oglasi|strategij|akcioni|arhiv|plan|ustav'},
    'bpk': {'page': 'https://bpkg.gov.ba/sluzbene-novine/7102/sluzbene-novine-bpk-gorazde', 'base': 'https://bpkg.gov.ba/',
            'keep': r'(?i)novine|broj|sl-nov', 'drop': r'(?i)poslovnik|ekspoze'},
}


class Get:
    def __init__(self, src: Path, interval: float):
        self.src, self.iv, self.last, self.bad = src, interval, 0.0, 0
        self.s = requests.Session()
        self.s.headers['User-Agent'] = UA

    def path(self, url: str) -> Path:
        return self.src / 'by-url' / hashlib.sha256(url.encode()).hexdigest()

    def stop(self, why: str):
        (self.src / 'STOP').write_text(why + '\n', encoding='utf-8')
        raise SystemExit('stop: ' + why)

    def get(self, url: str, refresh: bool = False) -> Path | None:
        p = self.path(url)
        if p.exists() and not refresh:
            return p
        w = self.iv - (time.time() - self.last)
        if w > 0:
            time.sleep(w)
        try:
            r = self.s.get(url, timeout=180)
            code = r.status_code
        except requests.RequestException:
            code, r = 0, None
        self.last = time.time()
        with open(self.src / 'requests.jsonl', 'a', encoding='utf-8') as f:
            f.write(json.dumps({'t': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'url': url, 'code': code}) + '\n')
        if code in (403, 429):
            self.stop(f'{code} on {url}')
        if code == 0 or code >= 500:
            self.bad += 1
            if self.bad >= 3:
                self.stop(f'three failures in a row ({code}) on {url}')
            time.sleep(20)
            return self.get(url, refresh)
        self.bad = 0
        if code != 200:
            print('skip', code, url, flush=True)
            return None
        head = r.content[:4000].lower()
        if b'just a moment' in head or b'captcha' in head or b'cf-chl' in head:
            self.stop(f'challenge page on {url}')
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix('.part')
        tmp.write_bytes(r.content)
        tmp.replace(p)
        return p


def listing(cc: str, g: Get) -> list[dict]:
    cfg = CANTONS[cc]
    t = g.get(cfg['page'], refresh=True).read_text(encoding='utf-8', errors='replace')
    out, seen = [], set()
    if cfg.get('advlisting'):
        for fid, name, day in re.findall(r'fileId=(\d+)"[^>]*>\s*([^<]+?)</a></td>\s*<td>([^<]*)</td>', t):
            url = f'{cfg["base"]}component/advlisting/?view=download&format=raw&fileId={fid}'
            m = re.search(r'(\d{4})', name)
            if re.search(cfg['keep'], name) and not re.search(cfg['drop'], name) and url not in seen:
                seen.add(url)
                out.append({'url': url, 'text': name.strip(), 'year': int(m.group(1)) if m else None, 'listed': day})
        return out
    for href, text in re.findall(r'<a[^>]+href="([^"]+\.pdf)"[^>]*>(.*?)</a>', t, re.I | re.S):
        href = html.unescape(href)
        url = urllib.parse.urljoin(cfg['base'], href) if not href.startswith('http') else href
        url = url.replace(' ', '%20')
        # three 2004 links still name the Assembly's old host (it answers 502); the same files are on its current host
        url = url.replace('http://www.skupstinatk.kim.ba/', 'https://skupstinatk.gov.ba/')
        txt = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', text))).strip()
        if not re.search(cfg['keep'], url + ' ' + txt) or re.search(cfg['drop'], url + ' ' + txt):
            continue
        if url in seen:
            if txt and txt not in ('Preuzmi', '<br />'):
                for o in out:
                    if o['url'] == url and o['text'] in ('', 'Preuzmi', '<br />'):
                        o['text'] = txt
            continue
        seen.add(url)
        m = re.search(r'/(19\d\d|20\d\d)/', url) if cc == 'tk' else None
        out.append({'url': url, 'text': txt, 'year': int(m.group(1)) if m else None})
    return out


def main(cc: str):
    ap = argparse.ArgumentParser()
    ap.add_argument('what', choices=['list', 'pdfs'])
    ap.add_argument('--src', required=True)
    ap.add_argument('--interval', type=float, default=0.6)
    ap.add_argument('--years')
    ap.add_argument('--only', help='a file of URLs to fetch (one per line)')
    a = ap.parse_args()
    try:
        import psutil
        psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
    except Exception:
        pass
    src = Path(a.src)
    src.mkdir(parents=True, exist_ok=True)
    (src / 'STOP').unlink(missing_ok=True)
    g = Get(src, a.interval)
    if a.what == 'list':
        rows = listing(cc, g)
        if len(rows) < 50:
            g.stop(f'the gazette page lists only {len(rows)} PDFs')
        (src / 'listing.json').write_text(json.dumps(rows, ensure_ascii=False, indent=0) + '\n', encoding='utf-8')
        st_p = src / 'refresh-state.json'
        st = json.loads(st_p.read_text()) if st_p.exists() else {}
        st.update(listing_read=time.strftime('%Y-%m-%d', time.gmtime()), listed=len(rows))
        st_p.write_text(json.dumps(st, indent=1), encoding='utf-8')
        print(len(rows), 'PDFs listed')
        return
    rows = json.loads((src / 'listing.json').read_text(encoding='utf-8'))
    want = None
    if a.only:
        want = set(Path(a.only).read_text(encoding='utf-8').split())
    elif a.years:
        y0, y1 = (int(x) for x in a.years.split('-'))
        want = {r['url'] for r in rows if r.get('year') and y0 <= r['year'] <= y1}
    todo = [r['url'] for r in rows if want is None or r['url'] in want]
    n = 0
    for i, u in enumerate(todo):
        if not g.path(u).exists():
            g.get(u)
            n += 1
        if i % 25 == 0:
            print(i, len(todo), flush=True)
    print('fetched', n, 'of', len(todo))
