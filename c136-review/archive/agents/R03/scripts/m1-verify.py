#!/usr/bin/env python3
"""m1-verify.py — 用对局包的 traj.csv（90 拍快照）+ 回放指令流，对引擎公式做数值核对。

用法：python3 m1-verify.py > ../out/m1-verify.txt
核对项：
  A 安静窗口利息/领土收入逐拍精确复算（含拍号对齐检验）
  B 硬上限 150×领土、软上限处的利率衰减
  C 开局：首次发兵的报价/手续费、中立 2 兵/格与“每格 >2 才推”、推进节拍 S+7、每 4 拍一圈
  D 纯挨打窗口：余额随领土的幂律指数（理论 1.6，大圈时更高）
  E 淘汰线：死亡时领土与峰值的比
  F 发兵账：窗口内只有本号指令时，余额 = 利息 − 兵 − 手续费（残差 = 退兵 − 防守损耗）
只读 /agent/repos/c136-data；回放指令流读 out/cache（replay-cmds.mjs 生成）。
"""
import math
import sys
from collections import Counter

import c136lib as L


def pct(a, b):
    return f"{100 * a / b:.1f}%" if b else "-"


def bot_cmd_ticks(rep, pid):
    """该号自己的花钱指令拍 + 别人给它捐款的拍。"""
    own, inc = [], []
    for t, cid, p, a, b in rep["cmds"]:
        if t < 0:
            continue
        if p == pid and cid in L.SPEND_CMDS:
            own.append(t)
        if cid == L.CMD_DONATE and b == pid:
            inc.append(t)
    return own, inc


def any_in(ticks, lo, hi):
    return any(lo <= t < hi for t in ticks)


# ------------------------------------------------------------------ A
def check_a():
    print("== A. 安静窗口利息 + 领土收入的逐拍精确复算 ==")
    print("条件：相邻两个快照相隔 90 拍、领土不变、无船、窗口内本号无任何指令、无人给它捐款；")
    print("      严格档再要求前 180 拍本号也无指令（排除仍在推进的进攻退兵）。")
    tot = Counter()
    worst = []
    for mid in L.R03_MATCHES:
        rep = L.load_replay(mid)
        if rep is None:
            continue
        land = L.match_land(mid, rep)
        traj = L.load_traj(mid)
        for pid, bot in L.squad_map(mid, rep).items():
            rows = traj.get(bot, [])
            own, inc = bot_cmd_ticks(rep, pid)
            for r0, r1 in zip(rows, rows[1:]):
                t0, t1 = r0["t"], r1["t"]
                if t1 - t0 != 90 or r0["terr"] != r1["terr"] or r0["boats"] or r1["boats"] or r0["terr"] <= 0:
                    continue
                if any_in(own, t0, t1) or any_in(inc, t0, t1):
                    continue
                strict = not any_in(own, t0 - 180, t0)
                pred = L.simulate_quiet(r0["bal"], r0["terr"], t0, t1, land)
                pred_m = L.simulate_quiet(r0["bal"], r0["terr"], t0 - 1, t1 - 1, land)
                pred_p = L.simulate_quiet(r0["bal"], r0["terr"], t0 + 1, t1 + 1, land)
                d = r1["bal"] - pred
                key = "strict" if strict else "loose"
                tot[key] += 1
                tot[key + "_exact"] += d == 0
                tot[key + "_exact_m"] += r1["bal"] == pred_m
                tot[key + "_exact_p"] += r1["bal"] == pred_p
                over = r0["bal"] > 100 * r0["terr"]
                if strict:
                    tot["strict_over"] += over
                    tot["strict_over_exact"] += over and d == 0
                    early = t0 < 1920
                    tot["strict_early"] += early
                    tot["strict_early_exact"] += early and d == 0
                if d != 0:
                    worst.append((abs(d) / max(r1["bal"], 1), mid, bot, t0, r0["terr"], r0["bal"], r1["bal"], pred, d, strict))
    for key in ("strict", "loose"):
        n = tot[key]
        print(f"  {key:6s} 窗口 {n:5d}：差值=0 的 {tot[key + '_exact']:5d}（{pct(tot[key + '_exact'], n)}）"
              f" | 对照：把结算区间整体前移 1 拍（t0-1..t1-2，即“快照取在该拍结算之后”）只剩 {tot[key + '_exact_m']} 个相等；"
              f"后移 1 拍（t0+1..t1）覆盖的结算拍相同，仍是 {tot[key + '_exact_p']} 个")
    print(f"  严格档里余额高于软上限(>100×领土)的窗口 {tot['strict_over']}，精确 {tot['strict_over_exact']}；"
          f"t<1920（开局高利率段）的窗口 {tot['strict_early']}，精确 {tot['strict_early_exact']}")
    worst.sort(reverse=True)
    pos_s = sum(1 for w in worst if w[8] > 0 and w[9])
    neg_s = sum(1 for w in worst if w[8] < 0 and w[9])
    pos_l = sum(1 for w in worst if w[8] > 0 and not w[9])
    neg_l = sum(1 for w in worst if w[8] < 0 and not w[9])
    small = sum(1 for w in worst if w[0] < 0.001)
    print(f"  不为 0 的窗口共 {len(worst)} 个：严格档 正残差 {pos_s} / 负残差 {neg_s}，宽松档 正 {pos_l} / 负 {neg_l}；"
          f"相对误差 <0.1% 的 {small} 个。正残差 = 实际比预测多（更早的进攻退兵、船兵返还）。")
    print(f"  按相对误差排前 12：")
    for rel, mid, bot, t0, terr, b0, b1, pred, d, strict in worst[:12]:
        print(f"    {mid} {bot:8s} t={t0:5d} 领土{terr:6d} 余额{b0:8d}→{b1:8d} 预测{pred:8d} 差{d:+8d}（{100 * rel:.2f}%）{'严格' if strict else '宽松'}")


