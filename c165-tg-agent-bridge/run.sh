#!/bin/sh
# crontab 每分钟调用：进程不在就拉起；有 disabled 文件就不拉起
cd "$(dirname "$0")" || exit 1
umask 077
[ -f disabled ] && exit 0
if [ -f bridge.pid ] && grep -q uvicorn "/proc/$(cat bridge.pid)/cmdline" 2>/dev/null; then exit 0; fi
if [ -f server.log ] && [ "$(stat -c%s server.log)" -gt 10000000 ]; then mv -f server.log server.log.1; fi
nohup .venv/bin/python -m uvicorn app:app --host 0.0.0.0 --port 8787 --no-access-log --log-level warning --timeout-keep-alive 75 >> server.log 2>&1 &
echo $! > bridge.pid
