#!/usr/bin/env bash
# bus-init.sh — 模型开工第一步：建好（或找回）自己的分支和工作区。重开后再跑一次也安全。
#
# 用法（在 stseww3/jvfoedfve 的任意一个本地克隆或工作区里执行）：
#   H=$(git ls-remote origin refs/heads/cursor/c136-hub-3ce1 | cut -f1)
#   git fetch -q --no-tags --refmap='' origin refs/heads/cursor/c136-hub-3ce1
#   BUS_ME=R03 BUS_SUFFIX=<分支后缀> bash <(git show $H:c136-review/tools/bus-init.sh)
#
#   BUS_SUFFIX：你的系统说明里规定了分支后缀就填它；没有规定可以不填，脚本随机生成。
#
# 做的事：
#   - 远端已有 cursor/c136-r03-* ：取下来接着用（重开的情况）
#   - 没有：从联络分支最新提交建 cursor/c136-r03-<后缀>
#   - 工作区放在克隆目录旁边：<克隆的上级目录>/c136-r03
#   - 建好 c136-review/agents/R03/ 的目录骨架
# 最后打印工作区路径和下一步该读的文件。

set -u

ME="${BUS_ME:-}"
SUFFIX="${BUS_SUFFIX:-}"
REMOTE="${BUS_REMOTE:-origin}"
HUB_BRANCH="${BUS_HUB_BRANCH:-cursor/c136-hub-3ce1}"
ROOT_DIR="c136-review"

die() { echo "BUS-INIT: ERROR $*" >&2; exit 2; }

case "$ME" in
  R[0-9][0-9]) ;;
  *) die "请先设置 BUS_ME=R01..R10" ;;
esac
NN="$(printf '%s' "$ME" | sed -E 's/^R//')"

COMMON="$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null)" || die "当前目录不在 git 仓库里"
MAIN_TOP="$(dirname "$COMMON")"
WT="$(dirname "$MAIN_TOP")/c136-r$NN"

if [ -e "$WT/.git" ]; then
  BRANCH="$(git -C "$WT" rev-parse --abbrev-ref HEAD 2>/dev/null)"
  echo "BUS-INIT: OK 工作区已存在：$WT（分支 $BRANCH）"
else
  EXISTING="$(timeout 40 git ls-remote "$REMOTE" "refs/heads/cursor/c136-r$NN-*" 2>/dev/null | head -n 1)"
  if [ -n "$EXISTING" ]; then
    SHA="${EXISTING%%[[:space:]]*}"
    REF="${EXISTING##*[[:space:]]}"
    BRANCH="${REF#refs/heads/}"
    timeout 100 git fetch -q --no-tags --refmap='' "$REMOTE" "$REF" || die "取不到 $REF"
    if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
      git worktree add -q "$WT" "$BRANCH" || die "建工作区失败"
      git -C "$WT" merge -q --ff-only "$SHA" 2>/dev/null || true
    else
      git worktree add -q -b "$BRANCH" "$WT" "$SHA" || die "建工作区失败"
    fi
    echo "BUS-INIT: OK 找回已有分支 $BRANCH，工作区：$WT"
  else
    [ -n "$SUFFIX" ] || SUFFIX="$(printf '%04x' $(( (RANDOM << 8 ^ RANDOM) & 0xffff )))"
    printf '%s' "$SUFFIX" | grep -Eq '^[a-z0-9]{2,12}$' || die "BUS_SUFFIX 只能是 2~12 位小写字母或数字"
    BRANCH="cursor/c136-r$NN-$SUFFIX"
    HUBLINE="$(timeout 40 git ls-remote "$REMOTE" "refs/heads/$HUB_BRANCH" 2>/dev/null | head -n 1)"
    [ -n "$HUBLINE" ] || die "远端找不到联络分支 $HUB_BRANCH"
    HUBSHA="${HUBLINE%%[[:space:]]*}"
    timeout 100 git fetch -q --no-tags --refmap='' "$REMOTE" "refs/heads/$HUB_BRANCH" || die "取不到联络分支"
    git worktree add -q -b "$BRANCH" "$WT" "$HUBSHA" || die "建工作区失败"
    echo "BUS-INIT: OK 新建分支 $BRANCH，工作区：$WT"
  fi
fi

mkdir -p "$WT/$ROOT_DIR/agents/$ME/outbox" "$WT/$ROOT_DIR/agents/$ME/reports" \
         "$WT/$ROOT_DIR/agents/$ME/scripts" "$WT/$ROOT_DIR/agents/$ME/out"
touch "$WT/$ROOT_DIR/agents/$ME/acks.txt"

cat <<EOF

下一步：
  cd $WT
  读 $ROOT_DIR/LIAISON.md（联络协议），照做
  BUS_ME=$ME bash $ROOT_DIR/tools/bus-wait.sh 0      # 取广播和你的任务
你只能写 $ROOT_DIR/agents/$ME/ 下面的文件。
EOF
