#!/usr/bin/env python3
"""truth.py — 把 resim_r08.mjs 的全场真值（out/<局>/resim.json）整理成可读底稿。

    python3 truth.py <matchId>                       # 写 out/<matchId>/truth.txt 并打印
    python3 truth.py <matchId> --bot <名字> [--t0 a --t1 b --every 30]   # 单个号的逐拍明细（打印，不写文件）
    python3 truth.py <matchId> --pairs <名字> [--t0 a --t1 b]            # 单个号逐 30 拍的交战明细
    python3 truth.py <matchId> --cmds <名字> [--t0 a --t1 b]             # 单个号的全部已执行指令

节：
  [TA] 房间、分队、录像来源、核对结果       [TB] 我方每个号：队、出生点、离开拍、阵亡拍、阵亡时身上的进攻
  [TC] 各队领土占比时间线（含内置 AI、我方各队分支）   [TD] 我方各号每 270 拍：地、兵、在外兵、身上的兵、最大邻居
  [TE] 交战账：我方每个号打谁/被谁打（整局合计，按对手）   [TF] 编队内部互打、与同房另一支编队互打
  [TG] 指令账：每个号各类指令条数、没生效的条数、叠加到已有进攻上的条数、重发串
  [TH] 捐款账（真值：是否成交、到账、扣税、收款人额度）   [TI] 离开的号：离开时的地/兵，之后被谁吃掉
  [TJ] 船靠岸到队友身上（兵是否蒸发）   [TK] 余额单窗跌 ≥30% 的真值对账
名字后缀：*=本编队  +=同房另一支编队  ~=已离开的空壳  #=内置 AI  T<n>=队号
"""
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out")
NEUTRAL = 512


class Truth:
    def __init__(self, mid):
        self.mid = mid
        self.R = R = json.load(open(os.path.join(OUT, mid, "resim.json"), encoding="utf-8"))
        self.H = R["H"]
        self.land = R["land"]
        self.names = [str(n).strip() for n in R["names"]]
        self.teams = R["teams"]
        self.nTeams = R["nTeams"]
        self.botsTeamed = R["botsTeamed"]
        self.snapT = R["snapT"]
        self.idx = {t: i for i, t in enumerate(self.snapT)}
        self.squad = {}   # 名字 -> id（本编队）
        self.peer = {}    # 名字 -> id（同房另一支）
        for b, s in R["squad"].items():
            if s["id"] < 0:
                continue
            if s.get("peer"):
                self.peer[b.split(":", 1)[1]] = s["id"]
            else:
                self.squad[b] = s["id"]
        self.sqIds = set(self.squad.values())
        self.peerIds = set(self.peer.values())
        self.leftT = R["leftT"]
        self.deathT = R["deathT"]
        self.end = R["endTick"]

    def team(self, p):
        if p >= NEUTRAL:
            return 0
        if p < self.H:
            return self.teams[p]
        return 1 + (p % self.nTeams) if self.botsTeamed and self.nTeams else 0

    def nm(self, p, t=None):
        if p >= NEUTRAL:
            return "空地"
        if p >= self.H:
            return f"AI{p}#" + (f"T{self.team(p)}" if self.botsTeamed else "")
        tag = "*" if p in self.sqIds else "+" if p in self.peerIds else ""
        husk = "~" if self.is_husk(p, t) else ""
        return f"{self.names[p][:14]}{tag}{husk}T{self.team(p)}"

    def is_husk(self, p, t=None):
        """离开后还没被吃完的空壳。t=None：整局里当过空壳。"""
        lt, dt = self.leftT[p], self.deathT[p]
        if lt < 0 or (0 <= dt <= lt):
            return False
        return t is None or (t >= lt and (dt < 0 or t < dt))

    def at(self, t):
        """不晚于 t 的最近一个快照下标。"""
        if t in self.idx:
            return self.idx[t]
        best = 0
        for i, tt in enumerate(self.snapT):
            if tt <= t:
                best = i
            else:
                break
        return best

    def terr(self, p, t):
        return self.R["snapTerr"][self.at(t)][p]

    def bal(self, p, t):
        return self.R["snapBal"][self.at(t)][p]

    def sq_of(self, name):
        key = name if name in self.R["sq"] else f"{self.R.get('peer')}:{name}"
        return self.R["sq"][key]

    def id_of(self, name):
        if name in self.squad:
            return self.squad[name]
        if name in self.peer:
            return self.peer[name]
        for p in range(self.H):
            if self.names[p].lower().endswith(name.lower()):
                return p
        raise SystemExit(f"找不到 {name}")

    def alive(self, p, t):
        d = self.deathT[p]
        return d < 0 or t < d

    def active(self, p, t):
        return self.alive(p, t) and (self.leftT[p] < 0 or t < self.leftT[p])


def pct(x, land):
    return 100.0 * x / land


