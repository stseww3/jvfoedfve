#!/usr/bin/env python3
"""g0facts.py — 会审提案 G0（离线模拟器自身保真度验收）用的事实表。

把已有缓存里的保真度数字按层摆出来，外加两条只用录像指令流就能做的通道规则检验。不重跑重放。
  输入：out/cache/<局>-resim.json、out/cache/<局>-shadow.json、out/dossier/<局>-shadow-facts.json、
        bundles/<局>/card.json、out/council/abl/*.txt（g0ablate.mjs 的输出，有几条摘几条）
  输出：out/council/G0-facts.txt

用法：timeout 120 python3 scripts/g0facts.py
"""
import glob
import json
import os
import statistics
import sys
from collections import Counter, OrderedDict, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
OUT = os.path.join(ROOT, "out")
DATA = os.environ.get("C136_DATA", "/agent/repos/c136-data")
MIDS = "A051 A087 A066 A025 A045 A067 A071 A090 A042 A046 A041".split()
NEUTRAL = 512
PHASES = [(0, 600, "0~599"), (600, 1500, "600~1499"), (1500, 4284, "1500~4283"), (4284, 10 ** 9, "4284 起")]

_cache = {}


def J(path):
    if path not in _cache:
        with open(path, encoding="utf8") as f:
            _cache[path] = json.load(f)
    return _cache[path]


def resim(m):
    return J(os.path.join(OUT, "cache", f"{m}-resim.json"))


def shadow(m):
    return J(os.path.join(OUT, "cache", f"{m}-shadow.json"))


def sfacts(m):
    return J(os.path.join(OUT, "dossier", f"{m}-shadow-facts.json"))


def card(m):
    return J(os.path.join(DATA, "bundles", m, "card.json"))


def pct(a, b, nd=0):
    return "—" if not b else f"{100.0 * a / b:.{nd}f}%"


def med(xs):
    return statistics.median(xs) if xs else None


def quant(xs, q):
    if not xs:
        return None
    s = sorted(xs)
    return s[min(len(s) - 1, int(q * len(s)))]


def squad_ids(R):
    return sorted(s["id"] for s in R["squad"].values() if s["id"] >= 0)


L = []


def w(s=""):
    L.append(s)


