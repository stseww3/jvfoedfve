#!/usr/bin/env bash
# fetch-inputs.sh — 把 R03 用到的输入取到本地临时目录（只读使用，不进仓库）。
# 用法（在 c136 工作区里执行）：bash c136-review/agents/R03/scripts/fetch-inputs.sh
# 输出目录：/tmp/c136-r03/{b,a,c58,nm}
#   b/    数据 B：live_game_js.js（引擎，2.17.1）、live_dictionary.json
#   a/    数据 A：c116-winrate/data/（小队日志、结算）
#   c58/  数据 C：territorial-sim/sim、NOTES、tools 的一部分（fdvg cursor/c58-v24-95b7）
#   nm/   node 依赖（acorn、astring），版本见 package.json
set -u
OUT="${R03_TMP:-/tmp/c136-r03}"
REMOTE="${BUS_REMOTE:-origin}"
HERE="$(cd "$(dirname "$0")" && pwd)"
die() { echo "FETCH: ERROR $*" >&2; exit 2; }
mkdir -p "$OUT/b" "$OUT/a" "$OUT/c58" "$OUT/nm"

# 固定的提交号：换了提交号，下面的 sha256 校验会报出来。
B_BRANCH="cursor/team-squad-c99-67fd";       B_SHA="e923d6db751585afb763d4759101443c2862c989"
A_BRANCH="cursor/c116-winrate-liaison-b3bc"
C58_SHA="2d3bbd365638421fe43ed9e6aee415d8aba8334f"
ENGINE_SHA256="2b5731c7247dad761598fb8d978cb96b485e3264f4cef8f82c951b1c1d1dcba6"

git cat-file -e "${B_SHA}^{commit}" 2>/dev/null || timeout 110 git fetch -q --no-tags --refmap='' "$REMOTE" "refs/heads/$B_BRANCH" || die "取不到 $B_BRANCH"
for f in live_game_js.js live_dictionary.json; do
  git show "$B_SHA:tsb/squad/$f" > "$OUT/b/$f" || die "取不到 $f"
done
GOT="$(sha256sum "$OUT/b/live_game_js.js" | cut -d' ' -f1)"
[ "$GOT" = "$ENGINE_SHA256" ] || die "live_game_js.js 的 sha256 不符：$GOT"
echo "FETCH: OK 引擎 $OUT/b/live_game_js.js sha256=$GOT"

if [ "${1:-}" != "--engine-only" ]; then
  A_LINE="$(timeout 40 git ls-remote "$REMOTE" "refs/heads/$A_BRANCH" | head -n 1)"
  [ -n "$A_LINE" ] || die "远端找不到 $A_BRANCH"
  A_SHA="${A_LINE%%[[:space:]]*}"
  git cat-file -e "${A_SHA}^{commit}" 2>/dev/null || timeout 110 git fetch -q --no-tags --refmap='' "$REMOTE" "refs/heads/$A_BRANCH" || die "取不到 $A_BRANCH"
  git archive "$A_SHA" -- c116-winrate/data | tar -x -C "$OUT/a" --strip-components=1 || die "解包数据 A 失败"
  echo "$A_SHA" > "$OUT/a/COMMIT"
  echo "FETCH: OK 数据 A @${A_SHA:0:12} -> $OUT/a/data"
  if [ -d /agent/repos/fdvg/.git ]; then
    git -C /agent/repos/fdvg archive "$C58_SHA" -- territorial-sim/sim territorial-sim/NOTES-c6.md territorial-sim/NOTES-c22-ocean.md \
      territorial-sim/tools/oracle.js territorial-sim/tools/clone-test.js territorial-sim/tools/rng-trace.js \
      | tar -x -C "$OUT/c58" || die "解包数据 C 失败"
    echo "FETCH: OK 数据 C @${C58_SHA:0:12} -> $OUT/c58/territorial-sim"
  fi
fi

if [ ! -d "$OUT/nm/node_modules/acorn" ] || [ ! -d "$OUT/nm/node_modules/astring" ]; then
  cp "$HERE/package.json" "$OUT/nm/package.json"
  (cd "$OUT/nm" && timeout 110 npm install --no-audit --no-fund >/dev/null 2>&1) || die "npm install 失败"
fi
echo "FETCH: OK node 依赖 $OUT/nm/node_modules"