def sec_TA(T, out):
    R = T.R
    v = R["validate"]
    out.append(f"[TA] {T.mid} 真值重演：录像取自 {R.get('replayFrom')}，重演到 t={R['endTick']}（over={R['over']} winnerTeam={R['winnerTeam']}）；"
               f"真人 {T.H}，地图陆地 {T.land}，{T.nTeams} 队（录像头 {R['nTeamsHeader']}），各队真人数 {R['teamSizes'][1:]}，内置 AI 入队={R['botsTeamed']}")
    out.append(f"     与本包 traj.csv 核对：{v['rows']} 行，领土一致 {v['terrExact']}，余额一致 {v['balExact']}，都一致 {v['bothExact']}"
               + (f"；首个不一致 {v['mism'][0]}" if v["mism"] else ""))
    out.append("     战队标签：" + " ".join(f"{c['tag']}×{c['size']}→T{c['team']}" for c in R["clans"]))
    out.append("     引擎事件：" + (" ".join(f"t={e[0]}:{'领先队≥80%，AI 开始猎杀' if e[1] == 'hunt' else '领先队≥90%，AI 提速'}(T{e[2]})" for e in R["engineEvents"]) or "无"))
    for label, grp in (("本编队", T.squad), ("同房另一支编队", T.peer)):
        if not grp:
            continue
        by = defaultdict(list)
        for n, p in grp.items():
            by[T.team(p)].append(n)
        out.append(f"     {label} {len(grp)} 个号的分队：" + "；".join(f"T{k}×{len(v)}（{' '.join(sorted(v))}）" for k, v in sorted(by.items())))


def sec_TB(T, out):
    R = T.R
    out.append("[TB] 名字 | 号 | 队 | 出生点 | 峰值领土@拍 | 离开拍(离开时地/兵) | 阵亡拍 | 阵亡时身上的进攻（谁:兵）")
    deaths = {d["p"]: d for d in R["deaths"]}
    spawn_seen = defaultdict(list)
    for label, grp in (("", T.squad), ("+", T.peer)):
        for n, p in sorted(grp.items(), key=lambda kv: kv[1]):
            peak, pt = 0, 0
            for i, t in enumerate(T.snapT):
                if R["snapTerr"][i][p] > peak:
                    peak, pt = R["snapTerr"][i][p], t
            lt = T.leftT[p]
            ls = f"{lt}({T.terr(p, lt)}/{T.bal(p, lt)})" if lt >= 0 else "-"
            d = deaths.get(p)
            ds = "-"
            if T.deathT[p] >= 0:
                ds = str(T.deathT[p])
            atk = " ".join(f"{T.nm(a, d['t'])}:{tr}" for a, tr in (d["attackers"] if d else [])[:5]) if d else ""
            sp = R["spawnXY"][p]
            if sp:
                spawn_seen[tuple(sp)].append(n + label)
            out.append(f"     {n + label:<16} | {p:>3} | T{T.team(p)} | {tuple(sp) if sp else None} | {peak}@{pt} | {ls} | {ds} | {atk}")
    dup = {k: v for k, v in spawn_seen.items() if len(v) > 1}
    if dup:
        out.append("     出生点完全相同的号：" + "；".join(f"{k}: {' '.join(v)}" for k, v in dup.items()))
    # 出生点最近距离（同队）
    pts = [(n, p, R["spawnXY"][p]) for n, p in T.squad.items() if R["spawnXY"][p]]
    close = []
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            a, b = pts[i], pts[j]
            dd = ((a[2][0] - b[2][0]) ** 2 + (a[2][1] - b[2][1]) ** 2) ** 0.5
            if dd < 60:
                close.append((dd, a[0], b[0], T.team(a[1]), T.team(b[1])))
    for dd, a, b, ta, tb in sorted(close):
        out.append(f"     出生点相距 {dd:.0f} 格：{a}(T{ta}) 与 {b}(T{tb})" + ("（不同队）" if ta != tb else ""))


def checkpoints(end):
    ts = [90, 180, 270, 360, 450, 540, 630, 720, 810, 900, 990, 1080, 1170, 1260, 1350, 1440, 1530, 1620, 1710, 1800]
    t = 1980
    while t < end:
        ts.append(t)
        t += 180
    return [t for t in ts if t <= end]


def sec_TC(T, out):
    R = T.R
    nT = T.nTeams
    out.append("[TC] 拍 | 各队占陆地%（T1..Tn）| 内置 AI% | 空地% | 活跃真人数（各队）| 本编队各队分支占陆地%（号数）| 同房另一支%")
    for t in checkpoints(T.end) + [T.end]:
        i = T.at(t)
        tl = R["teamLand"][i]
        used = sum(tl) + R["botLand"][i]
        act = [0] * (nT + 1)
        for p in range(T.H):
            if T.active(p, t) and R["snapTerr"][i][p] > 0:
                act[T.team(p)] += 1
        mine = defaultdict(lambda: [0, 0])
        for n, p in T.squad.items():
            if T.active(p, t) and R["snapTerr"][i][p] > 0:
                mine[T.team(p)][0] += R["snapTerr"][i][p]
                mine[T.team(p)][1] += 1
        peer = sum(R["snapTerr"][i][p] for p in T.peerIds if T.active(p, t))
        peern = sum(1 for p in T.peerIds if T.active(p, t) and R["snapTerr"][i][p] > 0)
        out.append(f"     {t:>5} | " + " ".join(f"{pct(x, T.land):5.1f}" for x in tl[1:]) + f" | {pct(R['botLand'][i], T.land):5.1f} | {pct(T.land - used, T.land):5.1f} | "
                   + "/".join(str(x) for x in act[1:]) + " | "
                   + " ".join(f"T{k}:{pct(v[0], T.land):.2f}({v[1]})" for k, v in sorted(mine.items()))
                   + (f" | {pct(peer, T.land):.2f}({peern})" if T.peerIds else ""))