# ------------------------------------------------------------------ B
def check_b():
    print("\n== B. 硬上限 150×领土 / 软上限 100×领土 ==")
    n = over150 = over100 = 0
    mx = (0, None)
    for mid in L.all_match_ids():
        for bot, rows in L.load_traj(mid).items():
            for r in rows:
                if not r["terr"]:
                    continue
                n += 1
                ratio = r["bal"] / r["terr"]
                if ratio > 150:
                    over150 += 1
                if ratio > 100:
                    over100 += 1
                if ratio > mx[0]:
                    mx = (ratio, (mid, bot, r["t"], r["terr"], r["bal"]))
    print(f"  全部 {len(L.all_match_ids())} 局的快照 {n} 个：密度 >150 的 {over150} 个；>100 的 {over100} 个（{pct(over100, n)}）；最大密度 {mx[0]:.2f} {mx[1]}")
    print("  利率在软上限以上的衰减（表值 r0，余额 = x × 100 × 领土）：r = r0 − floor(2·r0·(x−1))，x=1.25 减半，x≥1.5 为 0。")
    for x in (1.0, 1.1, 1.25, 1.4, 1.5):
        terr = 3000
        r = L.interest_rate(3000, terr, int(x * 100 * terr), 664497)
        print(f"    x={x:.2f}: 利率 {r}/10000 每 10 拍；每格每 10 拍利息 {r * x * 100 / 10000:.3f} 兵")


# ------------------------------------------------------------------ C
def diamond_rings():
    r = 12
    while True:
        yield r
        r += 4


