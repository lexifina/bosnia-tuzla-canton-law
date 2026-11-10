"""Write each canton's live/PROGRESS.md from its census (<src>/census.json) and clone (2026-11-09). Private.

    python -X utf8 write_progress.py
"""
import json
import subprocess
from pathlib import Path

D = Path('C:/Users/alany/Documents')
CC = {'tk': 'bosnia-tuzla-canton-law', 'zdk': 'bosnia-zenica-doboj-canton-law', 'sbk': 'bosnia-central-bosnia-canton-law',
      'bpk': 'bosnia-bosnian-podrinje-canton-law'}
for cc, rn in CC.items():
    src, repo = D / f'{rn}-src', D / f'{rn}-pub'
    c = json.loads((src / 'census.json').read_text(encoding='utf-8'))
    s = c['summary']
    git = lambda *a: subprocess.run(['git', *a], cwd=repo, capture_output=True, text=True, encoding='utf-8').stdout.strip()  # noqa: E731
    log = git('log', '--format=%h %s', '-4', 'origin/main')
    heads = sum(b['zakon_headings'] for y, b in s['issues_by_year'].items() if y in s['unread_years'])
    issues = sum(b['issues'] for b in s['issues_by_year'].values())
    text = f"""# {rn} to the romania-law standard (gitlaw-bosnia-standard, alan-dell, 2026-11-09)

Claim: scripts/world-law/claims/{rn}.txt. Clone: {repo.as_posix()}. Source cache: {src.as_posix()}
(listing.json, by-url/ PDFs, acts/ scan, census.json, held.json, labels.json, verify-ok.json, verify-failed.json).
Shared code: scripts/bosnia-tuzla-canton-law/live (canton_fetch.py, canton_build.py, canton_census.py, canton_readme.py,
freshness_canton.py, canton_refresh.sh, first_publish.sh, spotcheck.py) and scripts/bosnia-brcko-law/live
(recover_acts.py, bosnia_fresh.py). The first build's readers (scan.py, parse.py, verify.py) are used unchanged.

## Census (every issue on the canton's gazette page fetched and read)
- Issues on the page: {issues} files; issues dated and read: {s['issues_read']}; unreadable/undated: {s['issues_lost']}.
- Assembly laws the reader finds: {s['laws_found']}: {dict(s['states'])}.
- Held reasons: {dict(s['held_reasons'])}.
- Years the reader finds no law in although the gazette prints ZAKON headings (all editions counted): {', '.join(s['unread_years']) or 'none'}
  ({heads} headings): the measured gap, held as years in data/held.json.
- Per year (issues, ZAKON headings all editions, laws read): {json.dumps({y: [b['issues'], b['zakon_headings'], b['laws_read']] for y, b in s['issues_by_year'].items()})}
- Before this work main held 4-6 laws and listed nothing held: every other law was a silent drop.

## Pushed (origin/main)
{log}

## Gates (first_publish.sh)
Two parses byte-identical; independent pypdf check (verify.py) on every added act, failures held; append dry run
held_acts []; 20 spot-checks in src/spotcheck.txt; check_repo gate 0 before each push.

## Runner
refresh_{cc}.sh / refresh_{cc}_run.sh (daily; ONCE=1 for one pass), not registered. Register with
balkan-audit/work/register_runner.py bosnia-{ {'tk': 'tuzla', 'zdk': 'zdk', 'sbk': 'sbk', 'bpk': 'bpk'}[cc]}-refresh {rn[:-4]} {src.as_posix().replace('/', chr(92))} {cc} "..."
"""
    (D / 'lexifina' / 'scripts' / rn / 'live' / 'PROGRESS.md').write_text(text, encoding='utf-8', newline='\n')
    print(rn, 'written')
