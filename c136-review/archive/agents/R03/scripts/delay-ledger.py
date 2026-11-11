#!/usr/bin/env python3
"""delay-ledger.py — 「选点落地 / 发令→落地延迟 / 迟到落空 / 重发与同拍批」的硬账（广播 0007 第 2 节），
全部从重放缓存与影子策略缓存机械算出，不含判断。

用法：
  python3 scripts/delay-ledger.py A045 [--quiet]     # 写 out/dossier/A045-delay.txt 和 A045-delay-facts.json
  python3 scripts/delay-ledger.py A045 A067 …        # 多局依次

输入：out/cache/<mid>-shadow.json（shadow.mjs）、out/cache/<mid>-resim.json、对局包 in_game.log / spawn.csv / traj.csv / results.csv、
      out/cache/<mid>-replay.json（选点期指令）。

各节与口径：
  [L1] 选点：协调器求解了几轮；每个在场号「日志里收到的指派序列」对「录像里落地的选点指令序列」做保序对齐
       （录像同一拍内的指令是后发先列，引擎按列出的顺序处理，所以同拍两条里先发的那条最后生效）；
       终解坐标落地了没有、停在第几轮的旧坐标、开局时与队友是否叠在同一点、有没有 0 条落地。
  [L2] 发令→落地延迟（服务器落地拍 − 本地发令拍），按发令拍分 0~600 / 600~1500 / 1500~3000 / 3000+ 四段：
       条数、P50 / P90 / 最大、>30 拍和 >90 拍的条数；每个号（= 每个客户端）各段的中位数。
       对齐是 shadow.mjs 做的保序对齐，对「同 pct 同目标」的重复指令给出的是延迟下界。
  [L3] 漏斗：影子想发（含同拍被本地拒掉的）→ 本地受理（= 日志 cmds 计数）→ 录像落地 → 落地且引擎受理（非空令）。
  [L4] 迟到的代价：落地时目标已死、被引擎改成打无主地的指令（条数、兵、其中空令），其它空令；
       各段对无主地实际送出的兵 vs pairLog 里对无主地烧掉的兵（差额 = 退回余额的部分，含原本就打无主地的指令，是上界口径）。
  [L5] 确认窗内重发：上一条还没落地就把同一个决定再发（同目标同源码行、相邻发令 ≤10 拍并成一串）——
       同步串（首条延迟 ≤45 拍）首条花了多少、多花了多少；落后串（首条延迟 >45 拍）；
       同拍批：同一个号同一个服务器拍落地 ≥3 条的批次、每批抽走余额的比例、抽走 ≥50% 的批次。
"""
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict

import c136lib as L

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out")
NEUTRAL = 512
PERIODS = [(0, 600, "0~600"), (600, 1500, "600~1500"), (1500, 3000, "1500~3000"), (3000, 10 ** 9, "3000+")]
SOLVED_RE = re.compile(r"^(\d+)\t\[BACKEND-SPAWN-COORD\] Solved (\d+) bots in ([\d.]+)ms \(map=(\d+)x(\d+), minSep=(\d+)px, boss=([^)]*)\): (.*)$")
ENTRY_RE = re.compile(r"(?:\[[^\]]*\]\s*)*(.+?)\((\w+)\)->\((-?\d+),(-?\d+)\)\s*$")
TICK_RE = re.compile(r"^(\d+)\t\[([^\]]+)\] \[HL-TICK\] t=(\d+)")


def k(v):
    v = float(v)
    a = abs(v)
    if a >= 1e6:
        return f"{v / 1e6:.2f}M"
    if a >= 1e4:
        return f"{v / 1e3:.0f}k"
    if a >= 1e3:
        return f"{v / 1e3:.1f}k"
    return f"{v:.0f}"


def q(sorted_vals, p):
    """最近秩分位数：第 ceil(p·n) 个。"""
    if not sorted_vals:
        return None
    return sorted_vals[max(0, math.ceil(p * len(sorted_vals)) - 1)]


def period_of(t):
    for i, (a, b, _) in enumerate(PERIODS):
        if a <= t < b:
            return i
    return len(PERIODS) - 1


