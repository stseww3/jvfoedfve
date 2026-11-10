#!/usr/bin/env bash
# bus-wait.sh — c136 复盘项目的「等待消息进程」。
#
# 一条阻塞命令，同时等两路消息，谁先到就返回：
#   1. 联络分支上有人给我留言（GitHub）
#   2. Telegram 桥的长等待返回（可选，设置了 TG_AGENT 和 TG_WAIT_URL 才启用）
#
# 用法（在自己的 c136 工作区里执行）：
#   BUS_ME=R03 bash c136-review/tools/bus-wait.sh          # 长等待，默认最长 6720 秒
#   BUS_ME=R03 bash c136-review/tools/bus-wait.sh 0        # 只看一眼，立刻返回
#   TG_AGENT='你的身份' TG_WAIT_URL='http://…/wait' BUS_ME=R03 bash c136-review/tools/bus-wait.sh
#
# 环境变量：
#   BUS_ME          必填。HUB（c136）或 R01..R10
#   TG_AGENT        可选。Telegram 桥身份，只通过环境变量传，绝不写进文件
#   TG_WAIT_URL     可选。桥的长等待地址，就是任务原文或【续棒】里 curl 的那个 URL
#   BUS_POLL        可选。隔多少秒问一次远端，默认 20
#   BUS_REMOTE      可选。远端名，默认 origin
#   BUS_HUB_BRANCH  可选。联络分支，默认 cursor/c136-hub-3ce1
#
# 输出的第一行说明为什么返回：
#   BUS-WAIT: MESSAGE <n>   后面是 n 条新留言的全文（已自动记为已读）
#   BUS-WAIT: TELEGRAM      后面是桥返回的最后一行，照它说的做（通常是去 read_chat）
#   BUS-WAIT: TIMEOUT       等满了，没有消息
#   BUS-WAIT: NONE          只看一眼，没有新留言
#   BUS-WAIT: ERROR <原因>  配置有问题（退出码 2）

set -u

ME="${BUS_ME:-}"
MAX="${1:-6720}"
POLL="${BUS_POLL:-20}"
REMOTE="${BUS_REMOTE:-origin}"
HUB_BRANCH="${BUS_HUB_BRANCH:-cursor/c136-hub-3ce1}"
ROOT_DIR="c136-review"
MAX_LINES=400

case "$ME" in
  HUB|R[0-9][0-9]) ;;
  *) echo "BUS-WAIT: ERROR 请先设置 BUS_ME=HUB 或 BUS_ME=R01..R10"; exit 2 ;;
esac
case "$MAX" in ''|*[!0-9]*) echo "BUS-WAIT: ERROR 等待秒数必须是非负整数"; exit 2 ;; esac
case "$POLL" in ''|*[!0-9]*) POLL=20 ;; esac
[ "$POLL" -lt 5 ] && POLL=5

TOP="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "BUS-WAIT: ERROR 当前目录不在 git 工作区里"; exit 2; }
cd "$TOP" || exit 2

if [ "$ME" = HUB ]; then
  ACKS="$ROOT_DIR/hub/acks.txt"
  PATTERN="refs/heads/cursor/c136-r[0-9][0-9]-*"
else
  ACKS="$ROOT_DIR/agents/$ME/acks.txt"
  PATTERN="refs/heads/$HUB_BRANCH"
fi
mkdir -p "$(dirname "$ACKS")"
touch "$ACKS"

declare -A SEEN_SHA
FOUND=()

