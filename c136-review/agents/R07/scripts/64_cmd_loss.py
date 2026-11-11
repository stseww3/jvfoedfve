#!/usr/bin/env python3
"""64_cmd_loss.py — R07：把「策略想发的指令」（65_shadow.mjs 的影子指令）和「服务器真正收下的指令」（录像）逐条配对，
量出每个号的指令延迟和丢失。

用法：python3 64_cmd_loss.py <matchId> [--win 300] [--detail bot]
输入：out/<matchId>/shadow_cmds.tsv（影子：策略在本地第 t 拍发出的指令）、truth_cmd.tsv（录像：服务器第 T 拍收下的指令）、
      shadow_check.txt（影子可信度——cmds 计数对不上的号，本表的「想发」只能当参考）
配对规则：同一个号、同一种指令、同一比例 pct、同一目标；每条录像指令配「发令拍 t ≤ T 且还没配过的最晚一条影子指令」
      （最晚优先 = 给出延迟的下限；同时另算一遍「最早优先」= 按先发先到算的延迟上限，两个中位数都列出）。
      第二轮：录像里目标是无主地（512）却配不上的进攻，再按「同 pct、任意目标」配一次——晚到的进攻落地时原目标已死，
      录像里记成打无主地（A062 kaito9 t=945 的 9 条就是这样），这类记作「改投无主地」。
      配不上的影子指令 = 没被服务器收下（丢失，或者那一拍客户端已经不在了）。
      配不上的录像指令 = 影子没发过（真号和影子在那一拍决策不同）。
输出：stdout + out/<matchId>/cmd_loss.txt
  A. 每个号：想发 N、收下 M、配上 K、延迟（T−t）中位/90 分位/最大、延迟 ≥35 拍的条数、同一拍落地 ≥3 条的批数
  B. 每 win 拍一档：想发/收下/配上/中位延迟（看卡顿从哪一拍开始）
  C. --detail bot：该号逐条配对明细
  D. 按 in_game.log 的落盘先后，量每个号的本地进度比全队最快的号落后多少拍（客户端卡顿的直接证据）
注意：影子的「想发」里包含引擎会拒收的指令（比如进攻时没有接壤边界），所以「没配上」不全是网络丢失；
      开局阶段影子用到随机数的地方也可能和真号不同。延迟是硬数字（两边都有的指令的拍差）。
"""
import csv
import os
import statistics
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))


