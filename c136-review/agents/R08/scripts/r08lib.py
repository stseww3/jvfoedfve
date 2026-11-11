#!/usr/bin/env python3
"""r08lib.py — R08 v2.0 公共库：读标准化对局包、日志标签→局内玩家号的身份还原、引擎公式。

数据只读自 /agent/repos/c136-data/bundles/<matchId>/（可用环境变量 C136_DATA 改根目录）。
所有行号都是 in_game.log 每行开头的原始日志行号。

身份还原（B 组必需）：20 号编队的日志前缀名（label）会在一局中途整体轮换，
同一个局内玩家（HL-GAME-INIT 的 me=）前后会用不同的 label 打日志。
这里按 HL-TICK 里的工作进程统计量（maxMs、cmds、boats、skip 单调不减）把 label 串回同一个玩家。
"""
import csv
import json
import math
import os
import re
from collections import defaultdict

DATA = os.environ.get("C136_DATA", "/agent/repos/c136-data")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")

TICK_RE = re.compile(
    r"\[HL-TICK\] t=(\d+) terr=(\d+)\(([\d.]+)%\) bal=(-?\d+) dens=([\d.]+) nb=(\d+) neut=(\d+) cmds=(\d+) boats=(\d+)"
    r"(?: avgMs=([\d.]+) maxMs=([\d.]+) skip=(\d+))?")
LINE_RE = re.compile(r"^(\d+)\t(.*)$")
LABEL_RE = re.compile(r"^\[([^\]]+)\] \[(HL-[A-Z-]+)\] ?(.*)$")
RESULT_RE = re.compile(r"^\[RESULT (.+?)\] result=(\w+) event=(\w+) place=(\d+) peak=(\d+) team=(.*)$")
INIT_RE = re.compile(r"mode=(\d+) map=(\d+) mapSeed=(\d+) seeded=(\d+) me=(\d+)")
OPEN_RE = re.compile(r"t=(\d+) cyc=(\d+) DP expand rings=(\d+) spend=(\d+)/(\d+) terr=(\d+)")


def bundle_dir(mid):
    for sub in ("bundles", "validation_bundles"):
        d = os.path.join(DATA, sub, mid)
        if os.path.isdir(d):
            return d
    raise FileNotFoundError(mid)


def read_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def num(v):
    if v is None or v == "":
        return None
    try:
        f = float(v)
    except ValueError:
        return v
    return int(f) if f == int(f) and re.fullmatch(r"-?\d+", str(v)) else f


def load_card(mid):
    with open(os.path.join(bundle_dir(mid), "card.json"), encoding="utf-8") as f:
        return json.load(f)


def load_results(mid):
    rows = read_csv(os.path.join(bundle_dir(mid), "results.csv"))
    out = []
    for r in rows:
        o = {k: num(v) for k, v in r.items()}
        tt = r.get("teamTotals")
        o["teamTotals"] = json.loads(tt) if tt else None
        out.append(o)
    return out


def parse_log(mid):
    """返回逐行解析结果列表：{line, label, tag, body, raw}（RESULT 行 tag='RESULT'）。"""
    out = []
    path = os.path.join(bundle_dir(mid), "in_game.log")
    with open(path, encoding="utf-8") as f:
        for idx, raw in enumerate(f):
            raw = raw.rstrip("\n")
            m = LINE_RE.match(raw)
            if not m:
                continue
            line, rest = int(m.group(1)), m.group(2)
            rec = {"line": line, "idx": idx, "raw": rest, "label": None, "tag": None, "body": rest}
            mr = RESULT_RE.match(rest)
            if mr:
                team = None
                try:
                    team = json.loads(mr.group(6))
                except Exception:  # noqa: BLE001
                    team = None
                rec.update(label=mr.group(1).replace("[Nope] ", ""), tag="RESULT", result=mr.group(2), event=mr.group(3),
                           place=int(mr.group(4)), peak=int(mr.group(5)), team=team)
            else:
                ml = LABEL_RE.match(rest)
                if ml:
                    rec.update(label=ml.group(1), tag=ml.group(2), body=ml.group(3))
                elif rest.startswith("[BACKEND-SPAWN-COORD]"):
                    rec["tag"] = "BACKEND-SPAWN-COORD"
                elif rest.startswith("[OPENING-CHECK"):
                    rec["tag"] = "OPENING-CHECK"
            if rec["tag"] == "HL-TICK":
                mt = TICK_RE.search(rest)
                if mt:
                    g = mt.groups()
                    rec["tick"] = dict(t=int(g[0]), terr=int(g[1]), pct=float(g[2]), bal=int(g[3]), dens=float(g[4]),
                                       nb=int(g[5]), neut=int(g[6]), cmds=int(g[7]), boats=int(g[8]),
                                       avgMs=float(g[9]) if g[9] else None, maxMs=float(g[10]) if g[10] else None,
                                       skip=int(g[11]) if g[11] else None)
            elif rec["tag"] == "HL-GAME-INIT":
                mi = INIT_RE.search(rest)
                if mi:
                    rec["init"] = dict(mode=int(mi.group(1)), map=int(mi.group(2)), mapSeed=int(mi.group(3)),
                                       seeded=int(mi.group(4)), me=int(mi.group(5)))
            out.append(rec)
    return out


