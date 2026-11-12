#!/usr/bin/env python3
"""shadow-digest.py — 把 shadow.mjs 的影子策略输出整理成可读的「决策—执行」摘要。

用法：
  python3 shadow-digest.py A051            # 写 out/dossier/A051-shadow.txt 和 A051-shadow-facts.json
  python3 shadow-digest.py A051 --bot talon5 --raw 1500 2100   # 逐条列出某号某段本地拍的发令与成交

输入：out/cache/<mid>-shadow.json（shadow.mjs）、out/cache/<mid>-resim.json（resim.mjs）、策略源码（取行文本）。

各节：
  [S0] 校验：影子与线上日志的一致率（HL-TICK 的 nb/neut/cmds/boats、HL-DISPATCH、HL-OPENING、录像成交对齐）
  [S1] 执行层：每 300 本地拍 发令/成交/丢弃、成交延迟；全队汇总
  [S2] 决策串：连续同一「种类+目标+源码行」的发令并成一串——发了几条、成交几条（落在哪些服务器拍）、丢了几条
  [S3] 落地时的错位：目标已死改成中立、空令、同一决定重复落地的清仓批
  [S4] 不出手的窗口（t≥1500 连续 ≥60 拍无发令）：当时最便宜报价 c、门槛 worth、余额/密度
  [S5] isNoFullSend / shadowQuota 的变化（核对「7 拍窗口误锁」假设）
  [S6] 上一条还没成交就重发（同步串 / 落后串）
  [S7] 同拍挤占：同一决策拍先发的一条占掉指令位，后面那条本地被拒（每拍只收 1 条）
"""
import json
import os
import statistics
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out")
DATA = os.environ.get("C136_DATA", "/agent/repos/c136-data")
NEUTRAL = 512


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


