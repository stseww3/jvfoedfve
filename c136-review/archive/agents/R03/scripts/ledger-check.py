#!/usr/bin/env python3
"""ledger-check.py — 核对「延迟账与抢地账」一节里手写的数字：叙述版第 12 节和笔记 ledgerNotes 里出现的每个数，
都要能在本局的 delay.txt / land.txt / ledger-brief.txt / freeze.txt / 卷宗 <局>.txt 里原样找到（去掉千分位逗号后按整词比对）。

    python3 scripts/ledger-check.py <mid> [<mid> ...]
找不到的逐个列出（带上下文）；全部找到就打一行「全部有出处」。
白名单：节号、[L1]~[L5] 这类标签里的数字、日志行号（7 位数）、D 编号、源码行号（L 开头）。
"""
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
NUM = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?")


def _notes(mid):
    p = os.path.join(HERE, "notes", f"{mid}.py")
    spec = importlib.util.spec_from_file_location(f"notes_{mid}", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ln = mod.NOTES.get("ledgerNotes") or {}
    return "\n".join(str(v) for k, v in ln.items() if k not in ("sources", "statementType"))


def _md_section(mid):
    p = os.path.join(ROOT, "reviews", f"{mid}.md")
    if not os.path.exists(p):
        return ""
    s = open(p, encoding="utf-8").read()
    i = s.find("\n## 12.")
    if i < 0:
        return ""
    body = s[i + 1:]
    return "\n".join(body.split("\n")[1:])     # 去掉标题行（里面是文件名）


def check(mid):
    src = ""
    for suf in ("-delay.txt", "-land.txt", "-ledger-brief.txt", "-freeze.txt", ".txt"):
        p = os.path.join(ROOT, "out", "dossier", f"{mid}{suf}")
        if os.path.exists(p):
            src += open(p, encoding="utf-8", errors="replace").read() + "\n"
    src = src.replace(",", "")
    have = set(m.group(0) for m in re.finditer(r"(?<![\d.])\d+(?:\.\d+)?(?![\d])", src))
    miss = []
    for name, text in (("笔记 ledgerNotes", _notes(mid)), ("叙述版第 12 节", _md_section(mid))):
        clean = re.sub(r"\[[A-Z]\d+\]|D\d+|L\d+|第 \d+ 节|行 \d{7}|日志行 \d{7}|A\d{3}|B\d{3}", " ", text)
        for m in NUM.finditer(clean):
            tok = m.group(0).replace(",", "").rstrip(".")
            if not tok or tok in have:
                continue
            # 坐标 (x,y) 被逗号粘成一个数：拆开再查
            parts = m.group(0).split(",")
            if len(parts) == 2 and all(p_ in have for p_ in parts):
                continue
            ctx = clean[max(0, m.start() - 24):m.end() + 16].replace("\n", " ")
            miss.append((name, m.group(0), ctx))
    return miss


def main():
    bad = 0
    for mid in [a for a in sys.argv[1:] if not a.startswith("--")]:
        miss = check(mid)
        if not miss:
            print(f"{mid}: 第 12 节与 ledgerNotes 的数字全部有出处")
            continue
        bad += 1
        print(f"{mid}: {len(miss)} 个数字在 delay/land/ledger-brief/freeze/卷宗 里找不到")
        for name, tok, ctx in miss:
            print(f"   [{name}] {tok}　…{ctx}…")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