def top_nb(T, o, t):
    best = None
    for tt, lst in o["nb"]:
        if tt <= t:
            best = lst
        else:
            break
    return best or []


def sec_TD(T, out, step=270):
    R = T.R
    out.append(f"[TD] 我方各号每 {step} 拍：地 | 兵 | 密度 | 在外兵→最大目标 | 身上的兵←最大来源 | 接壤最多的 3 家（接壤格数）| 受捐额度已用")
    for n, p in sorted(T.squad.items(), key=lambda kv: (T.team(kv[1]), kv[1])):
        o = T.sq_of(n)
        out.append(f"   -- {n}({p}) T{T.team(p)}  离开={T.leftT[p]} 阵亡={T.deathT[p]}")
        last = T.deathT[p] if T.deathT[p] >= 0 else T.end
        for t in range(90, last + 1, step):
            i = T.at(t)
            terr, bal = R["snapTerr"][i][p], R["snapBal"][i][p]
            if terr <= 0:
                continue
            outs = o["out"][i]
            inn = o["inn"][i]
            so = sum(x[1] for x in outs)
            si = sum(x[1] for x in inn)
            mo = max(outs, key=lambda x: x[1]) if outs else None
            mi = max(inn, key=lambda x: x[1]) if inn else None
            nb = top_nb(T, o, t)[:3]
            out.append(f"      {t:>5} | {terr:>6} | {bal:>8} | {bal / max(terr, 1):6.1f} | {so:>7}" + (f"→{T.nm(mo[0], t)}" if mo else "") + f" | {si:>7}" + (f"←{T.nm(mi[0], t)}" if mi else "")
                       + " | " + " ".join(f"{T.nm(q, t)}:{c}" for q, c in nb) + f" | {o['quota'][i]}")


def pair_totals(T, t0=0, t1=10 ** 9):
    """(攻, 守) -> [格, 攻方耗兵, 守方余额损失, 守方反击槽损失, 次数]"""
    tot = defaultdict(lambda: [0, 0, 0, 0, 0])
    for t, a, d, tiles, burnt, dB, dS, n in T.R["pairLog"]:
        if t0 < t <= t1:
            r = tot[(a, d)]
            r[0] += tiles; r[1] += burnt; r[2] += dB; r[3] += dS; r[4] += n
    return tot


def sec_TE(T, out):
    tot = pair_totals(T)
    out.append("[TE] 交战账（整局合计）。打出去：目标 格数 耗兵（每格）；挨打：来源 丢的格数 对方耗兵 自己余额被打掉")
    for n, p in sorted(T.squad.items(), key=lambda kv: (T.team(kv[1]), kv[1])):
        outs = sorted(((d, r) for (a, d), r in tot.items() if a == p), key=lambda x: -x[1][1])
        ins = sorted(((a, r) for (a, d), r in tot.items() if d == p), key=lambda x: -x[1][0])
        so = sum(r[1] for _, r in outs)
        sg = sum(r[0] for _, r in outs)
        sl = sum(r[0] for _, r in ins)
        out.append(f"   -- {n}({p}) T{T.team(p)}：打出去共耗兵 {so}，拿地 {sg} 格；被拿走 {sl} 格")
        hum = [x for x in outs if x[0] < NEUTRAL]
        neu = [x for x in outs if x[0] >= NEUTRAL]
        ai = [x for x in hum if x[0] >= T.H]
        hm = [x for x in hum if x[0] < T.H]
        if neu:
            r = neu[0][1]
            out.append(f"        →空地 {r[0]} 格 耗兵 {r[1]}（{r[1] / max(r[0], 1):.1f}/格）")
        if ai:
            g = sum(r[0] for _, r in ai); b = sum(r[1] for _, r in ai)
            out.append(f"        →内置 AI（{len(ai)} 个）{g} 格 耗兵 {b}（{b / max(g, 1):.1f}/格）")
        for d, r in hm[:8]:
            same = "【同队】" if T.team(d) == T.team(p) else ""
            out.append(f"        →{T.nm(d)}{same} {r[0]} 格 耗兵 {r[1]}（{r[1] / max(r[0], 1):.1f}/格）对方余额被打掉 {r[2]}")
        for a, r in ins[:8]:
            if r[0] <= 0 and r[2] <= 0:
                continue
            same = "【同队】" if T.team(a) == T.team(p) and a < T.H else ""
            out.append(f"        ←{T.nm(a)}{same} 丢 {r[0]} 格 对方耗兵 {r[1]}（{r[1] / max(r[0], 1):.1f}/格）自己余额被打掉 {r[2]}")


def sec_TF(T, out):
    tot = pair_totals(T)
    out.append("[TF] 编队内部互打（同一编队、不同队）与两支编队互打：攻 → 守 格数 攻方耗兵 守方余额损失")
    rows = []
    for (a, d), r in tot.items():
        if a >= T.H or d >= T.H:
            continue
        ours_a, ours_d = a in T.sqIds, d in T.sqIds
        peer_a, peer_d = a in T.peerIds, d in T.peerIds
        if (ours_a and ours_d) or (ours_a and peer_d) or (peer_a and ours_d):
            if r[0] or r[1]:
                rows.append((r[1], a, d, r))
    s_in = [0, 0, 0]
    for _, a, d, r in sorted(rows, reverse=True):
        kind = "编队内" if (a in T.sqIds and d in T.sqIds) else "跨编队"
        if kind == "编队内":
            s_in[0] += r[0]; s_in[1] += r[1]; s_in[2] += r[2]
        out.append(f"     [{kind}] {T.nm(a)} → {T.nm(d)}  {r[0]} 格 耗兵 {r[1]} 守方余额损失 {r[2]}")
    out.append(f"     编队内部互打合计：{s_in[0]} 格，攻方耗兵 {s_in[1]}，守方余额损失 {s_in[2]}")