class Ledger:
    def __init__(self, mid):
        self.mid = mid
        self.S = json.load(open(os.path.join(OUT, "cache", f"{mid}-shadow.json")))
        self.R = json.load(open(os.path.join(OUT, "cache", f"{mid}-resim.json")))
        self.H = self.R["H"]
        self.W = self.R["W"]
        self.names = [str(n) for n in self.R["names"]]
        self.lines = []
        self.facts = {"matchId": mid, "strategy": self.S.get("strategy"), "periods": [p[2] for p in PERIODS]}
        self.sq = {b: v["id"] for b, v in self.R["squad"].items() if v["id"] >= 0}
        self.rep = L.load_replay(mid)

    def w(self, s=""):
        self.lines.append(s)

    def nm(self, p):
        if p is None or p < 0:
            return "?"
        if p >= NEUTRAL:
            return "无主地"
        if p >= self.H:
            return f"AI{p}"
        n = self.names[p]
        for tag in ("[APEX] ",):
            n = n.replace(tag, "")
        return f"{n[:14]}#{p}"

    # ---------------------------------------------------------------- L1
    def sec_spawn(self):
        self.w("[L1] 选点执行（指派 = 日志里该号收到的坐标；落地 = 录像里服务器执行的选点指令；坐标单位像素）")
        log_path = os.path.join(L.bundle_dir(self.mid), "in_game.log")
        rounds = []
        if os.path.exists(log_path):
            with open(log_path, encoding="utf-8", errors="replace") as f:
                for line in f:
                    m = SOLVED_RE.match(line.rstrip("\n"))
                    if not m:
                        continue
                    sol = {}
                    for ent in m.group(8).split(" | "):
                        e = ENTRY_RE.match(ent.strip())
                        if e:
                            sol[e.group(1).strip()] = (int(e.group(3)), int(e.group(4)))
                    rounds.append({"line": int(m.group(1)), "n": int(m.group(2)), "ms": float(m.group(3)), "minSep": int(m.group(6)), "boss": m.group(7), "sol": sol})
        spawn_rows = defaultdict(list)
        try:
            for r in L.load_spawn(self.mid):
                spawn_rows[r["bot"]].append(r)
        except Exception:
            pass
        cen = {}
        for p in range(self.H):
            bx = self.R["startBox"][p]
            if bx and bx[2] >= bx[0] and self.R["snapTerr"][0][p] > 0:
                cen[p] = ((bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2)
        execd = defaultdict(list)   # p -> [(tick, x, y)]，发令顺序（同拍内倒序）
        if self.rep:
            by_tick = defaultdict(lambda: defaultdict(list))
            for t, cid, pl, a, b in self.rep["cmds"]:
                if cid == 0:
                    by_tick[pl][t].append((a % self.W, a // self.W))
            for pl, d in by_tick.items():
                for t in sorted(d):
                    for xy in reversed(d[t]):
                        execd[pl].append((t, xy[0], xy[1]))
        steps = self.rep.get("spawnSteps") if self.rep else None
        fr = {"rounds": len(rounds), "spawnSteps": steps, "bots": {}}
        if rounds:
            distinct = len({tuple(sorted(r["sol"].items())) for r in rounds})
            names_solved = sorted(rounds[-1]["sol"])
            absent = [n for n in names_solved if n not in self.sq]
            fr.update({"distinctSolutions": distinct, "solvedBots": rounds[-1]["n"], "minSepFirst": rounds[0]["minSep"], "minSepLast": rounds[-1]["minSep"],
                       "boss": rounds[-1]["boss"], "absentNames": absent, "solveMsMedian": sorted(r["ms"] for r in rounds)[len(rounds) // 2]})
            self.w(f"  协调器求解 {len(rounds)} 轮（互不相同的解 {distinct} 个），每轮解 {rounds[-1]['n']} 个名字"
                   + (f"（其中 {('、'.join(absent))} 不在本房间）" if absent else "")
                   + f"；minSep {rounds[0]['minSep']}→{rounds[-1]['minSep']} 像素，boss={rounds[-1]['boss']}；选点期 {steps} 步")
        else:
            self.w(f"  日志里没有 [BACKEND-SPAWN-COORD] Solved 行（本局不走后端协调器，或日志缺这一段）；选点期 {steps} 步")
        final = rounds[-1]["sol"] if rounds else {}
        on_final = stale = zero = 0
        for bot, p in sorted(self.sq.items(), key=lambda x: x[1]):
            A = [(r["x"], r["y"], r["line"], r.get("role", "")) for r in spawn_rows.get(bot, [])]
            E = execd.get(p, [])
            # 保序对齐（从末尾往前，取最晚可行的指派）
            j = len(A) - 1
            last_idx = None
            matched = 0
            for (t, x, y) in reversed(E):
                jj = j
                while jj >= 0 and (A[jj][0], A[jj][1]) != (x, y):
                    jj -= 1
                if jj >= 0:
                    if last_idx is None:
                        last_idx = jj
                    matched += 1
                    j = jj - 1
            trailing = (len(A) - 1 - last_idx) if last_idx is not None else len(A)
            fin = final.get(bot)
            act = cen.get(p)
            row = {"assigned": len(A), "executed": len(E), "executedMatched": matched, "trailingUnexecuted": trailing,
                   "final": list(fin) if fin else None, "actual": [round(act[0]), round(act[1])] if act else None}
            desc = f"  {bot:<7}#{p:<3} 指派 {len(A):2d} 条、落地 {len(E):2d} 条（对上指派 {matched}）"
            if not E:
                zero += 1
                desc += "；0 条落地"
            if act is None:
                desc += "；开局没有地"
            if fin and act:
                d = math.hypot(act[0] - fin[0], act[1] - fin[1])
                row["distToFinal"] = round(d, 1)
                if d <= 6:
                    on_final += 1
                    desc += f"；在终解坐标 ({fin[0]},{fin[1]}) 上"
                    if trailing:
                        desc += f"（末尾 {trailing} 条指派没落地，位置恰好相同）"
                else:
                    stale += 1
                    # 实际位置对应第几轮的坐标
                    old = None
                    for ri in range(len(rounds) - 1, -1, -1):
                        c = rounds[ri]["sol"].get(bot)
                        if c and math.hypot(act[0] - c[0], act[1] - c[1]) <= 6:
                            old = ri
                            break
                    row["staleRound"] = (old + 1) if old is not None else None
                    owner = [b2 for b2, c in final.items() if b2 != bot and math.hypot(act[0] - c[0], act[1] - c[1]) <= 6]
                    row["finalOwnerOfMySpot"] = owner
                    desc += (f"；终解要它去 ({fin[0]},{fin[1]})，实际在 ({act[0]:.0f},{act[1]:.0f})（差 {d:.0f} 像素）"
                             + (f"＝第 {old + 1} 轮（倒数第 {len(rounds) - old} 轮）给它的坐标" if old is not None else "，不是任何一轮给它的坐标")
                             + (f"；这个点在终解里归 {'、'.join(owner)}" if owner else "")
                             + f"；末尾 {trailing} 条指派没落地")
            if act:
                near = None
                for b2, p2 in self.sq.items():
                    if p2 == p or p2 not in cen:
                        continue
                    d2 = math.hypot(cen[p2][0] - act[0], cen[p2][1] - act[1])
                    if near is None or d2 < near[0]:
                        near = (d2, b2)
                if near:
                    row["nearestSquad"] = [near[1], round(near[0], 1)]
                    if near[0] <= 12:
                        desc += f"；与 {near[1]} 叠在一起（相距 {near[0]:.0f} 像素）"
            if E:
                row["lastExecStep"] = E[-1][0]
                desc += f"；最后一条落地在选点期第 {E[-1][0]} 步"
            fr["bots"][bot] = row
            self.w(desc)
        stacks = set()
        for bot, row in fr["bots"].items():
            ns = row.get("nearestSquad")
            if ns and ns[1] <= 12:
                stacks.add(tuple(sorted((bot, ns[0]))))
        fr.update({"onFinal": on_final, "notOnFinal": stale, "zeroExecuted": zero, "stackPairs": [list(s) for s in sorted(stacks)],
                   "trailingUnexecutedBots": sum(1 for r in fr["bots"].values() if r["trailingUnexecuted"] > 0)})
        self.w(f"  小结：在场 {len(self.sq)} 个号——在终解坐标上 {on_final} 个，不在 {stale} 个，0 条落地 {zero} 个；"
               f"末尾有指派没落地的 {fr['trailingUnexecutedBots']} 个；开局叠点 {len(stacks)} 对" + ("（" + "、".join("+".join(s) for s in sorted(stacks)) + "）" if stacks else ""))
        self.facts["spawn"] = fr
        self.w()

    # ---------------------------------------------------------------- 对齐 pairs ↔ cmdLog 行
    def join_rows(self, b):
        """返回 rows[i] = cmdLog 行，与 b['match']['pairs'][i] 一一对应（shadow.mjs 的同拍倒序口径）。"""
        me = b["me"]
        ex = [c for c in self.R["cmdLog"] if c[1] == me and c[2] in (1, 2, 3)]
        groups = []
        for c in ex:
            if groups and groups[-1][0][0] == c[0]:
                groups[-1].append(c)
            else:
                groups.append([c])
        rows = []
        for g in groups:
            rows.extend(reversed(g))
        pairs = b["match"]["pairs"]
        if len(rows) != len(pairs):
            raise SystemExit(f"{self.mid} {me}: pairs {len(pairs)} 与 cmdLog {len(rows)} 条数不一致")
        for p, r in zip(pairs, rows):
            if p[0] != r[0] or p[2] != r[2] or p[3] != r[3]:
                raise SystemExit(f"{self.mid} {me}: 第 {p[0]} 拍对不上 {p} {r[:6]}")
        return rows

    # ---------------------------------------------------------------- L2
    def sec_lag(self):
        self.w("[L2] 发令→落地延迟（服务器落地拍 − 本地发令拍；按发令拍分段；陆攻/捐款/船 合计）")
        allp = [[] for _ in PERIODS]
        per_bot = {}
        for bot, b in self.S["bots"].items():
            mine = [[] for _ in PERIODS]
            for p in b["match"]["pairs"]:
                if p[1] < 0:
                    continue
                i = period_of(p[1])
                mine[i].append(p[0] - p[1])
                allp[i].append(p[0] - p[1])
            per_bot[bot] = mine
        rows = []
        for i, (_, _, name) in enumerate(PERIODS):
            v = sorted(allp[i])
            row = {"period": name, "n": len(v), "p50": q(v, 0.5), "p90": q(v, 0.9), "max": v[-1] if v else None, "min": v[0] if v else None,
                   "gt30": sum(1 for x in v if x > 30), "gt90": sum(1 for x in v if x > 90)}
            rows.append(row)
            self.w(f"  {name:<10} 落地 {row['n']:4d} 条：P50 {row['p50']}  P90 {row['p90']}  最大 {row['max']}  最小 {row['min']}；>30 拍 {row['gt30']} 条，>90 拍 {row['gt90']} 条" if v
                   else f"  {name:<10} 没有落地的指令")
        v = sorted(x for a in allp for x in a)
        tot = {"n": len(v), "p50": q(v, 0.5), "p90": q(v, 0.9), "max": v[-1] if v else None, "gt30": sum(1 for x in v if x > 30), "gt90": sum(1 for x in v if x > 90)}
        self.w(f"  整局       落地 {tot['n']:4d} 条：P50 {tot['p50']}  P90 {tot['p90']}  最大 {tot['max']}；>30 拍 {tot['gt30']} 条（{100 * tot['gt30'] / max(1, tot['n']):.1f}%），>90 拍 {tot['gt90']} 条")
        self.w("  每个号（= 每个客户端）各段：条数@中位/最大")
        fb = {}
        for bot in self.S["bots"]:
            cells = []
            fb[bot] = []
            for i in range(len(PERIODS)):
                s = sorted(per_bot[bot][i])
                fb[bot].append({"n": len(s), "p50": q(s, 0.5), "p90": q(s, 0.9), "max": s[-1] if s else None})
                cells.append(f"{len(s)}@{q(s, 0.5)}/{s[-1]}" if s else "—")
            self.w(f"    {bot:<7} " + "   ".join(f"{PERIODS[i][2]} {cells[i]}" for i in range(len(PERIODS))))
        self.facts["lag"] = {"byPeriod": rows, "total": tot, "byBot": fb}
        # 相对时钟：日志全局行序
        log_path = os.path.join(L.bundle_dir(self.mid), "in_game.log")
        rel = {}
        if os.path.exists(log_path):
            rws = []
            with open(log_path, encoding="utf-8", errors="replace") as f:
                for line in f:
                    m = TICK_RE.match(line)
                    if m and m.group(2) in self.sq:
                        rws.append((int(m.group(1)), m.group(2), int(m.group(3))))
            rws.sort()
            front = 0
            for seq, bot, t in rws:
                front = max(front, t)
                d = front - t
                r = rel.setdefault(bot, {"max": 0, "at": None, "rows": 0, "ge90": 0})
                r["rows"] += 1
                if d >= 90:
                    r["ge90"] += 1
                if d > r["max"]:
                    r["max"], r["at"] = d, t
            worst = sorted(((r["max"], b_) for b_, r in rel.items()), reverse=True)
            self.w("  队内相对时钟（日志全局行序：某号打出 t=T 这一行时，队里已经打出的最大 t 减 T；精度 90 拍，看不出全队一起落后）："
                   + ("；".join(f"{b_} 最大落后 {mx} 拍（本地 t={rel[b_]['at']}，≥90 拍的行 {rel[b_]['ge90']}/{rel[b_]['rows']}）" for mx, b_ in worst if mx >= 90) or "没有哪个号落后队友 ≥90 拍"))
        self.facts["lag"]["relativeClock"] = rel
        # 出局时本地拍 − 服务器拍
        try:
            res = {r["bot"]: r for r in L.load_results(self.mid)}
        except Exception:
            res = {}
        ends = []
        for bot, p in self.sq.items():
            r = res.get(bot)
            dt = self.R["deathT"][p]
            if r and r.get("event") == "died" and dt >= 0:
                ends.append((bot, int(r["tick"]) - dt))
        if ends:
            self.w("  出局时 本地拍 − 服务器拍（results.csv 的本地拍 对 重放里的出局拍）：" + "、".join(f"{b_} {d:+d}" for b_, d in ends))
            self.facts["lag"]["localMinusServerAtDeath"] = dict(ends)
        self.w()

    # ---------------------------------------------------------------- L3
    def sec_funnel(self):
        self.w("[L3] 漏斗（按本地发令拍分段）：想发 → 本地受理 → 录像落地 → 落地且非空令；括号里是 陆攻/捐款/船")
        fun = [dict(want=Counter(), acc=Counter(), land=Counter(), eff=Counter()) for _ in PERIODS]
        for bot, b in self.S["bots"].items():
            cm, ex = b["cmds"], b["match"]["execOf"]
            effective = {}
            issued_idx = [i for i, c in enumerate(cm) if c[4] == 1 and c[1] <= 3]
            for p in b["match"]["pairs"]:
                if p[6] >= 0:
                    effective[issued_idx[p[6]]] = bool(p[5])
            for i, c in enumerate(cm):
                if c[1] > 3:
                    continue
                f = fun[period_of(c[0])]
                f["want"][c[1]] += 1
                if c[4] == 1:
                    f["acc"][c[1]] += 1
                    if ex[i] >= 0:
                        f["land"][c[1]] += 1
                        if effective.get(i):
                            f["eff"][c[1]] += 1
        rows = []
        def cell(cn):
            return f"{sum(cn.values())}（{cn[1]}/{cn[2]}/{cn[3]}）"
        for i, (_, _, name) in enumerate(PERIODS):
            f = fun[i]
            rows.append({"period": name, **{kk: {"total": sum(v.values()), "attack": v[1], "donate": v[2], "boat": v[3]} for kk, v in f.items()}})
            self.w(f"  {name:<10} 想发 {cell(f['want'])} → 受理 {cell(f['acc'])} → 落地 {cell(f['land'])} → 有效 {cell(f['eff'])}")
        tot = {kk: sum(sum(f[kk].values()) for f in fun) for kk in ("want", "acc", "land", "eff")}
        self.w(f"  整局       想发 {tot['want']} → 受理 {tot['acc']} → 落地 {tot['land']} → 有效 {tot['eff']}"
               f"；本地拒掉 {tot['want'] - tot['acc']}（同拍只收一条/目标不相邻等），受理后没落地 {tot['acc'] - tot['land']}（捐款撞额度、页面落后丢失、对局结束）")
        # 日志 cmds 计数对照
        try:
            traj = L.load_traj(self.mid)
        except Exception:
            traj = {}
        chk = []
        for bot, b in self.S["bots"].items():
            acc = sum(1 for c in b["cmds"] if c[4] == 1 and c[1] <= 3)
            real = max((int(float(r["cmds"])) for r in traj.get(bot, []) if r.get("cmds") not in (None, "")), default=None)
            landed = sum(1 for e in b["match"]["execOf"] if e >= 0)
            chk.append((bot, acc, real, landed))
        self.w("  逐号 影子受理 / 日志 cmds 最大值 / 录像落地：" + "；".join(f"{b_} {a}/{r}/{l_}" for b_, a, r, l_ in chk))
        self.facts["funnel"] = {"byPeriod": rows, "total": tot, "byBot": {b_: {"shadowAccepted": a, "logCmdsMax": r, "replayLanded": l_} for b_, a, r, l_ in chk}}
        self.w()

    # ---------------------------------------------------------------- L4
    def sec_late(self):
        self.w("[L4] 迟到的代价（按本地发令拍分段；只看陆攻）")
        st = [Counter() for _ in PERIODS]
        ex_list = []
        for bot, b in self.S["bots"].items():
            rows = self.join_rows(b)
            for p, r in zip(b["match"]["pairs"], rows):
                if p[2] != 1 or p[1] < 0:
                    continue
                c = st[period_of(p[1])]
                lag = p[0] - p[1]
                want = p[7]
                ok = bool(r[5])
                troops = r[6] if ok else 0
                kind = "neutral" if want >= NEUTRAL else ("ai" if want >= self.H else "human")
                c[f"n_{kind}"] += 1
                c[f"troops_{kind}"] += troops
                if not ok:
                    c[f"noop_{kind}"] += 1
                if lag > 30:
                    c["late30"] += 1
                    c["late30Troops"] += troops
                if p[4] >= NEUTRAL and want < NEUTRAL:
                    c["dead"] += 1
                    c["deadTroops"] += troops
                    c[f"dead_{kind}"] += 1
                    if not ok:
                        c["deadNoop"] += 1
                    if lag > 30:
                        c["deadLate30"] += 1
                    ex_list.append({"bot": bot, "intent": p[1], "exec": p[0], "lag": lag, "want": self.nm(want), "troops": troops, "ok": ok})
                if p[4] >= NEUTRAL and ok:
                    c["toNeutralTroops"] += troops
                    c["toNeutralFee"] += r[7]
        # pairLog：对无主地烧掉的兵（落地拍口径）
        sqids = set(self.sq.values())
        burnt = [0] * len(PERIODS)
        tiles = [0] * len(PERIODS)
        for r in self.R["pairLog"]:
            if r[1] in sqids and r[2] >= NEUTRAL:
                i = period_of(max(0, r[0] - 15))
                burnt[i] += r[4]
                tiles[i] += r[3]
        out = []
        for i, (_, _, name) in enumerate(PERIODS):
            c = st[i]
            n_all = c["n_neutral"] + c["n_ai"] + c["n_human"]
            row = {"period": name, "attacks": n_all, "toAI": c["n_ai"], "toHuman": c["n_human"], "toNeutral": c["n_neutral"],
                   "troopsAI": c["troops_ai"], "troopsHuman": c["troops_human"], "troopsNeutral": c["troops_neutral"],
                   "late30": c["late30"], "late30Troops": c["late30Troops"],
                   "deadTarget": c["dead"], "deadTargetAI": c["dead_ai"], "deadTargetHuman": c["dead_human"], "deadTargetTroops": c["deadTroops"],
                   "deadTargetNoop": c["deadNoop"], "deadTargetLate30": c["deadLate30"],
                   "noopOther": c["noop_ai"] + c["noop_human"] + c["noop_neutral"] - c["deadNoop"],
                   "neutralSentTroops": c["toNeutralTroops"], "neutralBurnt": burnt[i], "neutralTiles": tiles[i]}
            out.append(row)
            if not n_all:
                self.w(f"  {name:<10} 没有落地的陆攻")
                continue
            self.w(f"  {name:<10} 落地陆攻 {n_all} 条（瞄准 AI {c['n_ai']} 条 {k(c['troops_ai'])} 兵、真人 {c['n_human']} 条 {k(c['troops_human'])}、无主地 {c['n_neutral']} 条 {k(c['troops_neutral'])}）；"
                   f"延迟 >30 拍 {c['late30']} 条 {k(c['late30Troops'])} 兵；"
                   f"落地时目标已死被改成打无主地 {c['dead']} 条（AI {c['dead_ai']}、真人 {c['dead_human']}；{k(c['deadTroops'])} 兵，占这一段瞄准 AI/真人兵力的 {100 * c['deadTroops'] / max(1, c['troops_ai'] + c['troops_human']):.1f}%；其中空令 {c['deadNoop']}、延迟 >30 拍的 {c['deadLate30']}）；"
                   f"其它空令 {row['noopOther']}")
            self.w(f"             对无主地：实际送出 {k(c['toNeutralTroops'])} 兵（含上面改道的），pairLog 记烧掉 {k(burnt[i])} 兵、得 {tiles[i]} 格"
                   + (f" → 至少 {k(c['toNeutralTroops'] - burnt[i])} 兵没烧掉、退回余额（{100 * (c['toNeutralTroops'] - burnt[i]) / max(1, c['toNeutralTroops']):.0f}%）" if c["toNeutralTroops"] > burnt[i] else ""))
        ex_list.sort(key=lambda e: -e["troops"])
        if ex_list:
            self.w("  目标已死改道的指令（按兵力前 8）：" + "；".join(f"{e['bot']} 发 {e['intent']} 落 {e['exec']}（+{e['lag']}）→{e['want']} {k(e['troops'])}{'' if e['ok'] else ' 空令'}" for e in ex_list[:8]))
        self.facts["late"] = {"byPeriod": out, "deadTargetTop": ex_list[:12]}
        self.w()

    # ---------------------------------------------------------------- L5
    def sec_reissue(self):
        self.w("[L5] 确认窗内重发 与 同拍批（陆攻、目标非无主地；同目标同源码行、相邻发令 ≤10 拍并成一串；按串的首条发令拍分段）")
        st = [Counter() for _ in PERIODS]
        big = []
        for bot, b in self.S["bots"].items():
            cm, ex = b["cmds"], b["match"]["execOf"]
            rows = self.join_rows(b)
            issued_idx = [i for i, c in enumerate(cm) if c[4] == 1 and c[1] <= 3]
            row_of = {}
            for p, r in zip(b["match"]["pairs"], rows):
                if p[6] >= 0:
                    row_of[issued_idx[p[6]]] = r
            bursts = []
            for i, c in enumerate(cm):
                if c[1] != 1 or c[4] != 1 or c[3] >= NEUTRAL:
                    continue
                site = c[7].split(">")[-4] if c[7].count(">") >= 3 else c[7]
                key = (c[3], site)
                if bursts and bursts[-1]["key"] == key and c[0] - bursts[-1]["idx"][-1][1] <= 10:
                    bursts[-1]["idx"].append((i, c[0]))
                else:
                    bursts.append({"key": key, "idx": [(i, c[0])]})
            for bu in bursts:
                n = len(bu["idx"])
                c = st[period_of(bu["idx"][0][1])]
                c["strings"] += 1
                c["cmds"] += n
                if n < 2:
                    continue
                exs = [(ex[i], t, i) for i, t in bu["idx"] if ex[i] >= 0]
                if not exs:
                    c["deadStrings"] += 1
                    c["deadCmds"] += n
                    continue
                first_exec = min(e[0] for e in exs)
                first = min(exs)
                lag = first[0] - first[1]
                before = sorted((e, t, i) for (e, t, i) in exs if t < first_exec)
                if lag > 45:
                    c["lagStrings"] += 1
                    c["lagIssued"] += n
                    c["lagExecuted"] += len(exs)
                    sp = sum((row_of[i][6] + row_of[i][7]) for (_, _, i) in exs if i in row_of and row_of[i][5])
                    c["lagSpent"] += sp
                    continue
                if len(before) < 2:
                    continue
                # 「首条」按服务器处理顺序算：最早落地的那一拍里余额最大（= 最先被处理）的那条。
                # 只发一条的话送出的就是这个数；同拍内先发的那条反而最后处理、按剩下的余额算。
                rws = [row_of[i] for (_, _, i) in before if i in row_of and row_of[i][5]]
                if not rws:
                    continue
                fr_ = min(rws, key=lambda r: (r[0], -r[8]))
                first_sp = fr_[6] + fr_[7]
                total_sp = sum(r[6] + r[7] for r in rws)
                b0 = fr_[8]
                c["syncStrings"] += 1
                c["syncCmds"] += len(before)
                c["syncFirst"] += first_sp
                c["syncExtra"] += total_sp - first_sp
                c["syncExtraCmds"] += len(before) - 1
                big.append({"bot": bot, "t0": bu["idx"][0][1], "target": self.nm(bu["key"][0]), "site": bu["key"][1], "n": len(before), "first": first_sp, "extra": total_sp - first_sp,
                            "B0": b0, "fracOfB0": round(total_sp / b0, 3) if b0 else None})
        out = []
        for i, (_, _, name) in enumerate(PERIODS):
            c = st[i]
            out.append({"period": name, **{kk: c[kk] for kk in ("strings", "cmds", "syncStrings", "syncCmds", "syncFirst", "syncExtra", "syncExtraCmds", "lagStrings", "lagIssued", "lagExecuted", "lagSpent", "deadStrings", "deadCmds")}})
            if not c["strings"]:
                self.w(f"  {name:<10} 没有对 AI/真人的陆攻")
                continue
            self.w(f"  {name:<10} 决定 {c['strings']} 个、发令 {c['cmds']} 条；确认窗内重发的同步串 {c['syncStrings']} 串 {c['syncCmds']} 条：首条花 {k(c['syncFirst'])}，多花 {k(c['syncExtra'])}（{c['syncExtraCmds']} 条）；"
                   f"落后串（首条延迟 >45 拍）{c['lagStrings']} 串、发 {c['lagIssued']} 成 {c['lagExecuted']}、共花 {k(c['lagSpent'])}；整串没落地 {c['deadStrings']} 串 {c['deadCmds']} 条")
        tot = Counter()
        for c in st:
            tot.update(c)
        self.w(f"  整局       同步串 {tot['syncStrings']} 串 {tot['syncCmds']} 条：首条 {k(tot['syncFirst'])}，多花 {k(tot['syncExtra'])}（{tot['syncExtraCmds']} 条，是首条的 {tot['syncExtra'] / max(1, tot['syncFirst']):.2f} 倍）；落后串 {tot['lagStrings']} 串")
        big.sort(key=lambda e: -e["extra"])
        if big:
            self.w("  多花最多的 6 串：" + "；".join(f"{e['bot']} {e['t0']} 拍→{e['target']} {e['n']} 条 首 {k(e['first'])} 多 {k(e['extra'])}（占余额 {100 * e['fracOfB0']:.0f}%）" if e["fracOfB0"] is not None
                                           else f"{e['bot']} {e['t0']} 拍→{e['target']} {e['n']} 条 首 {k(e['first'])} 多 {k(e['extra'])}" for e in big[:6]))
        # 同拍批
        bat = [Counter() for _ in PERIODS]
        worst = []
        for bot, p in self.sq.items():
            groups = defaultdict(list)
            for c in self.R["cmdLog"]:
                if c[1] == p and c[2] in (1, 3) and c[5]:
                    groups[c[0]].append(c)
            for t, g in groups.items():
                if len(g) < 2:
                    continue
                b0 = max(c[8] for c in g)
                sp = sum(c[6] + c[7] for c in g)
                fr = sp / max(1, b0)
                cc = bat[period_of(t)]
                if len(g) == 2:
                    cc["pairs"] += 1
                    continue
                cc["batches"] += 1
                cc["cmds"] += len(g)
                cc["spent"] += sp
                cc["maxN"] = max(cc["maxN"], len(g))
                if fr >= 0.5:
                    cc["drain50"] += 1
                    cc["drain50Spent"] += sp
                if fr >= 0.8:
                    cc["drain80"] += 1
                worst.append({"bot": bot, "t": t, "n": len(g), "spent": sp, "B0": b0, "frac": round(fr, 3)})
        bout = []
        for i, (_, _, name) in enumerate(PERIODS):
            c = bat[i]
            bout.append({"period": name, **{kk: c[kk] for kk in ("pairs", "batches", "cmds", "spent", "maxN", "drain50", "drain50Spent", "drain80")}})
            self.w(f"  {name:<10} 同一服务器拍落地 2 条的 {c['pairs']} 次；≥3 条的批 {c['batches']} 个（共 {c['cmds']} 条、最多一批 {c['maxN']} 条、花 {k(c['spent'])}），其中抽走余额 ≥50% 的 {c['drain50']} 批（{k(c['drain50Spent'])}）、≥80% 的 {c['drain80']} 批")
        worst.sort(key=lambda e: (-e["frac"], -e["spent"]))
        if worst:
            self.w("  抽得最狠的 6 批：" + "；".join(f"{e['bot']} {e['t']} 拍 {e['n']} 条 花 {k(e['spent'])}/余额 {k(e['B0'])}（{100 * e['frac']:.0f}%）" for e in worst[:6]))
        self.facts["reissue"] = {"byPeriod": out, "total": {kk: tot[kk] for kk in ("strings", "cmds", "syncStrings", "syncCmds", "syncFirst", "syncExtra", "syncExtraCmds", "lagStrings", "lagIssued", "lagExecuted", "lagSpent", "deadStrings", "deadCmds")},
                                 "top": big[:10]}
        self.facts["sameTickBatches"] = {"byPeriod": bout, "worst": worst[:10]}
        self.w()

    def run(self):
        self.w(f"# {self.mid} 延迟账（delay-ledger.py；策略 {self.S.get('strategy')}；编队 {len(self.sq)} 个号；重放到 {self.R['endTick']} 拍）")
        self.w()
        self.sec_spawn()
        self.sec_lag()
        self.sec_funnel()
        self.sec_late()
        self.sec_reissue()
        os.makedirs(os.path.join(OUT, "dossier"), exist_ok=True)
        with open(os.path.join(OUT, "dossier", f"{self.mid}-delay.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(self.lines) + "\n")
        with open(os.path.join(OUT, "dossier", f"{self.mid}-delay-facts.json"), "w", encoding="utf-8") as f:
            json.dump(self.facts, f, ensure_ascii=False)
        return self.lines


def main():
    quiet = "--quiet" in sys.argv
    mids = [a for a in sys.argv[1:] if not a.startswith("--")]
    for mid in mids:
        lines = Ledger(mid).run()
        if not quiet:
            print("\n".join(lines))
        else:
            print(f"{mid}: 已写 out/dossier/{mid}-delay.txt（{len(lines)} 行）")


if __name__ == "__main__":
    main()
