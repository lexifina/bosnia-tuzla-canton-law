"""Bosnian cantons, romania-law standard (2026-11-09): every Assembly law in every fetched gazette issue, against main.
Shared by the four canton refresh runners. Private (never published).

    python -X utf8 canton_build.py scan   --cc tk --src DIR
    python -X utf8 canton_build.py parse  --cc tk --src DIR --repo CLONE --out LIVE/corpus.d [--retrieved D]
    python -X utf8 canton_build.py verify --cc tk --src DIR --out LIVE/corpus.d

The canton's own first-build readers are used unchanged (scripts/bosnia-<canton>-law: scan.py with tkread/gzread,
parse.py's split_units, cite_re, load, verify.py), pointed at <src> instead of their .cache/.tmp:
- scan: every listed issue (<src>/listing.json) -> <src>/acts/<sha>.json (the Assembly laws found, in reading order).
  An issue the reader fails on, or whose number/date it cannot read, is recorded with no laws and reported.
- parse: every law found is judged. The first build published only laws nothing later touched; here (the kit's
  rule) a law a later law amends, or whose gazette number a later law cites next to words of repeal, is published as
  enacted and labelled "amended, not consolidated", with amended_by naming each later law (gazette number, title,
  issue link); amending laws are published as acts of their own; official consolidated texts (prečišćeni tekst) as
  acts of their own, dated their issue day. Held, with the reason (<src>/held.json): budget laws (temporary),
  texts that do not split into articles, laws whose in-force clause is not readable, laws the independent check fails
  (<src>/verify-failed.json), and laws the first build left out by hand (its LEFT_OUT). Laws in force after the
  retrieval day are pending. Laws main already holds (same gazette issue and act number) are not parsed again;
  labels for them go to <src>/labels.json (recover_acts.py --extra).
  New acts: slug zakon-<year>-sn<issue>-<act no> (folder zakon/<year>/sn<issue>-<act no>/).
- verify: the first build's independent check (pypdf) on <out>/30-gazette.json; failures -> verify-failed.json.
Deterministic: the same inputs give the same bytes.
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import importlib
import json
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2]
CANTONS = {
    'tk': {'dir': 'bosnia-tuzla-canton-law', 'key': 'sntk', 'gaz': 'Službene novine Tuzlanskog kantona'},
    'zdk': {'dir': 'bosnia-zenica-doboj-canton-law', 'key': 'snzdk', 'gaz': 'Službene novine Zeničko-dobojskog kantona'},
    'sbk': {'dir': 'bosnia-central-bosnia-canton-law', 'key': 'snsbk', 'gaz': 'Službene novine Srednjobosanskog kantona'},
    'bpk': {'dir': 'bosnia-bosnian-podrinje-canton-law', 'key': 'snbpk', 'gaz': 'Službene novine Bosansko-podrinjskog kantona Goražde'},
}
BUDGET = re.compile(r'bud[žz]et|prora[čc]un')
# Some issues' fonts (Zenica-Doboj 2013-2019) map č, Č, ž, Ž, đ/Đ to ĉ, Ĉ, ţ, Ţ, Ċ: none of these letters occurs in
# Bosnian, so they are restored one for one (Ċ as Đ inside a word in capitals, else đ). Applied to the reader's lines
# and, in verify, to the independent reader's text alike.
_GLYPHS = str.maketrans({'ĉ': 'č', 'Ĉ': 'Č', 'ţ': 'ž', 'Ţ': 'Ž'})


def fix_glyphs(t: str) -> str:
    if not any(c in t for c in 'ĉĈţŢĊ'):
        return t
    t = t.translate(_GLYPHS)
    return re.sub(r'\w*Ċ\w*', lambda m: m.group(0).replace(
        'Ċ', 'Đ' if len(m.group(0)) > 1 and m.group(0).replace('Ċ', '').isupper() else 'đ'), t)


def acts_relaxed(S, lines):
    """The first build's act finder with the act-number size floor at 9.5 pt (issues set in 10 pt, Zenica-Doboj
    2013-2019), for issues where it finds nothing at 11 pt."""
    starts = [i for i, l in enumerate(lines) if l['bold'] and 9.5 <= l['size'] and S.ACTNO.match(l['text'])]
    out = []
    for k, st in enumerate(starts):
        e = starts[k + 1] if k + 1 < len(starts) else len(lines)
        body = lines[st + 1:e]
        z = next((i for i, l in enumerate(body[:60]) if l['bold'] and S.ZAKON.match(l['text'])), None)
        if z is None:
            continue
        pre = ' '.join(l['text'] for l in body[:z])
        if not re.search(r'Skupštin', pre):
            continue
        out.append({'no': int(S.ACTNO.match(lines[st]['text']).group(1)), 'page': lines[st]['page'], 'lines': body})
    return out


def modules(cc: str, src: Path):
    d = SCRIPTS / CANTONS[cc]['dir']
    sys.path.insert(0, str(d))
    sys.path.insert(0, str(SCRIPTS / 'world-law'))
    for m in ('scan', 'parse', 'verify', 'tkread', 'gzread', 'dehyph'):
        sys.modules.pop(m, None)
    if (d / 'dehyph.py').exists():
        dh = importlib.import_module('dehyph')
        words = src / 'words.json'
        if not words.exists():  # the first build's dictionary (its 2022-2026 issues), kept fixed so text never moves
            shutil.copy2(d / '.tmp' / 'words.json', words)
        dh.WORDS = words
    S = importlib.import_module('scan')
    P = importlib.import_module('parse')
    S.CACHE, S.OUT = src, src / 'acts'
    if hasattr(S, 'LINES'):
        S.LINES = src / 'lines'
    P.TMP = src / 'acts'
    return S, P


def scan(cc: str, src: Path):
    S, _ = modules(cc, src)
    rows = json.loads((src / 'listing.json').read_text(encoding='utf-8'))
    urls = [r['url'] for r in rows if not re.search(r'(?i)registar|sadrzaj', r['url'] + ' ' + (r.get('text') or ''))]
    (src / 'issues.txt').write_text('\n'.join(urls) + '\n', encoding='utf-8')
    S.OUT.mkdir(parents=True, exist_ok=True)
    n = bad = 0
    for u in urls:
        p = src / 'by-url' / hashlib.sha256(u.encode()).hexdigest()
        if not p.exists():
            continue
        o = S.OUT / (p.name + '.json')
        if o.exists():
            continue
        rec = {'url': u, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
        try:
            lc = getattr(S, 'LINES', None)
            lc = lc / (p.name + '.json.gz') if lc else None
            if lc and lc.exists():
                meta = json.loads(gzip.decompress(lc.read_bytes()))
                lines, (num, date, lang), pages = meta['lines'], meta['meta'], meta['pages']
            else:
                lines, doc = S.tkread.issue_lines(p)
                num, date, lang = S.issue_meta(doc, u)
                pages = doc.page_count
                if lc:
                    lc.parent.mkdir(parents=True, exist_ok=True)
                    lc.write_bytes(gzip.compress(json.dumps({'lines': lines, 'meta': [num, date, lang], 'pages': pages},
                                                            ensure_ascii=False).encode()))
            for l in lines:
                l['text'] = fix_glyphs(l['text'])
            acts = S.acts_of(lines)
            if not acts and date:
                acts = acts_relaxed(S, lines)
                if acts:
                    rec['reader'] = 'act numbers from 9.5 pt'
            rec.update(issue=num, date=date, lang=lang, pages=pages, acts=acts)
            if date is None and acts:
                rec.update(acts=[], undated_laws=len(acts), date=None)
        except Exception as e:  # noqa: BLE001
            bad += 1
            rec.update(issue=None, date=None, lang=None, pages=None, acts=[], error=f'{type(e).__name__}: {str(e)[:150]}')
        o.write_text(json.dumps(rec, ensure_ascii=False), encoding='utf-8')
        n += 1
        if n % 20 == 0:
            print('scanned', n, flush=True)
    print('scanned', n, 'failed', bad)


def parse(cc: str, src: Path, repo: Path, out: Path, retrieved: str):
    S, P = modules(cc, src)
    cfg = CANTONS[cc]
    # issues without a readable date (or a failed read) cannot be ordered: P.load refuses undated issues with laws
    issues, laws = P.load()
    lost = []
    for f in sorted((src / 'acts').glob('*.json')):
        d = json.loads(f.read_text(encoding='utf-8'))
        if d.get('error') or d.get('undated_laws'):
            lost.append({'url': d['url'], 'reason': d.get('error') or f'issue date not readable ({d["undated_laws"]} laws in it)'})
    # what main holds: law keys from data/laws.csv (root) and registry/data/laws.csv
    import csv
    import io
    held_keys = {}
    for rel in ('data/laws.csv', 'registry/data/laws.csv'):
        p = repo / rel
        if p.exists():
            held_keys.update({r['key']: r['url'] for r in csv.DictReader(io.StringIO(p.read_text(encoding='utf-8')))})
    on_main_acts = {}
    for rel in ('data/versions.json', 'registry/data/versions.json'):
        p = repo / rel
        if p.exists():
            for a in json.loads(p.read_text(encoding='utf-8'))['acts']:
                on_main_acts[a['slug']] = a
    vf = src / 'verify-failed.json'
    failed = json.loads(vf.read_text(encoding='utf-8')) if vf.exists() else {}
    part = {'sources': [], 'laws': {}, 'acts': [], 'applies': [], 'decisions': [], 'ai_use': []}
    held, labels, census = [], {}, []
    key_of = lambda x: f'{cfg["key"]}-{x["date"][:4]}-{x["issue"]:03d}-{x["no"]}'  # noqa: E731
    ref_of = lambda y: f'{cfg["gaz"]} {y["issue"]}/{int(y["date"][:4]) % 100:02d}'  # noqa: E731
    amend_re = getattr(P, 'AMEND', r'izmjen|dopun|prestank|izmjeni')
    for i, x in enumerate(laws):
        lk = key_of(x)
        row = {'key': lk, 'issue': f'{x["issue"]}/{x["date"][:4]}', 'date': x['date'], 'no': x['no'], 'url': x['url']}
        try:
            units, lbls, title, days = P.split_units(x['lines'])
        except ValueError as e:
            row.update(state='held', why=f'text does not split into articles: {e}')
            census.append(row)
            held.append(row)
            continue
        except Exception as e:  # noqa: BLE001
            row.update(state='held', why=f'unreadable: {type(e).__name__}')
            census.append(row)
            held.append(row)
            continue
        row['title'] = title
        if any(k.startswith('clan-') and len([p for p in ps if p.strip()]) < 2 for k, ps in units.items()):
            # an article with only its number: its text went elsewhere (into the signature block, ZDK 8/10)
            row.update(state='held', why='text does not split into articles: an article with no text')
            census.append(row)
            held.append(row)
            continue
        tl = P.lat(title).lower()
        amending = bool(re.search(amend_re, tl))
        # later laws that cite it: amending/consolidating ones next to its subject, or any next to words of repeal
        c = P.cite_re(x['issue'], int(x['date'][:4]))
        st = P.stems(title)
        hits = []
        for y in laws[i + 1:]:
            yam = bool(re.search(amend_re + '|prečišćen', P.lat(y.get('head', '')).lower()))
            for m in c.finditer(y['text']):
                win = y['text'][max(0, m.start() - 300):m.end() + 120].lower()
                # an amending law counts only when its own title names this law's subject (most of its word stems):
                # a citation in passing (a list of laws in another law's amendment) is not a change of this law
                yh = P.lat(y.get('head', '')).lower()
                names_it = bool(st) and sum(s in yh for s in st) * 3 >= len(st) * 2
                if (not st or any(s in win for s in st)) and ((yam and names_it) or P.REPEAL.search(win)):
                    hits.append(y)
                    break
        if lk in held_keys:
            # an act appended here has the slug of its gazette issue and act number; a first-build act is found by its
            # source file, among the first build's acts only (one issue file holds many laws)
            slug = f'zakon-{x["date"][:4]}-sn{x["issue"]:03d}-{x["no"]}'
            if slug not in on_main_acts:
                slug = next((s for s, a in on_main_acts.items() if not s.startswith('zakon-') and
                             any(v.get('source_url') == held_keys[lk] for v in a['versions'])), None)
            row.update(state='on main', act=slug)
            if hits and not amending:
                # the published act carries the label: find it by its law key in laws.csv (first_law / earlier_laws)
                labels[slug or lk] = {'label': 'amended, not consolidated',
                              'amended_by': [{'ref': ref_of(y), 'title': (y.get('head') or '')[:200], 'url': y['url'],
                                              'date': y['date']} for y in hits]}
            census.append(row)
            continue
        if BUDGET.search(tl) and not amending:
            row.update(state='held', why='budget law (temporary), out of scope')
            census.append(row)
            held.append(row)
            continue
        if BUDGET.search(tl):
            row.update(state='held', why='amends a budget law (temporary), out of scope')
            census.append(row)
            held.append(row)
            continue
        if days is None:
            row.update(state='held', why='its in-force clause is not readable')
            census.append(row)
            held.append(row)
            continue
        if (x['date'], x['no']) in getattr(P, 'LEFT_OUT', {}):
            row.update(state='held', why=P.LEFT_OUT[(x['date'], x['no'])])
            census.append(row)
            held.append(row)
            continue
        cons = days == 'consolidated'
        frm = x['date'] if cons else (dt.date.fromisoformat(x['date']) + dt.timedelta(days=days)).isoformat()
        slug = f'zakon-{x["date"][:4]}-sn{x["issue"]:03d}-{x["no"]}'
        if slug in failed:
            row.update(state='held', why='independent text check failed: ' + failed[slug])
            census.append(row)
            held.append(row)
            continue
        if frm > retrieved:
            row.update(state='pending', why=f'takes effect {frm}, after the issue was read', in_force_from=frm)
            census.append(row)
            held.append(row)
            continue
        lang = P.LANGS.get(x['lang'], x['lang']) or "the issue's only"  # older issues print one edition and do not name it
        cyr = bool(re.search('[а-яА-Я]', title))
        name = ('Закон ' if cyr else 'Zakon ') + P.nice_title(title)
        yy = int(x['date'][:4]) % 100
        part['laws'][lk] = {'label': f'{cfg["gaz"]} {x["issue"]}/{yy:02d}' + (' (prečišćeni tekst)' if cons else ''),
                            'title': name, 'kind': 'law', 'enacted': None, 'published': x['date'], 'url': x['url'],
                            'temporary_until': None, 'restores': None, 'note': None}
        u = {}
        for k, ps in units.items():
            if ps:
                kind = 'art' if k.startswith('clan-') else ('heading' if k == 'naslov' else 'note')
                u[k] = {'label': lbls[k], 'kind': kind, 'text': '\n'.join(ps) + '\n'}
        act = {'slug': slug, 'short': name[:60].rstrip(' ,-'), 'title': name, 'url': x['url'],
               'first_law': None if cons else lk, 'earlier_laws': [lk] if cons else [],
               'versions': [{'from': frm, 'source_url': x['url'], 'sha256': x['sha256'], 'units': u,
                             'credits': {k: [lk] for k in u},
                             'note': (f'Official consolidated text (prečišćeni tekst), {cfg["gaz"]} {x["issue"]}/{yy:02d} of '
                                      f'{x["date"]} (act {x["no"]}, {lang} edition); it applies from its publication. '
                                      'Earlier versions are not in the record.' if cons else
                                      f'As published in the {cfg["gaz"]} {x["issue"]}/{yy:02d} of {x["date"]} (act '
                                      f'{x["no"]}, {lang} edition); in force {days} day(s) after publication, as its '
                                      'final article says.')}]}
        if hits and not amending:
            act['label'] = 'amended, not consolidated'
            act['amended_by'] = [{'ref': ref_of(y), 'title': (y.get('head') or '')[:200], 'url': y['url'], 'date': y['date']} for y in hits]
            act['versions'][0]['note'] += (f' Later laws in the gazette amend or repeal it ({len(hits)}), with no official '
                                           'consolidated text after them: this is the text as enacted (amended, not '
                                           'consolidated).')
        part['acts'].append(act)
        row.update(state='added', act=slug, frm=frm, amended_after=len(hits), amending=amending, consolidated=cons)
        census.append(row)
    first = issues[0]['date'] if issues else None
    last = issues[-1]['date'] if issues else None
    part['sources'].append({'name': f'{cfg["gaz"]} (each issue as a PDF)', 'url': P.GAZETTE, 'retrieved': retrieved,
                            'licence': P.LICENCE})
    part['decisions'] += [
        f'Every Assembly law the reader finds in the gazette issues read ({first} to {last}) is accounted for: published, '
        'or held with the reason (data/held.json).',
        'A law that later laws in those issues amend, or cite next to words of repeal, is published as enacted and '
        'labelled "amended, not consolidated"; the later laws are listed in amended_by (data/acts.json). Amending laws are '
        'published as acts of their own; official consolidated texts (prečišćeni tekst) as acts of their own, dated '
        'their issue day. Budget laws are out of scope (temporary).',
        'Each law is dated its issue date plus the days its final article names, credited to itself.']
    part['ai_use'].append('none: the text is read from the gazette PDFs\' text layer by a deterministic parser; no model output is legal text.')
    out.mkdir(parents=True, exist_ok=True)
    tmp = out / '30-gazette.json.tmp'
    tmp.write_text(json.dumps(part, ensure_ascii=False, indent=0) + '\n', encoding='utf-8', newline='\n')
    tmp.replace(out / '30-gazette.json')
    # Years the reader finds no law in, although the gazette prints laws ('ZAKON' headings, canton_census.py), or whose
    # issues are images: measured gap, held as whole years with the reason.
    gc = {}
    if (src / 'gazette-census.json').exists():
        gc = {i['url']: i for i in json.loads((src / 'gazette-census.json').read_text(encoding='utf-8'))['issues']}
    found_by_url = Counter(r['url'] for r in census)
    years = {}
    for f in sorted((src / 'acts').glob('*.json')):
        d = json.loads(f.read_text(encoding='utf-8'))
        g = gc.get(d['url'], {})
        y = (d.get('date') or '')[:4] or str(g.get('year') or 'undated')
        b = years.setdefault(y, Counter())
        b['issues'] += 1
        b['image_issues'] += bool(g.get('scanned'))
        b['zakon_headings'] += len(g.get('laws', []))
        b['laws_read'] += found_by_url[d['url']]
    unread = []
    for y, b in sorted(years.items()):
        if not b['laws_read'] and (b['zakon_headings'] or b['image_issues'] * 2 > b['issues']):
            why = ('issues are scanned images with no text layer' if b['image_issues'] * 2 > b['issues'] else
                   'the reader (built for the 2022-2026 layout) finds no law in this year\'s issues')
            unread.append({'year': y, 'reason': why,
                           'detail': f'{b["issues"]} issues read, {b["zakon_headings"]} ZAKON headings printed (all '
                                     f'editions counted), {b["image_issues"]} image-only issues; 0 laws read'})
    by_year = {}
    for r in census:
        b = by_year.setdefault(r['date'][:4], Counter())
        b[r['state']] += 1
    res = {'issues_read': len(issues), 'issues_lost': len(lost), 'laws_found': len(laws),
           'states': Counter(r['state'] for r in census), 'added_labelled': sum(1 for a in part['acts'] if a.get('label')),
           'labels_on_main': len(labels), 'held_reasons': Counter(r['why'].split(':')[0][:60] for r in held),
           'by_year': {k: dict(v) for k, v in sorted(by_year.items())},
           'issues_by_year': {k: dict(v) for k, v in sorted(years.items())}, 'unread_years': [u['year'] for u in unread]}
    for name, obj in (('census.json', {'laws': census, 'lost_issues': lost, 'unread_years': unread, 'summary': res}), ('held.json', held),
                      ('labels.json', labels)):
        (src / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(res, ensure_ascii=False))


def _sig(a):
    return hashlib.sha256(json.dumps([{k: v.get(k) for k in ('from', 'source_url', 'sha256', 'units')}
                                      for v in a['versions']], ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def verify_chunk(cc: str, src: Path, k: int):
    """One worker: verify.py on <src>/w<k>/corpus.d/30-gazette.json (written by verify()); output to <src>/w<k>/out."""
    S, P = modules(cc, src)
    V = importlib.import_module('verify')
    w = src / f'w{k}'
    if not (w / '.cache').exists():
        import subprocess
        subprocess.run(['cmd', '/c', 'mklink', '/J', str(w / '.cache'), str(src)], capture_output=True, check=True)
    V.HERE = w
    _it = V.issue_text
    V.issue_text = lambda path: fix_glyphs(_it(path))

    # verify.py's fallback alignment (difflib, quadratic) can run for hours when a span differs widely, as it does
    # for older layouts: a span whose length differs from ours by more than 3,000 letters cannot be "ours plus the
    # masthead" anyway, so it is reported as not matching at once.
    import difflib as _real_difflib
    _RealSM = _real_difflib.SequenceMatcher

    class _SM:
        def __init__(self, isjunk, a, b, autojunk=False):
            self.a, self.b = a, b
            self.real = None if abs(len(a) - len(b)) > 3000 else _RealSM(isjunk, a, b, autojunk=autojunk)

        def get_opcodes(self):
            return self.real.get_opcodes() if self.real else [('replace', 0, len(self.a), 0, len(self.b))]

    class _Difflib:
        SequenceMatcher = _SM
    V.difflib = _Difflib
    import contextlib
    import io as _io

    class _Tee(_io.StringIO):  # progress lines also go to <src>/w<k>/progress as they come
        def write(self, x):
            with open(w / 'progress', 'a', encoding='utf-8') as f:
                f.write(x)
            return super().write(x)
    (w / 'progress').unlink(missing_ok=True)
    buf = _Tee()
    with contextlib.redirect_stdout(buf):
        V.main('30-gazette.json')
    (w / 'out').write_text(buf.getvalue(), encoding='utf-8')


def verify(cc: str, src: Path, out: Path, workers: int = 4):
    """The first build's independent check on every act not yet confirmed, split by issue file over worker processes."""
    okf = src / 'verify-ok.json'
    ok = json.loads(okf.read_text(encoding='utf-8')) if okf.exists() else {}
    part = json.loads((out / '30-gazette.json').read_text(encoding='utf-8'))
    sig = _sig
    todo = [a for a in part['acts'] if ok.get(a['slug']) != sig(a)]
    if not todo:
        print('nothing new to verify | newly failed 0')
        return 0
    by_url = {}
    for a in todo:
        by_url.setdefault(a['versions'][0]['source_url'], []).append(a)
    chunks = [[] for _ in range(min(workers, len(by_url)))]
    for i, (u, acts) in enumerate(sorted(by_url.items(), key=lambda kv: -len(kv[1]))):
        min(chunks, key=len).extend(acts)
    import subprocess
    procs = []
    for k, ch in enumerate(chunks):
        w = src / f'w{k}'
        (w / 'corpus.d').mkdir(parents=True, exist_ok=True)
        (w / 'corpus.d' / '30-gazette.json').write_text(json.dumps({**part, 'acts': ch}, ensure_ascii=False), encoding='utf-8')
        (w / 'out').unlink(missing_ok=True)
        procs.append(subprocess.Popen([sys.executable, '-X', 'utf8', __file__, 'verify-chunk', '--cc', cc, '--src', str(src),
                                       '--chunk', str(k)]))
    for p in procs:
        p.wait()
    text = ''.join((src / f'w{k}' / 'out').read_text(encoding='utf-8') if (src / f'w{k}' / 'out').exists() else
                   f'FAIL worker {k} produced no output\n' for k in range(len(chunks)))
    text = '\n'.join(l for l in text.splitlines() if not l.startswith('acts failing')) + '\n'
    text += f"acts failing: {sum(1 for l in text.splitlines() if l.startswith('FAIL'))}\n"
    (src / 'verify.out').write_text(text, encoding='utf-8')
    vf = src / 'verify-failed.json'
    failed = json.loads(vf.read_text(encoding='utf-8')) if vf.exists() else {}
    new = 0
    for line in text.splitlines():
        m = re.match(r'FAIL (\S+)', line)
        if m and m.group(1) != 'worker':
            slug = m.group(1)
            full = next((a['slug'] for a in json.loads((out / '30-gazette.json').read_text(encoding='utf-8'))['acts']
                         if a['slug'].startswith(slug)), slug)
            if full not in failed:
                failed[full] = 'the second PDF reader (pypdf) does not give the same text in the same order'
                new += 1
    vf.write_text(json.dumps(failed, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    for line in text.splitlines():
        m = re.match(r'OK\s+(\S+)', line)
        a = next((a for a in todo if m and a['slug'].startswith(m.group(1))), None)
        if a:
            ok[a['slug']] = sig(a)
    okf.write_text(json.dumps(ok, ensure_ascii=False, indent=0) + '\n', encoding='utf-8')
    print(text.splitlines()[-1] if text else 'no output', '| newly failed', new)
    return new


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('what', choices=['scan', 'parse', 'verify', 'verify-chunk'])
    ap.add_argument('--chunk', type=int)
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--cc', required=True, choices=list(CANTONS))
    ap.add_argument('--src', required=True)
    ap.add_argument('--repo')
    ap.add_argument('--out')
    ap.add_argument('--retrieved')
    a = ap.parse_args()
    try:
        import psutil
        psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
    except Exception:
        pass
    src = Path(a.src)
    if a.what == 'scan':
        scan(a.cc, src)
    elif a.what == 'parse':
        st = json.loads((src / 'refresh-state.json').read_text())
        parse(a.cc, src, Path(a.repo), Path(a.out), a.retrieved or st['listing_read'])
    elif a.what == 'verify-chunk':
        verify_chunk(a.cc, src, a.chunk)
    else:
        sys.exit(0 if verify(a.cc, src, Path(a.out), a.workers) == 0 else 3)


if __name__ == '__main__':
    main()