KIND = {1: "陆攻", 2: "捐款", 3: "发船", 4: "追船/召回", 5: "撤军", 8: "离开", 9: "离开"}


def clusters(cmds, gap=14):
    per = defaultdict(list)
    for c in cmds:
        if c[2] in (1, 3):
            per[(c[1], c[2], c[4] if c[2] == 1 else c[10] if len(c) > 10 else -1)].append(c)
    out = []
    for key, lst in per.items():
        cur = [lst[0]]
        for c in lst[1:]:
            if c[0] - cur[-1][0] <= gap:
                cur.append(c)
            else:
                out.append(cur)
                cur = [c]
        out.append(cur)
    return out


def sec_TG(T, out):
    R = T.R
    out.append("[TG] 指令账（已执行的指令）：号 | 陆攻 条数/没生效/叠加到已有进攻 | 发船 条数/没生效 | 捐款 条数/没生效 | 撤军 | 重发串（同目标、执行拍相隔≤14）数/多发条数 | 多发占陆攻+发船%")
    allc = defaultdict(list)
    for c in R["cmdLog"]:
        allc[c[1]].append(c)
    tot_cmd = tot_extra = 0
    big = []
    for n, p in sorted(T.squad.items(), key=lambda kv: (T.team(kv[1]), kv[1])):
        cs = allc.get(p, [])
        atk = [c for c in cs if c[2] == 1]
        boat = [c for c in cs if c[2] == 3]
        don = [c for c in cs if c[2] == 2]
        ret = [c for c in cs if c[2] == 5]
        cl = clusters(cs)
        dups = [c for c in cl if len(c) >= 2]
        extra = sum(len(c) - 1 for c in dups)
        nab = len(atk) + len(boat)
        tot_cmd += nab; tot_extra += extra
        out.append(f"     {n:<14}({p:>2}) T{T.team(p)} | {len(atk)}/{sum(1 for c in atk if not c[5])}/{sum(1 for c in atk if c[5] and c[10] > 0)} | {len(boat)}/{sum(1 for c in boat if not c[5])} | "
                   f"{len(don)}/{sum(1 for c in don if not c[5])} | {len(ret)} | {len(dups)}/{extra} | {100 * extra / max(nab, 1):.0f}%")
        for c in dups:
            if c[0][2] != 1:
                continue
            B0 = c[0][8]
            sent = sum(x[6] + x[7] for x in c if x[5])
            if B0 > 0 and len(c) >= 3:
                big.append((sent / B0, n, p, c, B0, sent))
    out.append(f"     合计：陆攻+发船 {tot_cmd} 条，其中重发串里多发的 {tot_extra} 条（{100 * tot_extra / max(tot_cmd, 1):.0f}%）")
    out.append("     抽兵最狠的陆攻重发串（≥3 条）：号 起止拍 目标 条数 pct 序列 | 首条执行前余额 → 整串实发兵+手续费（占首条前余额%）| 首条本意%")
    for fr, n, p, c, B0, sent in sorted(big, key=lambda x: -x[0])[:14]:
        tgt = c[0][4]
        out.append(f"       {n}({p}) t={c[0][0]}~{c[-1][0]} →{T.nm(min(tgt, NEUTRAL), c[0][0])} ×{len(c)} pct={[x[3] for x in c]} | {B0} → {sent}（{100 * fr:.0f}%）| {100 * (c[0][3] + 1) / 1024:.0f}%")


def sec_TH(T, out):
    R = T.R
    out.append("[TH] 捐款账（真值）：拍 捐出→收款 pct | 是否成交 | 到账 | 捐出方实际少掉的兵−到账（税）| 捐出方余额/领土 | 收款方当时领土/余额 | 收款方额度已用/额度上限")
    n_ok = n_bad = 0
    got_sum = tax_sum = 0
    for c in R["cmdLog"]:
        if c[2] != 2:
            continue
        p, q = c[1], c[4]
        if p not in T.sqIds and q not in T.sqIds:
            continue
        ok = c[5]
        if p in T.sqIds:
            if ok:
                n_ok += 1; got_sum += c[6]; tax_sum += c[7]
            else:
                n_bad += 1
        cross = "" if q >= NEUTRAL or T.team(p) == T.team(q) else "【不同队】"
        out.append(f"     {c[0]:>5} {T.nm(p, c[0])}→{T.nm(min(q, NEUTRAL), c[0])}{cross} pct={c[3]} | {'成交' if ok else '没成交'} | {c[6]} | {c[7]} | {c[8]}/{c[9]} | "
                   + (f"{c[13]}/{c[14]} | {c[10]}/{c[11]}" if len(c) > 14 else ""))
    out.append(f"     本编队捐出：成交 {n_ok} 笔，到账合计 {got_sum}，税合计 {tax_sum}；没成交 {n_bad} 笔")


