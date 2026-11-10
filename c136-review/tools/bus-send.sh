#!/usr/bin/env bash
# bus-send.sh — 在联络分支体系里发一条留言：写文件、提交、推送，一步完成。
#
# 模型 → c136（在自己的 c136 工作区里执行，正文从标准输入读）：
#   BUS_ME=R03 bash c136-review/tools/bus-send.sh <主题> [--type 类型] [--re 回复的留言路径] <<'EOF'
#   正文
#   EOF
#   留言写到 c136-review/agents/R03/outbox/NNNN-<主题>.md；
#   同时把 c136-review/agents/R03/ 下所有改动一起提交推送（报告、脚本、已读记录）。
#
# c136 → 模型：
#   BUS_ME=HUB bash c136-review/tools/bus-send.sh <主题> --to R03|ALL [--type 类型] [--re 路径] <<'EOF'
#   正文
#   EOF
#   留言写到 c136-review/inbox/R03/NNNN-<主题>.md（ALL 为广播）。
#
# 主题：小写英文、数字、短横线，例如 r1-report、question-replay-format。
# 类型：hello | report | question | answer | task | alert | note（默认 note）。

set -u

ME="${BUS_ME:-}"
REMOTE="${BUS_REMOTE:-origin}"
HUB_BRANCH="${BUS_HUB_BRANCH:-cursor/c136-hub-3ce1}"
ROOT_DIR="c136-review"

die() { echo "BUS-SEND: ERROR $*" >&2; exit 2; }

case "$ME" in
  HUB|R[0-9][0-9]) ;;
  *) die "请先设置 BUS_ME=HUB 或 BUS_ME=R01..R10" ;;
esac

TOPIC="${1:-}"
[ -n "$TOPIC" ] || die "缺少主题。用法见脚本开头"
shift
printf '%s' "$TOPIC" | grep -Eq '^[a-z0-9][a-z0-9-]{0,59}$' || die "主题只能用小写英文、数字、短横线（最长 60 个字符）"

TO="HUB"
TYPE="note"
RE=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --to)   TO="${2:-}";   shift 2 ;;
    --type) TYPE="${2:-}"; shift 2 ;;
    --re)   RE="${2:-}";   shift 2 ;;
    *) die "不认识的参数：$1" ;;
  esac
done

TOP="$(git rev-parse --show-toplevel 2>/dev/null)" || die "当前目录不在 git 工作区里"
cd "$TOP" || exit 2
BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null)"

if [ "$ME" = HUB ]; then
  [ "$BRANCH" = "$HUB_BRANCH" ] || die "HUB 只能在联络分支 $HUB_BRANCH 上发信（当前：$BRANCH）"
  case "$TO" in
    ALL|R[0-9][0-9]) ;;
    *) die "HUB 发信必须带 --to R01..R10 或 --to ALL" ;;
  esac
  DIR="$ROOT_DIR/inbox/$TO"
  ACKS="$ROOT_DIR/hub/acks.txt"
else
  NN="$(printf '%s' "$ME" | sed -E 's/^R//')"
  case "$BRANCH" in
    cursor/c136-r"$NN"-*) ;;
    *) die "$ME 只能在自己的分支 cursor/c136-r$NN-<后缀> 上发信（当前：$BRANCH）。先跑 bus-init.sh" ;;
  esac
  DIR="$ROOT_DIR/agents/$ME/outbox"
  ACKS="$ROOT_DIR/agents/$ME/acks.txt"
fi

BODY="$(cat)"
[ -n "$BODY" ] || die "正文为空（正文从标准输入读）"

mkdir -p "$DIR"
LAST="$(ls "$DIR" 2>/dev/null | grep -E '^[0-9]{4}-' | sort | tail -n 1 | cut -c1-4)"
SEQ="$(printf '%04d' $(( 10#${LAST:-0} + 1 )))"
FILE="$DIR/$SEQ-$TOPIC.md"

{
  echo "---"
  echo "from: $ME"
  echo "to: $TO"
  echo "type: $TYPE"
  [ -n "$RE" ] && echo "re: $RE"
  echo "time: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "---"
  echo
  printf '%s\n' "$BODY"
} > "$FILE"

if [ "$ME" = HUB ]; then
  git add -- "$FILE"
  [ -f "$ACKS" ] && git add -- "$ACKS"
else
  git add -- "$ROOT_DIR/agents/$ME"
fi
git commit -q -m "bus($ME->$TO): $TOPIC" || die "提交失败"

DELAY=4
for TRY in 1 2 3 4 5; do
  if timeout 100 git push -q -u "$REMOTE" HEAD 2>/dev/null; then
    echo "BUS-SEND: OK $FILE（已推送到 $BRANCH）"
    exit 0
  fi
  [ "$TRY" -eq 5 ] && break
  sleep "$DELAY"
  DELAY=$(( DELAY * 2 ))
done
die "推送失败（已提交在本地）。稍后手动执行：git push -u $REMOTE HEAD"
