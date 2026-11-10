"""Write a canton's root README for the romania-law standard (2026-11-09): the first build's README with its
"What this repository holds" section rewritten from the last parse (<src>/census.json) and a Freshness section
(summary block, monitoring paragraph) before "Limits". The result is LIVE/README.md, which freshness_canton.py fills
and commits. Private.

    python -X utf8 canton_readme.py --cc tk --repo CLONE --src DIR --out LIVE/README.md
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from canton_build import CANTONS  # noqa: E402

FRESH = """## Freshness

<!-- freshness-summary -->
<!-- /freshness-summary -->

`python tools/freshness.py <act>` gives an act's status, its last check and the official link. A refresh runner re-reads the canton's list of gazette issues every day (at most two requests a second), reads every new issue, appends new laws and writes these files; [data/status.json](data/status.json) says whether updates are running and whether the source is answering. Acts a later law amends with no official consolidated text are marked `amended, not consolidated` and name the amending laws ([registry/data/acts.json](registry/data/acts.json)); laws and gazette years held back are listed with the reason in [data/held.json](data/held.json), and laws published but not yet in force in [data/pending.json](data/pending.json). Statuses and fields: [data/freshness.json](data/freshness.json).

"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cc', required=True)
    ap.add_argument('--repo', required=True)
    ap.add_argument('--src', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    cfg = CANTONS[a.cc]
    text = (Path(a.repo) / 'README.md').read_text(encoding='utf-8')
    if '<!-- freshness-summary -->' in text:
        text = re.sub(r'\n## Freshness\n.*?(?=\n## )', '\n', text, flags=re.S)
    c = json.loads((Path(a.src) / 'census.json').read_text(encoding='utf-8'))
    s = c['summary']
    laws = c['laws']
    years = sorted({r['date'][:4] for r in laws if r['state'] in ('added', 'on main')})
    first = years[0] if years else '?'
    added = [r for r in laws if r['state'] == 'added']
    n_main = sum(1 for r in laws if r['state'] in ('added', 'on main'))
    n_amd = sum(1 for r in added if r.get('amending'))
    n_lab = sum(1 for r in added if r.get('amended_after') and not r.get('amending'))
    n_cons = sum(1 for r in added if r.get('consolidated'))
    n_held = sum(1 for r in laws if r['state'] == 'held')
    unread = c.get('unread_years', [])
    gap = ''
    if unread:
        gap = (' Gazette years whose issues the reader cannot yet read (' + ', '.join(u['year'] for u in unread) +
               ') are listed in data/held.json with the reason; their laws are not in the record.')
    lost = len(c.get('lost_issues', []))
    iy = sorted(y for y in s.get('issues_by_year', {}) if y.isdigit())
    span = f'{iy[0]} to {iy[-1]}' if iy else '?'
    holds = (f'The canton publishes the {cfg["gaz"]} on its site for {span}; every issue listed there is read. Of the '
             f'{len(laws)} Assembly laws the reader finds in them, {n_main} are here (from {first}), as:')
    section = f"""## What this repository holds

{holds}

- the law as enacted, dated the day it took effect; where later laws in the gazette amend it and no official consolidated text has been published since, it is marked `amended, not consolidated` and the amending laws are named ({n_lab} laws added on 2026-11-09);
- amending laws, each as an act of its own ({n_amd} added on 2026-11-09);
- official consolidated texts (prečišćeni tekst), dated the day of their issue ({n_cons} added on 2026-11-09).

The first build (October 2026) holds its laws in folders named after them; laws added later are in `zakon/<year>/sn<issue>-<act number>/`, indexed in [registry/ACTS.md](registry/ACTS.md) and [registry/data/acts.json](registry/data/acts.json).

Held back, with the reason, in [data/held.json](data/held.json) ({n_held} laws): budget laws and laws amending them (temporary), texts that do not split into articles, laws whose in-force clause cannot be read, and texts a second, independent PDF reader does not confirm.{gap}{f' {lost} issues could not be read or dated and are listed there too.' if lost else ''}
"""
    text = re.sub(r'## What this repository holds\n.*?(?=\n## )', section.rstrip('\n') + '\n', text, flags=re.S)
    text = re.sub(r'\n## Limits', '\n' + FRESH.rstrip('\n') + '\n\n## Limits', text, count=1)
    text = re.sub(r'\(a law is left out when ([^)]*)\)', r'(a law is marked `amended, not consolidated` when \1)', text)
    text = text.replace('Only the laws listed in `data/versions.json` are included',
                        'Only the laws listed in `data/versions.json` and `registry/data/acts.json` are included')
    Path(a.out).write_text(text, encoding='utf-8', newline='\n')
    print('README written', len(text))


if __name__ == '__main__':
    main()