def sec_TI(T, out):
    R = T.R
    left = [(n, p) for n, p in T.squad.items() if T.leftT[p] >= 0]
    if not left:
        out.append("[TI] 本编队没有号在录像里执行过「离开」指令")
        return
    out.append("[TI] 离开的号：离开拍 | 离开时地/兵 | 占当时本队分支% | 之后这块地被谁拿走（按队合计格数）| 空壳阵亡拍")
    for n, p in sorted(left, key=lambda kv: T.leftT[kv[1]]):
        lt = T.leftT[p]
        tot = pair_totals(T, lt, 10 ** 9)
        by = defaultdict(int)
        who = defaultdict(int)
        for (a, d), r in tot.items():
            if d == p and r[0] > 0:
                key = "内置AI" if a >= T.H else f"T{T.team(a)}"
                by[key] += r[0]
                who[a] += r[0]
        topw = " ".join(f"{T.nm(a)}:{v}" for a, v in sorted(who.items(), key=lambda x: -x[1])[:4])
        out.append(f"     {n}({p}) T{T.team(p)} | {lt} | {T.terr(p, lt)}/{T.bal(p, lt)} | | " + " ".join(f"{k}:{v}" for k, v in sorted(by.items(), key=lambda x: -x[1])) + f"（{topw}）| {T.deathT[p]}")


def sec_TJ(T, out):
    R = T.R
    rows = [l for l in R["landings"] if l[1] in T.sqIds and l[2] < T.H and l[2] != l[1] and T.team(l[1]) == T.team(l[2])]
    out.append(f"[TJ] 本编队的船靠岸在同队真人身上：{len(rows)} 次：拍 船主→地主 船上兵 | 地主到账 | 地主额度已用/上限")
    for l in rows[:20]:
        out.append(f"     {l[0]} {T.nm(l[1], l[0])}→{T.nm(l[2], l[0])} {l[3]} | {l[4]} | {l[5]}/{l[6]}")


def sec_TM(T, out):
    """空壳赠兵（bots.js botDonate→botGive）：离开的真人按内置 AI 跑，没有目标可打时把全部余额交给一个刚打过仗或有船在外的队友（手续费 64/1024，不占额度）。"""
    gifts = T.R.get("huskGifts")
    if gifts is None:
        out.append("[TM] 空壳赠兵：resim.json 没有 huskGifts（重跑 resim_r08.mjs）")
        return
    big = [x for x in gifts if x[6] - x[5] >= 2000]
    out.append(f"[TM] 空壳赠兵（引擎 botDonate，真值）：共 {len(gifts)} 次，其中到账 ≥2000 的 {len(big)} 次：拍 空壳→收款 | 空壳余额 前→后 / 领土 | 收款方到账 | 收款方余额 前→后 / 领土")
    for x in sorted(big, key=lambda r: -(r[6] - r[5]))[:25]:
        t, p, q = x[0], x[1], x[2]
        tag = lambda i: ("*" if i in T.sqIds else "") + ("+" if i in getattr(T, "peerIds", ()) else "")  # noqa: E731
        out.append(f"     {t:>5} {T.nm(p, t)}→{T.nm(q, t)} | {x[4]}→{x[7]} / {x[8]} | {x[6] - x[5]} | {x[5]}→{x[6]} / {x[9]}")
    tot = defaultdict(lambda: [0, 0])
    for x in gifts:
        k = ("本编队空壳" if x[1] in T.sqIds else "其它空壳", "空壳" if T.is_husk(x[2], x[0]) else ("本编队在线的号" if x[2] in T.sqIds else "其它真人"))
        tot[k][0] += 1
        tot[k][1] += x[6] - x[5]
    out.append("     合计（谁的空壳 → 给了谁：次数 / 到账）：" + "；".join(f"{a}→{b} {v[0]} 次 / {v[1]}" for (a, b), v in sorted(tot.items(), key=lambda kv: -kv[1][1])))


def boat_ledger(T, ids=None):
    """每个号的船账：发船（条数、船上兵、手续费）；靠岸分类（空地 / 敌方 / 自己的地 / 同队：到账与蒸发）；没靠岸的差额（海上衰减每 5 拍 1/128、海战、终局仍在海上）。"""
    R = T.R
    ids = T.sqIds if ids is None else ids
    led = {p: dict(n=0, troops=0, fee=0, small=0, smallFee=0, neutral=[0, 0], enemy=[0, 0], own=[0, 0], mate=[0, 0, 0], evap=[0, 0]) for p in ids}
    for c in R["cmdLog"]:
        if c[2] == 3 and c[1] in led and c[5]:
            d = led[c[1]]
            d["n"] += 1
            d["troops"] += c[6]
            d["fee"] += c[7]
            if c[7] > c[6]:
                d["small"] += 1
                d["smallFee"] += c[7]
    for l in R["landings"]:
        t, p, tg, troops, got = l[0], l[1], l[2], l[3], l[4]
        if p not in led:
            continue
        d = led[p]
        if tg == NEUTRAL or tg < 0:
            k = "neutral"
        elif tg == p:
            k = "own"
        elif tg < T.H and T.team(tg) == T.team(p):
            if got <= 0:
                d["evap"][0] += 1
                d["evap"][1] += troops
            else:
                d["mate"][0] += 1
                d["mate"][1] += troops
                d["mate"][2] += got
            continue
        else:
            k = "enemy"
        d[k][0] += 1
        d[k][1] += troops
    return led


