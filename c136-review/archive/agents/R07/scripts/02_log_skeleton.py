#!/usr/bin/env python3
"""02_log_skeleton.py — 小队日志的骨架：按行号列出能划分对局边界的行。

用法：
  python3 02_log_skeleton.py <raw_dir> > out/common/log_skeleton.txt

列出：
  [HL-GAME-INIT]（每号每局一条）、[RESULT …]、[OPENING-CHECK …]、[HOT-IMPORT]、
  [BACKEND-SPAWN-COORD] 的首条（每一段连续出现只列第一条和条数）、
  "ERROR: Strategy bot stopped" 按（号, 连续段）汇总首末行号与条数。
日志本身没有墙上时间，只有行号和拍号 t=；对局边界靠 GAME-INIT / RESULT 的顺序确定。
连接 / 握手 / 验证相关的行不输出（范围外）。
"""
import re
import sys

raw = sys.argv[1] if len(sys.argv) > 1 else "/tmp/c136-r07/raw"
path = f"{raw}/G01-G09-squad.log"

BOT_PREFIX = re.compile(r"^\[\[Nope\] ([A-Za-z0-9_]+)\] ?(.*)$", re.S)

rows = []
err_runs = {}      # bot -> [first, last, n, msg]
coord_run = None   # [first, last, n, sample]


def flush_coord():
    global coord_run
    if coord_run:
        rows.append((coord_run[0], f"COORD x{coord_run[2]} (lines {coord_run[0]}..{coord_run[1]}) {coord_run[3][:200]}"))
        coord_run = None


def flush_err(bot):
    r = err_runs.pop(bot, None)
    if r:
        rows.append((r[0], f"ERROR-RUN bot={bot} x{r[2]} (lines {r[0]}..{r[1]}) msg={r[3][:160]}"))


with open(path, encoding="utf-8", errors="replace") as f:
    for ln, line in enumerate(f, 1):
        line = line.rstrip("\n")
        m = BOT_PREFIX.match(line)
        bot = m.group(1) if m else None
        body = m.group(2) if m else line
        if body.startswith("[BACKEND-SPAWN-COORD]"):
            if coord_run is None:
                coord_run = [ln, ln, 1, body]
            else:
                coord_run[1] = ln
                coord_run[2] += 1
            continue
        if body.startswith("[HL-GAME-INIT]"):
            flush_coord()
            rows.append((ln, f"INIT bot={bot} {body}"))
        elif body.startswith("[RESULT"):
            flush_coord()
            for b in list(err_runs):
                flush_err(b)
            rows.append((ln, body[:400]))
        elif body.startswith("[OPENING-CHECK"):
            rows.append((ln, body[:140] + " …"))
        elif body.startswith("[HOT-IMPORT]"):
            rows.append((ln, body[:200]))
        elif body.startswith("ERROR: Strategy"):
            r = err_runs.get(bot)
            if r is None:
                err_runs[bot] = [ln, ln, 1, body]
            else:
                r[1] = ln
                r[2] += 1
for b in list(err_runs):
    flush_err(b)
flush_coord()

for ln, text in sorted(rows):
    print(f"{ln}\t{text}")
