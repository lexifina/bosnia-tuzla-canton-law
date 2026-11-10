"""Per-repo summary for the report (2026-11-09/10): origin/main head, acts on main, labelled acts, held, pending,
freshness summary, and whether each romania-law item is present on origin/main. Private.

    python -X utf8 final_table.py
"""
import json
import subprocess
from pathlib import Path

D = Path('C:/Users/alany/Documents')
REPOS = ['bosnia-brcko-law', 'bosnia-tuzla-canton-law', 'bosnia-zenica-doboj-canton-law',
         'bosnia-central-bosnia-canton-law', 'bosnia-bosnian-podrinje-canton-law']
for rn in REPOS:
    repo = D / f'{rn}-pub'
    git = lambda *a: subprocess.run(['git', *a], cwd=repo, capture_output=True, text=True, encoding='utf-8').stdout  # noqa: E731
    git('fetch', '-q', 'origin')
    show = lambda p: git('show', f'origin/main:{p}')  # noqa: E731
    has = lambda p: bool(git('ls-tree', 'origin/main', p).strip())  # noqa: E731
    acts = json.loads(show('registry/data/acts.json') or '{"acts": []}')['acts']
    fr = json.loads(show('data/freshness.json') or '{}')
    held = json.loads(show('data/held.json') or '{"count": 0}')
    pend = json.loads(show('data/pending.json') or '{"count": 0}')
    readme = show('README.md')
    src_ok = git('log', 'origin/main', '--format=%(trailers:key=Source,valueonly)%(trailers:key=Consolidated,valueonly)%x1e%(trailers:key=In-force,valueonly)')
    law = [r for r in src_ok.split('\x1e') if r.strip()]
    row = {
        'head': git('rev-parse', '--short', 'origin/main').strip(), 'commits': git('rev-list', '--count', 'origin/main').strip(),
        'acts_on_main': len(acts), 'labelled': sum(1 for a in acts if a.get('status') == 'amended, not consolidated'),
        'held': held.get('count'), 'pending': pend.get('count'),
        'freshness': fr.get('totals', {}).get('by_status'), 'checked': fr.get('checked_against_official_source'),
        'tools/freshness.py': has('tools/freshness.py'), 'data/freshness.json': has('data/freshness.json'),
        'data/status.json': has('data/status.json'), 'data/held.json': has('data/held.json'),
        'data/pending.json': has('data/pending.json'),
        'README block': '<!-- freshness-summary -->' in readme, 'README monitoring': 'refresh runner' in readme,
        'acts with portal link': sum(1 for a in acts if a.get('portal')),
    }
    print(rn, json.dumps(row, ensure_ascii=False))
