#!/usr/bin/env bash
# fetch-src.sh — 把 R05 分析用到的源码和数据，按固定提交号取到本地临时目录（只读使用）。
# 用法（在自己的 c136 工作区里执行）：bash c136-review/agents/R05/scripts/fetch-src.sh [目标目录]
# 默认目标目录：/tmp/c136-r05/src
# 所有后续脚本都从这个目录读，文件名固定，提交号写死，任何人重跑得到同样的输入。
set -u
DEST="${1:-/tmp/c136-r05/src}"
REMOTE="${BUS_REMOTE:-origin}"

# 数据 B：c110 线（当前主线），分支 cursor/team-squad-c99-67fd
B_SHA=e923d6db751585afb763d4759101443c2862c989
B_REF=refs/heads/cursor/team-squad-c99-67fd
# 数据 A：c116 线，分支 cursor/c116-winrate-liaison-b3bc
A_SHA=d9a56dcde66f1ed24f0a88168580a2fbd2b0b088
A_REF=refs/heads/cursor/c116-winrate-liaison-b3bc
# G01~G09 那晚的版本（任务卡给的提交）
G_SHA=917e6b1f4960ede7046c00055809d7afae5d3c00

die() { echo "FETCH-SRC: ERROR $*" >&2; exit 2; }
git rev-parse --git-dir >/dev/null 2>&1 || die "当前目录不在 git 仓库里"

need() { # <sha> <ref>
  git cat-file -e "$1^{commit}" 2>/dev/null && return 0
  timeout 110 git fetch -q --no-tags --refmap='' "$REMOTE" "$2" || die "取不到 $2"
  git cat-file -e "$1^{commit}" 2>/dev/null || die "$2 上没有提交 $1（分支可能已前进；提交仍应在历史里）"
}
need "$B_SHA" "$B_REF"
need "$A_SHA" "$A_REF"
git cat-file -e "$G_SHA^{commit}" 2>/dev/null || need "$G_SHA" "$B_REF"

mkdir -p "$DEST" || die "建不了目录 $DEST"
get() { # <sha> <路径> <本地名>
  git show "$1:$2" > "$DEST/$3" 2>/dev/null || die "$1 里没有 $2"
}
get "$B_SHA" tsb/squad/v27-team-live.js            c110.js
get "$B_SHA" tsb/squad/make_v27_team.py            c110-make.py
get "$A_SHA" c116-winrate/v27-apex-live.js         c116.js
get "$G_SHA" tsb/squad/v27-team-live.js            g09.js
get "$G_SHA" tsb/squad/make_v27_team.py            g09-make.py
get "$A_SHA" c116-winrate/data/README.md           data-README.md
get "$A_SHA" c116-winrate/data/G01-G09-squad.log   squad.log
get "$A_SHA" c116-winrate/data/commit-log-6d4aadd-to-917e6b1.txt commit-log.txt
get "$A_SHA" c116-winrate/data/code-diff-6d4aadd-to-917e6b1.patch code-diff.patch

# 数据 C：模拟器仓库 stseww3/fdvg，分支 cursor/c58-v24-95b7（只读取对象，不切换那边检出的分支）
F_REPO="${R05_FDVG:-/agent/repos/fdvg}"
F_SHA=2d3bbd365638421fe43ed9e6aee415d8aba8334f
F_REF=refs/heads/cursor/c58-v24-95b7
if ! git -C "$F_REPO" cat-file -e "$F_SHA^{commit}" 2>/dev/null; then
  timeout 110 git -C "$F_REPO" fetch -q --no-tags --refmap='' origin "$F_REF" || die "fdvg 取不到 $F_REF"
fi
mkdir -p "$DEST/sim"
for f in index.js game.js bots.js boats.js clone.js map.js rng.js; do
  git -C "$F_REPO" show "$F_SHA:territorial-sim/sim/$f" > "$DEST/sim/$f" 2>/dev/null || die "fdvg $F_SHA 里没有 sim/$f"
done
# make_v27_team.py 的输入：单人版 v27-live.js
git -C "$F_REPO" show "$F_SHA:territorial-sim/strategy/pool/v27-live.js" > "$DEST/v27-live-base.js" 2>/dev/null || die "fdvg 里没有 v27-live.js"

{
  echo "sim/*.js      fdvg@$F_SHA territorial-sim/sim/"
  echo "v27-live-base.js fdvg@$F_SHA territorial-sim/strategy/pool/v27-live.js"
  echo "c110.js       $B_SHA tsb/squad/v27-team-live.js"
  echo "c110-make.py  $B_SHA tsb/squad/make_v27_team.py"
  echo "c116.js       $A_SHA c116-winrate/v27-apex-live.js"
  echo "g09.js        $G_SHA tsb/squad/v27-team-live.js"
  echo "g09-make.py   $G_SHA tsb/squad/make_v27_team.py"
  echo "data-README.md $A_SHA c116-winrate/data/README.md"
  echo "squad.log     $A_SHA c116-winrate/data/G01-G09-squad.log"
  echo "commit-log.txt $A_SHA c116-winrate/data/commit-log-6d4aadd-to-917e6b1.txt"
  echo "code-diff.patch $A_SHA c116-winrate/data/code-diff-6d4aadd-to-917e6b1.patch"
} > "$DEST/SOURCES.txt"
( cd "$DEST" && sha256sum c110.js c110-make.py c116.js g09.js g09-make.py squad.log v27-live-base.js sim/game.js > SHA256SUMS.txt )
echo "FETCH-SRC: OK -> $DEST"
cat "$DEST/SHA256SUMS.txt"
wc -lc "$DEST"/c110.js "$DEST"/c110-make.py "$DEST"/c116.js "$DEST"/g09.js "$DEST"/g09-make.py "$DEST"/squad.log "$DEST"/v27-live-base.js
