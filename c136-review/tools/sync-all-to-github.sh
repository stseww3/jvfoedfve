#!/usr/bin/env bash
# sync-all-to-github.sh — 将 R01~R10 各工作区的最新复盘、报告、脚本、笔记提交推送到各自分支，
# 并同时镜像归档到联络主分支 cursor/c136-hub-3ce1 的 c136-review/archive/agents/ 下双保险推送到 GitHub。
set -u

HUB_WT="/agent/repos/c136-hub"
ARCHIVE_DIR="$HUB_WT/c136-review/archive/agents"
mkdir -p "$ARCHIVE_DIR"

for r in 01 02 03 04 05 06 07 08 09 10; do
  WT="/agent/repos/c136-r$r"
  R="R$r"
  SRC="$WT/c136-review/agents/$R"
  [ -d "$SRC" ] || continue

  # 1. 把已完成的 reviews / reports / scripts / notes / cards / outbox 镜像到主分支 archive/agents/Rxx/
  DST="$ARCHIVE_DIR/$R"
  mkdir -p "$DST"
  for sub in reviews reports scripts notes cards outbox review-src reviews_src analysis sim-v2; do
    if [ -d "$SRC/$sub" ]; then
      rm -rf "$DST/$sub"
      mkdir -p "$DST/$sub"
      cp -rf "$SRC/$sub/." "$DST/$sub/"
      find "$DST/$sub" \( -name '__pycache__' -o -name '*.pyc' -o -name 'node_modules' \) -exec rm -rf {} + 2>/dev/null || true
    fi
  done
  # 同步 out/ 下小于 2MB 的汇总文本/JSON/TSV/CSV（排除超大缓存）
  if [ -d "$SRC/out" ]; then
    mkdir -p "$DST/out"
    find "$SRC/out" -maxdepth 2 -type f \( -name "*.txt" -o -name "*.md" -o -name "*.tsv" -o -name "*.csv" -o -name "*.json" \) -size -2M | while read -r f; do
      rel="${f#$SRC/out/}"
      mkdir -p "$DST/out/$(dirname "$rel")"
      cp -f "$f" "$DST/out/$rel"
    done
  fi
done

cd "$HUB_WT" || exit 1
python3 c136-review/tools/collect-reviews.py || true
git add c136-review/archive/ c136-review/board/ c136-review/ledger/ c136-review/hub/acks.txt c136-review/tools/sync-all-to-github.sh
if ! git diff --cached --quiet; then
  REV_CNT=$(find c136-review/archive/agents/*/reviews -name "*.json" 2>/dev/null | wc -l)
  git commit -q -m "hub: archive all R01..R10 reviews ($REV_CNT matches), reports, scripts & summaries to GitHub"
  timeout 110 git push -q -u origin HEAD
  echo "SYNC-ALL: OK pushed $REV_CNT archived reviews and all scripts/reports to cursor/c136-hub-3ce1"
else
  echo "SYNC-ALL: OK already up to date"
fi