# ---------------------------------------------------------------- G0-0
def g00():
    w("[G0-0] 建局的历史分布（manifest.jsonl，发现集 123 局；自由运行的模拟器要从这个分布里取房间，而不是用一个固定配置）")
    rows = []
    with open(os.path.join(DATA, "manifest.jsonl"), encoding="utf8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    w("编队档 | 局数 | 有录像的 | 开局真人数：最小 / 下四分位 / 中位 / 上四分位 / 最大 | 实际队数的分布（队数×局数） | 名义队数≠实际队数的局 | 地图数 | 赢的局")
    for co in ("squad8", "squad10", "squad20"):
        rs = [r for r in rows if r["cohort"] == co]
        sp = sorted(r["seededPlayers"] for r in rs)
        q = lambda f: sp[min(len(sp) - 1, int(f * len(sp)))]
        dist = Counter(r["actualTeams"] for r in rs)
        w(f"{co} | {len(rs)} | {sum(1 for r in rs if r['dataCompleteness']['replay'])} | {sp[0]} / {q(.25)} / {q(.5)} / {q(.75)} / {sp[-1]} | "
          f"{' '.join(f'{k}×{v}' for k, v in sorted(dist.items()))} | {sum(1 for r in rs if r['nominalTeams'] != r['actualTeams'])} | {len(set(r['mapId'] for r in rs))} | {sum(1 for r in rs if r['outcome']['resultLabel'] == 'won')}")
    eight = [r for r in rows if r["actualTeams"] >= 8]
    w(f"实际 8 队的局（内置 AI 入队的局）：{len(eight)} 局，其中有录像的 {sum(1 for r in eight if r['dataCompleteness']['replay'])} 局："
      + " ".join(f"{r['matchId']}（{r['cohort']}，{r['seededPlayers']} 人）" for r in eight))
    noteam = [r for r in rows if r["mode"] in (7, 8)]
    w(f"mode 7/8（没有队伍的房间）：{len(noteam)} 局：" + " ".join(r["matchId"] for r in noteam))
    w("[G0-0b] 我的 11 局：编队所在的队；分队算法（resim.mjs 的 assignTeams，按引擎 dP.ee 移植）算出来的队数、编队所在队号 对 manifest 里采集层记的 actualTeams、ourPrimaryTeam")
    w("局 | 真人席位 | 录像头队数 | 重放算出的队数 | manifest 实际队数 | 编队所在队号 重放 / manifest | 编队号是否同在一队 | 编队所在队的人数 | 其中编队号 | 同队路人 | 编队占本队人头 | 地图号 陆地格数")
    man = {r["matchId"]: r for r in rows}
    okn = okt = nteam = 0
    for m in MIDS:
        R = resim(m)
        sq = squad_ids(R)
        mm = man[m]
        if R["nTeams"] >= 2:
            team = R["teams"][sq[0]]
            same = len(set(R["teams"][p] for p in sq)) == 1
            size = sum(1 for p in range(R["H"]) if R["teams"][p] == team)
            nteam += 1
            okn += 1 if R["nTeams"] == mm["actualTeams"] else 0
            okt += 1 if team == mm["ourPrimaryTeam"] else 0
            w(f"{m} | {R['H']} | {R['nTeamsHeader']} | {R['nTeams']} | {mm['actualTeams']} | {team} / {mm['ourPrimaryTeam']} | {'是' if same else '否'} | {size} | {len(sq)} | {size - len(sq)} | {pct(len(sq), size)} | {R['mapIdx']} {R['land']:,}")
        else:
            w(f"{m} | {R['H']} | {R['nTeamsHeader']} | 0 | {mm['actualTeams']} | — / {mm['ourPrimaryTeam']} | — | — | {len(sq)} | — | — | {R['mapIdx']} {R['land']:,}")
    w(f"有队伍的 {nteam} 局：队数与 manifest 相同的 {okn} 局，编队所在队号相同的 {okt} 局")
    w("注：teamgate.mjs 的默认房间是 8 号编队 + 5 队×8 人 = 48 个真人、6 队，编队单独成一队（没有同队路人），内置 AI 轮流入队。")
    w()


# ---------------------------------------------------------------- G0-1
def g01():
    w("[G0-1] 物理层 + 建局层：真值重演 对 traj.csv（resim.mjs；把录像里全场的指令按原拍喂给模拟器，逐行核对编队号的地和兵）")
    w("局 | 真人席位 | 队数 录像头→实际 | 内置 AI 入队 | traj 行 | 地一致 | 兵一致 | 都一致 | 重放结束拍 | 录像放到分出胜负 | 猎杀次数 终局提速拍 | AI/空壳送兵笔数")
    tot = Counter()
    for m in MIDS:
        R = resim(m)
        v = R["validate"]
        sq = squad_ids(R)
        team = R["teams"][sq[0]] if R["nTeams"] else 0
        ev = R["engineEvents"]
        hunts = sum(1 for e in ev if e[1] == "hunt")
        fast = [e[0] for e in ev if e[1] == "fast"]
        label = card(m).get("outcome", {}).get("resultLabel", "?")
        if R["over"] and R["nTeams"]:
            won = f"是（重放胜队 {R['winnerTeam']}，编队在 {team} 队，卡片记 {label}）"
        else:
            won = f"否（卡片记 {label}）"
        w(f"{m} | {R['H']} | {R['nTeamsHeader']}→{R['nTeams']} | {'是' if R['botsTeamed'] else '否'} | {v['rows']} | {v['terrExact']} | {v['balExact']} | {v['bothExact']} | {R['endTick']} | "
          f"{won} | {hunts} {fast[0] if fast else '—'} | {len(R.get('botGifts', []))}")
        tot["rows"] += v["rows"]; tot["terr"] += v["terrExact"]; tot["bal"] += v["balExact"]; tot["both"] += v["bothExact"]
        tot["m"] += 1
        if v["rows"] == v["bothExact"]:
            tot["mfull"] += 1
    w(f"合计：{tot['m']} 局 traj {tot['rows']} 行，地一致 {tot['terr']}，兵一致 {tot['bal']}，都一致 {tot['both']}（{pct(tot['both'], tot['rows'], 1)}）；逐行全对的 {tot['mfull']}/{tot['m']} 局")
    w("注：traj.csv 每 90 拍一行、只有编队号；其他真人和内置 AI 的状态没有逐行真值，只能通过「编队号的地、兵逐兵相等」间接约束。")
    w("[G0-1b] 上面逐行一致的范围里覆盖到的船（录像里的船令全部成交；靠岸 = 引擎 landAt 被调用的那一刻，按靠岸那一格的归属分类）")
    w("局 | 全场真人船令 | 编队船令 | 编队的船靠岸：合计 | 无主地 | 自己的地（兵退回余额） | 编队友（交兵） | 同队路人（交兵） | 内置 AI | 敌方真人 | 离线托管后的靠岸")
    tb = Counter()
    for m in MIDS:
        R = resim(m)
        H = R["H"]
        sq = set(squad_ids(R))
        tg = R["nTeams"] >= 2
        teams = R["teams"]
        allb = sum(1 for c in R["cmdLog"] if c[2] == 3 and c[5] == 1)
        sqb = sum(1 for c in R["cmdLog"] if c[2] == 3 and c[5] == 1 and c[1] in sq)
        k = Counter()
        left = R["leftT"]
        for t, p, target, troops, got, q0, cap in R["landings"]:
            if p not in sq:
                continue
            if 0 <= left[p] <= t:
                k["husk"] += 1
                continue
            if target == p:
                k["self"] += 1
            elif target == NEUTRAL:
                k["neutral"] += 1
            elif target in sq:
                k["squad"] += 1
            elif target >= H:
                k["ai"] += 1
            elif tg and teams[target] == teams[p]:
                k["mate"] += 1
            elif target >= 0:
                k["enemy"] += 1
            else:
                k["other"] += 1
        n = sum(k.values())
        n = n - k["husk"]
        w(f"{m} | {allb} | {sqb} | {n} | {k['neutral']} | {k['self']} | {k['squad']} | {k['mate']} | {k['ai']} | {k['enemy']} | {k['husk']}")
        tb["all"] += allb; tb["sq"] += sqb; tb["n"] += n
        for kk in ("neutral", "self", "squad", "mate", "ai", "enemy", "husk"):
            tb[kk] += k[kk]
    w(f"合计 | {tb['all']} | {tb['sq']} | {tb['n']} | {tb['neutral']} | {tb['self']} | {tb['squad']} | {tb['mate']} | {tb['ai']} | {tb['enemy']} | {tb['husk']}")
    w("注：靠岸数只算号还在控的时候；最后一列是号离线、由内置 AI 托管之后它自己发的船的靠岸次数（不是录像指令，也不在 traj 核对范围里）。船令比靠岸多出来的那些船没有走到 landAt（沉在海上、到岸时无处可落、或局终时还在路上，没有分开数）。")
    w("    「单点航线」没有单独数：重放没有记每条船的航线长度。")
    w()


# ---------------------------------------------------------------- G0-2
def g02():
    w("[G0-2] 决策层 + 适配层：影子策略 对 线上日志（shadow.mjs；当局的策略源码在重放的真实状态上逐拍运行，发出的指令不落地）")
    w("局 | 策略文件 | HL-TICK 行 | cmds 一致 | nb 一致 | neut 一致 | 调度日志 相同/日志 | 开局日志 相同/日志 | 录像成交 对上/成交 | 适配层取值（每拍多令 / 捐款严格 / 陆攻判定 / isBot / 最小延迟）")
    tot = Counter()
    for m in MIDS:
        S = shadow(m)
        c = sfacts(m)["check"]
        w(f"{m} | {S['strategy']} | {c['rows']} | {c['cmds']} | {c['nb']} | {c['neut']} | {c['ds']}/{c['dl']} | {c['os']}/{c['ol']} | {c['mt']}/{c['ex']} | "
          f"{'是' if S.get('multi') else '否'} / {'是' if S.get('strictDonate') else '否'} / {S.get('adapter')} / {S.get('isBotMode')} / {S.get('minLat') or 6}")
        for k in ("rows", "cmds", "nb", "neut", "ds", "dl", "os", "ol", "mt", "ex"):
            tot[k] += c[k]
        tot["m"] += 1
        if c["cmds"] == c["rows"]:
            tot["mcmds"] += 1
    w(f"合计：HL-TICK {tot['rows']} 行，cmds 一致 {tot['cmds']}（{pct(tot['cmds'], tot['rows'], 1)}），nb 一致 {tot['nb']}，neut 一致 {tot['neut']}；"
      f"调度日志 {tot['ds']}/{tot['dl']}；开局日志 {tot['os']}/{tot['ol']}；录像成交对上影子发令 {tot['mt']}/{tot['ex']}；cmds 逐行全对的 {tot['mcmds']}/{tot['m']} 局")
    w("注：HL-TICK 每 90 拍一行（nb = 陆上邻居数，neut = 相邻无主地格数，cmds = 策略自己数的发令数）；调度日志 = events.csv 的 DISPATCH 行（拍、档、pct、对象、当时余额五项全同才算相同）；")
    w("    开局日志 = opening.csv（拍、周期、圈数、花费、余额、领土六项全同）；成交对上 = 录像里这个号的每条陆攻/捐款/船，都能在影子的发令序列里按顺序找到同种类、同 pct、同对象的一条。")
    # cmds 是累计计数器，差 1 条之后每行都不一致：列出每个不一致的号的首差拍，以及首差拍之后它还有多少行
    import csv as _csv
    lines = []
    tot_bad = tot_after = 0
    for m in MIDS:
        S = shadow(m)
        trows = defaultdict(list)
        with open(os.path.join(DATA, "bundles", m, "traj.csv"), encoding="utf8") as f:
            for r in _csv.DictReader(f):
                try:
                    trows[r["bot"]].append(int(r["t"]))
                except (ValueError, KeyError):
                    pass
        for bot, B in S["bots"].items():
            c = B["check"]["tick"]
            if not c.get("firstCmdsDiff"):
                continue
            t0, lg, sh = c["firstCmdsDiff"]
            bad = c["rows"] - c["cmds"]
            after = sum(1 for t in trows[bot] if t >= t0)
            tot_bad += bad; tot_after += after
            lines.append(f"{m} {bot} 首差 {t0} 拍（日志 {lg}、影子 {sh}），不一致 {bad} 行 / 首差拍起共 {after} 行")
    w(f"[G0-2b] cmds 不一致的号（cmds 是累计计数器，差一条之后的行都带着这个差）：{len(lines)} 个号，不一致 {tot_bad} 行，这些号首差拍起一共 {tot_after} 行")
    for l in lines:
        w("  " + l)
    w()


# ---------------------------------------------------------------- G0-3
def g03():
    w("[G0-3] 通道层的历史签名：影子发令（本地被接受的陆攻/捐款/船）→ 录像成交")
    w("局 | 影子发令 | 成交 | 没成交 | 其中捐款 发令→成交 | 其中陆攻+船 发令→成交 | 成交延迟（拍）中位 / 九成位 / 最大 | 延迟>30 拍占成交 | >150 拍占成交")
    allrows = {}
    for m in MIDS:
        S = shadow(m)
        iss = Counter(); exe = Counter(); lags = []
        ph = {p[2]: [0, 0, []] for p in PHASES}
        for b in S["bots"].values():
            eo = b["match"]["execOf"]
            for i, c in enumerate(b["cmds"]):
                if c[4] != 1 or c[1] > 3:
                    continue
                kind = "don" if c[1] == 2 else "atk"
                iss[kind] += 1
                ex = eo[i] if i < len(eo) else -1
                name = next(p[2] for p in PHASES if p[0] <= c[0] < p[1])
                ph[name][0] += 1
                if ex >= 0:
                    exe[kind] += 1
                    lags.append(ex - c[0])
                    ph[name][1] += 1
                    ph[name][2].append(ex - c[0])
        ni = iss["don"] + iss["atk"]; ne = exe["don"] + exe["atk"]
        late30 = sum(1 for x in lags if x > 30); late150 = sum(1 for x in lags if x > 150)
        w(f"{m} | {ni} | {ne} | {ni - ne}（{pct(ni - ne, ni)}） | {iss['don']}→{exe['don']} | {iss['atk']}→{exe['atk']}（{pct(exe['atk'], iss['atk'])}） | "
          f"{med(lags):.0f} / {quant(lags, 0.9)} / {max(lags)} | {pct(late30, ne)} | {pct(late150, ne)}")
        allrows[m] = ph
    w("分段（按本地发令拍）：每格 = 发令→成交 @成交延迟中位")
    w("局 | " + " | ".join(p[2] for p in PHASES))
    for m in MIDS:
        ph = allrows[m]
        cells = []
        for p in PHASES:
            a, b, lg = ph[p[2]]
            cells.append(f"{a}→{b} @{med(lg):.0f}" if lg else f"{a}→{b} @—")
        w(f"{m} | " + " | ".join(cells))
    w("注：延迟 = 录像里的落地拍 − 影子发令的本地拍；重复签名（同 pct 同对象）按最晚可行的一条对齐，所以是延迟的下界。没成交 = 影子发了、录像里找不到对应的一条（额度拒捐、超过通道上限被丢、或页面当时没在跑）。")
    w()


# ---------------------------------------------------------------- G0-4
def g04():
    w("[G0-4] 通道规则检验（只用录像指令流 resim 的 cmdLog；不依赖影子对齐）")
    # 4a 回合边界
    w("[G0-4a] 指令只在回合边界落地：真人席位的全部指令里，落地拍是 7 的倍数的条数 / 全部条数")
    tot = [0, 0]
    cells = []
    for m in MIDS:
        R = resim(m)
        n = len(R["cmdLog"]); k = sum(1 for c in R["cmdLog"] if c[0] % 7 == 0)
        tot[0] += k; tot[1] += n
        cells.append(f"{m} {k}/{n}")
    w("  " + "  ".join(cells))
    w(f"  合计 {tot[0]}/{tot[1]}")
    # 4b 连续 k 回合上限
    w("[G0-4b] 一个号在任意连续 k 个回合里落地的指令条数的最大值（全部指令种类；回合 = 7 拍）")
    w("局 | 编队号 k=1 / 2 / 3 / 4 / 5 / 6 | 其他真人 k=1 / 2 / 3 / 4 / 5 / 6")
    win3 = Counter(); win4over = 0; gap_after9 = Counter(); comp = Counter()
    for m in MIDS:
        R = resim(m)
        sq = set(squad_ids(R))
        per = defaultdict(Counter)
        for c in R["cmdLog"]:
            per[c[1]][c[0]] += 1

        def maxk(p, k):
            ts = per[p]
            return max(sum(ts.get(t + 7 * i, 0) for i in range(k)) for t in ts)

        a = [max((maxk(p, k) for p in sq if p in per), default=0) for k in range(1, 7)]
        others = [p for p in per if p not in sq]
        b = [max((maxk(p, k) for p in others), default=0) for k in range(1, 7)]
        w(f"{m} | {' / '.join(map(str, a))} | {' / '.join(map(str, b))}")
        for p in sq:
            ts = per.get(p, {})
            turns = sorted(ts)
            for i, t in enumerate(turns):
                w3 = tuple(ts.get(t + 7 * k, 0) for k in range(3))
                win3[sum(w3)] += 1
                if sum(w3) == 9:
                    comp[w3] += 1
                if sum(ts.get(t + 7 * k, 0) for k in range(4)) > 9:
                    win4over += 1
                if ts[t] == 9 and i + 1 < len(turns):
                    gap_after9[(turns[i + 1] - t) // 7] += 1
    n3 = sum(win3.values())
    w(f"  编队号合计：从有指令的回合起算的 3 回合窗口 {n3} 个，恰好 9 条的 {win3[9]} 个，超过 9 条的 {sum(v for k, v in win3.items() if k > 9)} 个；同样起算的 4 回合窗口里超过 9 条的 {win4over} 个")
    w("  恰好 9 条的 3 回合窗口的构成（第 1 / 2 / 3 回合各几条 → 个数）：" + "；".join(f"{a}+{b}+{c} → {n}" for (a, b, c), n in sorted(comp.items(), key=lambda x: -x[1])))
    g = sorted(gap_after9.items())
    w(f"  单回合 9 条满批 {sum(gap_after9.values())} 个（后面还有指令的）：同一个号的下一条指令最早隔 {g[0][0]} 个回合（{g[0][1]} 个），隔 3~5 个回合的 {sum(v for k, v in g if 3 <= k <= 5)} 个，隔 6 个及以上的 {sum(v for k, v in g if k >= 6)} 个")
    w("  注：A051 的「其他真人」里有同房间另一支我方编队（B033）的号，所以那一行也到 9。")
    # 4c 同拍倒序
    w("[G0-4c] 同一回合落地多条时的顺序：把录像里一个号同一拍的多条指令，逐条去影子发令序列里找签名（种类、pct、对象）唯一的那一条，看落地顺序与发令顺序的关系")
    w("局 | 同拍 ≥2 条的批 | 每条都能唯一辨认的批 | 落地顺序与发令顺序相反 | 相同 | 混合 | 其中 2 条 / 3 条 / ≥4 条的倒序批")
    T = Counter()
    for m in MIDS:
        R = resim(m); S = shadow(m)
        death = R["deathT"]; H = R["H"]
        c = Counter()
        for b in S["bots"].values():
            me = b["me"]
            issued = [(i, x) for i, x in enumerate(b["cmds"]) if x[4] == 1 and x[1] <= 3]
            groups = OrderedDict()
            for x in R["cmdLog"]:
                if x[1] == me and x[2] in (1, 2, 3):
                    groups.setdefault(x[0], []).append(x)
            for St, g in groups.items():
                if len(g) < 2:
                    continue
                c["batches"] += 1
                cand = []
                ok = True
                for x in g:
                    kind, p_ = x[2], x[3]
                    tgt = min(x[4], NEUTRAL) if kind == 1 else x[4]
                    cs = []
                    for i, y in issued:
                        if y[0] > St - 5 or y[0] < St - 400 or y[1] != kind or y[2] != p_:
                            continue
                        if y[3] != tgt:
                            if kind != 1 or tgt != NEUTRAL:
                                continue
                            dead_h = y[3] < H and 0 <= death[y[3]] <= St
                            if not (dead_h or (H <= y[3] < NEUTRAL)):
                                continue
                        cs.append(i)
                    if len(cs) != 1:
                        ok = False
                        break
                    cand.append(cs[0])
                if not ok or len(set(cand)) != len(cand):
                    continue
                c["unique"] += 1
                dec = all(cand[i] > cand[i + 1] for i in range(len(cand) - 1))
                inc = all(cand[i] < cand[i + 1] for i in range(len(cand) - 1))
                if dec:
                    c["lifo"] += 1
                    c["n2" if len(g) == 2 else "n3" if len(g) == 3 else "n4"] += 1
                elif inc:
                    c["fifo"] += 1
                else:
                    c["mixed"] += 1
        w(f"{m} | {c['batches']} | {c['unique']} | {c['lifo']} | {c['fifo']} | {c['mixed']} | {c['n2']} / {c['n3']} / {c['n4']}")
        T.update(c)
    w(f"合计 | {T['batches']} | {T['unique']} | {T['lifo']} | {T['fifo']} | {T['mixed']} | {T['n2']} / {T['n3']} / {T['n4']}")
    # 4d 成批占比、重复落地
    w("[G0-4d] 同拍成批与重复落地（编队号的陆攻/捐款/船；录像成交口径）")
    w("局 | 成交条数 | 落在同拍 ≥2 条的批里 | ≥4 条的批里 | 9 条的批里 | 同批同一决定的重复落地（影子口径） | 上一条没落地就重发：重发条数 ÷ 串内条数（影子口径） | 其他真人：成交条数 落在 ≥2 条的批里 ≥4 条")
    for m in MIDS:
        R = resim(m); F = sfacts(m)
        sq = set(squad_ids(R)); H = R["H"]
        per = defaultdict(Counter)
        for c in R["cmdLog"]:
            if c[2] in (1, 2, 3):
                per[c[1]][c[0]] += 1

        def shares(ps):
            n = b2 = b4 = b9 = 0
            for p in ps:
                for t, k in per.get(p, {}).items():
                    n += k
                    if k >= 2: b2 += k
                    if k >= 4: b4 += k
                    if k >= 9: b9 += k
            return n, b2, b4, b9

        n, b2, b4, b9 = shares(sq)
        on, ob2, ob4, _ = shares([p for p in range(H) if p not in sq])
        mf = F["misfire"]; re = F["reissue"]
        w(f"{m} | {n} | {b2}（{pct(b2, n)}） | {b4}（{pct(b4, n)}） | {b9}（{pct(b9, n)}） | {mf.get('dupInBatch', 0)}（{pct(mf.get('dupInBatch', 0), mf['exec'])}） | "
          f"{re['syncExtraCmds']} ÷ {re['syncCmds']}（{pct(re['syncExtraCmds'], re['syncCmds'])}） | {on} {pct(ob2, on)} {pct(ob4, on)}")
    w()


# ---------------------------------------------------------------- G0-5
def g05():
    import re as _re
    files = sorted(glob.glob(os.path.join(OUT, "council", "abl", "*-*.txt")))
    w("[G0-5] 反向检验（g0ablate.mjs）：把重放 / 影子里的一条线上细节换回数据仓库模拟器的默认做法，其余不动，看核对指标掉多少")
    if not files:
        w("  （还没有输出）")
        w()
        return
    PH = {"base": "不换（对照）", "colors": "组队局改用自由混战配色", "botteams": "强制内置 AI 入队", "nobotteams": "强制内置 AI 不入队", "cache32": "猎杀与终局提速用数据仓库模拟器的写法"}
    SH = {"base": "不换（对照）", "multi": "一个决策拍允许多条", "strict-donate": "本地按额度拒捐", "offline": "g.online 设为假", "adapter-sim": "陆攻受理用数据仓库模拟器的判定", "isbot-sim": "内置 AI 的判别用数据仓库模拟器的"}
    ORDER = {k: i for i, k in enumerate(list(SH)[1:], 10)}
    ORDER.update({k: i for i, k in enumerate(PH)})
    phys, shad = [], []
    for f in files:
        for line in open(f, encoding="utf8"):
            c = [x.strip() for x in line.strip().split(" | ")]
            if len(c) < 5:
                continue
            last = lambda x: x.split()[-1]
            no = lambda x: "无" if x == "-1" else x
            if c[1].startswith("phys="):
                k = c[1][5:]
                un = last(c[2]).replace("until=", "")
                phys.append((c[0], ORDER.get(k, 99), [c[0], PH.get(k, k), "整局" if un in ("end", "Infinity", "undefined") else un + " 拍", last(c[3]), last(c[4]), last(c[5]), last(c[6]), no(last(c[7])), last(c[8]), no(last(c[9])), no(last(c[10])), last(c[11]), f"{int(last(c[12])):,}"]))
            elif c[1].startswith("shadow="):
                k = c[1][7:]
                un = last(c[2]).replace("until=", "")
                d = _re.match(r"调度 日志 (\d+) 影子 (\d+) 相同 (\d+)", c[9])
                o = _re.match(r"开局 日志 (\d+) 相同 (\d+)", c[10])
                e = _re.match(r"成交 (\d+) 对上 (\d+)", c[11])
                shad.append((c[0], ORDER.get(k, 99), [c[0], SH.get(k, k), "整局" if un in ("end", "Infinity", "undefined") else un + " 拍", last(c[4]), last(c[5]), last(c[6]), last(c[7]),
                                                     f"{d.group(3)}/{d.group(1)}（影子 {d.group(2)} 条）", f"{o.group(2)}/{o.group(1)}", f"{e.group(2)}/{e.group(1)}", last(c[12]), last(c[13])]))
    if phys:
        w("[G0-5a] 物理层与建局层（重放对 traj.csv）")
        w("局 | 换掉什么 | 跑到 | traj 行 | 地一致 | 兵一致 | 都一致 | 首个不一致拍 | 结束拍 | 胜队 | 终局提速拍 | 猎杀次数 | 末拍编队地")
        for _m, _o, r in sorted(phys, key=lambda x: (x[0], x[2][2], x[1])):
            w(" | ".join(r))
    if shad:
        w("[G0-5b] 决策层与适配层（影子对线上日志）")
        w("局 | 换掉什么 | 跑到 | HL-TICK 行 | cmds 一致 | nb 一致 | neut 一致 | 调度日志 相同/日志 | 开局日志 相同/日志 | 录像成交 对上/成交 | 影子发令 | 报错的号")
        for _m, _o, r in sorted(shad, key=lambda x: (x[0], x[2][2], x[1])):
            w(" | ".join(r))
    w()


def main():
    w("# G0 事实表（g0facts.py）：离线模拟器保真度的现有核对数字，按层排列。11 局 = A051 A087 A066 A025 A045 A067 A071 A090 A042 A046 A041")
    w("# 三套东西要分清：①数据仓库模拟器 src/sim/sim（game.js 等，自由运行时用，teamgate.mjs 调的就是它）；②真值重演 resim.mjs = ①加上组队配色随机数、分队算法、32 拍队伍总地缓存，")
    w("#   用录像里全场的指令驱动；③影子策略 shadow.mjs = 在②的状态上旁路运行当局的策略源码。下面的核对数字是②和③的，不是①自由运行的。")
    w()
    g00(); g01(); g02(); g03(); g04(); g05()
    os.makedirs(os.path.join(OUT, "council"), exist_ok=True)
    path = os.path.join(OUT, "council", "G0-facts.txt")
    with open(path, "w", encoding="utf8") as f:
        f.write("\n".join(L) + "\n")
    print(f"写 {os.path.relpath(path, ROOT)}（{len(L)} 行）")
    # [G0-2b] 这一段另存一份，报告里原文引用
    i = next(k for k, x in enumerate(L) if x.startswith("[G0-2b]"))
    j = next(k for k in range(i, len(L)) if not L[k].strip())
    with open(os.path.join(OUT, "council", "G0-2b-cmds.txt"), "w", encoding="utf8") as f:
        f.write("\n".join(x.strip() for x in L[i + 1:j]) + "\n")


if __name__ == "__main__":
    sys.exit(main())
