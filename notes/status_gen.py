#!/usr/bin/env python3
"""Bring plan/STATUS.md up to the merges of the fast lane (A0 #67664, COMMON 0.10).

    python3 /tmp/c164_s2/status_gen.py <checkout>/c164-realms/plan/STATUS.md "HH:MM"

Reads, beside this file:
    manual.tsv        merges made by s2 before the watch began (same columns as the ledger)
    words.tsv         merge commit, tab, what it brought (the approver's 【合并】 line in a few words)
    applied.json      the notes the overrides have put into the rows so far (written here)
    ledger.tsv        what watch.sh has seen come into the assembly: time (UTC), who, what, delivered, merge
    overrides.json    {"<category>/<package>": {"state": ..., "who": ..., "note": ...}}
    status_top.md     the text of the section "快车道以后" above the table of merges
    headcheck.txt     one line a check of the head: "HH:MM <head> <words>"; the last is quoted

and rewrites: the section between the two markers (put before "## 排队" the first time), the rows
of the packages named in the two ledgers (state, commit, a note of every merge, once), and the
line of counts. Running it twice changes nothing more.
"""
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BEGIN, END = "<!-- s2:fast-lane:begin -->", "<!-- s2:fast-lane:end -->"
CATEGORIES = ("common", "materials", "sky", "main", "site", "machines", "props", "interiors", "motion")
STATES = ("待领", "制作中", "已交付", "已合并", "已出图", "暂过", "已过审", "退回")
NAMES = {"c164-s2": "s2", "c164-a1": "a1", "c164-facade": "facade", "c164-cr2": "cr2", "c164-a4": "a4",
         "c164-cr3": "cr3", "c164-a6": "a6", "c164-stair": "cr4", "c164-cr4": "cr4"}


def _words():
    """words.tsv: the merge commit (8), a tab, what the merge brought in the approver's words."""
    out, path = {}, os.path.join(HERE, "words.tsv")
    if os.path.exists(path):
        for line in open(path, encoding="utf-8").read().split("\n"):
            if "\t" in line:
                sha, words = line.split("\t", 1)
                out[sha.strip()[:8]] = words.strip()
    return out


COMMON_WORDS = _words()


ONCE = [
    ("## 等总监定的\n",
     "## 等总监定的\n\n**快车道以后（11-16 08:20）不等总监裁**：有两个方案的，做的人的默认先进总装；本类里的二选一由审批人定。下面是 08:20 以前记的，"
     "还没了的各家按自己的默认走，总监看合出来的整图再改。11-16 上午定掉的两条划掉了：浑天仪定甲、不要地平环；桅杆的红灯不改。\n"),
    ("- 浑天仪甲乙，在 `v2_axis`、`v2_entrance` 上定；", "- ~~浑天仪甲乙，在 `v2_axis`、`v2_entrance` 上定~~（11-16 07:36 定甲，不要地平环）；原话："),
    ("- V1 里桅杆的红灯和格构紧挨彗头：", "- ~~V1 里桅杆的红灯和格构紧挨彗头~~（11-16 07:17 定：红灯不改、拉索不加粗、V12 的碎点不改）；原话："),
    ("- 带两版比选、等出图的：报时塔第二稿甲乙（尖和圆，tower c327）、行星仪甲乙（orrery c343）。",
     "- ~~带两版比选、等出图的：报时塔第二稿甲乙、行星仪甲乙~~（11-16：报时塔的塔顶定甲，facade 定的；行星仪默认甲进了总装，乙留测试场景）。"),
]


def beijing(stamp):
    t = datetime.datetime.strptime("2026-" + stamp, "%Y-%m-%d %H:%M") + datetime.timedelta(hours=8)
    return t.strftime("%m-%d %H:%M")


def merges():
    """[(time in Beijing, who, category, package, words, delivered, merge)] in the order they came."""
    out = []
    for name in ("manual.tsv", "ledger.tsv"):
        path = os.path.join(HERE, name)
        if not os.path.exists(path):
            continue
        for line in open(path, encoding="utf-8").read().split("\n"):
            cells = line.split("\t")
            if len(cells) < 5:
                continue
            stamp, who, what, delivered, merge = cells[:5]
            m = re.match(r"merge ([a-z]+)/([a-z0-9_-]+)(.*)", what)
            if not m:
                m = re.match(r"merge (common)()(.*)", what)
                if not m:
                    continue
            words = m.group(3).strip()
            words = re.sub(r"^[0-9a-f]{7,10}\b:? ?", "", words)
            words = COMMON_WORDS.get(merge[:8], words)
            out.append((beijing(stamp), NAMES.get(who, who.replace("c164-", "")), m.group(1), m.group(2),
                        words, delivered[:8], merge[:8]))
    return out