class Track:
    """一个局内玩家（一个工作进程）的全部日志。"""

    def __init__(self, me, label):
        self.me = me
        self.labels = [label]
        self.ticks = []      # HL-TICK dict（附 line、label）
        self.lines = []      # 全部归属的日志记录
        self.result = None
        self.last = None     # 最近一条 HL-TICK
        self.closed = False

    @property
    def name(self):
        return self.labels[0]


def _consistent(tr, s):
    """s（新的 HL-TICK）能否接在轨迹 tr 的最近一条 HL-TICK 后面。"""
    l = tr.last
    if l is None:
        return True
    if s["t"] <= l["t"]:
        return False
    if s["cmds"] < l["cmds"] or s["boats"] < l["boats"]:
        return False
    if s["maxMs"] is not None and l["maxMs"] is not None and s["maxMs"] < l["maxMs"] - 1e-9:
        return False
    if s["skip"] is not None and l["skip"] is not None and s["skip"] < l["skip"]:
        return False
    return True


def _dist(tr, s):
    l = tr.last
    if l is None:
        return 1e6
    d = 0.0
    if s["maxMs"] is not None and l["maxMs"] is not None:
        d += 50.0 * abs(s["maxMs"] - l["maxMs"])
    d += 2.0 * (s["cmds"] - l["cmds"]) + 5.0 * (s["boats"] - l["boats"])
    d += 0.02 * abs(s["t"] - l["t"] - 90)
    d += 0.5 * abs(math.log((s["terr"] + 50) / (l["terr"] + 50))) * 100
    return d


def resolve_identities(recs):
    """把日志记录按玩家归并。返回 (tracks: {me: Track}, notes: [str], unresolved: [rec])。"""
    tracks = {}
    cur = {}          # label -> me（当前绑定）
    pending = defaultdict(list)   # label -> 还没归属的记录
    notes = []
    unresolved = []

    def bind(label, me, why, line):
        old = cur.get(label)
        if old is not None and old != me:
            notes.append(f"line {line}: label '{label}' 由玩家 {old} 改绑到玩家 {me}（{why}）")
        for lab, m in list(cur.items()):
            if m == me and lab != label:
                del cur[lab]
        cur[label] = me
        tr = tracks[me]
        if tr.labels[-1] != label:
            tr.labels.append(label)
            notes.append(f"line {line}: 玩家 {me} 的 label {tr.labels[-2]} -> {label}（{why}）")
        for r in pending.pop(label, []):
            tr.lines.append(r)

    for r in recs:
        tag, label = r["tag"], r["label"]
        if tag == "HL-GAME-INIT" and "init" in r:
            me = r["init"]["me"]
            if me not in tracks:
                tracks[me] = Track(me, label)
            bind(label, me, "init", r["line"])
            tracks[me].lines.append(r)
            continue
        if label is None:
            continue
        mm = re.search(r"\bme=(\d+)\b", r["raw"]) if tag in ("HL-SPAWN", "HL-SPAWN-BACKEND") else None
        if mm:
            me = int(mm.group(1))
            if me not in tracks:
                tracks[me] = Track(me, label)
            if cur.get(label) != me:
                bind(label, me, "spawn me=", r["line"])
            tracks[me].lines.append(r)
            continue
        if tag == "HL-TICK" and "tick" in r:
            s = r["tick"]
            me = cur.get(label)
            if me is not None and not tracks[me].closed and _consistent(tracks[me], s):
                # label 当前绑定且连续
                pass
            else:
                cands = [tr for tr in tracks.values() if not tr.closed and _consistent(tr, s)
                         and (tr.last is None or tr.last["t"] < s["t"])]
                # 已经在本拍用别的 label 打过点的轨迹排除（由 _consistent 的 t 判断保证）
                if me is not None:
                    cands = [tr for tr in cands if tr.me != me] or cands
                if not cands:
                    unresolved.append(r)
                    continue
                cands.sort(key=lambda tr: _dist(tr, s))
                best = cands[0]
                if len(cands) > 1 and _dist(cands[1], s) - _dist(best, s) < 1.0:
                    notes.append(f"line {r['line']}: label '{label}' t={s['t']} 归属有歧义："
                                 f"{best.me}({_dist(best, s):.1f}) vs {cands[1].me}({_dist(cands[1], s):.1f})")
                bind(label, best.me, "HL-TICK 连续性", r["line"])
                me = best.me
            tr = tracks[me]
            rec = dict(s)
            rec["line"] = r["line"]
            rec["label"] = label
            tr.ticks.append(rec)
            tr.last = rec
            tr.lines.append(r)
            continue
        if tag == "RESULT":
            me = cur.get(label)
            if me is None or tracks[me].closed:
                # 轮换后还没打过 HL-TICK 就结算：按 peak 与最后领土匹配
                cands = [tr for tr in tracks.values() if not tr.closed]
                best = None
                for tr in cands:
                    mx = max([x["terr"] for x in tr.ticks], default=0)
                    if mx <= r["peak"] and (best is None or mx > best[0]):
                        best = (mx, tr)
                if best is None:
                    unresolved.append(r)
                    continue
                me = best[1].me
                notes.append(f"line {r['line']}: RESULT '{label}' 按 peak={r['peak']} 归到玩家 {me}"
                             f"（该玩家日志峰值 {best[0]}）")
                bind(label, me, "RESULT peak 匹配", r["line"])
            tr = tracks[me]
            tr.result = r
            tr.lines.append(r)
            tr.closed = True
            continue
        me = cur.get(label)
        if me is None or tracks[me].closed:
            pending[label].append(r)
        else:
            tracks[me].lines.append(r)
    for label, rs in pending.items():
        unresolved.extend(rs)
    return tracks, notes, unresolved


