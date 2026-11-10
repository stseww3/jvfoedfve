#!/usr/bin/env bash
# bus-get.sh — 把别人已推送的目录原样取到本地临时目录（只读使用，不进你的分支）。
#
# 用法（在自己的 c136 工作区里执行）：
#   bash c136-review/tools/bus-get.sh <来源> <仓库内路径> <本地目标目录>
#
#   来源：HUB（联络分支）｜R01..R10（对应模型的分支）｜任意远端分支全名（例如 cursor/c116-winrate-liaison-b3bc）
#
# 例：
#   bash c136-review/tools/bus-get.sh R01 c136-review/agents/R01/out/bundles /tmp/c136-r07/bundles
#   bash c136-review/tools/bus-get.sh cursor/team-squad-c99-67fd tsb/squad /tmp/c136-r05/c99-squad
#
# 输出：BUS-GET: OK <分支>@<提交号> -> <目标目录>（<文件数> 个文件）
# 只取 c136 广播里公布过的路径；不要取其他复盘员尚未公布的结论。

set -u
REMOTE="${BUS_REMOTE:-origin}"
HUB_BRANCH="${BUS_HUB_BRANCH:-cursor/c136-hub-3ce1}"
die() { echo "BUS-GET: ERROR $*" >&2; exit 2; }

SRC="${1:-}"; PATHSPEC="${2:-}"; DEST="${3:-}"
[ -n "$SRC" ] && [ -n "$PATHSPEC" ] && [ -n "$DEST" ] || die "用法：bus-get.sh <来源> <仓库内路径> <本地目标目录>"
git rev-parse --git-dir >/dev/null 2>&1 || die "当前目录不在 git 仓库里"

case "$SRC" in
  HUB) PATTERN="refs/heads/$HUB_BRANCH" ;;
  R[0-9][0-9]) PATTERN="refs/heads/cursor/c136-r${SRC#R}-*" ;;
  *) PATTERN="refs/heads/$SRC" ;;
esac

LINE="$(timeout 40 git ls-remote "$REMOTE" "$PATTERN" 2>/dev/null | head -n 1)"
[ -n "$LINE" ] || die "远端找不到 $SRC 的分支（$PATTERN）"
SHA="${LINE%%[[:space:]]*}"
REF="${LINE##*[[:space:]]}"
if ! git cat-file -e "${SHA}^{commit}" 2>/dev/null; then
  timeout 110 git fetch -q --no-tags --refmap='' "$REMOTE" "$REF" || die "取不到 $REF"
fi
git cat-file -e "${SHA}:${PATHSPEC}" 2>/dev/null || die "$REF@${SHA:0:8} 里没有路径 $PATHSPEC"

mkdir -p "$DEST" || die "建不了目录 $DEST"
STRIP="$(printf '%s' "${PATHSPEC%/}" | awk -F/ '{print NF}')"
if [ "$(git cat-file -t "${SHA}:${PATHSPEC}")" = "tree" ]; then
  git archive "$SHA" -- "$PATHSPEC" | tar -x -C "$DEST" --strip-components="$STRIP" || die "解包失败"
else
  git show "${SHA}:${PATHSPEC}" > "$DEST/$(basename "$PATHSPEC")" || die "写文件失败"
fi
N="$(find "$DEST" -type f | wc -l)"
echo "BUS-GET: OK ${REF#refs/heads/}@${SHA:0:12} -> $DEST（$N 个文件）"
