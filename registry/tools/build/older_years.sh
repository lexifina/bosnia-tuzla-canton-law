#!/bin/bash
# Older gazette years (2026-11-10): rescan the issues in which the reader found no law (glyph restoration and the
# 9.5 pt act-number floor, canton_build.py), then verify the new acts and publish them with first_publish.sh.
#   bash older_years.sh <cc> <repo name>
set -u
CC=$1; RN=$2; D=/c/Users/alany/Documents; S=$D/$RN-src; T=$D/lexifina/scripts/bosnia-tuzla-canton-law/live
python -X utf8 - "$(cygpath -m $S)" <<'PY'
import json, glob, os, sys
n = 0
for f in glob.glob(sys.argv[1] + '/acts/*.json'):
    d = json.load(open(f, encoding='utf-8'))
    if d.get('date') and not d['acts'] and not d.get('error') and not d.get('reader'):
        os.remove(f); n += 1
print('rescan', n)
PY
python -X utf8 $T/canton_build.py scan --cc $CC --src $S | tail -n 1
python -X utf8 $T/canton_build.py parse --cc $CC --src $S --repo $D/$RN-pub --out $D/lexifina/scripts/$RN/live/corpus.d | cut -c1-300
python -X utf8 $T/canton_build.py verify --cc $CC --src $S --out $D/lexifina/scripts/$RN/live/corpus.d --workers 4 | tail -n 1
bash $T/first_publish.sh $CC $RN push
