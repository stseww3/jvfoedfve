#!/usr/bin/env bash
# prep.sh — 准备 R04 机制分析的只读输入（v2.0）。
#
# 用法（在自己的 c136 工作区里执行）：
#   bash c136-review/agents/R04/scripts/prep.sh
#
# 输入（只读）：/agent/repos/c136-data/src/engine/live_game_js.js
# 输出（全部在 c136-review/agents/R04/tmp/，该目录被 .gitignore 排除，不进分支，可随时重建）：
#   tmp/nodetools/           acorn@8 / acorn-walk@8 / prettier@3
#   tmp/pretty/live.pretty.js  排版后的全文
#   tmp/pretty/index.json      构造函数 / 成员 / 全局实例索引（jsfn.cjs 用）
#
# 每条命令都带 timeout；重复执行安全。
set -u
LIVE_SHA=2b5731c7247dad761598fb8d978cb96b485e3264f4cef8f82c951b1c1d1dcba6
HERE="$(cd "$(dirname "$0")" && pwd)"
TOP="$(git -C "$HERE" rev-parse --show-toplevel)"
T="$HERE/../tmp"
LIVE="${R04_LIVE:-/agent/repos/c136-data/src/engine/live_game_js.js}"

mkdir -p "$T/nodetools" "$T/pretty"
GOT="$(sha256sum "$LIVE" | cut -d' ' -f1)"
if [ "$GOT" != "$LIVE_SHA" ]; then
  echo "PREP: WARNING live_game_js.js 的 sha256 变了：$GOT（规格书针对 $LIVE_SHA）"
fi

if [ ! -d "$T/nodetools/node_modules/prettier" ]; then
  ( cd "$T/nodetools" && timeout 60 npm init -y >/dev/null 2>&1; npm_config_cache="$T/nodetools/.npmcache" timeout 110 npm install --no-audit --no-fund acorn@8 acorn-walk@8 prettier@3 >/dev/null 2>&1 ) || { echo "PREP: ERROR npm install 失败"; exit 2; }
fi

NODE_PATH="$T/nodetools/node_modules" HEAVY_QUEUE=90 timeout 115 bash "$TOP/c136-review/tools/run-heavy.sh" node "$HERE/jsindex.cjs" "$LIVE" "$T/pretty" || exit 2
echo "PREP: OK  $T/pretty/live.pretty.js  $T/pretty/index.json"