# 问一次远端；把新留言登记到 FOUND（元素格式：<提交号> <路径>）。
check_bus() {
  local out sha ref agent files f
  local -a dirs
  out="$(timeout 40 git ls-remote "$REMOTE" "$PATTERN" 2>/dev/null)" || return 1
  [ -n "$out" ] || return 0
  while IFS=$'\t' read -r sha ref; do
    [ -n "$sha" ] && [ -n "$ref" ] || continue
    [ "${SEEN_SHA[$ref]:-}" = "$sha" ] && continue
    if ! git cat-file -e "${sha}^{commit}" 2>/dev/null; then
      # --refmap='' ：只取对象，不更新共享的远端跟踪引用，多个模型同时取也不会抢锁
      timeout 100 git fetch -q --no-tags --refmap='' "$REMOTE" "$ref" 2>/dev/null || continue
      git cat-file -e "${sha}^{commit}" 2>/dev/null || continue
    fi
    if [ "$ME" = HUB ]; then
      agent="$(printf '%s' "$ref" | sed -E 's#^refs/heads/cursor/c136-r([0-9]{2})-.*$#R\1#')"
      dirs=("$ROOT_DIR/agents/$agent/outbox")
    else
      dirs=("$ROOT_DIR/inbox/$ME" "$ROOT_DIR/inbox/ALL")
    fi
    files="$(git ls-tree -r --name-only "$sha" -- "${dirs[@]}" 2>/dev/null | grep -E '\.md$' | sort | grep -Fxv -f "$ACKS" || true)"
    SEEN_SHA[$ref]="$sha"
    [ -n "$files" ] || continue
    while IFS= read -r f; do
      [ -n "$f" ] && FOUND+=("$sha $f")
    done <<< "$files"
  done <<< "$out"
  return 0
}

print_found() {
  local item sha path total
  echo "BUS-WAIT: MESSAGE ${#FOUND[@]}"
  for item in "${FOUND[@]}"; do
    sha="${item%% *}"
    path="${item#* }"
    echo
    echo "=== [BUS] $path  (@${sha:0:8}) ==="
    total="$(git show "$sha:$path" 2>/dev/null | wc -l)"
    git show "$sha:$path" 2>/dev/null | head -n "$MAX_LINES"
    if [ "$total" -gt "$MAX_LINES" ]; then
      echo "…（共 $total 行，只显示前 $MAX_LINES 行；看全文：git show ${sha:0:12}:$path）"
    fi
    echo "$path" >> "$ACKS"
  done
  echo
  echo "（以上留言已记入 $ACKS，下次提交时一并提交。）"
}

TGPID=""
TGOUT=""
TG_ON=0
if [ -n "${TG_AGENT:-}" ] && [ -n "${TG_WAIT_URL:-}" ] && [ "$MAX" -gt 0 ]; then
  TG_ON=1
  TGOUT="$(mktemp)"
fi

cleanup() {
  [ -n "$TGPID" ] && kill "$TGPID" 2>/dev/null
  [ -n "$TGOUT" ] && rm -f "$TGOUT"
}
trap cleanup EXIT

START="$(date +%s)"
start_tg() {
  local left=$(( MAX - ( $(date +%s) - START ) ))
  [ "$left" -lt 5 ] && return 1
  : > "$TGOUT"
  curl -sSN -m "$left" -H "X-Agent: $TG_AGENT" "$TG_WAIT_URL" > "$TGOUT" 2>&1 &
  TGPID=$!
  return 0
}

check_bus
if [ "${#FOUND[@]}" -gt 0 ]; then print_found; exit 0; fi
if [ "$MAX" -eq 0 ]; then echo "BUS-WAIT: NONE"; exit 0; fi

[ "$TG_ON" -eq 1 ] && start_tg
TG_RETRY_AT=0
NEXT_POLL=$(( $(date +%s) + POLL ))

while :; do
  NOW="$(date +%s)"
  if [ $(( NOW - START )) -ge "$MAX" ]; then
    echo "BUS-WAIT: TIMEOUT"
    exit 0
  fi

  if [ "$TG_ON" -eq 1 ]; then
    if [ -n "$TGPID" ] && ! kill -0 "$TGPID" 2>/dev/null; then
      wait "$TGPID" 2>/dev/null
      RC=$?
      TGPID=""
      if [ "$RC" -eq 0 ]; then
        echo "BUS-WAIT: TELEGRAM"
        tail -n 1 "$TGOUT"
        echo
        exit 0
      fi
      # 连接断了或超时：过 30 秒自动重连，期间继续等联络分支
      TG_RETRY_AT=$(( NOW + 30 ))
    fi
    if [ -z "$TGPID" ] && [ "$TG_RETRY_AT" -gt 0 ] && [ "$NOW" -ge "$TG_RETRY_AT" ]; then
      TG_RETRY_AT=0
      start_tg || TG_ON=0
    fi
  fi

  if [ "$NOW" -ge "$NEXT_POLL" ]; then
    NEXT_POLL=$(( NOW + POLL ))
    check_bus
    if [ "${#FOUND[@]}" -gt 0 ]; then print_found; exit 0; fi
  fi

  sleep 1
done
