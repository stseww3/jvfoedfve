#!/usr/bin/env bash
# bus-sync.sh — 把联络分支的最新提交合并进你自己的分支（拿到更新后的脚本和文档）。
# 用法（在自己的 c136 工作区里执行）：bash c136-review/tools/bus-sync.sh
# 你只写 c136-review/agents/RNN/，联络分支不写那里，所以不会冲突。

set -u
REMOTE="${BUS_REMOTE:-origin}"
HUB_BRANCH="${BUS_HUB_BRANCH:-cursor/c136-hub-3ce1}"
die() { echo "BUS-SYNC: ERROR $*" >&2; exit 2; }

BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null)" || die "当前目录不在 git 工作区里"
case "$BRANCH" in
  cursor/c136-r[0-9][0-9]-*) ;;
  *) die "只能在自己的 cursor/c136-rNN-<后缀> 分支上执行（当前：$BRANCH）" ;;
esac
LINE="$(timeout 40 git ls-remote "$REMOTE" "refs/heads/$HUB_BRANCH" 2>/dev/null | head -n 1)"
[ -n "$LINE" ] || die "远端找不到联络分支"
SHA="${LINE%%[[:space:]]*}"
if ! git cat-file -e "${SHA}^{commit}" 2>/dev/null; then
  timeout 110 git fetch -q --no-tags --refmap='' "$REMOTE" "refs/heads/$HUB_BRANCH" || die "取不到联络分支"
fi
if git merge-base --is-ancestor "$SHA" HEAD 2>/dev/null; then
  echo "BUS-SYNC: OK 已是最新（${SHA:0:12}）"
  exit 0
fi
git merge -q --no-edit -m "sync hub ${SHA:0:12}" "$SHA" || die "合并失败，请把输出发给 c136"
echo "BUS-SYNC: OK 已合并联络分支 ${SHA:0:12}"
