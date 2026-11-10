#!/usr/bin/env bash
# prep.sh — 准备 R04 机制分析的只读输入（全部放在 /tmp/c136-r04，不进分支）。
#
# 用法（在自己的 c136 工作区里执行）：
#   bash c136-review/agents/R04/scripts/prep.sh
#
# 做的事：
#   1. 取数据 B（游戏客户端代码 live_game_js.js 等）和数据 A（c116 日志、结算、录像）
#   2. 校验 live_game_js.js 的 sha256（本目录所有「出处」都针对这个版本）
#   3. 从 fdvg 取模拟器源码（数据 C、D），不切换那边的分支
#   4. 装固定版本的 acorn / prettier，生成排版后的 live.pretty.js 和函数索引
#
# 每条命令都带 timeout；重复执行安全。
set -u
T=/tmp/c136-r04
LIVE_SHA=2b5731c7247dad761598fb8d978cb96b485e3264f4cef8f82c951b1c1d1dcba6
C58=2d3bbd365638421fe43ed9e6aee415d8aba8334f     # fdvg cursor/c58-v24-95b7
C117=97124c5caf5be8f48b5e8f06e164a56c8ce8e769    # fdvg cursor/c117-sim-teams-96f2
HERE="$(cd "$(dirname "$0")" && pwd)"
TOP="$(git -C "$HERE" rev-parse --show-toplevel)"
FDVG="${FDVG:-/agent/repos/fdvg}"

mkdir -p "$T"
cd "$TOP" || exit 2
[ -f "$T/c99-squad/live_game_js.js" ] || timeout 120 bash c136-review/tools/bus-get.sh cursor/team-squad-c99-67fd tsb/squad "$T/c99-squad" || exit 2
[ -d "$T/c116/data" ] || timeout 120 bash c136-review/tools/bus-get.sh cursor/c116-winrate-liaison-b3bc c116-winrate "$T/c116" || exit 2

GOT="$(sha256sum "$T/c99-squad/live_game_js.js" | cut -d' ' -f1)"
if [ "$GOT" != "$LIVE_SHA" ]; then
  echo "PREP: WARNING live_game_js.js 的 sha256 变了：$GOT（规格书针对 $LIVE_SHA）"
fi

if [ ! -d "$T/c58/territorial-sim/sim" ]; then
  mkdir -p "$T/c58" "$T/c117"
  git -C "$FDVG" cat-file -e "$C58^{commit}" 2>/dev/null || timeout 110 git -C "$FDVG" fetch -q --no-tags --refmap='' origin refs/heads/cursor/c58-v24-95b7
  git -C "$FDVG" cat-file -e "$C117^{commit}" 2>/dev/null || timeout 110 git -C "$FDVG" fetch -q --no-tags --refmap='' origin refs/heads/cursor/c117-sim-teams-96f2
  timeout 100 git -C "$FDVG" archive "$C58" -- territorial-sim/sim territorial-sim/NOTES-c6.md territorial-sim/NOTES-c22-ocean.md territorial-sim/package.json | tar -x -C "$T/c58"
  timeout 100 git -C "$FDVG" archive "$C117" -- territorial-sim/sim territorial-sim/tools/c117 | tar -x -C "$T/c117"
fi

if [ ! -d "$T/nodetools/node_modules/prettier" ]; then
  mkdir -p "$T/nodetools"
  ( cd "$T/nodetools" && timeout 60 npm init -y >/dev/null 2>&1; timeout 110 npm install --no-audit --no-fund acorn@8.19.0 acorn-walk@8 prettier@3.9.10 >/dev/null 2>&1 ) || { echo "PREP: ERROR npm install 失败"; exit 2; }
fi

mkdir -p "$T/pretty"
NODE_PATH="$T/nodetools/node_modules" timeout 110 node "$HERE/jsindex.cjs" "$T/c99-squad/live_game_js.js" "$T/pretty" || exit 2
echo "PREP: OK  $T/pretty/live.pretty.js  $T/pretty/index.json"