def sec_TL(T, out):
    led = boat_ledger(T)
    if not any(d["n"] for d in led.values()):
        return
    out.append("[TL] 船账（真值）：号 | 发船 条数/船上兵/手续费（每条船收余额的 32/1024）| 其中手续费>船上兵的 条数/手续费 | 靠岸：空地 次/兵 | 敌方 次/兵 | 自己的地 次/兵 | 同队到账 次/船上兵 | 同队蒸发 次/兵 | 没靠岸的差额（海上衰减、海战、终局在海上）")
    tot = dict(n=0, troops=0, fee=0, small=0, smallFee=0, neutral=0, enemy=0, own=0, mate=0, evap=0, landed=0)
    for name, p in sorted(T.squad.items(), key=lambda kv: kv[1]):
        d = led[p]
        if not d["n"]:
            continue
        landed = d["neutral"][1] + d["enemy"][1] + d["own"][1] + d["mate"][1] + d["evap"][1]
        out.append(f"     {name:12s} | {d['n']}/{d['troops']}/{d['fee']} | {d['small']}/{d['smallFee']} | {d['neutral'][0]}/{d['neutral'][1]} | {d['enemy'][0]}/{d['enemy'][1]} | {d['own'][0]}/{d['own'][1]} | "
                   f"{d['mate'][0]}/{d['mate'][1]} | {d['evap'][0]}/{d['evap'][1]} | {d['troops'] - landed}")
        for k in ("n", "troops", "fee", "small", "smallFee"):
            tot[k] += d[k]
        for k in ("neutral", "enemy", "own", "mate", "evap"):
            tot[k] += d[k][1]
        tot["landed"] += landed
    out.append(f"     合计：发船 {tot['n']} 条，船上兵 {tot['troops']}，手续费 {tot['fee']}（其中 {tot['small']} 条手续费大于船上兵，共付 {tot['smallFee']}）；靠岸在空地 {tot['neutral']}、敌方 {tot['enemy']}、自己的地 {tot['own']}、"
               f"同队到账 {tot['mate']}、同队蒸发 {tot['evap']}；没靠岸 {tot['troops'] - tot['landed']}")


def sec_TK(T, out, win=90, frac=0.30):
    """余额单窗（90 拍）跌 ≥30% 的真值对账：自己执行的指令（陆攻/船/捐款，含手续费与税）、挨打被打掉的余额，剩下的差额=利息/回流/误差。"""
    R = T.R
    rows = []
    for name, info in sorted(R["squad"].items(), key=lambda kv: kv[1]["id"]):
        p = info["id"]
        if p < 0 or info.get("peer"):
            continue
        for t0 in range(90, T.end - win + 1, win):
            t1 = t0 + win
            if T.terr(p, t0) <= 0 or T.is_husk(p, t0):
                continue
            b0, b1 = T.bal(p, t0), T.bal(p, t1)
            if b0 < 1000 or b1 > (1 - frac) * b0:
                continue
            atk = boat = don = 0
            n_atk = n_boat = n_don = 0
            tgts = defaultdict(int)
            for c in R["cmdLog"]:
                if c[1] != p or not (t0 < c[0] <= t1) or not c[5]:
                    continue
                if c[2] == 1:
                    atk += c[6] + c[7]
                    n_atk += 1
                    tgts[min(c[4], NEUTRAL)] += c[6]
                elif c[2] == 3:
                    boat += c[6] + c[7]
                    n_boat += 1
                elif c[2] == 2:
                    don += c[6] + c[7]
                    n_don += 1
            hit = 0
            who = defaultdict(int)
            for t, a, d, tiles, burnt, dB, dS, n in R["pairLog"]:
                if d == p and t0 < t <= t1:
                    hit += dB + dS
                    who[a] += dB + dS
            resid = (b1 - b0) + atk + boat + don + hit
            top_t = max(tgts.items(), key=lambda kv: kv[1])[0] if tgts else None
            top_w = max(who.items(), key=lambda kv: kv[1])[0] if who else None
            cause = max((("陆攻", atk), ("发船", boat), ("捐款", don), ("挨打", hit)), key=lambda kv: kv[1])[0]
            rows.append((t0, name, p, b0, b1, T.terr(p, t0), T.terr(p, t1), atk, n_atk, top_t, boat, n_boat, don, n_don, hit, top_w, resid, cause))
    out.append(f"[TK] 余额单窗（{win} 拍）跌 ≥{int(frac * 100)}% 的真值对账（{len(rows)} 段）：窗口 号 | 余额 前→后（跌幅）| 地 前→后 | 陆攻 条数/兵+费→主要目标 | 船 条数/兵+费 | 捐款 笔数/到账+税 | 挨打被打掉（主要来源）| 其余（利息、回流等）| 主因")
    for t0, name, p, b0, b1, l0, l1, atk, n_atk, top_t, boat, n_boat, don, n_don, hit, top_w, resid, cause in sorted(rows):
        tt = "" if top_t is None else "→" + ("空地" if top_t >= NEUTRAL else f"AI{top_t}" if top_t >= T.H else T.nm(top_t, t0))
        ww = "" if top_w is None else "（" + (f"AI{top_w}" if top_w >= T.H else T.nm(top_w, t0)) + "）"
        out.append(f"     {t0}-{t0 + win} {name}*T{T.team(p)} | {b0}→{b1}（-{100 * (b0 - b1) / b0:.0f}%）| {l0}→{l1} | {n_atk}/{atk}{tt} | {n_boat}/{boat} | {n_don}/{don} | {hit}{ww} | {resid:+d} | {cause}")
    by = defaultdict(int)
    for r in rows:
        by[r[-1]] += 1
    out.append("     主因合计：" + "，".join(f"{k} {v}" for k, v in sorted(by.items(), key=lambda kv: -kv[1])))