# ---------------- 引擎公式（engine-evidence.txt 的编号） ----------------

def g0(a, b):
    """[C2] 整数除法 floor((a+0.5)/b)。"""
    return math.floor((a + 0.5) / b)


def isqrt_engine(n):
    """[C3] 牛顿迭代的整数开方（迭代 9 次，与 E3 的 aMh(x, 9) 一致）。"""
    if n <= 0:
        return 0
    ej = g0(n + 1, 2)
    for _ in range(9):
        if ej == 0:
            break
        ej = g0(ej + g0(n, ej), 2)
    return ej


def interest_rate(terr, land, bal, t):
    """[E3..E7] 每 10 拍利息率（万分之一）。"""
    i = g0(511 * terr, land)
    r = 100 + isqrt_engine(g0(i * 25600, 508))
    if t < 1920:
        r = max(g0(100 * (13440 - 6 * t), 1920), r)
    cap = min(100 * terr, 10 ** 9)
    if cap > 0 and bal > cap:
        r -= g0(2 * r * (bal - cap), cap)
    return min(max(r, 0), 700)


def donate_quote(bal, pct):
    """[B1] 捐款：到账（对方有空间时）与手续费。"""
    fee = g0(64 * bal, 1024)
    amt = min(g0(bal * (pct + 1), 1024), bal - fee)
    return max(amt, 0), fee


def attack_quote(bal, pct, k=12):
    """[A2] 陆攻报价：兵、费。k=32 为发船。"""
    fee = g0(k * bal, 1024)
    troops = min(g0(bal * (pct + 1), 1024), bal - fee)
    return max(troops, 0), fee


def quota_cap(t):
    """[B3] 全场受捐额度 aOY 在第 t 拍的值（t%100==99 时递增）。t>=4284 起不检查。"""
    cap = 15
    k = 99
    while k <= t:
        cap += 4 if k < 1071 else 6 if k < 2142 else 8 if k < 3213 else 10
        k += 100
    return cap


def quota_points(t, amount, land, recv_terr):
    """[B4] 一笔到账 amount 消耗的受捐点数。"""
    if t >= 3213:
        return 4 + g0(100 * amount, min(100 * max(recv_terr, 1), 10 ** 9))
    uv = 1 + g0(land, 300)
    den = uv if t < 357 else 4 * uv if t < 714 else 10 * uv if t < 1071 else 30 * uv if t < 2142 else 100 * uv
    return 2 + g0(100 * amount, den)


def def_per_px(bal, terr):
    """[X11] 每格防御量（cnt=1）。"""
    return g0(bal, 1 + g0(10 * terr, 16))


def elim_cost(bal, terr, peak):
    """策略 elimCost：把目标从当前领土压到 peak/4 需要的兵。"""
    left = peak // 4
    x = min(1.0, left / max(terr, 1))
    return 2 * bal * (1 - x ** 1.6) + 2 * terr * (1 - x)


def win_ratio(t):
    """策略 winRatio（winT=[[1500,3],[2000,2.85],[2500,1.8]]，winR=0.002）。"""
    T = [(1500, 3.0), (2000, 2.85), (2500, 1.8)]
    if t < T[0][0]:
        return 0.002 * max(1, t)
    for i in range(1, len(T)):
        if t <= T[i][0]:
            return T[i - 1][1] + (T[i][1] - T[i - 1][1]) * (t - T[i - 1][0]) / (T[i][0] - T[i - 1][0])
    return T[-1][1]
