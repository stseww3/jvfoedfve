#!/usr/bin/env python3
"""namepool.py — 「名字池误认」的真相口径账（squad20 = c110 的局；整局重演）。

c110 的互保是按名字认人的（v27-team-c110.js L3973-3996）：名字在 SQUAD_POOL_SET 里（或带 [NPL] / [NOPE]）的席位，只要场上还有
「占地 ≥80 格、名字不在池里的真人」活着，就不列为邻居、不打；引擎的敌我却只看队伍。两套口径不一致的地方有四种席位：
    跨队的我方号（引擎把编队分到了几个队里）｜离开以后的我方号（空壳，引擎按内置 AI 的打法接管）｜名字撞进池子的外人｜这些外人离开后的空壳
本脚本只量历史上这四种席位和我方号之间实际发生了什么（挨着、互相吃地、互相捐兵），不改任何规则。

原料：namepool.mjs → out/_run/namepool/<局>.json（整局重演；只读 /agent/repos/c136-data 发现集）
    python3 namepool.py [--quiet]     → out/_cross/namepool.txt、namepool.json

口径：
  · 「受保护的引擎敌人」（下面简称 PE）= 名字在池里、和这个我方号不在一个队（自由混战里人人都不在一个队）的席位，且当时保护开着；
    保护开着 = 场上还有占地 ≥80 格、名字不在池里的真人席位（含它们离开后的空壳——客户端分不出来）。
  · 「在线」= 还没发过离开指令；「空壳」= 发过离开指令以后（引擎按内置 AI 接管）。
  · 地的流水来自重演里每一次进攻结算（谁从谁手里吃了几格），300 拍一窗；保护开没开按窗的起点算。
  · 接触来自每 90 拍一次的边界扫描（每个我方号接触格数最多的 12 个对象）。

节：
  [NP-A] 名册：每局我方号分在几个队、池里的外人几个、保护什么时候解除。
  [NP-B] 接触：我方在线的号 × 90 拍样本里，贴着 PE 的占比；只剩 PE 可打（没有无主地、没有内置 AI、没有不受保护的真人）的占比。
  [NP-C] 地的流水：我方号被谁吃走了多少格、从谁手里吃到多少格（按对方的种类；保护开着 / 解除以后）。
  [NP-D] 我方号对 PE 的陆攻指令条数（保护开着的时候应该是 0）。
  [NP-E] 捐兵：我方号捐给谁（同队我方 / 同队外人 / 跨队——引擎不收 / 空壳），空壳把余额给了谁。
  [NP-F] 逐局一行。
"""
import glob
import json
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import xbatch as XB  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")
RUN = os.path.join(OUT, "_run", "namepool")
PERIODS = [("0~600", 0, 600), ("600~1500", 600, 1500), ("1500~3000", 1500, 3000), ("3000~4284", 3000, 4284), ("4284+", 4284, 10 ** 9)]
KINDS = ["AI", "wild_on", "wild_shell", "apex_on", "apex_shell", "ownx_on", "ownx_shell", "poolx_on", "poolx_shell", "ownteam_on", "ownteam_shell", "poolteam"]
KIND_CN = dict(AI="内置 AI", wild_on="野人（在线）", wild_shell="野人的空壳", apex_on="[APEX] 号（在线）", apex_shell="[APEX] 的空壳",
               ownx_on="跨队的我方号（在线）", ownx_shell="跨队的我方空壳", poolx_on="池里的外人·跨队（在线）", poolx_shell="池里的外人·跨队的空壳",
               ownteam_on="同队的我方号（在线）", ownteam_shell="同队的我方空壳", poolteam="池里的外人·同队")
PE_KINDS = ("ownx_on", "ownx_shell", "poolx_on", "poolx_shell")


def pct(a, b, nd=0):
    return "–" if not b else f"{100 * a / b:.{nd}f}%"


def period_of(t):
    for i, (_, a, z) in enumerate(PERIODS):
        if a <= t < z:
            return i
    return len(PERIODS) - 1


