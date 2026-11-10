#!/bin/bash
# First publish of a canton's additions after its full scan, parse and verify (2026-11-09), by hand, step by step:
#   bash first_publish.sh <cc> <repo name> [push]
# 1. re-parse (verify failures held), parse twice and compare bytes; seed verify-ok.json from verify.out
# 2. append dry run (held_acts must be empty), 20 spot-checks to <src>/spotcheck.txt
# 3. with "push": append, check_repo gate, push main + tags, README, freshness commit, gate, push.
set -eu
CC=$1; RN=$2; D=/c/Users/alany/Documents
T=$D/lexifina/scripts/bosnia-tuzla-canton-law/live; G=$D/lexifina/scripts/world-law/balkan-builder
L=C:/Users/alany/Documents/lexifina/scripts/$RN/live; R=$D/$RN-pub; S=$D/$RN-src; SW=C:/Users/alany/Documents/$RN-src
export GITLAW_DOCS_PREFIX=registry/ GITLAW_LAYOUT_KINDS=zakon GITLAW_PART_CACHE=$SW/part-cache
cd $T
python -X utf8 canton_build.py parse --cc $CC --src $S --repo $R --out $L/corpus.d > $S/parse1.out
cp $L/corpus.d/30-gazette.json $S/parse1.json
python -X utf8 canton_build.py parse --cc $CC --src $S --repo $R --out $L/corpus.d > $S/parse2.out
cmp -s $S/parse1.json $L/corpus.d/30-gazette.json && echo "deterministic: $(sha256sum $S/parse1.json | cut -c1-16)" || { echo "NOT deterministic"; exit 1; }
python -X utf8 - "$SW" "$L" <<'EOF'
import json, re, hashlib, sys
src, live = sys.argv[1], sys.argv[2]
part = json.load(open(live + '/corpus.d/30-gazette.json', encoding='utf-8'))
sig = lambda a: hashlib.sha256(json.dumps([{k: v.get(k) for k in ('from', 'source_url', 'sha256', 'units')} for v in a['versions']], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
oks = set(m.group(1) for m in re.finditer(r'^OK\s+(\S+)', open(src + '/verify.out', encoding='utf-8').read(), re.M))
try:
    ok = json.load(open(src + '/verify-ok.json', encoding='utf-8'))
except OSError:
    ok = {}
ok.update({a['slug']: sig(a) for a in part['acts'] if a['slug'][:50] in oks})
json.dump(ok, open(src + '/verify-ok.json', 'w', encoding='utf-8'), indent=0)
print('verified', len(ok), 'of', len(part['acts']))
EOF
# acts the independent reader does not confirm are held: parse again until a verify finds nothing new
until python -X utf8 $T/canton_build.py verify --cc $CC --src $S --out $L/corpus.d --workers 4; do
  python -X utf8 canton_build.py parse --cc $CC --src $S --repo $R --out $L/corpus.d > $S/parse2.out
done
tail -n 1 $S/parse2.out | cut -c1-400
cd $G
python -X utf8 append.py $L --repo $R --docs-date $(date -u +%F) --dry-run > $S/dry.out 2>&1
python -X utf8 -c "import ast,sys;d=ast.literal_eval(open(sys.argv[1],encoding='utf-8').read().strip().splitlines()[-1]);print('dry run: new',len(d['new_acts']),'held_acts',d['held_acts']);sys.exit(1 if d['held_acts'] else 0)" $S/dry.out
python -X utf8 $T/spotcheck.py $L/corpus.d/30-gazette.json $SW 20 > $S/spotcheck.txt
echo "spot-checks title+art1 found: $(grep -c 'title in issue: True | art 1 in issue: True' $S/spotcheck.txt)/20"
[ "${3:-}" = "push" ] || exit 0
python -X utf8 append.py $L --repo $R --docs-date $(date -u +%F) > $S/append.out 2>&1
gate() { python -X utf8 $G/check_repo.py $R --corpus $L/corpus.json | python -X utf8 -c "import json,sys;d=json.load(sys.stdin);print(sum(d[k] for k in ('trailer_errors','missing_in_force','merges','backwards','future_dated')))"; }
[ "$(gate)" = "0" ] || { echo "GATE FAILED"; exit 1; }
cd $R; git fetch -q origin; git merge-base --is-ancestor origin/main main
git push -q origin main 2>&1 | grep -v -i "bypass\|protected\|^remote: *$" || true
git push -q origin --tags 2>&1 | grep -v -i "bypass\|protected\|^remote: *$" || true
echo "pushed append: $(git rev-parse --short origin/main)"
cd $T
python -X utf8 canton_readme.py --cc $CC --repo $R --src $S --out $L/README.md
python -X utf8 freshness_canton.py --cc $CC --repo $R --src $S --readme $L/README.md --commit | cut -c1-300
[ "$(gate)" = "0" ] || { echo "GATE FAILED after freshness"; exit 1; }
cd $R; git merge-base --is-ancestor origin/main main
git push -q origin main 2>&1 | grep -v -i "bypass\|protected\|^remote: *$" || true
git fetch -q origin; echo "pushed freshness: $(git rev-parse --short origin/main)"