class Digest:
    def __init__(self, mid):
        self.mid = mid
        self.S = json.load(open(os.path.join(OUT, "cache", f"{mid}-shadow.json")))
        self.R = json.load(open(os.path.join(OUT, "cache", f"{mid}-resim.json")))
        self.H = self.R["H"]
        self.names = self.R["names"]
        self.teams = self.R["teams"]
        self.src = open(os.path.join(DATA, "src/strategy", self.S["strategy"]), encoding="utf-8").read().split("\n")
        self.lines = []
        self.facts = {"matchId": mid, "strategy": self.S["strategy"], "bots": {}}
        self.sqid = {v["id"]: b for b, v in self.R["squad"].items() if v["id"] >= 0}

    def nm(self, q):
        if q is None or q < 0:
            return "?"
        if q >= NEUTRAL:
            return "中立"
        if q >= self.H:
            return f"AI{q}"
        if q in self.sqid:
            return self.sqid[q]
        n = self.names[q].strip()[:11]
        return f"{n}#{q}T{self.teams[q]}"

    def w(self, s=""):
        self.lines.append(s)

    def site(self, path):
        """发令的源码位置：调用栈里最靠近 g.attack/g.donate 的那个非 send 帧。"""
        fr = path.split(">") if path else []
        fr2 = [f for f in fr if not f.startswith("send:")]
        return fr2[-1] if fr2 else (fr[-1] if fr else "?")

    def site_text(self, site):
        try:
            ln = int(site.split(":")[1])
            return self.src[ln - 1].strip()[:90]
        except Exception:
            return ""

    # ---------- S0 ----------
    def sec_check(self):
        self.w(f"[S0] 影子策略校验（{self.S['strategy']}；每拍只收 1 条指令={not self.S['multi']}）——影子=同一份源码在重放的真实状态上逐拍运行")
        v = self.S["validate"]
        self.w(f"  重放状态核对 traj：{v['bothExact']}/{v['rows']} 行地、兵都一致")
        if self.S.get("minLat", 6) != 6:
            self.w(f"  成交对齐的最小延迟下界 = {self.S['minLat']} 拍（默认 6；本局有 5 拍落地的指令，按默认值对齐会整段串位）")
        tot = Counter()
        for bot, b in self.S["bots"].items():
            c = b["check"]
            t = c["tick"]
            m = b["match"]
            self.w(f"  {bot:7s} HL-TICK {t['rows']:3d} 行：nb 一致 {t['nb']} neut {t['neut']} cmds {t['cmds']} boats {t['boats']}"
                   + (f"（cmds 首差 @t={t['firstCmdsDiff'][0]}：日志 {t['firstCmdsDiff'][1]} 影子 {t['firstCmdsDiff'][2]}）" if t["firstCmdsDiff"] else "")
                   + f" | 调度 日志 {c['dispatch']['log']} 影子 {c['dispatch']['shadow']} 完全相同 {c['dispatch']['same']}"
                   + f" | 开局 日志 {c['opening']['log']} 相同 {c['opening']['same']}"
                   + f" | 录像成交 {m['exec']} 条中 {m['matched']} 条对上影子发令"
                   + (f" | 影子报错 @{b['error']['t']}" if b["error"] else ""))
            tot["rows"] += t["rows"]; tot["cmds"] += t["cmds"]; tot["nb"] += t["nb"]; tot["neut"] += t["neut"]
            tot["dl"] += c["dispatch"]["log"]; tot["ds"] += c["dispatch"]["same"]
            tot["ol"] += c["opening"]["log"]; tot["os"] += c["opening"]["same"]
            tot["ex"] += m["exec"]; tot["mt"] += m["matched"]
        self.w(f"  合计：HL-TICK {tot['rows']} 行 cmds 一致 {tot['cmds']}、nb 一致 {tot['nb']}、neut 一致 {tot['neut']}；调度 {tot['ds']}/{tot['dl']}；开局 {tot['os']}/{tot['ol']}；成交对上 {tot['mt']}/{tot['ex']}")
        self.facts["check"] = dict(tot)
        self.w()

    # ---------- S1 ----------
    def sec_exec(self):
        self.w("[S1] 执行层：每 300 本地拍 发令/成交/丢弃 与成交延迟（服务器落地拍 − 本地发令拍；正常 7~20 拍）")
        team = defaultdict(lambda: [0, 0, []])
        for bot, b in self.S["bots"].items():
            cm, ex = b["cmds"], b["match"]["execOf"]
            rows = []
            for w0 in range(0, 9000, 300):
                idx = [i for i, c in enumerate(cm) if c[4] == 1 and c[1] <= 3 and w0 <= c[0] < w0 + 300]
                if not idx:
                    continue
                lags = [ex[i] - cm[i][0] for i in idx if ex[i] >= 0]
                rows.append((w0, len(idx), len(lags), lags))
                team[w0][0] += len(idx); team[w0][1] += len(lags); team[w0][2] += lags
            issued = sum(r[1] for r in rows); done = sum(r[2] for r in rows)
            alll = [x for r in rows for x in r[3]]
            self.w(f"  {bot:7s} 发 {issued} 成 {done} 丢 {issued - done}（{100 * (issued - done) / max(1, issued):.0f}%）"
                   + (f" 延迟中位 {int(statistics.median(alll))} 最大 {max(alll)}" if alll else "")
                   + (f"；页面中途退出：results.csv 状态拍 {b.get('stopResultsT')}，日志最后一行在本地 {b.get('lastLogT')} 拍，影子跑到 {b['stopT'] - 1} 拍" if b["stopT"] else ""))
            if b["stopT"]:
                self.facts["bots"].setdefault(bot, {})["stop"] = {"resultsTick": b.get("stopResultsT"), "lastLogTick": b.get("lastLogT"), "shadowUntil": b["stopT"] - 1}
            self.w("          " + "  ".join(
                f"{r[0]}:{r[1]}/{r[2]}" + (f"@{int(statistics.median(r[3]))}" if r[3] else "@—") for r in rows))
            self.facts["bots"].setdefault(bot, {})["exec"] = {
                "issued": issued, "executed": done, "dropped": issued - done,
                "lagMedian": int(statistics.median(alll)) if alll else None, "lagMax": max(alll) if alll else None,
                "windows": [[r[0], r[1], r[2], int(statistics.median(r[3])) if r[3] else None] for r in rows]}
        self.w("  全队（窗口: 发/成 @延迟中位）： " + "  ".join(
            f"{w0}:{v[0]}/{v[1]}" + (f"@{int(statistics.median(v[2]))}" if v[2] else "@—") for w0, v in sorted(team.items())))
        self.facts["teamExec"] = [[w0, v[0], v[1], int(statistics.median(v[2])) if v[2] else None, max(v[2]) if v[2] else None] for w0, v in sorted(team.items())]
        self.w()

    # ---------- S2 ----------
    def runs_of(self, b):
        cm, ex = b["cmds"], b["match"]["execOf"]
        runs = []
        for i, c in enumerate(cm):
            if c[1] > 3:
                continue
            key = (c[1], c[3] if c[1] != 3 else 0, self.site(c[7]), c[4])
            if runs and runs[-1]["key"] == key and c[0] - runs[-1]["t1"] <= 60:
                r = runs[-1]
            else:
                r = {"key": key, "t0": c[0], "t1": c[0], "n": 0, "ex": [], "pcts": [], "B0": c[5], "L0": c[6], "path": c[7]}
                runs.append(r)
            r["t1"] = c[0]; r["n"] += 1; r["pcts"].append(c[2]); r["B1"] = c[5]; r["L1"] = c[6]
            if ex[i] >= 0:
                r["ex"].append(ex[i])
        return runs

    def sec_runs(self):
        self.w("[S2] 决策串（本地拍；连续同一 种类+目标+源码行 并成一串）：发 n 条 → 成交 m 条（服务器拍×条数）")
        kinds = {1: "攻", 2: "捐", 3: "船"}
        site_cnt = Counter()
        for bot, b in self.S["bots"].items():
            self.w(f"  -- {bot}#{b['me']}")
            fr = []
            for r in self.runs_of(b):
                kind, tgt, site, ok = r["key"]
                site_cnt[site] += r["n"]
                exs = Counter(r["ex"])
                exs_s = " ".join(f"{t}×{n}" for t, n in sorted(exs.items())) if exs else "—"
                pc = r["pcts"]
                pcs = f"{pc[0]}" if len(set(pc)) == 1 else f"{pc[0]}→{pc[-1]}（{min(pc)}~{max(pc)}）"
                tgt_s = self.nm(tgt) if kind != 3 else "船"
                line = (f"     {r['t0']:5d}-{r['t1']:<5d} {kinds[kind]} {tgt_s:22s} pct {pcs:22s} 发{r['n']:3d}"
                        + (f" 成{len(r['ex']):3d} [{exs_s}]" if ok else " （本地就被拒：目标不相邻/已有队列/同拍已发）")
                        + f" | 兵 {k(r['B0'])}→{k(r['B1'])} 地 {r['L0']}→{r['L1']} | {site}")
                self.w(line)
                fr.append({"t0": r["t0"], "t1": r["t1"], "kind": kind, "target": tgt, "targetName": tgt_s, "n": r["n"], "ok": ok,
                           "executed": len(r["ex"]), "execTicks": sorted(exs.items()), "pct0": pc[0], "pct1": pc[-1], "B0": r["B0"], "B1": r["B1"],
                           "L0": r["L0"], "L1": r["L1"], "site": site})
            self.facts["bots"].setdefault(bot, {})["runs"] = fr
        self.w("  源码发令点（全队发令条数）：")
        for site, n in site_cnt.most_common(14):
            self.w(f"     {site:22s} ×{n:4d}  {self.site_text(site)}")
        self.facts["sites"] = [[s, n, self.site_text(s)] for s, n in site_cnt.most_common(20)]
        self.w()

    # ---------- S3 ----------
    def sec_misfire(self):
        self.w("[S3] 落地时的错位（按成交指令统计）")
        tot = Counter()
        for bot, b in self.S["bots"].items():
            c = Counter()
            pairs = b["match"]["pairs"]
            byS = defaultdict(list)
            for p in pairs:
                c["exec"] += 1
                if p[1] < 0:
                    c["unmatched"] += 1
                    continue
                lag = p[0] - p[1]
                if lag > 30:
                    c["late30"] += 1
                if lag > 150:
                    c["late150"] += 1
                if p[2] == 1 and p[4] == NEUTRAL and p[7] != NEUTRAL:
                    c["deadTarget"] += 1
                    if not p[5]:
                        c["deadTargetNoop"] += 1
                elif p[2] == 1 and not p[5]:
                    c["noop"] += 1
                byS[p[0]].append(p)
            dup = 0
            for S_, ps in byS.items():
                sig = Counter((p[2], p[7]) for p in ps if p[1] >= 0)
                for _, n in sig.items():
                    if n >= 3:
                        dup += n - 1
            c["dupInBatch"] = dup
            self.w(f"  {bot:7s} 成交 {c['exec']}：延迟>30 拍 {c['late30']}，>150 拍 {c['late150']}；目标已死被改成中立 {c['deadTarget']}（其中空令 {c['deadTargetNoop']}）；其它空令 {c['noop']}；同批同一决定的重复落地 {c['dupInBatch']}")
            for kk, v in c.items():
                tot[kk] += v
            self.facts["bots"].setdefault(bot, {})["misfire"] = dict(c)
        self.w(f"  全队：成交 {tot['exec']}，延迟>30 拍 {tot['late30']}（{100 * tot['late30'] / max(1, tot['exec']):.0f}%），>150 拍 {tot['late150']}；目标已死改中立 {tot['deadTarget']}；重复落地 {tot['dupInBatch']}")
        self.facts["misfire"] = dict(tot)
        self.w()

    # ---------- S4 ----------
    def sec_holds(self):
        self.w("[S4] 不出手的窗口（本地拍 t≥1500，连续 ≥60 拍没有任何发令）：窗口首/末的余额密度、最便宜报价与门槛")
        for bot, b in self.S["bots"].items():
            acts = [a for a in b["acts"] if a[0] >= 1500]
            if not acts:
                continue
            out = []
            cur = None
            for a in acts:
                if a[10] == 0:
                    if cur is None:
                        cur = [a, a]
                    else:
                        cur[1] = a
                else:
                    if cur is not None and cur[1][0] - cur[0][0] >= 60:
                        out.append(cur)
                    cur = None
            if cur is not None and cur[1][0] - cur[0][0] >= 60:
                out.append(cur)
            if not out:
                continue
            self.w(f"  -- {bot}")
            fr = []
            for a0, a1 in out:
                def desc(a):
                    d = a[1] / max(1, a[2])
                    top = a[9][0] if a[9] else None
                    s = f"兵 {k(a[1])} 密 {d:.0f} nb={a[3]} neut={a[4]} 报价数 {a[8]}"
                    if top:
                        s += f" 最便宜 {self.nm(top[0])} c={top[1]} need={k(top[2])}" + ("" if not top[3] else (" 真人" + ("/濒死" if top[4] else "") + ("/失血" if top[5] else "") + ("/打我" if top[6] else "") + ("/拥挤" if top[8] else "")))
                    s += f" worth={a[11]} over={a[12]} safe={k(a[13]) if a[13] >= 0 else '—'}"
                    return s
                self.w(f"     {a0[0]:5d}-{a1[0]:<5d}（{a1[0] - a0[0]} 拍） 首：{desc(a0)}")
                self.w(f"                           末：{desc(a1)}")
                fr.append({"t0": a0[0], "t1": a1[0], "B0": a0[1], "B1": a1[1], "L0": a0[2], "L1": a1[2], "nb0": a0[3], "nOffers0": a0[8],
                           "top0": a0[9][0] if a0[9] else None, "worth0": a0[11], "over0": a0[12], "top1": a1[9][0] if a1[9] else None, "worth1": a1[11], "over1": a1[12]})
            self.facts["bots"].setdefault(bot, {})["holds"] = fr
        self.w()

    # ---------- S5 ----------
    def sec_nfs(self):
        self.w("[S5] isNoFullSend（发兵限额标志，Policy.updateShadowQuota L3821-3834）在影子里的翻转，以及被 Policy.send L3844 守卫挡掉的出手：")
        any_ = False
        nflip = 0
        for bot, b in self.S["bots"].items():
            f = b.get("nfsFlip")
            blk = b.get("blocked") or []
            if not f and not blk:
                continue
            any_ = True
            line = f"  {bot:7s}"
            fact = {"flip": None, "blocked": len(blk)}
            if f:
                nflip += 1
                pc = f.get("pending") or {}
                me = b["me"]
                # 在待核对窗口里真正落地、让余额下降的是哪条指令
                landed = [c for c in self.R["cmdLog"] if c[1] == me and c[2] in (1, 2, 3) and c[5] and (pc.get("t", 0) - 1) <= c[0] < f["t"]]
                issued_t = pc.get("t", 0) - 1
                drop = (pc.get("bal0", 0) - f["B"])
                line += (f" t={f['t']} 翻成 true：{issued_t} 拍发令想发 {k(pc.get('want', 0))}（当时余额 {k(pc.get('bal0', 0))}，手续费 {k(pc.get('fee', 0))}），"
                         f"到 {f['t']} 拍余额只降了 {k(drop)}（扣掉手续费算作「实发」{k(max(0, drop - pc.get('fee', 0)))}）")
                if landed:
                    line += "；窗口内真正落地的是 " + "、".join(f"{c[0]} 拍 pct={c[3]}→{self.nm(min(c[4], NEUTRAL)) if c[2] == 1 else '捐/船'} 实发 {k(c[6])}" for c in landed[:3])
                fact["flip"] = {"t": f["t"], "issuedT": issued_t, "want": pc.get("want"), "bal0": pc.get("bal0"), "fee": pc.get("fee"), "B": f["B"],
                                "landed": [[c[0], c[3], min(c[4], NEUTRAL), c[6]] for c in landed[:3]]}
            if blk:
                tg = Counter(self.nm(x[1]) for x in blk)
                line += f" | 守卫挡掉 {len(blk)} 次出手（{blk[0][0]}~{blk[-1][0]} 拍；对象 " + " ".join(f"{n}×{c}" for n, c in tg.most_common(4)) + "）"
                fact["blockedSpan"] = [blk[0][0], blk[-1][0]]
                fact["blockedTargets"] = tg.most_common(6)
            self.w(line)
            self.facts["bots"].setdefault(bot, {})["nfs"] = fact
        if not any_:
            self.w("  全队整局没有任何一个号翻转过（始终为 false），也没有出手被守卫挡掉。")
        self.facts["nfsFlips"] = nflip
        self.w()

    # ---------- S6 ----------
    def sec_reissue(self):
        """同一个决定在上一条成交之前又发了几条（对非中立目标的陆攻；相邻发令间隔 ≤10 拍算同一串）。"""
        self.w("[S6] 上一条还没成交就重发（陆攻、目标非中立；相邻发令间隔 ≤10 拍并成一串；「首条前」= 在本串第一条成交之前发出的条数）")
        self.w("     同步串 = 第一条成交延迟 ≤45 拍；多花 = 首条之外、同样发在首条成交之前的那些指令实际送出的兵+手续费")
        rows_by = defaultdict(list)
        for c in self.R["cmdLog"]:
            if c[2] == 1:
                rows_by[(c[1], c[0], c[3])].append(c)
        tot = {"syncBursts": 0, "syncCmds": 0, "syncFirst": 0, "syncExtra": 0, "syncExtraCmds": 0,
               "lagBursts": 0, "lagIssued": 0, "lagExecuted": 0, "deadBursts": 0, "deadIssued": 0,
               "syncFirstFee": 0, "syncExtraFee": 0}
        lst = []
        per_bot = {}
        for bot, b in self.S["bots"].items():
            me = b["me"]
            cm, ex = b["cmds"], b["match"]["execOf"]
            bursts = []
            for i, c in enumerate(cm):
                if c[1] != 1 or c[4] != 1 or c[3] >= NEUTRAL:
                    continue
                key = (c[3], self.site(c[7]))
                if bursts and bursts[-1]["key"] == key and c[0] - bursts[-1]["idx"][-1][1] <= 10:
                    bursts[-1]["idx"].append((i, c[0]))
                else:
                    bursts.append({"key": key, "idx": [(i, c[0])]})
            for bu in bursts:
                if len(bu["idx"]) < 2:
                    continue
                exs = [(ex[i], t, i) for i, t in bu["idx"] if ex[i] >= 0]
                n = len(bu["idx"])
                t0, t1 = bu["idx"][0][1], bu["idx"][-1][1]
                if not exs:
                    tot["deadBursts"] += 1; tot["deadIssued"] += n
                    continue
                first_exec = min(e[0] for e in exs)
                first = min(exs)  # 最早成交的那条
                lag = first[0] - first[1]
                before = [(e, t, i) for (e, t, i) in exs if t < first_exec]
                if lag > 45:
                    tot["lagBursts"] += 1; tot["lagIssued"] += n; tot["lagExecuted"] += len(exs)
                    continue
                if len(before) < 2:
                    continue
                spent = []
                fees = []
                b0 = b1 = None
                for (e, t, i) in sorted(before):
                    pool = rows_by.get((me, e, cm[i][2]))
                    if not pool:
                        continue
                    r = pool.pop(0)
                    spent.append(r[6] + r[7])
                    fees.append(r[7])
                    if b0 is None:
                        b0 = r[8]
                    b1 = r[8] - r[6] - r[7]
                if len(spent) < 2:
                    continue
                tot["syncBursts"] += 1; tot["syncCmds"] += len(spent); tot["syncExtraCmds"] += len(spent) - 1
                tot["syncFirst"] += spent[0]; tot["syncExtra"] += sum(spent[1:])
                tot["syncFirstFee"] += fees[0]; tot["syncExtraFee"] += sum(fees[1:])
                pb = per_bot.setdefault(bot, {"bursts": 0, "first": 0, "extra": 0, "extraFee": 0, "extraCmds": 0})
                pb["bursts"] += 1; pb["first"] += spent[0]; pb["extra"] += sum(spent[1:]); pb["extraFee"] += sum(fees[1:]); pb["extraCmds"] += len(spent) - 1
                item = {"bot": bot, "t0": t0, "t1": t1, "target": self.nm(bu["key"][0]), "site": bu["key"][1], "issued": n,
                        "beforeFirstExec": len(spent), "firstLag": lag, "firstExec": first_exec, "B0": b0, "B1": b1,
                        "first": spent[0], "extra": sum(spent[1:]), "firstFee": fees[0], "extraFee": sum(fees[1:])}
                lst.append(item)
        lst.sort(key=lambda x: -x["extra"])
        for it in sorted(lst[:40], key=lambda x: (x["bot"], x["t0"])):
            self.w(f"  {it['bot']:7s} 发令 {it['t0']}-{it['t1']} → {it['target']:18s} {it['site']:16s} 首条前 {it['beforeFirstExec']} 条（首条延迟 {it['firstLag']} 拍）"
                   f" 余额 {k(it['B0'])}→{k(it['B1'])}：首条 {k(it['first'])}，多花 {k(it['extra'])}")
        self.w(f"  合计：同步串 {tot['syncBursts']} 个、{tot['syncCmds']} 条，首条共 {k(tot['syncFirst'])}，重发多花 {k(tot['syncExtra'])}（{tot['syncExtraCmds']} 条）"
               f" | 落后串（首条延迟 >45 拍）{tot['lagBursts']} 个：发 {tot['lagIssued']} 成交 {tot['lagExecuted']} | 整串没有成交 {tot['deadBursts']} 个共 {tot['deadIssued']} 条")
        if per_bot:
            self.w(f"  其中手续费（每条 = 当时余额的 12/1024）：首条共 {k(tot['syncFirstFee'])}，重发的 {tot['syncExtraCmds']} 条共 {k(tot['syncExtraFee'])}")
            self.w("  按号（同步串数：首条 / 重发多花，其中手续费）：" + "；".join(
                f"{b} {v['bursts']} 串：{k(v['first'])} / {k(v['extra'])}（{v['extraCmds']} 条，手续费 {k(v['extraFee'])}）"
                for b, v in sorted(per_bot.items(), key=lambda kv: -kv[1]["extra"])))
        self.facts["reissue"] = dict(tot, list=lst, perBot=per_bot)
        self.w()

    # ---------- S7 ----------
    def sec_crowd(self):
        """同一个决策拍里先发的一条占掉了指令位，后面那条在本地就被拒收（页面适配层每拍只收 1 条）。"""
        self.w("[S7] 同拍挤占：同一个决策拍里已经有一条被接受的指令，后面那条本地就被拒（每拍只收 1 条）。按「先发的源码行 → 被挤掉的源码行 → 目标」分组")
        tot = {"n": 0, "after1500": 0, "humanTarget": 0, "bots": 0}
        lst = []
        for bot, b in self.S["bots"].items():
            by_t = defaultdict(list)
            for c in b["cmds"]:
                by_t[c[0]].append(c)
            grp = {}
            for t, cs in by_t.items():
                acc = [c for c in cs if c[4] == 1]
                if not acc:
                    continue
                for r in cs:
                    if r[4] != 0:
                        continue
                    key = (self.site(acc[0][7]), self.site(r[7]), r[1], r[3])
                    g = grp.setdefault(key, {"n": 0, "t0": t, "t1": t, "pct": [r[2], r[2]], "B": [r[5], r[5]], "want": 0})
                    g["n"] += 1; g["t0"] = min(g["t0"], t); g["t1"] = max(g["t1"], t)
                    g["pct"] = [min(g["pct"][0], r[2]), max(g["pct"][1], r[2])]
                    g["B"][1] = r[5] if t >= g["t1"] else g["B"][1]
                    g["want"] = max(g["want"], (r[2] + 1) * r[5] // 1024)
            if grp:
                tot["bots"] += 1
            for (s1, s2, kind, q), g in sorted(grp.items(), key=lambda kv: kv[1]["t0"]):
                human = kind == 1 and q < self.R["H"]
                tot["n"] += g["n"]
                if g["t0"] >= 1500:
                    tot["after1500"] += g["n"]
                if human:
                    tot["humanTarget"] += g["n"]
                tgt = self.nm(q) if kind != 3 else "船"
                item = {"bot": bot, "first": s1, "crowded": s2, "target": tgt, "human": human, "n": g["n"], "t0": g["t0"], "t1": g["t1"], "pct": g["pct"], "maxWant": int(g["want"])}
                lst.append(item)
                self.w(f"  {bot:7s} {g['t0']}-{g['t1']} 先发 {s1:18s} 挤掉 {s2:16s} → {tgt:18s} × {g['n']:3d}（pct {g['pct'][0]}~{g['pct'][1]}，单条想发的兵最多 {k(g['want'])}）")
        if not lst:
            self.w("  全队整局没有。")
        self.w(f"  合计：{tot['n']} 条（t≥1500 的 {tot['after1500']} 条；目标是真人的 {tot['humanTarget']} 条），涉及 {tot['bots']} 个号")
        self.facts["crowd"] = dict(tot, list=lst)
        self.w()

    def run(self):
        self.w(f"===== {self.mid} 影子策略摘要（决策=策略源码在本地拍上的真实决定；成交=录像里服务器执行的指令）=====")
        self.sec_check()
        self.sec_exec()
        self.sec_misfire()
        self.sec_nfs()
        self.sec_reissue()
        self.sec_crowd()
        self.sec_runs()
        self.sec_holds()
        os.makedirs(os.path.join(OUT, "dossier"), exist_ok=True)
        open(os.path.join(OUT, "dossier", f"{self.mid}-shadow.txt"), "w", encoding="utf-8").write("\n".join(self.lines) + "\n")
        json.dump(self.facts, open(os.path.join(OUT, "dossier", f"{self.mid}-shadow-facts.json"), "w", encoding="utf-8"), ensure_ascii=False)
        return self.lines

    def raw(self, bot, t0, t1):
        b = self.S["bots"][bot]
        cm, ex = b["cmds"], b["match"]["execOf"]
        print(f"{bot} 本地 {t0}-{t1} 的发令（本地拍 种类 pct 目标 本地是否接受 → 成交服务器拍 | 兵 地 | 调用栈）")
        for i, c in enumerate(cm):
            if t0 <= c[0] <= t1:
                print(f"  {c[0]:5d} {'攻捐船?退??离'[c[1] - 1]} pct={c[2]:4d} → {self.nm(c[3]) if c[1] != 3 else c[3]:18s} ok={c[4]} 成交@{ex[i] if ex[i] >= 0 else '—':>5} | 兵 {k(c[5])} 地 {c[6]} | {c[7]}")
        print("同段的 act 记录（t 兵 地 nb neut cmds nfs quota 报价数 top… 发令数 worth over safe）")
        for a in b["acts"]:
            if t0 <= a[0] <= t1 and a[0] % 25 == 0:
                tops = " ".join(f"[{self.nm(o[0])} c={o[1]} need={k(o[2])} p{o[3]} nc{o[4]} bl{o[5]} om{o[6]} pm{o[7]} ch{o[8]} in={k(o[9])} tD={o[10]}]" for o in a[9][:3])
                print(f"  {a[0]:5d} 兵 {k(a[1])} 地 {a[2]} nb={a[3]} neut={a[4]} cmds={a[5]} nfs={a[6]} q={k(a[7])} 报价 {a[8]} {tops} 发 {a[10]} worth={a[11]} over={a[12]} safe={k(a[13]) if a[13] >= 0 else '—'}")


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(2)
    d = Digest(args[0])
    if "--raw" in args:
        bot = args[args.index("--bot") + 1]
        i = args.index("--raw")
        d.raw(bot, int(args[i + 1]), int(args[i + 2]))
        return
    lines = d.run()
    if "--quiet" not in args:
        print("\n".join(lines))
    else:
        print(f"{args[0]}: {len(lines)} 行 → out/dossier/{args[0]}-shadow.txt")


if __name__ == "__main__":
    main()