def bot_detail(T, name, t0, t1, every):
    p = T.id_of(name)
    o = T.sq_of(name)
    R = T.R
    print(f"{name}({p}) T{T.team(p)} 离开={T.leftT[p]} 阵亡={T.deathT[p]}：拍 | 地 | 兵 | 密度 | 在外（目标:兵）| 身上（来源:兵）| 邻居（接壤格数）| 船数/船上兵 | 额度")
    for i, t in enumerate(T.snapT):
        if t < t0 or t > t1 or t % every:
            continue
        terr, bal = R["snapTerr"][i][p], R["snapBal"][i][p]
        outs = " ".join(f"{T.nm(q, t)}:{tr}" for q, tr in o["out"][i])
        inn = " ".join(f"{T.nm(q, t)}:{tr}" for q, tr in sorted(o["inn"][i], key=lambda x: -x[1])[:5])
        nb = " ".join(f"{T.nm(q, t)}:{c}" for q, c in top_nb(T, o, t)[:6])
        print(f"  {t:>5} | {terr:>6} | {bal:>8} | {bal / max(terr, 1):6.1f} | {outs} | {inn} | {nb} | {o['boats'][i][0]}/{o['boats'][i][1]} | {o['quota'][i]}")


def pairs_detail(T, name, t0, t1):
    p = T.id_of(name)
    print(f"{name}({p}) 逐 30 拍交战：拍 | 方向 对手 | 格 | 攻方耗兵 | 守方余额损失 | 守方反击槽损失 | 次数")
    for t, a, d, tiles, burnt, dB, dS, n in T.R["pairLog"]:
        if t < t0 or t > t1:
            continue
        if a == p:
            print(f"  {t:>5} | → {T.nm(d, t)} | {tiles} | {burnt} | {dB} | {dS} | {n}")
        elif d == p:
            print(f"  {t:>5} | ← {T.nm(a, t)} | {tiles} | {burnt} | {dB} | {dS} | {n}")


def cmds_detail(T, name, t0, t1):
    p = T.id_of(name)
    print(f"{name}({p}) 已执行指令：拍 | 类型 pct 目标 | 生效 | 实发兵 手续费 | 执行前余额/领土 | 同目标已有在途兵（陆攻）")
    for c in T.R["cmdLog"]:
        if c[1] != p or c[0] < t0 or c[0] > t1:
            continue
        k = c[2]
        if k == 1:
            print(f"  {c[0]:>5} | 陆攻 {c[3]} →{T.nm(min(c[4], NEUTRAL), c[0])} | {c[5]} | {c[6]} {c[7]} | {c[8]}/{c[9]} | {c[10]}")
        elif k == 2:
            print(f"  {c[0]:>5} | 捐款 {c[3]} →{T.nm(min(c[4], NEUTRAL), c[0])} | {c[5]} | 到账 {c[6]} 税 {c[7]} | {c[8]}/{c[9]} | 收款方额度 {c[10]}/{c[11]} 收款方地/兵 {c[13]}/{c[14]}")
        elif k == 3:
            print(f"  {c[0]:>5} | 发船 {c[3]} →{T.nm(min(c[10], NEUTRAL), c[0]) if c[10] >= 0 else '?'} | {c[5]} | {c[6]} {c[7]} | {c[8]}/{c[9]} |")
        elif k == 5:
            print(f"  {c[0]:>5} | 撤军 目标={T.nm(min(c[3], NEUTRAL), c[0])} | {c[5]} | 退回 {c[6]} | {c[8]}/{c[9]} |")
        else:
            print(f"  {c[0]:>5} | {KIND.get(k, k)} {c[3]} {c[4]} | {c[5]} | {c[6]} | {c[8]}/{c[9]} |")


def timeline_point(T, t):
    """给复盘 JSON 的 timeline 用：t 拍（取不晚于 t 的最近快照）的全场真值。"""
    R = T.R
    i = T.at(t)
    tl = R["teamLand"][i]
    terr = R["snapTerr"][i]
    ts = T.snapT[i]
    act = [p for p in range(T.H) if T.active(p, ts) and terr[p] > 0]
    sq = [p for p in T.sqIds if T.active(p, ts) and terr[p] > 0]
    husk = sum(terr[p] for p in T.sqIds if T.is_husk(p, ts))
    sq_land = sum(terr[p] for p in sq)
    all_land = sum(terr[p] for p in act)
    by = defaultdict(lambda: [0, 0])
    for p in sq:
        by[T.team(p)][0] += 1
        by[T.team(p)][1] += terr[p]
    d = dict(snapT=ts,
             teamSharePct={f"T{k}": round(pct(tl[k], T.land), 1) for k in range(1, T.nTeams + 1)},
             builtInAiSharePct=round(pct(R["botLand"][i], T.land), 1),
             activeHumansByTeam={f"T{k}": sum(1 for p in act if T.team(p) == k) for k in range(1, T.nTeams + 1)},
             squadActive=len(sq), squadActiveSharePct=round(pct(sq_land, T.land), 2),
             squadHuskSharePct=round(pct(husk, T.land), 2),
             squadPerCapitaVsRoomActive=round((sq_land / len(sq)) / (all_land / len(act)), 2) if sq and act and all_land else None,
             squadByTeam={f"T{k}": dict(bots=v[0], sharePct=round(pct(v[1], T.land), 2)) for k, v in sorted(by.items())})
    if T.peerIds:
        pe = [p for p in T.peerIds if T.active(p, ts) and terr[p] > 0]
        d["peerActive"] = len(pe)
        d["peerActiveSharePct"] = round(pct(sum(terr[p] for p in pe), T.land), 2)
    return d