def main():
    path, now = sys.argv[1], sys.argv[2]
    text = open(path, encoding="utf-8").read()
    over = json.load(open(os.path.join(HERE, "overrides.json"), encoding="utf-8"))
    record = os.path.join(HERE, "applied.json")     # the note each override put into its row at the last run
    applied = json.load(open(record, encoding="utf-8")) if os.path.exists(record) else {}
    rows = merges()
    lines = text.split("\n")

    # ---- the rows of the packages --------------------------------------------------------------
    where, sec = {}, None
    for i, line in enumerate(lines):
        m = re.match(r"^## (\w+)", line)
        if m:
            sec = m.group(1)
        if sec in CATEGORIES and line.startswith("| ") and not line.startswith(("| ---", "| 包")):
            name = line.split("|")[1].strip().strip("`")
            name = re.split(r"[（(]", name)[0].strip()
            where[(sec, name)] = i
    missing = []
    for when, who, cat, pkg, words, delivered, merge in rows:
        if cat == "common" and not pkg:
            continue
        i = where.get((cat, pkg))
        if i is None:
            missing.append(f"{cat}/{pkg}")
            continue
        cells = lines[i].split("|")
        if merge in cells[7]:
            continue
        note = f"【{when} {who} 合 {delivered}→{merge}" + (f"，{words}" if words else "") + "】"
        cells[7] = " " + note + cells[7].rstrip() + " "
        cells[3] = " 已合并 "
        cells[5] = f" {merge} "
        lines[i] = "|".join(cells)
    for key, change in over.items():
        cat, pkg = key.split("/")
        i = where.get((cat, pkg))
        if i is None:
            missing.append(key + " (override)")
            continue
        cells = lines[i].split("|")
        if "state" in change:
            assert change["state"] in STATES, change["state"]
            cells[3] = f" {change['state']} "
        if "who" in change:
            cells[4] = f" {change['who']} "
        if "commit" in change:
            cells[5] = f" {change['commit']} "
        note, earlier = change.get("note") or "", applied.setdefault(key, [])
        if note and note not in cells[7]:
            for before in reversed(earlier):
                if before in cells[7]:
                    cells[7] = cells[7].replace(before, note, 1)    # the note of an earlier run, said anew
                    break
            else:
                cells[7] = " " + note + cells[7].rstrip() + " "
        if note and note not in earlier:
            earlier.append(note)
        lines[i] = "|".join(cells)

    # ---- the counts ----------------------------------------------------------------------------
    counts = {s: 0 for s in STATES}
    for (sec, name), i in where.items():
        state = lines[i].split("|")[3].strip()
        if state not in counts:
            raise SystemExit(f"{sec}/{name}: the state {state!r} is not one of the eight")
        counts[state] += 1
    total = sum(counts.values())
    tally = "，".join(f"{s} {counts[s]}" for s in STATES if counts[s])
    for i, line in enumerate(lines):
        if line.startswith("**汇总（"):
            lines[i] = f"**汇总（s2 c318 更新，11-16 {now}）：共 {total} 张卡 —— {tally}。**"
            break
    else:
        raise SystemExit("no line of counts")

    # ---- the old sections: what the morning's rulings took away -------------------------------
    text = "\n".join(lines)
    for old_line, new_line in ONCE:
        if new_line in text:
            continue
        if text.count(old_line) != 1:
            raise SystemExit(f"cannot place the edit: {old_line[:40]!r} is there {text.count(old_line)} times")
        text = text.replace(old_line, new_line)
    lines = text.split("\n")

    # ---- the section of the fast lane ----------------------------------------------------------
    top = open(os.path.join(HERE, "status_top.md"), encoding="utf-8").read().rstrip("\n")
    checks = [ln for ln in open(os.path.join(HERE, "headcheck.txt"), encoding="utf-8").read().split("\n") if ln.strip()]
    table = ["| 时间（北京） | 类别/包 | 交付的提交 | 合并提交 | 谁合的 | 说明 |", "| --- | --- | --- | --- | --- | --- |"]
    for when, who, cat, pkg, words, delivered, merge in rows:
        what = f"`{cat}/{pkg}`" if pkg else "common（公共文件）"
        table.append(f"| {when} | {what} | {delivered} | {merge} | {who} | {words} |")
    block = [BEGIN, "## 快车道以后（11-16 08:22 起；和下面各节冲突时以本节为准）", "",
             f"s2 c318 记，11-16 {now}。" + (f"总装头最近一次检查：{checks[-1]}。" if checks else ""), "", top, "",
             f"### 合并流水（11-16 06:40 以后进总装的，共 {len(rows)} 次；08:28 以前是 s2 过关口合的，以后是各类审批人合的）", ""]
    block += table + ["", END]
    text = "\n".join(lines)
    if BEGIN in text:
        a, b = text.index(BEGIN), text.index(END) + len(END)
        text = text[:a] + "\n".join(block) + text[b:]
    else:
        a = text.index("## 排队")
        text = text[:a] + "\n".join(block) + "\n\n" + text[a:]
    open(path, "w", encoding="utf-8").write(text)
    json.dump(applied, open(record, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{total} cards: {tally}; {len(rows)} merges in the table" + (f"; no row for: {', '.join(missing)}" if missing else ""))


if __name__ == "__main__":
    main()
