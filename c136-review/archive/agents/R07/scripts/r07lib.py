#!/usr/bin/env python3
"""r07lib.py — R07 v2.0 复盘脚本公共库（只用标准库）。

数据来源（只读）：/agent/repos/c136-data/bundles/<matchId>/ 与 /agent/repos/c136-data/src/。
引擎整数算术按 src/engine/engine-evidence.txt（[C2][C3][E1]~[E16][A2][B1]~[B5]）与 live-donation-check.txt 实现；
捐款到账公式 (pct+1)/1024 已用 G01 dave_w 的日志余额逐拍验算（见 30_donation_ledger.py 输出）。
"""
import csv
import json
import os
import re

DATA = "/agent/repos/c136-data"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "out"))


# ----------------------------------------------------------------------------- bundle loading

def bdir(mid):
    return os.path.join(DATA, "bundles", mid)


def load_card(mid):
    return json.load(open(os.path.join(bdir(mid), "card.json"), encoding="utf-8"))


def _num(v):
    if v is None or v == "":
        return None
    try:
        if re.fullmatch(r"-?\d+", v):
            return int(v)
        return float(v)
    except (ValueError, TypeError):
        return v


def load_csv(mid, name, numeric=True):
    path = os.path.join(bdir(mid), name)
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if numeric:
                r = {k: (_num(v) if k not in ("bot", "type", "kind", "targetName", "role", "event", "result", "teamTotals", "at", "boxedIn", "likelyRejected") else v)
                     for k, v in r.items()}
            rows.append(r)
    return rows


def load_traj(mid):
    """{bot: [snapshot rows sorted by t]}"""
    out = {}
    for r in load_csv(mid, "traj.csv"):
        out.setdefault(r["bot"], []).append(r)
    for b in out:
        out[b].sort(key=lambda r: r["t"])
    return out


def load_events(mid):
    ev = load_csv(mid, "events.csv")
    for e in ev:
        e["likelyRejected"] = (e.get("likelyRejected") == "True")
        e["boxedIn"] = {"True": True, "False": False}.get(e.get("boxedIn"), None)
    ev.sort(key=lambda e: (e["t"], e["line"]))
    return ev


def load_results(mid):
    rows = load_csv(mid, "results.csv")
    for r in rows:
        try:
            r["teamTotals"] = {int(k): v for k, v in json.loads(r["teamTotals"]).items()} if r.get("teamTotals") else {}
        except Exception:
            r["teamTotals"] = {}
    return rows


LOG_RE = re.compile(r"^(\d+)\t(?:\[([A-Za-z0-9_]+)\] )?(.*)$", re.S)


def load_log(mid):
    """[(origLine, bot|None, text)]"""
    out = []
    with open(os.path.join(bdir(mid), "in_game.log"), encoding="utf-8") as f:
        for ln in f:
            ln = ln.rstrip("\n")
            m = LOG_RE.match(ln)
            if m:
                out.append((int(m.group(1)), m.group(2), m.group(3)))
    return out


# ----------------------------------------------------------------------------- engine integer math

def g0(a, b):
    """引擎整数除法 [C2]：floor((a+0.5)/b)，a、b 为非负整数。"""
    return (2 * a + 1) // (2 * b)


def aQk(g1, n):
    """引擎整数开方 [C3]（n 次牛顿迭代）。"""
    ej = g0(g1 + 1, 2)
    for _ in range(n):
        ej = g0(ej + g0(g1, ej), 2)
    return ej


def _rate_table():
    tab = []
    for i in range(512):
        v = g0(i * 25600, 508)
        tab.append(100 + (aQk(v, 9) if v >= 1 else 0))
    return tab


RATE_TABLE = _rate_table()


def base_rate(terr, land, t):
    """未超软上限时的利息率（万分之一/10 拍）[E3][E4][E5]。"""
    eH = RATE_TABLE[min(511, g0(511 * terr, land))]
    if t < 1920:
        eH = max(g0(100 * (13440 - 6 * t), 1920), eH)
    return eH