def load(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def pctl(xs, q):
    if not xs:
        return None
    xs = sorted(xs)
    k = min(len(xs) - 1, max(0, int(round(q * (len(xs) - 1)))))
    return xs[k]


def main():
    argv = sys.argv[1:]
    mid = argv[0]
    win = 300
    detail = None
    if "--win" in argv:
        win = int(argv[argv.index("--win") + 1])
    if "--detail" in argv:
        detail = argv[argv.index("--detail") + 1]
    out = os.path.join(HERE, "..", "out", mid)
    sh = load(os.path.join(out, "shadow_cmds.tsv"))
    tr = load(os.path.join(out, "truth_cmd.tsv"))
    bots = sorted(set(r["bot"] for r in sh) | set(r["bot"] for r in tr if r["bot"]))
    want = defaultdict(list)
    for r in sh:
        if r["kind"] not in ("attack", "donate"):
            continue
        want[r["bot"]].append({"t": int(r["t"]), "kind": r["kind"], "pct": int(r["pct"]), "target": int(r["target"]), "hit": None})
    got = defaultdict(list)
    for r in tr:
        if not r["bot"] or r["bot"] not in bots:
            continue
        kind = {"attack": "attack", "donate": "donate", "don": "donate", "atk": "attack"}.get(r["kind"])
        if kind is None:
            continue
        got[r["bot"]].append({"T": int(r["tick"]), "kind": kind, "pct": int(r["a"]), "target": int(r["b"]), "hit": None})
    lines = []
    P = lines.append
    P(f"# {mid} 指令延迟与丢失（影子想发 vs 录像收下；只算进攻与捐兵）")
    P("# A. 每个号")
    P("bot\t想发\t收下\t精确配上\t改投无主地(条/中位延迟,启发式)\t延迟中位(下限)\t延迟中位(先发先到)\t延迟90分位\t延迟最大\t延迟>=35拍\t延迟>=90拍\t同拍>=3条的批数\t没配上的想发\t没配上的收下\t最后一条收下的拍")
    per_win = defaultdict(lambda: defaultdict(lambda: [0, 0, 0, []]))
    for b in bots:
        W, G = want[b], got[b]
        idx = defaultdict(list)
        for w in W:
            idx[(w["kind"], w["pct"], w["target"])].append(w)
        # 上限：最早优先（先发先到）
        used = set()
        lags_fifo = []
        for g in G:
            for w in idx.get((g["kind"], g["pct"], g["target"]), []):
                if id(w) not in used and w["t"] <= g["T"]:
                    used.add(id(w))
                    lags_fifo.append(g["T"] - w["t"])
                    break
        lags = []
        for g in G:
            cands = [w for w in idx.get((g["kind"], g["pct"], g["target"]), []) if w["hit"] is None and w["t"] <= g["T"]]
            if cands:
                w = cands[-1]
                w["hit"] = g["T"]
                g["hit"] = w["t"]
                lags.append(g["T"] - w["t"])
        retarget = 0
        re_lags = []
        for g in G:
            if g["hit"] is not None or g["kind"] != "attack" or g["target"] != 512:
                continue
            cands = [w for w in W if w["hit"] is None and w["kind"] == "attack" and w["pct"] == g["pct"] and w["t"] <= g["T"]]
            if cands:
                w = cands[-1]
                w["hit"] = g["T"]
                g["hit"] = w["t"]
                re_lags.append(g["T"] - w["t"])
                retarget += 1
        batches = defaultdict(int)
        for g in G:
            batches[g["T"]] += 1
        nb = sum(1 for v in batches.values() if v >= 3)
        P("\t".join(str(x) for x in [
            b, len(W), len(G), len(lags), f"{retarget}/{int(statistics.median(re_lags)) if re_lags else '-'}",
            "-" if not lags else int(statistics.median(lags)), "-" if not lags_fifo else int(statistics.median(lags_fifo)),
            "-" if not lags else pctl(lags, 0.9), "-" if not lags else max(lags),
            sum(1 for x in lags if x >= 35), sum(1 for x in lags if x >= 90), nb,
            sum(1 for w in W if w["hit"] is None), sum(1 for g in G if g["hit"] is None),
            max((g["T"] for g in G), default="-")]))
        for w in W:
            k = per_win[b][w["t"] // win]
            k[0] += 1
            if w["hit"] is not None:
                k[2] += 1
                k[3].append(w["hit"] - w["t"])
        for g in G:
            per_win[b][g["T"] // win][1] += 1
    P(f"\n# B. 每 {win} 拍一档（想发按发令拍归档，收下按落地拍归档）：想发/收下/配上（含改投无主地）/中位延迟")
    allw = sorted(set(k for b in bots for k in per_win[b]))
    P("bot\t" + "\t".join(f"{k * win}~" for k in allw))
    for b in bots:
        cells = []
        for k in allw:
            v = per_win[b].get(k)
            if not v or (v[0] == 0 and v[1] == 0):
                cells.append(".")
            else:
                cells.append(f"{v[0]}/{v[1]}/{v[2]}/{int(statistics.median(v[3])) if v[3] else '-'}")
        P(b + "\t" + "\t".join(cells))
    # D. 日志先后顺序：in_game.log 按落盘先后排列。某个号打出本地第 t 拍的 HL-TICK 时，别的号已经打到第几拍 → 它的本地进度落后多少拍
    import re
    log_path = os.path.join("/agent/repos/c136-data/bundles", mid, "in_game.log")
    if os.path.exists(log_path):
        rx = re.compile(r"^\d+\t\[([A-Za-z0-9_]+)\] \[HL-TICK\] t=(\d+) ")
        seen_max = 0
        behind = defaultdict(list)
        for ln, line in enumerate(open(log_path, encoding="utf-8", errors="replace"), 1):
            m = rx.match(line)
            if not m:
                continue
            b, t = m.group(1), int(m.group(2))
            behind[b].append((t, max(0, seen_max - t), ln))
            seen_max = max(seen_max, t)
        P("\n# D. 本地进度落后拍数（按日志落盘先后：该号打出第 t 拍快照时，全队最快的号已打到的拍号 − t；90 拍一档，所以 <90 的落后看不出来）")
        P("bot\t首次落后>=90拍\t最大落后\t最后一条快照(本地拍/落后/行号)\t逐条(本地拍:落后)")
        for b in sorted(behind):
            rows = behind[b]
            first = next((f"t={t}(落后{d}, L{ln})" for t, d, ln in rows if d >= 90), "-")
            mx = max(rows, key=lambda x: x[1])
            last = rows[-1]
            P(f"{b}\t{first}\t{mx[1]}@t={mx[0]}\tt={last[0]}/落后{last[1]}/L{last[2]}\t" + " ".join(f"{t}:{d}" for t, d, _ in rows if d >= 90)[:400])
    if detail:
        P(f"\n# C. {detail} 逐条明细（想发：t 种类 pct→目标 ⇒ 落地拍/丢；收下但影子没发的另列）")
        for w in want[detail]:
            P(f"想发 t={w['t']} {w['kind']} pct={w['pct']} → {w['target']} ⇒ " + (f"落地 T={w['hit']}（+{w['hit'] - w['t']}）" if w["hit"] is not None else "没被收下"))
        for g in got[detail]:
            if g["hit"] is None:
                P(f"收下但影子没发 T={g['T']} {g['kind']} pct={g['pct']} → {g['target']}")
    txt = "\n".join(lines) + "\n"
    if not detail:
        with open(os.path.join(out, "cmd_loss.txt"), "w") as f:
            f.write(txt)
    sys.stdout.write(txt)


if __name__ == "__main__":
    main()
