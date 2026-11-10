"""20 hand spot-checks of a canton part: per act its gazette issue, issue date, computed in-force day, the final
article's in-force sentence, label/amended_by, and whether its title and first article occur in the issue text read
by pymupdf (whole document). Prints for a person to read. Private.

    python -X utf8 spotcheck.py <part.json> <src> [n]
"""
import hashlib, json, re, sys
import pymupdf
from canton_build import fix_glyphs  # the issue's own font mapping, as the reader restores it
part, src = sys.argv[1], sys.argv[2]
n = int(sys.argv[3]) if len(sys.argv) > 3 else 20
c = json.load(open(part, encoding='utf-8'))
acts = c['acts']
step = max(1, len(acts) // n)
ld = lambda s: re.sub(r'[\W_]+', '', s.lower())
for a in acts[::step][:n]:
    v = a['versions'][0]
    t = ld(fix_glyphs(''.join(p.get_text() for p in pymupdf.open(src + '/by-url/' + hashlib.sha256(v['source_url'].encode()).hexdigest()))))
    u = v['units']
    arts = [k for k in u if k.startswith('clan-')]
    last = ' '.join(u[arts[-1]]['text'].split())
    m = re.search(r'[^.]*stupa[^.]*na snagu[^.]*\.', last) or re.search(r'.{0,160}$', last)
    print('==', a['slug'], '|', a['title'][:80])
    print('   note:', v['note'][:170])
    print('   from:', v['from'], '| clause:', m.group(0)[:170])
    print('   title in issue:', ld(a['title'].split(' ', 1)[1])[:60] in t, '| art 1 in issue:', ld(u[arts[0]]['text'])[:200] in t,
          '| label:', a.get('label'), [x['ref'] for x in a.get('amended_by', [])][:3])
