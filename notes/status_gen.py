#!/usr/bin/env python3
"""Bring plan/STATUS.md up to the merges of the fast lane (A0 #67664, COMMON 0.10).

    python3 /tmp/c164_s2/status_gen.py <checkout>/c164-realms/plan/STATUS.md "HH:MM"

Reads, beside this file:
    manual.tsv        merges made by s2 before the watch began (same columns as the ledger)
    words.tsv         merge commit, tab, what it brought (the approver's 【合并】 line in a few words)
    applied.json      the notes the overrides have put into the rows so far (written here)
    new_rows.json     rows for cards the tables do not have yet: [[category, after which package, row]]
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
DROPPED = "不做"          # a card the director dropped: its row stays, it is not counted
WHOLE = [               # (how a line of the file starts, the line that takes its place)
    ("- 待领（5 张，",
     "- 待领：没有了。67 张卡的第一版都在总装里（11-16 10:24 钟室最后一个进）；`common/offline-sky` 不做（总监 11-16 10:32）。"
     "手上没卡的人找本类的审批人领打磨的活（总监 09:12），名单在 aide 的 `plan/ROSTER.md`。"),
    ("- 待领：没有了。67 张卡的第一版都在总装里",
     "- 待领：没有了。67 张卡的第一版都在总装里（11-16 10:24 钟室最后一个进）；`common/offline-sky` 不做（总监 11-16 10:32）；"
     "11:03 总监新开一张 `motion/guide`（导览，制作中，第一版 11:50 前交）。"
     "手上没卡的人找本类的审批人领打磨的活（总监 09:12），名单在 aide 的 `plan/ROSTER.md`。"),
    ("- 待领：没有了。67 张卡的第一版都在总装里（11-16 10:24 钟室最后一个进）；`common/offline-sky` 不做（总监 11-16 10:32）；11:03",
     "- 待领：没有了。第一轮的 68 张卡（含 11:03 加的导览 `motion/guide`）都在总装里，成品是 A8（总装 8cddfa98）；"
     "`common/offline-sky` 不做。**第二轮（11-16 12:12 开工，卡页 `plan/round2.md`）新开 12 张卡**，在各类的表里标着「第二轮」："
     "火车是开场（`motion/travel`、`machines/train`、`site/railway`、`motion/arrival`、`motion/train-smoke-sound`、`props/station`）、"
     "蒸汽管线和气动信筒（`props/steam-mains`、`props/pneumatic`）、鸟和流星（`sky/birds`、`sky/meteors`）、喷泉（`site/fountain`）、"
     "小活物（`motion/small-life`）。另外两大块不单开卡，记在原来的卡上：已有的东西全动起来（每人自己的）、细节加密（评审每版圈空处）。"
     "名单在 aide 的 `plan/ROSTER.md`。"),
    ("状态：待领 → 制作中",
     "状态：待领 → 制作中 → 已交付 → 已合并 → 已出图 → 已过审；旁路：退回（回到制作中）、暂过（交叉看过了、评审还没评）、"
     "不做（总监砍掉的卡，行留着，不计数）。第 3 班的“已出图”是代码合并了、自查图也在总装里、关口核过，等评审。"),
]
NAMES = {"c164-s2": "s2", "c164-a1": "a1", "c164-facade": "facade", "c164-cr2": "cr2", "c164-a4": "a4",
         "c164-cr3": "cr3", "c164-a6": "a6", "c164-stair": "cr4", "c164-cr4": "cr4"}
CARD_OF = {             # a name an approver wrote in a merge's subject -> the card it is a part of
    ("props", "signs"): ("props", "electrics-signs"),
    ("motion", "guide-title"): ("motion", "guide"),      # the guide's part A (mast)
    ("props", "plaques"): ("motion", "guide"),           # the guide's part B, the common half (a6)
}


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
            m = re.match(r"merge ((?:[a-z]+/[a-z0-9_-]+(?:, | and |、)?)+)(.*)", what)
            if m:       # one merge may bring two cards of a line ("merge site/terrain, site/court <commit>")
                cards, rest = re.findall(r"([a-z]+)/([a-z0-9_-]+)", m.group(1)), m.group(2)
            else:
                m = re.match(r"merge (common)(.*)", what)
                if not m:
                    continue
                cards, rest = [("common", "")], m.group(2)
            words = re.sub(r"^[0-9a-f]{7,10}\b:? ?", "", rest.strip())
            words = COMMON_WORDS.get(merge[:8], words)
            for cat, pkg in cards:
                cat, pkg = CARD_OF.get((cat, pkg), (cat, pkg))
                out.append((beijing(stamp), NAMES.get(who, who.replace("c164-", "")), cat, pkg,
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

    # ---- rows the table does not have yet (new_rows.json: [[category, after which package, the row]]) ----
    path_new = os.path.join(HERE, "new_rows.json")
    for cat, after, row in (json.load(open(path_new, encoding="utf-8")) if os.path.exists(path_new) else []):
        name = re.split(r"[（(]", row.split("|")[1].strip().strip("`"))[0].strip()
        sec, at, there = None, None, False
        for i, line in enumerate(lines):
            m = re.match(r"^## (\w+)", line)
            if m:
                sec = m.group(1)
            if sec == cat and line.startswith("| ") and not line.startswith(("| ---", "| 包")):
                this = re.split(r"[（(]", line.split("|")[1].strip().strip("`"))[0].strip()
                there = there or this == name
                if this == after:
                    at = i
        if not there:
            if at is None:
                raise SystemExit(f"new row {cat}/{name}: no row {after!r} to put it after")
            lines.insert(at + 1, row)

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
        if cells[3].strip() in ("待领", "制作中", "已交付", "退回"):
            cells[3] = " 已合并 "       # a later round of a card that has passed a review leaves it passed
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
            assert change["state"] in STATES or change["state"] == DROPPED, change["state"]
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
    dropped = []
    for (sec, name), i in where.items():
        state = lines[i].split("|")[3].strip()
        if state.startswith(DROPPED):
            dropped.append(f"`{sec}/{name}`")
            continue
        if state not in counts:
            raise SystemExit(f"{sec}/{name}: the state {state!r} is not one of the eight")
        counts[state] += 1
    total = sum(counts.values())
    tally = "，".join(f"{s} {counts[s]}" for s in STATES if counts[s])
    for i, line in enumerate(lines):
        if line.startswith("**汇总（"):
            also = f"另有不做的 {len(dropped)} 张（{"、".join(dropped)}），不计数。" if dropped else ""
            lines[i] = f"**汇总（s2 c318 更新，11-16 {now}）：共 {total} 张卡 —— {tally}。{also}**"
            break
    else:
        raise SystemExit("no line of counts")

    for i, line in enumerate(lines):
        for start, whole in WHOLE:
            if line.startswith(start):
                lines[i] = whole

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
             f"### 合并流水（11-16 06:40 以后进总装的，共 {len({r[6] for r in rows})} 次；08:28 以前是 s2 过关口合的，以后是各类审批人合的）", ""]
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