def main():
    quiet = "--quiet" in sys.argv
    pool = XB.name_pool()
    cohort = {mid: card.get("cohort") for mid, card in XB.discovery_ids()}
    lines = []
    J = {"matches": {}}

    def P(s=""):
        lines.append(s)

    files = sorted(glob.glob(os.path.join(RUN, "*.json")))
    rows = []
    tot_contact = [Counter() for _ in PERIODS]
    tot_flow_lost = {True: Counter(), False: Counter()}
    tot_flow_gain = {True: Counter(), False: Counter()}
    tot_flow_lost_p = [Counter() for _ in PERIODS]
    tot_atk = {True: Counter(), False: Counter()}
    tot_don = Counter()
    tot_don_amt = Counter()
    tot_husk = Counter()
    tot_husk_amt = Counter()
    n_used = 0
    for fp in files:
        R = json.load(open(fp, encoding="utf-8"))
        mid = R["matchId"]
        if cohort.get(mid) != "squad20":
            continue
        H = R["H"]
        names = [str(x).strip() for x in R["names"]]
        low = [x.lower() for x in names]
        teams = R["teams"]
        team_game = R["gameMode"] != 0
        left = R["leftT"]
        own = sorted(i for i in R["squad"].values() if i >= 0)
        own_set = set(own)
        if not own:
            continue
        n_used += 1
        in_pool = [low[s] in pool or "[npl]" in low[s] or "[nope]" in low[s] for s in range(H)]
        apex = ["[apex]" in low[s] for s in range(H)]
        poolx = [s for s in range(H) if in_pool[s] and s not in own_set]
        outsiders = [s for s in range(H) if not in_pool[s]]
        snapT, terr = R["snapT"], R["terr"]

        # 保护开着：每个快照上有没有占地 ≥80 的池外真人
        prot = [any(tr[s] >= 80 for s in outsiders) for tr in terr]
        t_off = next((snapT[i] for i in range(len(snapT)) if snapT[i] >= 90 and not prot[i]), None)

        def prot_at(t):
            # 取 ≤t 的最近快照
            i = min(len(snapT) - 1, max(0, t // 90))
            while i > 0 and snapT[i] > t:
                i -= 1
            return prot[i]

        def same_team(a, b):
            return team_game and teams[a] == teams[b] and teams[a] != 0

        def kind(me, q, t):
            if q >= 512:
                return "neutral"
            if q >= H:
                return "AI"
            shell = left[q] >= 0 and left[q] <= t
            if q in own_set:
                if same_team(me, q):
                    return "ownteam_shell" if shell else "ownteam_on"
                return "ownx_shell" if shell else "ownx_on"
            if in_pool[q]:
                if same_team(me, q):
                    return "poolteam"
                return "poolx_shell" if shell else "poolx_on"
            if same_team(me, q):
                return "mate"
            if apex[q]:
                return "apex_shell" if shell else "apex_on"
            return "wild_shell" if shell else "wild_on"

        # [NP-B] 接触
        m_contact = [Counter() for _ in PERIODS]
        for me_s, series in R["nb"].items():
            me = int(me_s)
            for t, lst in series:
                if left[me] >= 0 and left[me] <= t:
                    continue                      # 我方号自己已经离开
                i = min(len(snapT) - 1, t // 90)
                if terr[i][me] <= 0:
                    continue
                pi = period_of(t)
                on = prot_at(t)
                ks = [kind(me, q, t) for q, _ in lst]
                c = m_contact[pi]
                c["samples"] += 1
                pe = [k for k in ks if k in PE_KINDS]
                if on and pe:
                    c["touchPE"] += 1
                    for k in set(pe):
                        c["touch_" + k] += 1
                    free = [k for k in ks if k in ("neutral", "AI", "wild_on", "wild_shell", "apex_on", "apex_shell")]
                    if not free:
                        c["onlyPE"] += 1
                if not on:
                    c["protOff"] += 1
        for i in range(len(PERIODS)):
            tot_contact[i].update(m_contact[i])

        # [NP-C] 地的流水
        lost = {True: Counter(), False: Counter()}
        gain = {True: Counter(), False: Counter()}
        for b, p, q, tiles, burnt, dB in R["flows"]:
            if tiles <= 0:
                continue
            on = prot_at(b)
            if q in own_set and p != q:           # 我方号被 p 吃走
                k = kind(q, p, b) if p < 512 else "neutral"
                lost[on][k] += tiles
                tot_flow_lost_p[period_of(b)][k] += tiles
            if p in own_set and q != p and q < 512:   # 我方号从 q 手里吃到
                k = kind(p, q, b)
                gain[on][k] += tiles
        for on in (True, False):
            tot_flow_lost[on].update(lost[on])
            tot_flow_gain[on].update(gain[on])

        # [NP-D] 陆攻指令
        atk = {True: Counter(), False: Counter()}
        for b, p, q, n, ok, troops in R["atk"]:
            if q >= 512:
                continue
            on = prot_at(b)
            k = kind(p, q, b)
            atk[on][k] += n
            atk[on][k + "_ok"] += ok
        for on in (True, False):
            tot_atk[on].update(atk[on])

        # [NP-E] 捐兵
        don = Counter()
        don_amt = Counter()
        for t, p, q, ok, got, fee, b0 in R["dons"]:
            if p not in own_set or q >= H:
                continue
            if left[p] >= 0 and left[p] <= t:
                continue
            shell = left[q] >= 0 and left[q] <= t
            if not same_team(p, q):
                k = "跨队（引擎不收）"
            elif q in own_set:
                k = "同队我方空壳" if shell else "同队我方"
            elif in_pool[q]:
                k = "同队·池里的外人" + ("（空壳）" if shell else "")
            else:
                k = "同队外人" + ("（空壳）" if shell else "")
            don[k] += 1
            don[k + "|ok"] += ok
            don_amt[k + "|got"] += got
            don_amt[k + "|fee"] += fee
        tot_don.update(don)
        tot_don_amt.update(don_amt)
        husk = Counter()
        husk_amt = Counter()
        for t, p, q, b0, got in R["husk"]:
            if p >= H or p not in own_set:
                continue                           # 只看我方号离开后的空壳
            k = "给我方号" if q in own_set else ("给池里的外人" if q < H and in_pool[q] else ("给内置 AI" if q >= H else "给队里的外人"))
            husk[k] += 1
            husk_amt[k + "|gave"] += b0
            husk_amt[k + "|got"] += got
        tot_husk.update(husk)
        tot_husk_amt.update(husk_amt)

        own_teams = Counter(teams[s] for s in own) if team_game else Counter({0: len(own)})
        px_x = [s for s in poolx if not any(same_team(o, s) for o in own)]
        samples = sum(c["samples"] for c in m_contact)
        row = dict(mid=mid, H=H, teamGame=team_game, nTeams=R["nTeams"], end=R["endTick"], own=len(own), ownTeams=len(own_teams), ownLargest=max(own_teams.values()),
                   poolx=len(poolx), poolxApart=len(px_x), outsiders=len(outsiders), ownLeft=sum(1 for s in own if left[s] >= 0), tOff=t_off,
                   samples=samples, touchPE=sum(c["touchPE"] for c in m_contact), onlyPE=sum(c["onlyPE"] for c in m_contact),
                   lostPE=sum(lost[True][k] for k in PE_KINDS), lostAll=sum(v for on in (True, False) for k, v in lost[on].items() if k != "neutral"),
                   lostWild=sum(lost[on][k] for on in (True, False) for k in ("wild_on", "wild_shell", "apex_on", "apex_shell")),
                   lostAI=sum(lost[on]["AI"] for on in (True, False)),
                   gainPE_on=sum(gain[True][k] for k in PE_KINDS), gainPE_off=sum(gain[False][k] for k in PE_KINDS),
                   atkPE_on=sum(atk[True][k] for k in PE_KINDS), donX=don["跨队（引擎不收）"], donAll=sum(v for k, v in don.items() if "|" not in k))
        rows.append(row)
        J["matches"][mid] = row

    P(f"namepool.py — 「名字池误认」的真相口径账：squad20（c110）有对局段且重演对得上的 {n_used} 局（整局重演）")
    P()
    P("[NP-A] 名册")
    tg = [r for r in rows if r["teamGame"]]
    P(f"  组队局 {len(tg)}、自由混战 {len(rows) - len(tg)}；我方号合计 {sum(r['own'] for r in rows)} 个，中途离开的 {sum(r['ownLeft'] for r in rows)} 个")
    P(f"  组队局里我方号分在几个队：" + "；".join(f"{k} 个队 {v} 局" for k, v in sorted(Counter(r['ownTeams'] for r in tg).items()))
      + f"；最大的一块占我方号的比例 中位 {sorted(r['ownLargest'] / r['own'] for r in tg)[len(tg) // 2]:.2f}")
    P(f"  名字在池里的外人：有的局 {sum(1 for r in rows if r['poolx'])} / {len(rows)}，合计 {sum(r['poolx'] for r in rows)} 个席位（其中和任何一个我方号都不同队的 {sum(r['poolxApart'] for r in rows)} 个）")
    off = [r for r in rows if r["tOff"] is not None]
    P(f"  保护解除（场上不再有占地 ≥80 的池外真人）发生过的局 {len(off)} / {len(rows)}" + (f"：{'；'.join(f'{r['mid']} 在 {r['tOff']} 拍（录像 {r['end']} 拍）' for r in off)}" if off else ""))
    P()
    P("[NP-B] 接触：我方在线、有地的号 × 每 90 拍一个样本")
    P("  时段 | 样本 | 贴着 PE（受保护的引擎敌人）的 | 其中 PE 是：跨队我方在线 / 跨队我方空壳 / 池里外人在线 / 池里外人空壳 | 只剩 PE 可打的（没有无主地、内置 AI、不受保护的真人）| 保护已解除的样本")
    for i, (cn, _, _) in enumerate(PERIODS):
        c = tot_contact[i]
        n = c["samples"]
        P(f"  {cn} | {n} | {c['touchPE']}（{pct(c['touchPE'], n)}）| {c['touch_ownx_on']} / {c['touch_ownx_shell']} / {c['touch_poolx_on']} / {c['touch_poolx_shell']} | {c['onlyPE']}（{pct(c['onlyPE'], n)}）| {c['protOff']}")
    n = sum(c["samples"] for c in tot_contact)
    tp = sum(c["touchPE"] for c in tot_contact)
    op = sum(c["onlyPE"] for c in tot_contact)
    P(f"  合计 | {n} | {tp}（{pct(tp, n)}）| {sum(c['touch_ownx_on'] for c in tot_contact)} / {sum(c['touch_ownx_shell'] for c in tot_contact)} / {sum(c['touch_poolx_on'] for c in tot_contact)} / {sum(c['touch_poolx_shell'] for c in tot_contact)} | {op}（{pct(op, n)}）| {sum(c['protOff'] for c in tot_contact)}")
    J["contact"] = dict(samples=n, touchPE=tp, onlyPE=op, byPeriod=[dict(c) for c in tot_contact])
    P()
    P("[NP-C] 地的流水（格）：我方号被谁吃走、从谁手里吃到")
    P("  对方的种类 | 保护开着：我方被吃走 / 我方吃到 | 保护解除以后：我方被吃走 / 我方吃到")
    for k in KINDS + ["mate"]:
        a, b, c, d = tot_flow_lost[True][k], tot_flow_gain[True][k], tot_flow_lost[False][k], tot_flow_gain[False][k]
        if a + b + c + d == 0:
            continue
        P(f"  {KIND_CN.get(k, '同队外人')} | {a} / {b} | {c} / {d}")
    lost_all = sum(v for on in (True, False) for k, v in tot_flow_lost[on].items() if k != "neutral")
    lost_pe = sum(tot_flow_lost[True][k] for k in PE_KINDS)
    gain_pe = sum(tot_flow_gain[True][k] for k in PE_KINDS)
    lost_pe_off = sum(tot_flow_lost[False][k] for k in PE_KINDS)
    gain_pe_off = sum(tot_flow_gain[False][k] for k in PE_KINDS)
    lost_wild = sum(tot_flow_lost[on][k] for on in (True, False) for k in ("wild_on", "wild_shell", "apex_on", "apex_shell"))
    lost_ai = sum(tot_flow_lost[on]["AI"] for on in (True, False))
    P(f"  合计：我方被别的玩家吃走 {lost_all} 格 = 内置 AI {lost_ai}（{pct(lost_ai, lost_all)}）+ 野人和 [APEX]（含空壳）{lost_wild}（{pct(lost_wild, lost_all)}）+ 保护开着时的 PE {lost_pe}（{pct(lost_pe, lost_all)}）+ 保护解除后的池内席位 {lost_pe_off}（{pct(lost_pe_off, lost_all)}）+ 其它 {lost_all - lost_ai - lost_wild - lost_pe - lost_pe_off}")
    P(f"  保护开着时：我方被 PE 吃走 {lost_pe} 格，我方从 PE 手里吃到 {gain_pe} 格（差 {lost_pe - gain_pe}）；被 PE 吃走的按对方：" + "；".join(f"{KIND_CN[k]} {tot_flow_lost[True][k]}" for k in PE_KINDS))
    P("  我方被 PE 类席位吃走的格按时段：" + "；".join(f"{cn} {sum(tot_flow_lost_p[i][k] for k in PE_KINDS)}（同段被野人和 [APEX] 吃走 {sum(tot_flow_lost_p[i][k] for k in ('wild_on', 'wild_shell', 'apex_on', 'apex_shell'))}，被内置 AI {tot_flow_lost_p[i]['AI']}）" for i, (cn, _, _) in enumerate(PERIODS)))
    J["flow"] = dict(lostAll=lost_all, lostAI=lost_ai, lostWild=lost_wild, lostPE=lost_pe, gainPE=gain_pe, lostPEoff=lost_pe_off, gainPEoff=gain_pe_off,
                     lostOn={k: tot_flow_lost[True][k] for k in KINDS}, gainOn={k: tot_flow_gain[True][k] for k in KINDS},
                     lostOff={k: tot_flow_lost[False][k] for k in KINDS}, gainOff={k: tot_flow_gain[False][k] for k in KINDS})
    P()
    P("[NP-D] 我方号的陆攻指令（录像里落地的；目标是玩家的）按目标的种类：条数（其中生效的）")
    P("  目标的种类 | 保护开着 | 保护解除以后")
    for k in KINDS + ["mate"]:
        a, b = tot_atk[True][k], tot_atk[False][k]
        if a + b == 0:
            continue
        P(f"  {KIND_CN.get(k, '同队外人')} | {a}（{tot_atk[True][k + '_ok']}）| {b}（{tot_atk[False][k + '_ok']}）")
    J["atk"] = dict(on={k: tot_atk[True][k] for k in KINDS}, off={k: tot_atk[False][k] for k in KINDS})
    P()
    P("[NP-E] 捐兵（录像里落地的指令；重演结算）")
    P("  我方在线的号捐给谁 | 条数 | 成交 | 到账 | 损耗")
    for k in ("同队我方", "同队我方空壳", "同队·池里的外人", "同队·池里的外人（空壳）", "同队外人", "同队外人（空壳）", "跨队（引擎不收）"):
        if tot_don[k]:
            P(f"  {k} | {tot_don[k]} | {tot_don[k + '|ok']} | {tot_don_amt[k + '|got']} | {tot_don_amt[k + '|fee']}")
    P("  我方号离开后的空壳把余额给了谁（引擎的内置 AI 逻辑：没有可打的目标就把余额交给队友）| 次数 | 交出去的余额 | 对方到账")
    for k in ("给我方号", "给池里的外人", "给队里的外人", "给内置 AI"):
        if tot_husk[k]:
            P(f"  {k} | {tot_husk[k]} | {tot_husk_amt[k + '|gave']} | {tot_husk_amt[k + '|got']}")
    J["don"] = {k: v for k, v in tot_don.items()}
    J["donAmt"] = {k: v for k, v in tot_don_amt.items()}
    J["husk"] = {k: v for k, v in tot_husk.items()}
    J["huskAmt"] = {k: v for k, v in tot_husk_amt.items()}
    P()
    P("[NP-F] 逐局：局 | 真人 | 队数 | 录像拍 | 我方号（分在几个队 / 最大一块）| 离开的我方号 | 池里的外人（全不同队的）| 保护解除的拍 | 接触样本 | 贴着 PE | 只剩 PE 可打 | 我方被吃走的格：全部 / 内置 AI / 野人 / PE | 保护开着时我方对 PE 的陆攻 | 跨队捐兵 / 全部捐兵")
    for r in sorted(rows, key=lambda r: r["mid"]):
        P(f"  {r['mid']} | {r['H']} | {r['nTeams'] if r['teamGame'] else '混战'} | {r['end']} | {r['own']}（{r['ownTeams']} / {r['ownLargest']}）| {r['ownLeft']} | {r['poolx']}（{r['poolxApart']}）| {r['tOff'] if r['tOff'] is not None else '–'} | {r['samples']} | {pct(r['touchPE'], r['samples'])} | {pct(r['onlyPE'], r['samples'])} | "
          f"{r['lostAll']} / {r['lostAI']} / {r['lostWild']} / {r['lostPE']} | {r['atkPE_on']} | {r['donX']} / {r['donAll']}")

    os.makedirs(os.path.join(OUT, "_cross"), exist_ok=True)
    open(os.path.join(OUT, "_cross", "namepool.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    json.dump(J, open(os.path.join(OUT, "_cross", "namepool.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if not quiet:
        print("\n".join(lines))


if __name__ == "__main__":
    main()