def check_c():
    print("\n== C. 开局：报价、手续费、中立地价、推进节拍 ==")
    print("模型：出生余额 512；首条进攻在回放拍 S 执行（指令先于该拍的 n8）；兵 = floor(B·(pct+1)/1024)，费 = floor(12·B/1024)；")
    print("      调度器第 S+7 拍走第一圈，之后每 4 拍一圈（领土<1000）；每圈要 floor(剩余兵/圈格数) > 2 才推，推一圈扣 2×格数；")
    print("      推不动那一拍把剩余兵退回余额。圈格数按菱形 12,16,20,…（只在 t=180 领土恰为 12+Σ圈 时才用）。")
    n90 = ok90 = n180 = ok180 = 0
    bad = []
    cadence = Counter()
    for mid in L.R03_MATCHES:
        rep = L.load_replay(mid)
        if rep is None:
            continue
        land = L.match_land(mid, rep)
        traj = L.load_traj(mid)
        opening = {}
        for o in L.load_opening(mid):
            opening.setdefault(o["bot"], o)
        for pid, bot in L.squad_map(mid, rep).items():
            rows = traj.get(bot, [])
            s90, s180 = L.snapshot_at(rows, 90), L.snapshot_at(rows, 180)
            atks = [(t, a, b) for t, cid, p, a, b in rep["cmds"] if p == pid and t >= 0 and cid in L.SPEND_CMDS]
            if not atks or s90 is None or bot not in opening:
                continue
            S, p0, tgt = atks[0]
            terr0 = opening[bot]["terr"]
            if tgt < L.NEUTRAL or S >= 90 or any(t < 180 for t, _, _ in atks[1:2]):
                continue
            # 余额推进到 t=90
            bal = 512
            for t in range(0, 90):
                if t == S:
                    troops, fee = L.quote_attack(bal, p0)
                    bal -= troops + fee
                bal = L.econ_tick(t, terr0, bal, land)
            n90 += 1
            ok90 += bal == s90["bal"]
            if bal != s90["bal"]:
                bad.append((mid, bot, "t=90", S, p0, bal, s90["bal"]))
            # 节拍：t=90 的领土应等于 terr0 + 已走的圈
            steps_done = len([k for k in range(0, 40) if S + 7 + 4 * k <= 89])
            exp_terr = terr0
            for _, ring in zip(range(steps_done), diamond_rings()):
                exp_terr += ring
            if terr0 == 12:
                cadence["n"] += 1
                cadence["ok"] += exp_terr == s90["terr"]
            if s180 is None or terr0 != 12:
                continue
            # 完整模拟到 t=180（菱形圈）
            bal, terr, slot, step_at, rings = 512, terr0, None, None, diamond_rings()
            for t in range(0, 180):
                if t == S:
                    troops, fee = L.quote_attack(bal, p0)
                    bal -= troops + fee
                    slot, step_at = troops, S + 7
                bal = L.econ_tick(t, terr, bal, land)
                if slot is not None and t == step_at:
                    ring = next(rings)
                    if L.g0(slot, ring) > 2:
                        slot -= 2 * ring
                        terr += ring
                        step_at = t + 4
                    else:
                        bal = L.credit(terr, bal, slot)
                        slot = None
            if terr != s180["terr"]:
                continue
            n180 += 1
            ok180 += bal == s180["bal"]
            if bal != s180["bal"]:
                bad.append((mid, bot, "t=180", S, p0, bal, s180["bal"]))
    print(f"  t=90 余额（验证利息+报价+手续费）：{ok90}/{n90} 个号逐兵相等")
    print(f"  t=90 领土（验证 S+7 起步、每 4 拍一圈、菱形圈 12/16/20…）：{cadence['ok']}/{cadence['n']} 个号相等")
    print(f"  t=180 余额（再验证中立 2 兵/格、>2 门槛、退兵时点、第 99 拍领土收入）：{ok180}/{n180} 个号逐兵相等")
    for b in bad[:10]:
        print("    不等：", b)


