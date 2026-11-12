#!/usr/bin/env python3
"""cardsjson.py — 把 cards/H*.md 的卡头和陈述抽成机器可读的 cards/cards.json，并重写 cards/INDEX.md 里的卡片一览表。

    python3 cardsjson.py [--check]

卡头格式（每张卡的前几行）：
    # H03 标题
    - 现象的证据等级：**E2**（……）
    - 「值多少地」的证据等级：**E2 偏弱**——……
    - 对应模式：NEW-EC-05（……）
INDEX.md 和 reports/CROSS-MATCH-SUMMARY.md 里 <!-- cards-table:begin --> 和 <!-- cards-table:end --> 之间的表由本脚本生成；--check 只比对不写，表或 JSON 和卡片对不上时退出码 1。
只读写 cards/ 和 reports/CROSS-MATCH-SUMMARY.md 里那一张表，不碰数据包。
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CARDS = os.path.join(os.path.dirname(HERE), "cards")
BEGIN, END = "<!-- cards-table:begin -->", "<!-- cards-table:end -->"


def patterns_of(text):
    """NEW-SP-01 / 02 / 03、NEW-MT-09 / 09L 这种简写展开成完整编号，保持出现的顺序。"""
    out = []
    for m in re.finditer(r"NEW-([A-Z]{2})-([0-9A-Za-z]+)((?:\s*/\s*[0-9]+[A-Za-z]?(?![0-9A-Za-z-]))*)", text):
        pre = m.group(1)
        ids = [m.group(2)] + re.findall(r"/\s*([0-9]+[A-Za-z]?)", m.group(3))
        for i in ids:
            pid = f"NEW-{pre}-{i}"
            if pid not in out:
                out.append(pid)
    return out


def level_of(line):
    m = re.search(r"\*\*(E\d[^*]*)\*\*", line)
    return m.group(1).strip() if m else None


def section(lines, title):
    """返回 '## title…' 这一节的正文行（到下一个 '## ' 为止）。"""
    out, on = [], False
    for ln in lines:
        if ln.startswith("## "):
            if on:
                break
            on = ln[3:].strip().startswith(title)
            continue
        if on:
            out.append(ln)
    return out


def parse(path):
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    head = lines[0]
    m = re.match(r"# (H\d+)\s+(.*)", head)
    card = dict(id=m.group(1), file=os.path.basename(path), title=m.group(2).strip())
    levels = []
    for ln in lines[1:12]:
        if not ln.startswith("- "):
            continue
        body = ln[2:]
        if body.startswith("现象的证据等级"):
            card["phenomenonLevel"] = level_of(body)
            card["phenomenonNote"] = body.split("：", 1)[1]
        elif body.startswith("「值多少地」的证据等级"):
            card["valueLevel"] = level_of(body)
            card["valueNote"] = body.split("：", 1)[1]
        elif "证据等级" in body:
            levels.append(dict(what=body.split("的证据等级")[0], levels=re.findall(r"\*\*(E\d[^*]*)\*\*", body), note=body.split("：", 1)[1]))
        elif body.startswith("对应模式"):
            card["patterns"] = patterns_of(body)
            card["patternsNote"] = body.split("：", 1)[1]
        elif "valueLevel" not in card and "phenomenonLevel" in card and "patterns" not in card:
            card["valueLevel"] = None           # H02：这张卡本身就是结果量
            card["valueNote"] = body
    card.setdefault("valueLevel", None)
    card.setdefault("patterns", [])
    if levels:
        card["otherLevels"] = levels
    one = [ln.strip() for ln in section(lines, "一句话") if ln.strip()]
    card["oneLine"] = " ".join(one)
    claims = []
    for ln in section(lines, "可证伪的陈述"):
        mm = re.match(r"\s*(\d+)\.\s+(.*)", ln)
        if mm:
            claims.append(mm.group(2).strip())
        elif claims and ln.startswith("   ") and ln.strip():
            claims[-1] += ln.strip()
    card["claims"] = claims
    det = "\n".join(section(lines, "检测器"))
    card["scripts"] = sorted(set(re.findall(r"`([A-Za-z0-9_]+\.(?:py|mjs|sh))`", "\n".join(lines))))
    card["detectorScripts"] = sorted(set(re.findall(r"`([A-Za-z0-9_]+\.(?:py|mjs|sh))`", det)))
    card["outputSections"] = sorted(set(re.findall(r"\[(X[A-Z]-[A-Z0-9]+|F[A-Z]-[A-Z])\]", "\n".join(lines))))
    hand = [ln.strip() for ln in section(lines, "交给验证集") if ln.strip()]
    card["e3"] = next((ln for ln in hand if "E3" in ln), None)
    card["e4"] = next((ln for ln in hand if "E4" in ln), None)
    return card


def table(cards, prefix=""):
    rows = ["| 卡 | 现象 | 现象的等级 | 「值多少地」的等级 | 对应的模式编号 |", "|---|---|---|---|---|"]
    for c in cards:
        pats = "、".join(c["patterns"]) if c["patterns"] else "—"
        rows.append(f"| [{c['id']}]({prefix}{c['file']}) | {c['title']} | {c.get('phenomenonLevel') or '—'} | {c.get('valueLevel') or '—（它本身就是结果量）'} | {pats} |")
    return "\n".join(rows)


def rewrite(text, tbl):
    if BEGIN not in text or END not in text:
        return None
    a, rest = text.split(BEGIN, 1)
    _old, b = rest.split(END, 1)
    return a + BEGIN + "\n" + tbl + "\n" + END + b


def main():
    check = "--check" in sys.argv
    files = sorted(f for f in os.listdir(CARDS) if re.match(r"H\d+-.*\.md$", f))
    cards = [parse(os.path.join(CARDS, f)) for f in files]
    doc = dict(author="R08", note="由 scripts/cardsjson.py 从 cards/H*.md 抽出；证据等级照 PLAN.md §2（E0 猜想 / E1 单局个例 / E2 发现集脚本统计显著 / E3 验证集独立复现 / E4 模拟器反事实配对消融）",
               count=len(cards), cards=cards)
    js = json.dumps(doc, ensure_ascii=False, indent=1) + "\n"
    jp = os.path.join(CARDS, "cards.json")
    ip = os.path.join(CARDS, "INDEX.md")
    with open(ip, encoding="utf-8") as f:
        idx = f.read()
    new_idx = rewrite(idx, table(cards))
    if new_idx is None:
        print("INDEX.md 里没有 cards-table 标记", file=sys.stderr)
        return 1
    # 跨局报告 §10 里的同一张表（链接相对 reports/）
    rp = os.path.join(os.path.dirname(CARDS), "reports", "CROSS-MATCH-SUMMARY.md")
    rep = open(rp, encoding="utf-8").read() if os.path.exists(rp) else None
    new_rep = rewrite(rep, table(cards, "../cards/")) if rep is not None else None
    if check:
        old_js = open(jp, encoding="utf-8").read() if os.path.exists(jp) else ""
        bad = (old_js != js) or (new_idx != idx) or (new_rep is not None and new_rep != rep)
        print(f"cardsjson --check：{len(cards)} 张卡，" + ("和卡片对不上，重跑 cardsjson.py" if bad else "cards.json、INDEX.md 和跨局报告里的表都和卡片一致"))
        return 1 if bad else 0
    with open(jp, "w", encoding="utf-8") as f:
        f.write(js)
    with open(ip, "w", encoding="utf-8") as f:
        f.write(new_idx)
    if new_rep is not None:
        with open(rp, "w", encoding="utf-8") as f:
            f.write(new_rep)
    print(f"cardsjson：{len(cards)} 张卡 → cards/cards.json，INDEX.md" + ("、reports/CROSS-MATCH-SUMMARY.md" if new_rep is not None else "") + " 的卡片一览已重写")
    for c in cards:
        print(f"  {c['id']} | {c.get('phenomenonLevel')} | {c.get('valueLevel')} | {len(c['claims'])} 条陈述 | {len(c['patterns'])} 个模式 | {c['title'][:40]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
