#!/usr/bin/env python3
"""01_log_tag_census.py — 小队日志的句式普查：每种标签出现多少行、首末行号、一条样例。

用法：
  python3 01_log_tag_census.py <raw_dir> > out/common/log_tag_census.txt

行格式（观察）：
  [[Nope] <bot>] <正文>          某个号的输出；正文通常以 [TAG] 开头
  [TAG] <正文>                    编排器自身的输出
本脚本只统计，不解释。连接 / 握手 / 验证相关的行（范围外，LIAISON §9）只计数、不打印样例。
"""
import re
import sys
from collections import OrderedDict

raw = sys.argv[1] if len(sys.argv) > 1 else "/tmp/c136-r07/raw"
path = f"{raw}/G01-G09-squad.log"

BOT_PREFIX = re.compile(r"^\[\[Nope\] ([A-Za-z0-9_]+)\] ?(.*)$", re.S)
TAG = re.compile(r"^\[([A-Za-z0-9_\- ]+?)(?:\]| [^\]]*\])")
# 范围外（连接握手、验证、代理）：只计数，不展示内容
# [SELF-CHECK …] / [SQUAD-SYNC] 是进房与身份核对的行（含账号标识），同样只计数
OUT_OF_SCOPE = re.compile(r"turnstile|socket|Connection to Server|Attaching on port|devtools|Chrome|token|proxy|captcha|Minting|ws://|http://"
                          r"|^\[SELF-CHECK|^\[SQUAD-SYNC\]",
                          re.I)

stats = OrderedDict()
n = 0
with open(path, encoding="utf-8", errors="replace") as f:
    for ln, line in enumerate(f, 1):
        n += 1
        line = line.rstrip("\n")
        m = BOT_PREFIX.match(line)
        who = "BOT" if m else "ORCH"
        body = m.group(2) if m else line
        oos = bool(OUT_OF_SCOPE.search(body))
        t = TAG.match(body)
        if oos:
            tag = "(out-of-scope: connection/verification)"
        elif t:
            tag = "[" + t.group(1) + "]"
            # [RESULT <bot>] / [OPENING-CHECK 8 bots @ tick N] 归并
            tag = re.sub(r"^\[RESULT .*", "[RESULT]", tag)
            tag = re.sub(r"^\[OPENING-CHECK.*", "[OPENING-CHECK]", tag)
        else:
            # 没有标签的行：取前两个词作句式
            words = body.split()
            tag = "(untagged) " + " ".join(words[:2])
        key = (who, tag)
        s = stats.get(key)
        if s is None:
            stats[key] = s = {"n": 0, "first": ln, "last": ln, "sample": None if oos else line[:260]}
        s["n"] += 1
        s["last"] = ln

print(f"# total lines={n} file={path}")
print("who\ttag\tcount\tfirstLine\tlastLine\tsample")
for (who, tag), s in sorted(stats.items(), key=lambda kv: -kv[1]["n"]):
    print(f"{who}\t{tag}\t{s['n']}\t{s['first']}\t{s['last']}\t{s['sample'] or ''}")
