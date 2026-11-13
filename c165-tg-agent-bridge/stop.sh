#!/bin/sh
cd "$(dirname "$0")" || exit 1
here="$(pwd -P)"

ours() {
    grep -q uvicorn "/proc/$1/cmdline" 2>/dev/null && [ "$(readlink "/proc/$1/cwd")" = "$here" ]
}

pids=""
if [ -f bridge.pid ]; then
    pid="$(cat bridge.pid)"
    ours "$pid" && pids="$pid"
    rm -f bridge.pid
fi
# 只停这个目录里起的进程：同一个用户的别的项目也可能叫 app:app
# 从命令行开头匹配 python 跑 uvicorn，免得误杀命令里恰好提到 uvicorn app:app 的 shell
for pid in $(pgrep -u "$(id -u)" -f '^[^ ]*python[0-9.]* (-m uvicorn|[^ ]*/uvicorn) (app|server):app'); do
    ours "$pid" && pids="$pids $pid"
done
for pid in $pids; do kill "$pid" 2>/dev/null; done

# uvicorn 收到 TERM 后要等所有长连接（read_chat 能挂很久）断开才退出，这期间它还在拉 Telegram 消息、和新进程抢；
# 等 5 秒还没退就强杀，保证 ./stop.sh && ./run.sh 之后只剩新进程
i=0
while [ "$i" -lt 10 ]; do
    alive=""
    for pid in $pids; do kill -0 "$pid" 2>/dev/null && alive="$alive $pid"; done
    [ -z "$alive" ] && exit 0
    sleep 0.5
    i=$((i + 1))
done
for pid in $alive; do ours "$pid" && kill -9 "$pid" 2>/dev/null; done
exit 0