def death_summary(T, p, span=420):
    """给复盘 JSON 的 deaths 用：引擎里的离开拍 / 阵亡拍，阵亡前 span 拍谁拿走了地、花了多少兵。"""
    lt, dt = T.leftT[p], T.deathT[p]
    d = dict(engineLeftTick=lt if lt >= 0 else None, engineDeathTick=dt if dt >= 0 else None)
    if lt >= 0:
        d["leftWith"] = dict(terr=T.terr(p, lt), bal=T.bal(p, lt))
    if dt >= 0:
        tot = pair_totals(T, max(0, dt - span), dt + 30)
        takers = sorted(((a, r) for (a, dd), r in tot.items() if dd == p and r[0] > 0), key=lambda kv: -kv[1][0])[:3]
        d["takersLast420"] = [dict(by=T.nm(a, dt), tiles=r[0], troopsSpent=r[1], perTile=round(r[1] / max(r[0], 1), 1)) for a, r in takers]
        mine = sorted(((dd, r) for (a, dd), r in tot.items() if a == p and r[1] > 0), key=lambda kv: -kv[1][1])[:2]
        d["ownAttacksLast420"] = [dict(on=T.nm(dd, dt), tiles=r[0], troopsSpent=r[1], perTile=round(r[1] / max(r[0], 1), 1)) for dd, r in mine]
    return d


def death_detail(T, name, span=420):
    """阵亡（或离开）前 span 拍：每 30 拍状态、已执行指令、按对手合计的交战、收到的捐款。"""
    p = T.id_of(name)
    end = T.deathT[p] if T.deathT[p] >= 0 else T.end
    t0 = max(0, end - span)
    print(f"=== {name}({p}) T{T.team(p)} 离开={T.leftT[p]} 阵亡={T.deathT[p]}，窗口 {t0}~{end}")
    bot_detail(T, name, t0 - t0 % 30, end, 30)
    cmds_detail(T, name, t0, end)
    tot = pair_totals(T, t0, end + 30)
    print("  窗口内交战合计：")
    for (a, d), r in sorted(tot.items(), key=lambda kv: -kv[1][1]):
        if a == p and (r[0] or r[1]):
            print(f"    → {T.nm(d, end)} 拿 {r[0]} 格 耗兵 {r[1]}（{r[1] / max(r[0], 1):.1f}/格）对方余额被打掉 {r[2]}")
    for (a, d), r in sorted(tot.items(), key=lambda kv: -kv[1][0]):
        if d == p and (r[0] or r[2]):
            print(f"    ← {T.nm(a, end)} 丢 {r[0]} 格 对方耗兵 {r[1]}（{r[1] / max(r[0], 1):.1f}/格）自己余额被打掉 {r[2]}")
    don = [c for c in T.R["cmdLog"] if c[2] == 2 and c[4] == p and t0 <= c[0] <= end]
    print(f"  窗口内收到捐款 {len(don)} 笔，到账 {sum(c[6] for c in don)}：" + " ".join(f"{c[0]}:{T.nm(c[1], c[0])}:{c[6]}" for c in don[:8]))
    for d in T.R["deaths"]:
        if d["p"] == p:
            print(f"  阵亡记录：t={d['t']} {d['kind']} 地 {d['terr']} 兵 {d['bal']} 峰值 {d['peak']} 身上的进攻 " + " ".join(f"{T.nm(a, d['t'])}:{tr}" for a, tr in d["attackers"]))


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1
    mid = args[0]
    T = Truth(mid)
    opt = lambda k, d=None: args[args.index(k) + 1] if k in args else d  # noqa: E731
    t0, t1 = int(opt("--t0", 0)), int(opt("--t1", 10 ** 9))
    if "--bot" in args:
        bot_detail(T, opt("--bot"), t0, t1, int(opt("--every", 30)))
        return 0
    if "--death" in args:
        death_detail(T, opt("--death"), int(opt("--span", 420)))
        return 0
    if "--pairs" in args:
        pairs_detail(T, opt("--pairs"), t0, t1)
        return 0
    if "--cmds" in args:
        cmds_detail(T, opt("--cmds"), t0, t1)
        return 0
    out = []
    for sec in (sec_TA, sec_TB, sec_TC, sec_TD, sec_TE, sec_TF, sec_TG, sec_TH, sec_TI, sec_TJ, sec_TK, sec_TL, sec_TM):
        sec(T, out)
    txt = "\n".join(out)
    with open(os.path.join(OUT, mid, "truth.txt"), "w", encoding="utf-8") as f:
        f.write(txt + "\n")
    if "--quiet" not in args:
        print(txt)
    else:
        print(f"写入 out/{mid}/truth.txt（{len(out)} 行）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