# ------------------------------------------------------------------ D
def fit_k(b0, l0, b1, l1, t0, t1, land):
    """在 [t0,t1) 内领土线性变化、每拍按 (L'/L)^k 扣余额，再结算利息；二分求 k 使末余额吻合。"""
    def run(k):
        bal = float(b0)
        for t in range(t0, t1):
            la = l0 + (l1 - l0) * (t - t0) / (t1 - t0)
            lb = l0 + (l1 - l0) * (t + 1 - t0) / (t1 - t0)
            bal *= (lb / la) ** k
            bal = float(L.econ_tick(t, int(lb), int(bal), land))
        return bal
    lo, hi = 0.0, 8.0
    if run(lo) < b1:
        return None
    if run(hi) > b1:
        return None
    for _ in range(40):
        mid = (lo + hi) / 2
        if run(mid) > b1:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def check_d():
    print("\n== D. 纯挨打窗口：余额 ∝ 领土^k 的指数 ==")
    print("条件：90 拍窗口内领土掉 ≥8%，本号在本窗口和前一个窗口都没有任何指令，无人给它捐款，窗口末仍存活。")
    print("理论：每丢一圈 gV 格，余额扣 floor(gV·B/(1+floor(10L/16)))≈1.6·B·gV/L → 连续极限 k=1.6；")
    print("      单圈占领土比例 x 越大，等效 k=ln(1−1.6x)/ln(1−x) 越高（x=0.1→1.66，0.2→1.73，0.3→1.83）。")
    ks = []
    for mid in L.all_match_ids():
        rep = L.load_replay(mid)
        if rep is None:
            continue
        land = L.match_land(mid, rep)
        traj = L.load_traj(mid)
        for pid, bot in L.squad_map(mid, rep).items():
            rows = traj.get(bot, [])
            own, inc = bot_cmd_ticks(rep, pid)
            for r0, r1 in zip(rows, rows[1:]):
                t0, t1 = r0["t"], r1["t"]
                if t1 - t0 != 90 or r0["terr"] < 300 or r1["terr"] <= 0 or r0["boats"] or r1["boats"]:
                    continue
                if r1["terr"] > 0.92 * r0["terr"] or r0["bal"] < 2000:
                    continue
                if any_in(own, t0 - 90, t1) or any_in(inc, t0, t1):
                    continue
                k = fit_k(r0["bal"], r0["terr"], r1["bal"], r1["terr"], t0, t1, land)
                if k is not None:
                    ks.append((k, mid, bot, t0, r0["terr"], r1["terr"], r0["bal"], r1["bal"]))
    ks.sort()
    if not ks:
        print("  没有符合条件的窗口")
        return
    vals = [k for k, *_ in ks]
    n = len(vals)
    print(f"  窗口 {n} 个：k 的 10/25/50/75/90 分位 = "
          + " / ".join(f"{vals[min(n - 1, int(q * n))]:.2f}" for q in (0.1, 0.25, 0.5, 0.75, 0.9)))
    print(f"  k∈[1.4,2.0] 的占 {pct(sum(1 for v in vals if 1.4 <= v <= 2.0), n)}；k<1.4 的 {sum(1 for v in vals if v < 1.4)} 个；k>2.0 的 {sum(1 for v in vals if v > 2.0)} 个")
    print("  例子（中位附近 6 个）：")
    for k, mid, bot, t0, l0, l1, b0, b1 in ks[n // 2 - 3:n // 2 + 3]:
        print(f"    {mid} {bot:8s} t={t0:5d} 领土{l0:6d}→{l1:6d} 余额{b0:8d}→{b1:8d} k={k:.2f}")


# ------------------------------------------------------------------ E
def check_e():
    print("\n== E. 淘汰线：领土 ≤ floor(峰值/4)（峰值每拍衰减 max(1, floor((峰值−领土)/1000))） ==")
    ratios = []
    for mid in L.all_match_ids():
        for r in L.load_results(mid):
            if r["event"] != "died" or not r.get("peak") or r.get("lastTerritory") is None:
                continue
            ratios.append((r["lastTerritory"] / r["peak"], mid, r["bot"], r["lastTerritory"], r["peak"], r["tick"]))
    ratios.sort()
    n = len(ratios)
    if not n:
        return
    vals = [x[0] for x in ratios]
    print(f"  全部对局包里的死亡 {n} 例：死前最后一次读到的领土 / 历史峰值 的 0/10/50/90/100 分位 = "
          + " / ".join(f"{vals[min(n - 1, int(q * n))]:.3f}" for q in (0, 0.1, 0.5, 0.9, 1.0)))
    below = [x for x in ratios if x[0] <= 0.25]
    print(f"  其中 ≤0.25 的 {len(below)} 例（{pct(len(below), n)}），>0.25 的 {n - len(below)} 例。")
    print("  说明：results.csv 的 lastTerritory 是号最后一次决策（每 5 拍）读到的值，死亡发生在其后 ≤5 拍内；")
    print("        峰值在掉地期间每拍至少 −1，所以真实淘汰线略低于 记录峰值/4。>0.25 的例子 = 最后一两圈一次吃掉的格数。")
    print("  最小 3 例 / 最大 3 例：")
    for x in ratios[:3] + ratios[-3:]:
        print(f"    {x[1]} {x[2]:8s} 最后领土{x[3]:6d} 峰值{x[4]:6d} 比{x[0]:.3f} 死亡拍{x[5]}")


# ------------------------------------------------------------------ F
def check_f():
    print("\n== F. 发兵账：窗口内有本号指令时，余额 = 利息 − 兵 − 手续费 + 残差 ==")
    print("残差 = 实际末余额 − 只算指令账面的预测；正 = 进攻退兵/船兵返还，负 = 防守损耗/新攻补兵。")
    print("这里统计 领土不变 且 前一窗口无指令 的窗口（没有防守损耗，退兵也少），看报价/手续费公式本身准不准。")
    tot = Counter()
    ex = []
    for mid in L.R03_MATCHES:
        rep = L.load_replay(mid)
        if rep is None:
            continue
        land = L.match_land(mid, rep)
        traj = L.load_traj(mid)
        by_tick = L.cmds_by_tick(rep)
        for pid, bot in L.squad_map(mid, rep).items():
            rows = traj.get(bot, [])
            own, inc = bot_cmd_ticks(rep, pid)
            for r0, r1 in zip(rows, rows[1:]):
                t0, t1 = r0["t"], r1["t"]
                if t1 - t0 != 90 or r0["terr"] != r1["terr"] or r0["boats"] or r1["boats"] or r0["terr"] <= 0:
                    continue
                if not any_in(own, t0, t1) or any_in(inc, t0, t1) or any_in(own, t0 - 90, t0):
                    continue
                kinds = Counter(c[0] for t in range(t0, t1) for c in by_tick.get(t, ()) if c[1] == pid)
                if set(kinds) != {L.CMD_DONATE}:
                    continue
                state = {pid: [r0["bal"], r0["terr"]]}
                tl = L.simulate_window(by_tick, state, t0, t1, land)[pid]
                d = r1["bal"] - state[pid][0]
                tot["don"] += 1
                tot["don_exact"] += d == 0
                if len(ex) < 8:
                    ex.append((mid, bot, t0, r0["bal"], r1["bal"], state[pid][0], d, tl["n_don"], tl["don_out"], tl["don_fee"]))
    print(f"  只含捐款指令的窗口 {tot['don']} 个：逐兵相等 {tot['don_exact']}（{pct(tot['don_exact'], tot['don'])}）"
          "——验证 到账 = floor(B·(pct+1)/1024)、手续费 = floor(64·B/1024)=6.25%×全额、同拍多条逐条按当时余额重新报价。")
    for mid, bot, t0, b0, b1, pred, d, n, out, fee in ex:
        print(f"    {mid} {bot:8s} t={t0:5d} 余额{b0:8d}→{b1:8d} 预测{pred:8d} 差{d:+d} | {n} 笔捐款 到账合计{out} 手续费合计{fee}（费/到账={100 * fee / max(out, 1):.1f}%）")

    print("  同一拍成批进攻（≥6 条打同一个玩家、前一窗口无指令）：逐条按当时余额重新报价后的末余额 vs 实际：")
    rows_out = []
    for mid in L.R03_MATCHES:
        rep = L.load_replay(mid)
        if rep is None:
            continue
        land = L.match_land(mid, rep)
        traj = L.load_traj(mid)
        by_tick = L.cmds_by_tick(rep)
        for pid, bot in L.squad_map(mid, rep).items():
            rows = traj.get(bot, [])
            own, inc = bot_cmd_ticks(rep, pid)
            for r0, r1 in zip(rows, rows[1:]):
                t0, t1 = r0["t"], r1["t"]
                if t1 - t0 != 90 or r0["boats"] or r1["boats"] or r0["terr"] <= 0:
                    continue
                mine = [(t, c) for t in range(t0, t1) for c in by_tick.get(t, ()) if c[1] == pid]
                if len(mine) < 6 or len({t for t, _ in mine}) != 1:
                    continue
                if any(c[0] != L.CMD_ATTACK or c[3] >= L.NEUTRAL for _, c in mine) or len({c[3] for _, c in mine}) != 1:
                    continue
                if any_in(inc, t0, t1) or any_in(own, t0 - 90, t0):
                    continue
                state = {pid: [r0["bal"], r0["terr"]]}
                tl = L.simulate_window(by_tick, state, t0, t1, land)[pid]
                d = r1["bal"] - state[pid][0]
                rows_out.append((mid, bot, mine[0][0], len(mine), r0["bal"], tl["atk_troops"], tl["atk_fee"], state[pid][0], r1["bal"], d,
                                 r0["terr"], r1["terr"]))
    exact = sum(1 for r in rows_out if r[9] == 0)
    small = sum(1 for r in rows_out if abs(r[9]) <= 0.02 * r[4])
    print(f"    共 {len(rows_out)} 批：逐兵相等 {exact} 批，|残差| ≤ 发兵前余额 2% 的 {small} 批")
    for mid, bot, S, n, b0, troops, fee, pred, b1, d, l0, l1 in rows_out[:14]:
        print(f"    {mid} {bot:8s} 拍{S:5d} {n} 条 余额{b0:8d} 出兵{troops:8d} 费{fee:6d}（{100 * (troops + fee) / b0:.1f}%）"
              f" 预测末余额{pred:7d} 实际{b1:7d} 残差{d:+6d} 领土{l0}→{l1}")


if __name__ == "__main__":
    which = sys.argv[1:] or list("ABCDEF")
    for w in which:
        {"A": check_a, "B": check_b, "C": check_c, "D": check_d, "E": check_e, "F": check_f}[w.upper()]()
