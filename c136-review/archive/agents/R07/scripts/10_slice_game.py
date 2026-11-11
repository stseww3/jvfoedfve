#!/usr/bin/env python3
"""10_slice_game.py — 从 G01-G09-squad.log 里切出一局的日志切片。

用法：
  python3 10_slice_game.py <raw_dir> <G00..G09> <out_dir>
  例：python3 10_slice_game.py /tmp/c136-r07/raw G01 out/G01

切法（全部基于日志自身的顺序，日志没有墙上时间）：
  1. 把全部 [HL-GAME-INIT] 行按出现顺序分组：相邻两条 INIT 之间如果出现过 [RESULT …] 行，就算新的一局。
     得到 10 组（8+8+8+8+8+8+8+8+7+6=77 条 INIT），依次记为 G00..G09。
     G00 是 README 没编号的一局（16:20~16:24Z 结算、3 队），G01..G09 与 DISPATCH.md 明细表一一对应
     （用 mode / 结算记录里的 team.mine、终局拍核对，见 11_game_table.py）。
  2. 第 k 局的切片 = [本局第一条 INIT 行, 下一局第一条 INIT 行)；最后一局到文件最后一条 [RESULT] 行为止。
  3. 切片内只保留策略层 / 评估层的行；连接、握手、验证相关的行按 LIAISON §9 不输出，只计数。

输出：
  <out_dir>/squad.slice.log     每行：<原始行号>\t<原文>
  <out_dir>/slice.meta.json     切片边界、各类行计数
"""
import json
import os
import re
import sys

raw = sys.argv[1]
gid = sys.argv[2]
out_dir = sys.argv[3]
path = f"{raw}/G01-G09-squad.log"

BOT_PREFIX = re.compile(r"^\[\[Nope\] ([A-Za-z0-9_]+)\] ?(.*)$", re.S)
# [SELF-CHECK …] / [SQUAD-SYNC] 是进房与身份核对的行（含账号标识），同样不输出
OUT_OF_SCOPE = re.compile(
    r"turnstile|socket|Connection to Server|Attaching on port|devtools|Chrome|token|proxy|captcha|Minting|ws://|http://"
    r"|^\[SELF-CHECK|^\[SQUAD-SYNC\]",
    re.I)
KEEP_PREFIX = ("[HL-", "[BACKEND-SPAWN-COORD]", "[OPENING-CHECK", "[RESULT", "[HOT-IMPORT]", "ERROR: Strategy")

lines = []
with open(path, encoding="utf-8", errors="replace") as f:
    for ln, line in enumerate(f, 1):
        lines.append(line.rstrip("\n"))


def body_of(line):
    m = BOT_PREFIX.match(line)
    return (m.group(1), m.group(2)) if m else (None, line)


# 1. 分组
groups = []            # 每组：{"first_init": ln, "inits": [...], "last_result": ln}
seen_result_since_init = True
last_result_line = None
for i, line in enumerate(lines, 1):
    bot, body = body_of(line)
    if body.startswith("[HL-GAME-INIT]"):
        if seen_result_since_init:
            groups.append({"first_init": i, "inits": [], "last_result": None})
            seen_result_since_init = False
        groups[-1]["inits"].append({"line": i, "bot": bot, "text": body})
    elif body.startswith("[RESULT"):
        seen_result_since_init = True
        if groups:
            groups[-1]["last_result"] = i

idx = int(gid[1:])
if idx >= len(groups):
    sys.exit(f"no such game {gid}; groups={len(groups)}")
g = groups[idx]
start = g["first_init"]
end = groups[idx + 1]["first_init"] - 1 if idx + 1 < len(groups) else g["last_result"]

os.makedirs(out_dir, exist_ok=True)
kept = 0
dropped_oos = 0
kept_by_tag = {}
with open(f"{out_dir}/squad.slice.log", "w", encoding="utf-8") as out:
    for i in range(start, end + 1):
        line = lines[i - 1]
        bot, body = body_of(line)
        keep = body.startswith(KEEP_PREFIX) or not OUT_OF_SCOPE.search(body)
        if not keep:
            dropped_oos += 1
            continue
        kept += 1
        m = re.match(r"^\[([A-Z\-]+)", body)
        tag = m.group(1) if m else ("ERROR" if body.startswith("ERROR") else "other")
        kept_by_tag[tag] = kept_by_tag.get(tag, 0) + 1
        out.write(f"{i}\t{line}\n")

meta = {
    "game": gid,
    "source": "jvfoedfve cursor/c116-winrate-liaison-b3bc:c116-winrate/data/G01-G09-squad.log",
    "groupsFound": len(groups),
    "initsPerGroup": [len(x["inits"]) for x in groups],
    "sliceFirstLine": start,
    "sliceLastLine": end,
    "lastResultLine": g["last_result"],
    "inits": g["inits"],
    "keptLines": kept,
    "droppedOutOfScopeLines": dropped_oos,
    "keptByTag": dict(sorted(kept_by_tag.items())),
}
with open(f"{out_dir}/slice.meta.json", "w", encoding="utf-8") as out:
    json.dump(meta, out, ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in meta.items() if k != "inits"}, ensure_ascii=False))
