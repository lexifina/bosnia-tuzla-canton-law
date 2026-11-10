#!/bin/bash
# Bosnian canton refresh runner (2026-11-09), called by refresh_<cc>.sh with CC, SRC, R (clone), L (live dir):
# once a day, re-read the canton's gazette page, fetch new issues (at most 2 requests a second), scan every issue,
# parse every Assembly law against main (canton_build.py), hold texts the independent reader does not confirm,
# append new acts to main (fast-forward only, check_repo gate), then write and push the freshness files.
# Stops on the first failed gate. Log: $SRC/refresh.log. Stop: touch $SRC/STOP-REFRESH. Once: ONCE=1.
set -u
: "${CC:?}" "${SRC:?}" "${R:?}" "${L:?}"
T=/c/Users/alany/Documents/lexifina/scripts/bosnia-tuzla-canton-law/live
B=/c/Users/alany/Documents/lexifina/scripts/bosnia-brcko-law/live
G=/c/Users/alany/Documents/lexifina/scripts/world-law/balkan-builder
LW=$(cygpath -m $L)
export GITLAW_DOCS_PREFIX=registry/
export GITLAW_PART_CACHE=$(cygpath -m $SRC)/part-cache  # one fixed cache per repo (not %TEMP%)
export GITLAW_LAYOUT_KINDS=zakon
export GITLAW_MAX_NEW_ACTS=${BATCH:-200}
log() { echo "$(date -u +%FT%TZ) $*" >> $SRC/refresh.log; }
freegb() { df -BG --output=avail /c | tail -1 | tr -dc 0-9; }
gate() {
  python -X utf8 $G/check_repo.py $R --corpus $LW/corpus.json > $SRC/refresh-check.out 2>&1
  python -X utf8 -c "import json,sys;d=json.load(open(sys.argv[1],encoding='utf-8'));print(sum(d[k] for k in ('trailer_errors','missing_in_force','merges','backwards','future_dated')))" $SRC/refresh-check.out
}
echo $$ > $SRC/refresh.pid
log "start refresh runner $CC (pid $$)"
while true; do
  [ -f $SRC/STOP-REFRESH ] && { log "stop file"; exit 0; }
  [ "$(freegb)" -ge 50 ] || { log "FAILED: C: below 50 GB"; exit 1; }
  DOWN=""
  log "fetch: gazette list and new issues"
  if python -X utf8 $L/fetch_$CC.py list --src $SRC > $SRC/refresh-fetch.log 2>&1 \
     && python -X utf8 $L/fetch_$CC.py pdfs --src $SRC ${ONLY:+--only $ONLY} >> $SRC/refresh-fetch.log 2>&1; then :; else
    DOWN="--source-down"; log "fetch failed: $(tail -n 1 $SRC/refresh-fetch.log | cut -c1-200)"; fi
  cd $R && git fetch -q origin && git merge -q --ff-only origin/main || { log "FAILED: clone not FF with origin"; exit 1; }
  DOCS=$(date -u +%F)
  if [ -z "$DOWN" ]; then
    python -X utf8 $T/canton_build.py scan --cc $CC --src $SRC > $SRC/refresh-scan.out 2>&1 || { log "FAILED scan"; exit 1; }
    python -X utf8 $T/canton_build.py parse --cc $CC --src $SRC --repo $R --out $L/corpus.d > $SRC/refresh-parse.out 2>&1 || { log "FAILED parse: $(tail -n 2 $SRC/refresh-parse.out | tr '\n' ' ' | cut -c1-300)"; exit 1; }
    python -X utf8 $T/canton_build.py verify --cc $CC --src $SRC --out $L/corpus.d > $SRC/refresh-verify.out 2>&1
    if [ $? -ne 0 ]; then
      python -X utf8 $T/canton_build.py parse --cc $CC --src $SRC --repo $R --out $L/corpus.d > $SRC/refresh-parse.out 2>&1 || { log "FAILED parse (2)"; exit 1; }
    fi
    python -X utf8 $B/recover_acts.py $R $L/corpus.d/00-recovered.json --extra $SRC/labels.json > $SRC/refresh-recover.out 2>&1 || { log "FAILED recover"; exit 1; }
    log "parsed: $(tail -n 1 $SRC/refresh-parse.out | cut -c1-200)"
    cd $G
    python -X utf8 append.py $LW --repo $R --docs-date $DOCS --dry-run > $SRC/refresh-dry.out 2>&1 || { log "FAILED dry run: $(tail -n 3 $SRC/refresh-dry.out | tr '\n' ' ' | cut -c1-400)"; exit 1; }
    held=$(python -X utf8 -c "import ast,sys;d=ast.literal_eval(open(sys.argv[1],encoding='utf-8').read().strip().splitlines()[-1]);print(len(d.get('held_acts',[])))" $SRC/refresh-dry.out)
    [ "$held" = "0" ] || { log "FAILED dry run: $held published acts read differently"; exit 1; }
    while true; do
      [ -f $SRC/STOP-REFRESH ] && { log "stop file between batches"; exit 0; }
      before=$(git -C $R rev-parse main)
      while [ $(( $(git -C $R log -1 --format=%ct main) + 330 )) -gt $(date +%s) ]; do sleep 10; done
      python -X utf8 append.py $LW --repo $R --docs-date $DOCS > $SRC/refresh-append.out 2>&1 || { log "FAILED append: $(tail -n 3 $SRC/refresh-append.out | tr '\n' ' ' | cut -c1-400)"; git -C $R reset -q --hard $before; exit 1; }
      after=$(git -C $R rev-parse main)
      [ "$before" = "$after" ] && break
      [ "$(gate)" = "0" ] || { log "FAILED check; reset to $before, not pushed"; git -C $R reset -q --hard $before; exit 1; }
      git -C $R merge-base --is-ancestor origin/main main || { log "FAILED: not a fast-forward"; exit 1; }
      git -C $R push -q origin main 2>> $SRC/refresh-push.log || { log "FAILED push main"; exit 1; }
      git -C $R push -q origin --tags 2>> $SRC/refresh-push.log || { log "FAILED push tags"; exit 1; }
      git -C $R fetch -q origin
      log "batch pushed: $before -> $after ($(git -C $R rev-list --count $before..$after) commits)"
    done
  fi
  before=$(git -C $R rev-parse main)
  [ -z "$DOWN" ] && { python -X utf8 $T/canton_readme.py --cc $CC --repo $R --src $SRC --out $L/README.md > /dev/null 2>&1 || { log "FAILED readme"; exit 1; }; }
  python -X utf8 $T/freshness_canton.py --cc $CC --repo $R --src $SRC --readme $L/README.md --commit $DOWN > $SRC/refresh-fresh.out 2>&1 || { log "FAILED freshness: $(tail -n 2 $SRC/refresh-fresh.out | tr '\n' ' ' | cut -c1-300)"; git -C $R reset -q --hard $before; exit 1; }
  after=$(git -C $R rev-parse main)
  if [ "$before" != "$after" ]; then
    [ "$(gate)" = "0" ] || { log "FAILED check after freshness; reset"; git -C $R reset -q --hard $before; exit 1; }
    git -C $R merge-base --is-ancestor origin/main main && git -C $R push -q origin main 2>> $SRC/refresh-push.log || { log "FAILED push freshness"; exit 1; }
    git -C $R fetch -q origin
    log "freshness pushed: $(head -c 300 $SRC/refresh-fresh.out | tr '\n' ' ')"
  else
    log "freshness unchanged"
  fi
  [ "${ONCE:-0}" = "1" ] && { log "done (once)"; exit 0; }
  for i in $(seq 1 2880); do [ -f $SRC/STOP-REFRESH ] && break; sleep 30; done
done
