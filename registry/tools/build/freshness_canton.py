"""Bosnian cantons: write the freshness files (romania-law format), data/held.json, data/pending.json and the README's
freshness block, from the last read of the canton's gazette page (canton_fetch.py list -> <src>/refresh-state.json)
and the last scan and parse of every listed issue (canton_build.py -> <src>/held.json, census.json). 2026-11-09.

    python -X utf8 freshness_canton.py --cc tk --repo <clone> --src DIR [--readme LIVE/README.md] [--commit] [--source-down]
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'bosnia-brcko-law' / 'live'))
sys.path.insert(0, str(HERE))
import bosnia_fresh as BF  # noqa: E402
from canton_build import CANTONS  # noqa: E402
from canton_fetch import CANTONS as PAGES  # noqa: E402

CODES = {'tk': 'BA-03', 'zdk': 'BA-04', 'sbk': 'BA-06', 'bpk': 'BA-05'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cc', required=True, choices=list(CANTONS))
    ap.add_argument('--repo', required=True)
    ap.add_argument('--src', required=True)
    ap.add_argument('--readme')
    ap.add_argument('--commit', action='store_true')
    ap.add_argument('--source-down', action='store_true')
    a = ap.parse_args()
    cfg, src, repo = CANTONS[a.cc], Path(a.src), Path(a.repo)
    census = json.loads((src / 'census.json').read_text(encoding='utf-8'))
    held = [{'act': r.get('title') or f'law no. {r["no"]}', 'gazette': f'{cfg["gaz"]} {r["issue"]}', 'date': r['date'],
             'act_no': r['no'], 'reason': r['why'].split(':')[0], 'detail': r['why'], 'official_url': r['url']}
            for r in census['laws'] if r['state'] == 'held']
    held += [{'act': None, 'gazette': None, 'reason': 'issue not read', 'detail': x['reason'], 'official_url': x['url']}
             for x in census['lost_issues']]
    for y in census.get('unread_years', []):
        held.append({'act': None, 'gazette': f'{cfg["gaz"]}, {y["year"]}', 'reason': y['reason'], 'detail': y['detail'],
                     'official_url': PAGES[a.cc]['page']})
    pending = [{'act': r.get('title'), 'gazette': f'{cfg["gaz"]} {r["issue"]}', 'in_force_from': r.get('in_force_from'),
                'official_url': r['url']} for r in census['laws'] if r['state'] == 'pending']
    method = (f'The {cfg["gaz"]}: the canton\'s list of issues ({PAGES[a.cc]["page"]}) read that day, every listed '
              'issue read (PDF text layer), and every Assembly law in it compared with this repository: a later law that '
              'amends, consolidates or repeals an act here is found by its citation of the act\'s gazette number')
    readme = Path(a.readme).read_text(encoding='utf-8') if a.readme and Path(a.readme).exists() else None
    res = BF.run(repo, src, CODES[a.cc], f'{CANTONS[a.cc]["dir"]}@lexifina.com', 'gazette-index', method,
                 cfg['gaz'], PAGES[a.cc]['page'], held, pending, readme=readme, do_commit=a.commit,
                 source_ok=not a.source_down)
    print(json.dumps(res, ensure_ascii=False))


if __name__ == '__main__':
    main()
