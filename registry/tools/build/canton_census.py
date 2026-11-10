"""Census of a canton's gazette: for every fetched issue, its text layer and the laws the Assembly published in it
(a 'ZAKON' heading followed by its title), classed as base law, amending law, consolidated text or budget law.
Private (measurement for the audit and the refresh runner's index scan).

    python -X utf8 canton_census.py --src DIR [--out census.json] [--workers 3]

Writes <src>/gazette-census.json: {"issues": [{"url", "text", "year", "pages", "chars", "scanned", "laws": [...]}],
"by_year": {year: {"issues", "scanned", "laws", "base", "amending", "consolidated", "budget"}}}.
A page with fewer than 200 characters of text counts as an image; an issue whose pages are mostly images is
"scanned" (its laws cannot be counted without OCR). Deterministic.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ZAKON = re.compile(r'^\s*(Z\s?A\s?K\s?O\s?N|З\s?А\s?К\s?О\s?Н|ZAKONA?)\s*$')
TITLE_START = re.compile(r'^\s*(O|О|o|о)\s+\S')
CONS = re.compile(r'(?i)pre[čc]i[šs][ćc]en|пре[чц]и[шс][ћц]ен')
AMEND = re.compile(r'(?i)izmjen|izmen|dopun|измјен|измен|допун|prestank|престанк')
BUDGET = re.compile(r'(?i)bud[žz]et|prora[čc]un|буџет|izvr[šs]avanju')


def read(path: str) -> dict:
    try:
        return _read(path)
    except Exception as e:  # noqa: BLE001  (a library exception may not pickle back to the parent)
        return {'error': f'{type(e).__name__}: {str(e)[:120]}'}


def _read(path: str) -> dict:
    import pymupdf
    try:
        doc = pymupdf.open(path)
    except Exception as e:  # noqa: BLE001
        return {'error': f'{type(e).__name__}'}
    pages, chars, img_pages, laws = doc.page_count, 0, 0, []
    for pg in doc:
        t = pg.get_text()
        chars += len(t)
        if len(t.strip()) < 200:
            img_pages += 1
            continue
        lines = [l.strip() for l in t.split('\n')]
        for i, l in enumerate(lines):
            if ZAKON.match(l):
                nxt = [x for x in lines[i + 1:i + 6] if x][:3]
                if nxt and TITLE_START.match(nxt[0]):
                    title = ' '.join(nxt)
                    title = re.split(r'\s(?:Član|Члан|Članak|Чланак|DIO|POGLAVLJE|I\s)', title)[0][:200]
                    laws.append(title)
    def cls(t):
        if BUDGET.search(t):
            return 'budget'
        if CONS.search(t):
            return 'consolidated'
        if AMEND.search(t):
            return 'amending'
        return 'base'
    return {'pages': pages, 'chars': chars, 'scanned': pages > 0 and img_pages / pages > 0.5,
            'laws': [{'title': t, 'class': cls(t)} for t in laws]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', required=True)
    ap.add_argument('--out')
    ap.add_argument('--workers', type=int, default=3)
    a = ap.parse_args()
    try:
        import psutil
        psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
    except Exception:
        pass
    src = Path(a.src)
    rows = json.loads((src / 'listing.json').read_text(encoding='utf-8'))
    todo = []
    for r in rows:
        p = src / 'by-url' / hashlib.sha256(r['url'].encode()).hexdigest()
        if p.exists():
            todo.append((r, str(p)))
    with ProcessPoolExecutor(a.workers) as ex:
        res = list(ex.map(read, [p for _, p in todo], chunksize=4))
    issues = []
    by = defaultdict(lambda: defaultdict(int))
    for (r, p), x in zip(todo, res):
        year = r.get('year')
        if not year:
            m = re.search(r'(19\d\d|20\d\d)', r['text'] or '') or re.search(r'[-_ ](\d{2})(?:\D*)\.pdf$', r['url'])
            year = int(m.group(1)) if m and len(m.group(1)) == 4 else (2000 + int(m.group(1)) if m and int(m.group(1)) < 50 else 1900 + int(m.group(1)) if m else None)
        issues.append({**r, 'year': year, **x})
        b = by[str(year)]
        b['issues'] += 1
        if x.get('scanned') or x.get('error'):
            b['scanned'] += 1
        for l in x.get('laws', []):
            b['laws'] += 1
            b[l['class']] += 1
    out = Path(a.out) if a.out else src / 'gazette-census.json'
    out.write_text(json.dumps({'issues': issues, 'by_year': {k: dict(v) for k, v in sorted(by.items())}},
                              ensure_ascii=False, indent=0) + '\n', encoding='utf-8')
    print(json.dumps({k: dict(v) for k, v in sorted(by.items())}))


if __name__ == '__main__':
    main()
