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


def max_fit_amount(t, land, terr_recv, used=0):
    """在第 t 拍、受捐方已用 used 点时，能过额度检查的最大单笔到账金额（t≥4284 返回 None=不限）。"""
    if t >= QUOTA_FREE_FROM:
        return None
    room = quota_cap(t) - used
    lo, hi = 0, 1
    if quota_points(t, 1, land, terr_recv) > room:
        return 0
    while quota_points(t, hi, land, terr_recv) <= room:
        lo, hi = hi, hi * 2
        if hi > 4 * 10 ** 9:
            return hi
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if quota_points(t, mid, land, terr_recv) <= room:
            lo = mid
        else:
            hi = mid
    return lo


# ---------------------------------------------------------------- 回放指令流
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.normpath(os.path.join(HERE, "..", "out", "cache"))
NEUTRAL = 512

CMD_SPAWN, CMD_ATTACK, CMD_DONATE, CMD_BOAT, CMD_CHASE = 0, 1, 2, 3, 4
CMD_RETREAT, CMD_EMOJI, CMD_VOTE, CMD_SURRENDER, CMD_DISCONNECT, CMD_MOUNTAIN = 5, 6, 7, 8, 9, 10
SPEND_CMDS = (CMD_ATTACK, CMD_DONATE, CMD_BOAT, CMD_CHASE, CMD_MOUNTAIN)