def interest_rate(terr, land, t, bal):
    """[E4][E5][E6]：含超软上限扣减，夹在 0..700。"""
    eH = base_rate(terr, land, t)
    cap = min(100 * terr, 10 ** 9)
    if cap > 0 and bal > cap:
        eH -= g0(2 * eH * (bal - cap), cap)
    return min(max(eH, 0), 700)


def credit(bal, terr, amt):
    """入账 gy/a6a [E14][E15]：夹到 150*领土 与 15e8。"""
    amt = min(amt, 150 * terr - bal, 1500000000 - bal)
    return bal + max(amt, 0)


def income_tick(bal, terr, land, t):
    """处理第 t 拍的收入：t%10==9 利息，t%100==99 再加领土收入 [E1][E2][E9][E10]。返回新余额。"""
    if t % 10 != 9:
        return bal
    r = interest_rate(terr, land, t, bal)
    bal = credit(bal, terr, max(g0(r * bal, 10000), 1))
    if t % 100 == 99:
        bal = credit(bal, terr, g0(32 * terr, 32))
    return bal


def run_income(bal, terr, land, t_from, t_to):
    """从「t_from 拍开始时」的余额推进到「t_to 拍开始时」（处理 t_from..t_to-1 各拍的收入），领土恒定。"""
    t = t_from
    # 跳到下一个结息拍
    while t < t_to:
        nxt = t + ((9 - t % 10) % 10)
        if nxt >= t_to:
            break
        bal = income_tick(bal, terr, land, nxt)
        t = nxt + 1
    return bal


def donate_quote(bal, pct):
    """捐款 [B1]：返回 (到账额, 手续费)。到账 = min(g0(B*(pct+1),1024), B-费)；费 = g0(64*B,1024)。（未含受捐方空间与配额）"""
    fee = g0(64 * bal, 1024)
    amt = min(g0(bal * (pct + 1), 1024), bal - fee)
    return max(amt, 0), fee


def attack_quote(bal, pct, k=12):
    """陆攻/发船报价 [A2]：返回 (兵, 费)。k=12 陆攻，k=32 发船/追船。"""
    fee = g0(k * bal, 1024)
    tr = min(g0(bal * (pct + 1), 1024), bal - fee)
    return max(tr, 0), fee


def quota_cap(t):
    """全场受捐额度上限 aOY 在「第 t 拍开始时」的值 [B3]：初值 15；每个 tick%100==99 增加 4/6/8/10。"""
    cap = 15
    k = 99
    while k < t:
        cap += 4 if k < 1071 else 6 if k < 2142 else 8 if k < 3213 else 10
        k += 100
    return cap


def quota_points(t, amount, land, recv_terr):
    """一笔到账 amount 消耗的受捐点数 [B4]。"""
    if t >= 3213:
        return 4 + g0(100 * amount, max(1, min(100 * recv_terr, 10 ** 9)))
    uv = 1 + g0(land, 300)
    if t < 357:
        d = uv
    elif t < 714:
        d = 4 * uv
    elif t < 1071:
        d = 10 * uv
    elif t < 2142:
        d = 30 * uv
    else:
        d = 100 * uv
    return 2 + g0(100 * amount, d)


def quota_exempt(t):
    """[B5] t>=4284 后不再检查配额。"""
    return t >= 4284


# ----------------------------------------------------------------------------- small helpers

def snap_at(rows, t):
    """<= t 的最后一个快照（没有则 None）。"""
    best = None
    for r in rows:
        if r["t"] <= t:
            best = r
        else:
            break
    return best


def snap_after(rows, t):
    for r in rows:
        if r["t"] > t:
            return r
    return None


def ensure_out(mid):
    d = os.path.join(OUT, mid)
    os.makedirs(d, exist_ok=True)
    return d


def fmt_int(n):
    return f"{n:,}" if isinstance(n, int) else str(n)
