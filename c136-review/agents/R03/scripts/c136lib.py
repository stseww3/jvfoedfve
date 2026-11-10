#!/usr/bin/env python3
"""c136lib.py — R03 的公共库：读对局包 + 引擎经济/战斗公式的整数实现。

公式出处见 out/engine-evidence-2174.txt 的条目编号（[E3] 等）。
只读 /agent/repos/c136-data/；不写任何东西。
"""
import csv
import json
import os

DATA = os.environ.get("C136_DATA", "/agent/repos/c136-data")
BUNDLES = os.path.join(DATA, "bundles")

R03_MATCHES = [
    "A051", "A087", "A066", "A025", "A045", "A067", "A071",
    "A090", "A042", "A046", "A041", "A010", "A011", "B038",
]


# ---------------------------------------------------------------- 读文件
def bundle_dir(mid):
    return os.path.join(BUNDLES, mid)


def all_match_ids():
    return sorted(d for d in os.listdir(BUNDLES) if os.path.isdir(os.path.join(BUNDLES, d)))


def load_card(mid):
    with open(os.path.join(bundle_dir(mid), "card.json"), encoding="utf-8") as f:
        return json.load(f)


def _num(v):
    if v is None or v == "":
        return None
    try:
        if "." in v or "e" in v or "E" in v:
            return float(v)
        return int(v)
    except ValueError:
        return v


def load_csv(mid, name):
    path = os.path.join(bundle_dir(mid), name)
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k, v in list(r.items()):
            r[k] = _num(v)
    return rows


def load_traj(mid):
    """返回 {bot: [快照行, ...]}，每个号按 t 升序。"""
    out = {}
    for r in load_csv(mid, "traj.csv"):
        out.setdefault(r["bot"], []).append(r)
    for rows in out.values():
        rows.sort(key=lambda r: r["t"])
    return out


def load_events(mid):
    return load_csv(mid, "events.csv")


def load_results(mid):
    return load_csv(mid, "results.csv")


def load_opening(mid):
    return load_csv(mid, "opening.csv")


def load_spawn(mid):
    return load_csv(mid, "spawn.csv")


# ---------------------------------------------------------------- 引擎整数算术
def g0(a, b):
    """[C2] 引擎整数除法 floor((a+0.5)/b)。非负整数时等于 a//b。"""
    return (2 * a + 1) // (2 * b)


def isqrt9(x, iters=9):
    """[C3] aQk：牛顿迭代 9 次的整数开方；aMh 在 x<1 时返回 0。"""
    if x < 1:
        return 0
    e = g0(x + 1, 2)
    for _ in range(iters):
        e = g0(e + g0(x, e), 2)
    return e


# [E3] 利息表：aMg[i] = 100 + isqrt9(floor(i*25600/508))，i=0..511
INTEREST_TABLE = [100 + isqrt9(g0(i * 25600, 508)) for i in range(512)]

SOFT_MULT = 100      # [E7] 软上限 = 100 * 领土
HARD_MULT = 150      # [C1][E15] 硬上限 = 150 * 领土
SOFT_TOP = 10 ** 9   # [C1] a7X
HARD_TOP = 15 * 10 ** 8  # [C1] a6e


def soft_cap(terr):
    return min(SOFT_MULT * terr, SOFT_TOP)


def interest_rate(t, terr, bal, land):
    """[E4][E5][E6] 利息率（万分之一 / 每 10 拍）。t 是结算那一拍的拍号。"""
    r = INTEREST_TABLE[g0(511 * terr, land)]
    if t < 1920:
        r = max(g0(100 * (13440 - 6 * t), 1920), r)
    cap = soft_cap(terr)
    if bal > cap and cap > 0:
        r -= g0(2 * r * (bal - cap), cap)
    return min(max(r, 0), 700)


def credit(terr, bal, amount):
    """[E14][E15] 入账 gy：夹到硬上限 min(150*领土, 15e8)，返回入账后的余额。"""
    amount = min(amount, terr * HARD_MULT - bal)
    amount = min(amount, HARD_TOP - bal)
    amount = max(amount, 0)
    return bal + amount


def econ_tick(t, terr, bal, land):
    """第 t 拍的经济结算（[E1] t%10==9 利息；[E2] t%100==99 领土收入）。返回新余额。"""
    if t % 10 != 9:
        return bal
    r = interest_rate(t, terr, bal, land)
    bal = credit(terr, bal, max(g0(r * bal, 10000), 1))  # [E9]
    if t % 100 == 99:
        bal = credit(terr, bal, terr)                     # [E10][E11]
    return bal


def simulate_quiet(bal0, terr, t0, t1, land):
    """领土不变、没有任何出入账的安静区间：快照 t0 的余额推进到快照 t1。

    快照取在第 t 拍开始之前（策略钩子 beforeTick 在 n8 开头），所以区间内结算的是拍号 t0..t1-1。
    """
    bal = bal0
    for t in range(t0, t1):
        bal = econ_tick(t, terr, bal, land)
    return bal


# ---------------------------------------------------------------- 发兵/捐款报价
def quote_attack(bal, pct, fee_k=12):
    """[A1][A2] 陆攻报价：兵 = min(floor(B*(pct+1)/1024), B-费)，费 = floor(k*B/1024)。"""
    fee = g0(fee_k * bal, 1024)
    troops = min(g0(bal * (pct + 1), 1024), bal - fee)
    return troops, fee


def quote_donate(bal, pct):
    """[B1] 捐款报价（未计受捐方入账上限）：到账 = min(floor(B*(pct+1)/1024), B-费)，费 = floor(64*B/1024)。"""
    fee = g0(64 * bal, 1024)
    amount = min(g0(bal * (pct + 1), 1024), bal - fee)
    return amount, fee


def defense(cnt, bal_def, terr_def):
    """[X11] 防御量 hU = floor(cnt*B_def / (1+floor(10*L_def/16)))。"""
    return g0(cnt * bal_def, 1 + g0(10 * terr_def, 16))


def step_interval(terr):
    """[S2][S3] 推进间隔（拍/步）：领土 <1e3:4、<1e4:3、<6e4:2、否则 1。"""
    if terr < 1000:
        return 4
    if terr < 10000:
        return 3
    if terr < 60000:
        return 2
    return 1


def quota_cap(t):
    """[B3] 第 t 拍开始前的全场受捐额度上限 aOY（初值 15，每逢 τ%100==99 增加）。"""
    cap = 15
    for tau in range(99, t, 100):
        if tau < 1071:
            cap += 4
        elif tau < 2142:
            cap += 6
        elif tau < 3213:
            cap += 8
        else:
            cap += 10
    return cap


def quota_points(t, amount, land, terr_recv):
    """[B4] 一笔到账 amount 的捐款消耗的受捐点数。"""
    if t >= 3213:
        return 4 + g0(100 * amount, max(1, soft_cap(terr_recv)))
    uv = 1 + g0(land, 300)
    if t < 357:
        return 2 + g0(100 * amount, uv)
    if t < 714:
        return 2 + g0(100 * amount, 4 * uv)
    if t < 1071:
        return 2 + g0(100 * amount, 10 * uv)
    if t < 2142:
        return 2 + g0(100 * amount, 30 * uv)
    return 2 + g0(100 * amount, 100 * uv)


QUOTA_FREE_FROM = 4284  # [B5]


if __name__ == "__main__":
    print("table[0..5] =", INTEREST_TABLE[:6], " table[51] =", INTEREST_TABLE[51], " table[511] =", INTEREST_TABLE[511])
    print("matches in bundles:", len(all_match_ids()))