def load_replay(mid):
    """读 replay-cmds.mjs 解出的指令流；没有缓存或回放只有出生阶段时返回 None。"""
    path = os.path.join(CACHE, f"{mid}-replay.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        rep = json.load(f)
    if not rep.get("totalTicks"):
        return None
    return rep


def squad_map(mid, rep=None):
    """{玩家号: 号名}，取自 results.csv。

    对局包偶尔把“上一局还没打完的号”也收进来（例如 A025 的 sora_w/noah88/ryan_m：results 里
    seededPlayers=20、玩家号 17-19，而这局回放只有 12 个真人）。给了 rep 就按回放里的名字核对，
    只留下真在这局里的号。
    """
    out = {}
    for r in load_results(mid):
        pid = r.get("meId")
        if pid is None:
            continue
        if rep is not None:
            names = rep.get("names") or []
            if pid >= len(names) or not str(names[pid]).endswith(str(r["bot"])):
                continue
        out[pid] = r["bot"]
    return out


def foreign_bots(mid, rep):
    """results.csv 里有、但不在这局回放里的号（属于别的对局）。"""
    inside = set(squad_map(mid, rep).values())
    return sorted({r["bot"] for r in load_results(mid)} - inside)


def cmds_by_tick(rep, ids=SPEND_CMDS):
    """{拍号: [(id, player, a, b), ...]}，保持回放里的先后顺序（就是引擎执行顺序）。"""
    out = {}
    for t, cid, p, a, b in rep["cmds"]:
        if t < 0 or cid not in ids:
            continue
        out.setdefault(t, []).append((cid, p, a, b))
    return out


def snapshot_at(rows, t):
    for r in rows:
        if r["t"] == t:
            return r
    return None


def new_tally():
    return dict(n_atk=0, atk_troops=0, atk_fee=0, n_atk_noop=0, n_don=0, don_out=0, don_fee=0,
                n_boat=0, boat_troops=0, boat_fee=0, don_in=0, n_don_in=0, ext_in=0)


def simulate_window(by_tick, state, t0, t1, land, noop_neutral=()):
    """把一组本队号的余额从快照 t0 推进到快照 t1，执行回放里它们的指令。

    state: {玩家号: [余额, 领土]}（会被原地修改；领土在窗口内视为不变）。
    noop_neutral: 这些玩家号对中立的进攻视为“前线生成失败、不扣钱”（窗口两端都没有中立邻格的号）。
    只算账面：进攻/船 = 扣兵 + 手续费；捐款 = 捐方扣到账额 + 6.25% 费、受捐方入账（夹硬上限）。
    不模拟推进，所以进攻退兵、被打的防守损耗、新攻补兵都不在里面，留给残差。
    返回 {玩家号: tally}。
    """
    tallies = {p: new_tally() for p in state}
    for t in range(t0, t1):
        for cid, p, a, b in by_tick.get(t, ()):
            if cid == CMD_DONATE:
                if p in state:
                    bal = state[p][0]
                    amount, fee = quote_donate(bal, a)
                    if b in state:
                        room = max(0, min(state[b][1] * HARD_MULT - state[b][0], HARD_TOP - state[b][0]))
                        amount = min(amount, room)
                    state[p][0] = bal - amount - fee
                    tl = tallies[p]
                    tl["n_don"] += 1
                    tl["don_out"] += amount
                    tl["don_fee"] += fee
                    if b in state:
                        state[b][0] += amount
                        tallies[b]["don_in"] += amount
                        tallies[b]["n_don_in"] += 1
                elif b in state:
                    tallies[b]["ext_in"] += 1
                continue
            if p not in state:
                continue
            bal = state[p][0]
            tl = tallies[p]
            if cid == CMD_ATTACK:
                if b >= NEUTRAL and p in noop_neutral:
                    tl["n_atk_noop"] += 1
                    continue
                troops, fee = quote_attack(bal, a, 12)
                state[p][0] = bal - troops - fee
                tl["n_atk"] += 1
                tl["atk_troops"] += troops
                tl["atk_fee"] += fee
            elif cid in (CMD_BOAT, CMD_CHASE):
                if cid == CMD_CHASE and a == 849:
                    continue
                troops, fee = quote_attack(bal, a, 32)
                state[p][0] = bal - troops - fee
                tl["n_boat"] += 1
                tl["boat_troops"] += troops
                tl["boat_fee"] += fee
            elif cid == CMD_MOUNTAIN:
                pct = a >> 10
                fee = max(g0(bal, 10), 1000)
                troops = min(g0(bal * (pct + 1), 1024), bal - fee)
                if troops >= 0:
                    state[p][0] = bal - troops - fee
                    tl["n_atk"] += 1
                    tl["atk_troops"] += troops
                    tl["atk_fee"] += fee
        for p, st in state.items():
            st[0] = econ_tick(t, st[1], st[0], land)
    return tallies


# ---------------------------------------------------------------- 成批落地 / 捐款配对
def frac_left(cid, pct):
    """一条指令执行后余额剩下的比例（按报价公式，忽略取整）。"""
    k = {CMD_ATTACK: 12, CMD_DONATE: 64, CMD_BOAT: 32, CMD_CHASE: 32}.get(cid, 12)
    fee = k / 1024
    send = min((pct + 1) / 1024, 1 - fee)
    return max(0.0, 1 - send - fee)


def batches_of(rep, pid):
    """[(拍, [(id, a, b), ...])]，同一拍为一批，保持回放顺序。"""
    out = []
    for t, cid, p, a, b in rep["cmds"]:
        if p != pid or t < 0 or cid not in SPEND_CMDS:
            continue
        if out and out[-1][0] == t:
            out[-1][1].append((cid, a, b))
        else:
            out.append((t, [(cid, a, b)]))
    return out


def match_donations(logged, batches):
    """logged: [(T, pct, target)] 升序；batches: 回放里该号的批。返回 (配对表, 未执行数)。

    配对表每项 (S, T_min, T_max, pct, target)：T_max 是“最晚可能的决策拍”（延迟下界），
    T_min 是“最早可能的决策拍”（延迟上界）。批内逆序（后发先执行）。
    """
    execd = []
    for S, cmds in batches:
        dons = [(a, b) for cid, a, b in cmds if cid == CMD_DONATE]
        for a, b in reversed(dons):
            execd.append((S, a, b))
    n = len(execd)
    late = [None] * n
    hi = len(logged)
    for i in range(n - 1, -1, -1):
        S, pct, tgt = execd[i]
        j = hi - 1
        while j >= 0 and not (logged[j][0] < S and logged[j][1] == pct and logged[j][2] == tgt):
            j -= 1
        if j >= 0:
            late[i] = j
            hi = j
    early = [None] * n
    lo = 0
    for i in range(n):
        S, pct, tgt = execd[i]
        j = lo
        while j < len(logged) and not (logged[j][0] < S and logged[j][1] == pct and logged[j][2] == tgt):
            j += 1
        if j < len(logged) and logged[j][0] < S:
            early[i] = j
            lo = j + 1
    rows = []
    for i in range(n):
        S, pct, tgt = execd[i]
        tmax = logged[late[i]][0] if late[i] is not None else None
        tmin = logged[early[i]][0] if early[i] is not None else None
        rows.append((S, tmin, tmax, pct, tgt))
    return rows, len(logged) - sum(1 for x in late if x is not None)


if __name__ == "__main__":
    print("table[0..5] =", INTEREST_TABLE[:6], " table[51] =", INTEREST_TABLE[51], " table[511] =", INTEREST_TABLE[511])
    print("matches in bundles:", len(all_match_ids()))
