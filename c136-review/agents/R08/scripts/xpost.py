#!/usr/bin/env python3
"""xpost.py — 1500 拍以后挨着的内置 AI / 空壳的地：还剩多少、谁吃了、本编队的号有没有出手、买地规则卡在哪一关。

先跑重演（真引擎，到 3000 拍；每局 15~40 秒，必须套 run-heavy.sh，一批 2 局）：
    bash c136-review/agents/R08/scripts/xpost_batch.sh            # 逐批跑完 xtruth.json 里「对得上、录像到 1800 拍以后」的局，已有输出的跳过
再汇总：
    python3 xpost.py [--quiet]        → out/_cross/xpost.txt、xpost.json

只读 /agent/repos/c136-data/bundles/（发现集）和 src/；验证集不碰。不跑策略：规则是按代码照抄到引擎状态上的。

口径：
  · 席位分四组（xtruth.seat_groups）：own / [APEX] / 名字池 / 野人。own 只算日志快照和重演逐兵对得上的局。
  · 窗：(1500,1800]、(1800,2400]、(2400,3000]。一局的某一窗要求：录像到了窗末；重演到窗末为止对不上的核对行不超过 5%。
  · 人头：窗首那一拍还有地、到窗末没离开的席位（窗里出局的照算，吃到多少算多少）。
  · 空壳 = 已经离开的真人席位（引擎接管；策略里和内置 AI 一样算「非真人」目标）。
  · 接壤普查：窗里每 30 拍一个样本，在线（没离开、有地）的真人席位。「90 拍内出手」= 样本拍之后 90 拍内有一条生效的陆攻落在内置 AI 身上（看不满 90 拍的样本不进这一栏）。
  · 规则照抄（1500 拍后买「非真人」地那条路；参数取 out/_cross/params.json，squad20 → c110，squad10 → c116）：
      c110：Policy.offers L5008-5049（非真人报价：need = elimCost + 它压我的 − 我压它的；c = (need + 手续费) ÷ 能吃到的格）
            → Policy.buyLand L5250-5369：L5267 报价 ≥ worth 且不富余 → 停；L5322-5325 safe = min(max(sb, dpKeep), oppFloorCap×地)；
              L5328-5357 keep；avail = 余额 − 手续费 − max(keep, safe)；L5363-5369：已经在打的跳过、want = 1.25×need + 3×接触格、
              x = min(avail, want)、x < minCmd 或（x < want 且 x < chunk×余额）→ 跳过。
      c116：同一条路，但没有「已经在打的跳过」和「x < minCmd」这两条（buyLand L5449-5454：`if (x <= 0 || (x < want && x < P.chunk * B)) continue;`）。
      sb = safeFinite（V13 L2532-2542 / threatOf L464-491；botSkip = 0 所以不带 skip）；dpKeep L2491-2496（c110 的邻居表不含受保护的队友）。
    每个样本只看内置 AI 的报价，归一类：
      ok            至少有一个内置 AI 的报价过了全部关（规则这一拍会对它发兵）
      attacking     （只 c110）最便宜的那个已经在打，按 L5364 跳过
      slot          没有报价：挨着的内置 AI 都不在打，而进攻槽满 / 在打的非无主地目标数到了 maxTargets
      done          没有报价：挨着的内置 AI 的 need 都 ≤ 0（压上去的兵已经够）
      price         最便宜的报价 ≥ worth、≥ cheap，且余额没超过 100×地（L5267 停）
      keep          avail ≤ 0，起作用的是按报价算的 keep
      sb / sb(cap)  avail ≤ 0，起作用的是 safe，safe 来自 sb；(cap) = sb 超过 oppFloorCap×地，被封顶在 oppFloorCap×地
      dp / dp(cap)  同上，safe 来自 dpKeep
      minCmd(want)  （只 c110）吃光它要的 want 本身就小于 minCmd = feeK×⌊12×余额/1024⌋
      minCmd(avail) （只 c110）want 够大，但 avail 小于 minCmd
      chunk         x < want 且 x < chunk×余额
    野人 / [APEX] / 名字池的样本用这一局主编队那一档的规则当同一把尺子量（不是说它们按这套规则打）。
节：
  [XP-A] 覆盖   [XP-B] 内置 AI 还剩多少地   [XP-C] 分窗收支（谁吃了内置 AI / 空壳 / 无主地 / 真人的地）
  [XP-D] 接壤普查（挨不挨着、出不出手）   [XP-E] 规则照抄（卡在哪一关）   [XP-F] 生效陆攻的大小和手续费
  [XP-G] 和影子普查（跑真策略的 shadow.mjs census2）逐点对照   [XP-H] 逐局
"""
import json
import math
import os
import statistics
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import r08lib as L  # noqa: E402
from xbatch import name_pool, discovery_ids, MINE  # noqa: E402
from xtruth import seat_groups  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")
RUN = os.path.join(OUT, "_run", "xpost")
WINS = [("1500~1800", 1500, 1800), ("1800~2400", 1800, 2400), ("2400~3000", 2400, 3000)]
GROUPS = ("own", "apex", "pool", "wild")
CN = dict(own="本编队", apex="[APEX]", pool="名字池", wild="野人")
COHORT_FILE = dict(squad20="c110", squad10="c116")
CLASSES = ("ok", "attacking", "slot", "done", "price", "keep", "sb", "sb(cap)", "dp", "dp(cap)", "minCmd(want)", "minCmd(avail)", "chunk")
CLS_CN = {"ok": "放行", "attacking": "已经在打", "slot": "槽 / 目标数满", "done": "兵已压够", "price": "报价 ≥ worth", "keep": "keep", "sb": "safe:sb", "sb(cap)": "safe:sb 封顶",
          "dp": "safe:dpKeep", "dp(cap)": "safe:dpKeep 封顶", "minCmd(want)": "want < minCmd", "minCmd(avail)": "avail < minCmd", "chunk": "chunk"}
SRC = ("own", "apex", "pool", "wild", "shell", "ai", "none")
SRC_CN = dict(own="本编队的号", apex="[APEX]", pool="名字池", wild="野人", shell="空壳", ai="内置 AI", none="无")


def med(v):
    return statistics.median(v) if v else None


def fmt(x, nd=2):
    return "—" if x is None else f"{x:.{nd}f}"


def pct(a, b, nd=0):
    return "—" if not b else f"{100 * a / b:.{nd}f}%"


def win_ratio(P, t):
    T = P.get("winT")
    if not T or t < T[0][0]:
        return P["winR"] * max(1, t)
    for i in range(1, len(T)):
        if t <= T[i][0]:
            return T[i - 1][1] + (T[i][1] - T[i - 1][1]) * (t - T[i - 1][0]) / (T[i][0] - T[i - 1][0])
    return T[-1][1]


def base_rate(t, terr, land):
    i = (511 * terr) // land
    n1 = 100 + math.sqrt(25600 * i / 508)
    if t < 1920:
        n1 = max(100 * (13440 - 6 * t) / 1920, n1)
    return min(n1, 700) / 1e4


def post_eval(rw, P, c110, protected, dmed, land):
    """把 1500 拍后买非真人地的规则照抄到一个样本上。返回 (类别, 细节)。只看内置 AI 的报价。"""
    t, _p, B, L0, sb, sb_src, slot_free, active, persons, npc = rw[:10]
    Lm = max(1, L0)
    fee = (12 * B) // 1024
    d_me = B / Lm
    m = P["maxW"] * win_ratio(P, t)
    ref = max(d_me, P["marketFloor"] * dmed) if (dmed is not None and t >= P["marketFrom"]) else d_me
    worth = m * ref
    over = P["surplus"] > 0 and B > 100 * Lm
    cheap = 0.1 / base_rate(t, L0, land) if P["growth"] > 0 else 0
    min_cmd = P["feeK"] * fee
    mx, dp_src = 0, -1
    for q, v in persons:
        if q in protected:
            continue
        if v > mx:
            mx, dp_src = v, q
    dp = max(0.0, (mx - 1.5 * L0) / 1.78)
    s = max(sb, P["killW"] * dp)
    cap = P["oppFloorCap"] * Lm
    safe = min(s, cap)
    det = dict(sb=sb, sbSrc=sb_src, dp=dp, dpSrc=dp_src, cap=cap, dens=d_me, minCmd=min_cmd, worth=worth, over=over)
    offers = []
    n_slot = n_done = 0
    for a in npc:
        q, T, Bq, left, cnt, blen, mine, theirs, atk_pq, atk_qp, shell = a
        if shell:
            continue
        if not atk_pq and (active >= P["maxTargets"] or not slot_free):
            n_slot += 1
            continue
        x = min(1, left / max(T, 1))
        need = 2 * Bq * (1 - x ** 1.6) + 2 * T * (1 - x) + theirs - mine
        if need <= 0:
            n_done += 1
            continue
        share = min(1, cnt / max(1, blen))
        gain = max(1, T - left + left * P["shareW"] * share)
        offers.append(((need + fee) / gain, a, need))
    if not offers:
        return ("slot" if n_slot else "done"), det
    offers.sort(key=lambda o: o[0])
    first = None
    gated = False
    for c, a, need in offers:
        q, T, Bq, left, cnt, blen, mine, theirs, atk_pq, atk_qp, shell = a
        if c >= worth and c >= cheap and not over:
            gated = True
        if gated:
            why = "price"
        else:
            keep = math.inf
            if c < cheap:
                keep = 0
            if c < worth:
                worth_own = m * d_me if (P["ownWorthMinKeep"] > 0 and t >= P["ownWorthFrom"]) else worth
                budget = max(0, (worth_own * Lm - fee * m - c * Lm) / (1 + m))
                min_keep = c * Lm / m
                keep = min(keep, max(min_keep, B - fee - budget) if P["post"] > 0 else min_keep)
            if over:
                mult = P["hold"] if c110 else (0.82 if d_me >= 122 else P["hold"])
                keep = min(keep, mult * 100 * Lm)
            avail = B - fee - max(keep, safe)
            want = 1.25 * need + 3 * cnt
            x = min(avail, want)
            if avail <= 0:
                if keep >= safe:
                    why = "keep"
                else:
                    why = ("sb" if sb >= P["killW"] * dp else "dp") + ("(cap)" if s > cap else "")
            elif c110 and atk_pq and (not atk_qp or mine >= 0.35 * need):
                why = "attacking"
            elif c110 and x < min_cmd:
                why = "minCmd(want)" if want < min_cmd else "minCmd(avail)"
            elif x < want and x < P["chunk"] * B:
                why = "chunk"
            else:
                why = "ok"
            if first is None:
                det.update(want=want, x=x, keep=keep, safe=safe, c=c, T=T, Bq=Bq, need=need, avail=avail)
        if first is None:
            first = why
        if why == "ok":
            det["okSmall"] = x < min_cmd      # 放行的这一单不到 minCmd（c116 才会出现）
            det["okWant"] = want
            det["okX"] = x
            return "ok", det
    return first, det


def load_params():
    with open(os.path.join(OUT, "_cross", "params.json"), encoding="utf-8") as f:
        return json.load(f)["params"]


def scan(mid, row, pool, PARAMS):
    p = os.path.join(RUN, f"{mid}.json")
    if not os.path.exists(p):
        return None
    X = json.load(open(p, encoding="utf-8"))
    if "error" in X:
        return dict(matchId=mid, error=X["error"])
    H = X["H"]
    names, low, F, own, valid, _spawn_only, grp = seat_groups(X, mid, pool)
    v = X["validate"]
    sb0 = X.get("startBox") or [None] * H
    spawned = [q for q in range(H) if X["spawnXY"][q] or sb0[q]]
    left_t = X["leftT"]
    teams = X.get("teams") or [0] * H
    cohort = row.get("cohort")
    c110 = cohort == "squad20"
    P = PARAMS[COHORT_FILE.get(cohort, "c110")]
    oc = row.get("outcome") or {}
    rec = dict(matchId=mid, cohort=cohort, won=bool(oc.get("primaryTeamWon")), H=H, land=X["land"], endTick=X["endTick"], valid=valid, rows=v["rows"], exact=v["bothExact"],
               size={g: sum(1 for q in spawned if grp[q] == g) for g in GROUPS})
    # 每一窗能不能用
    per_tick = v["rows"] / max(1, X["endTick"])
    ok_win = []
    for _nm, a, z in WINS:
        bad = sum(1 for t in v.get("mismT", []) if t <= z)
        ok_win.append(bool(valid and X["endTick"] >= z and bad <= 0.05 * max(1.0, per_tick * z)))
    rec["okWin"] = ok_win
    # AI 的地
    rec["ai"] = {t: dict(n=len(ai), land=sum(a[1] for a in ai), bal=sum(a[2] for a in ai)) for t, ai in X["aiAt"].items()}
    # 分窗收支
    led = []
    for k, (_nm, a, z) in enumerate(WINS):
        c0 = X["cp"].get(str(a))
        if not ok_win[k] or not c0:
            led.append(None)
            continue
        cell = {}
        for g in GROUPS:
            sel = [q for q in spawned if grp[q] == g and c0["terr"][q] > 0 and not (0 <= left_t[q] <= z)]
            cell[g] = dict(n=len(sel), land=sum(c0["terr"][q] for q in sel), bal=sum(c0["bal"][q] for q in sel),
                           gain=[sum(X["gain"][k][q][i] for q in sel) for i in range(9)],
                           reach=[sum(X["reach"][k][q][i] for q in sel) for i in range(7)],
                           size=[sum(X["size"][k][q][i] for q in sel) for i in range(20)],
                           cmds=[sum(X["cmds"][k][q][i] for q in sel) for i in range(3)],
                           zeroAi=sum(1 for q in sel if X["gain"][k][q][0] == 0), adjAi=sum(1 for q in sel if X["reach"][k][q][1] > 0),
                           adjZero=sum(1 for q in sel if X["reach"][k][q][1] > 0 and X["gain"][k][q][0] == 0))
        led.append(cell)
    rec["ledger"] = led
    # 规则照抄
    is_prot = [grp.get(q) in ("own", "pool") or "[npl]" in low[q] or "[nope]" in low[q] for q in range(H)]

    def src_group(q, t):
        if q is None or q < 0:
            return "none"
        if q >= H:
            return "ai"
        if 0 <= left_t[q] <= t:
            return "shell"
        return grp.get(q, "wild")

    dens = {t: rows for t, rows in X.get("dens", [])}
    rule = [{g: dict(cls={c: [0, 0, 0] for c in CLASSES}, sbSrc=Counter(), dpSrc=Counter(), okSmall=0, det=defaultdict(list)) for g in GROUPS} for _ in WINS]
    pts = {}
    for rw in X["rows"]:
        t, q = rw[0], rw[1]
        k = next((i for i, (_n, a, z) in enumerate(WINS) if a < t <= z), -1)
        if k < 0 or not ok_win[k] or q not in grp:
            continue
        if not any(not a[10] for a in rw[9]):
            continue                      # 只挨着空壳、不挨内置 AI 的样本不进这张表
        g = grp[q]
        own_c110 = g == "own" and c110
        protected = {o for o, _ in rw[8] if is_prot[o]} if own_c110 else ()
        dmed = None
        if t >= P["marketFrom"] and t in dens:
            ds = [b / tr for o, b, tr in dens[t]
                  if o != q and not (teams[q] > 0 and teams[o] == teams[q]) and not (own_c110 and is_prot[o])]
            dmed = statistics.median(ds) if ds else None
        cls, det = post_eval(rw, P, c110, protected, dmed, X["land"])
        cell = rule[k][g]
        a = cell["cls"][cls]
        a[0] += 1
        if rw[10] >= 0:
            a[1] += 1
            a[2] += rw[10]
        if cls in ("sb", "sb(cap)"):
            cell["sbSrc"][src_group(det["sbSrc"], t)] += 1
        if cls in ("dp", "dp(cap)"):
            cell["dpSrc"][src_group(det["dpSrc"], t)] += 1
        if cls == "ok" and det.get("okSmall"):
            cell["okSmall"] += 1
        if g == "own":
            pts[(t, q)] = cls
            d = cell["det"]
            d["dens|" + cls].append(round(det["dens"], 1))
            if cls in ("minCmd(want)", "minCmd(avail)", "chunk", "sb", "sb(cap)", "dp", "dp(cap)", "keep"):
                d["T|" + cls].append(det.get("T", 0))
                d["wantShare|" + cls].append(round(det.get("want", 0) / max(1, rw[2]), 4))
            if cls in ("sb", "sb(cap)", "dp", "dp(cap)"):
                d["safeShare|" + cls].append(round(det.get("safe", 0) / max(1, rw[2]), 3))
    for k in range(len(WINS)):
        for g in GROUPS:
            c = rule[k][g]
            c["sbSrc"], c["dpSrc"], c["det"] = dict(c["sbSrc"]), dict(c["dpSrc"]), dict(c["det"])
    rec["rule"] = rule
    rec["_pts"] = pts
    rec["_own"] = {q: (b.get("name") or names[q]) for q, b in own.items()}
    rec["_names"] = names
    return rec


def shadow_compare(rec):
    """和 shadow.mjs census2（跑真策略的 offers / safeAt）逐点对照：同一拍、同一个号，最便宜的非真人报价卡在哪一关。"""
    mid = rec["matchId"]
    p = os.path.join(OUT, mid, "shadow_census.json")
    if not os.path.exists(p):
        return None
    S = json.load(open(p, encoding="utf-8"))
    name_to_q = {str(n).strip().lower(): q for q, n in enumerate(rec["_names"])}
    same = diff = 0
    conf = Counter()
    for name, b in S["bots"].items():
        q = b.get("id")
        for r in b.get("census2", []):
            t, why = r[0], r[16]
            mine = rec["_pts"].get((t, q))
            if mine is None or why in ("noAI",):
                continue
            theirs = {"safe:sb": "sb", "safe:sb(cap)": "sb(cap)", "safe:people": "dp", "noOffer": "slot"}.get(why, why)
            mine2 = {"dp(cap)": "dp", "done": "slot"}.get(mine, mine)
            if theirs == mine2 or (theirs == "attacking" and mine2 == "ok") or (theirs == "ok" and mine2 == "ok"):
                same += 1
            else:
                diff += 1
                conf[(theirs, mine2)] += 1
    return dict(matchId=mid, strategy=S.get("strategy"), replayFrom=S.get("replayFrom"), same=same, diff=diff, conf=[[a, b, n] for (a, b), n in conf.most_common(8)])


def main():
    quiet = "--quiet" in sys.argv
    pool = name_pool()
    PARAMS = load_params()
    recs = []
    failed = []
    for mid, row in discovery_ids():
        if not os.path.exists(os.path.join(RUN, f"{mid}.json")):
            continue
        r = scan(mid, row, pool, PARAMS)
        if r is None:
            continue
        if "error" in r:
            failed.append(mid)
            continue
        recs.append(r)
    lines = []

    def Pn(s=""):
        lines.append(s)

    val = [r for r in recs if r["valid"]]
    Pn(f"[XP-A] 覆盖：跑了重演的 {len(recs) + len(failed)} 局（失败 {len(failed)}），own 对得上的 {len(val)} 局；各窗可用的局数："
       + "；".join(f"{nm} {sum(1 for r in val if r['okWin'][k])}" for k, (nm, _a, _z) in enumerate(WINS))
       + "。按编队档：" + "；".join(f"{c} " + " / ".join(str(sum(1 for r in val if r['okWin'][k] and r['cohort'] == c)) for k in range(len(WINS))) for c in ("squad10", "squad20")))
    late = [r for r in val if r["endTick"] >= 1800 and not all(r["okWin"][k] for k in range(len(WINS)) if r["endTick"] >= WINS[k][2])]
    Pn(f"  录像够长、但重演到后面对不上而丢掉某一窗的局：{len(late)}" + ("（" + "、".join(r["matchId"] for r in late) + "）" if late else ""))
    Pn("  同一个房间出现在两份 bundle 里的（野人会被数两次）见 [XP-H] 的备注。")

    # ---- [XP-B] ----
    Pn("")
    Pn("[XP-B] 内置 AI 还剩多少地（真值；own 对得上的局）：拍 | 局数 | 内置 AI 的地 ÷ 全图陆地 中位（下四分位 ~ 上四分位） | 还有地的内置 AI 个数 中位 | AI 一格地都不剩的局")
    agg_b = {}
    for t in ("1500", "1800", "2400", "3000"):
        sel = [r for r in val if t in r["ai"] and r["endTick"] >= int(t)]
        sh = sorted(r["ai"][t]["land"] / r["land"] for r in sel)
        if not sh:
            continue
        agg_b[t] = dict(n=len(sh), median=med(sh), q25=sh[len(sh) // 4], q75=sh[(3 * len(sh)) // 4], aiN=med([r["ai"][t]["n"] for r in sel]), zero=sum(1 for x in sh if x == 0))
        Pn(f"  {t} | {len(sh)} | {100 * med(sh):.1f}%（{100 * sh[len(sh) // 4]:.1f}% ~ {100 * sh[(3 * len(sh)) // 4]:.1f}%） | {fmt(med([r['ai'][t]['n'] for r in sel]), 0)} | {sum(1 for x in sh if x == 0)}")

    # ---- [XP-C] ----
    Pn("")
    Pn("[XP-C] 分窗收支（真值；人头 = 窗首还有地、到窗末没离开的席位）")
    Pn("  窗 | 组 | 局数 | 人头 | 窗首人均地 / 兵密度 | 从内置 AI：人均格 / 每格烧的兵 | 从空壳：人均格 / 每格烧的兵 | 从无主地：人均格 / 每格烧的兵 | 从在线真人：人均格 / 每格烧的兵 | 被真人拿走：人均格 | 人均净增")
    agg_c = {}
    for k, (nm, _a, _z) in enumerate(WINS):
        sel = [r for r in val if r["okWin"][k] and r["ledger"][k] and r["ledger"][k]["own"]["n"] >= 3 and r["ledger"][k]["wild"]["n"] >= 5]
        agg_c[nm] = dict(matches=len(sel), groups={})
        for g in GROUPS:
            n = sum(r["ledger"][k][g]["n"] for r in sel)
            if not n:
                continue
            land = sum(r["ledger"][k][g]["land"] for r in sel)
            bal = sum(r["ledger"][k][g]["bal"] for r in sel)
            gn = [sum(r["ledger"][k][g]["gain"][i] for r in sel) for i in range(9)]
            agg_c[nm]["groups"][g] = dict(heads=n, land=land, bal=bal, gain=gn)
            Pn(f"  {nm} | {CN[g]} | {len(sel)} | {n} | {land / n:.0f} / {bal / max(1, land):.1f} | {gn[0] / n:.0f} / {gn[1] / max(1, gn[0]):.1f} | {gn[7] / n:.0f} / {gn[8] / max(1, gn[7]):.1f} | "
               f"{gn[2] / n:.0f} / {gn[3] / max(1, gn[2]):.1f} | {gn[4] / n:.0f} / {gn[5] / max(1, gn[4]):.1f} | {gn[6] / n:.0f} | {(gn[0] + gn[7] + gn[2] + gn[4] - gn[6]) / n:+.0f}")

        def ratio_of(r, i):
            o, w = r["ledger"][k]["own"], r["ledger"][k]["wild"]
            if not w["gain"][i]:
                return None
            return (o["gain"][i] / o["n"]) / (w["gain"][i] / w["n"])

        def line(tag, sub):
            parts = []
            for i, cn in ((0, "内置 AI"), (7, "空壳"), (2, "无主地"), (4, "在线真人")):
                xs = [x for x in (ratio_of(r, i) for r in sub) if x is not None]
                parts.append(f"{cn} {fmt(med(xs))}（{len(xs)} 局，<1 的 {sum(1 for x in xs if x < 1)}）" if xs else f"{cn} —")
            return f"    {tag}逐局 own ÷ 野人（人均吃到的格）：" + "；".join(parts)

        Pn(line("", sel))
        for tag, fn in (("squad10·", lambda r: r["cohort"] == "squad10"), ("squad20·", lambda r: r["cohort"] == "squad20"), ("主队赢的局·", lambda r: r["won"]), ("没赢的局·", lambda r: not r["won"])):
            sub = [r for r in sel if fn(r)]
            if sub:
                Pn(line(tag, sub))
        z_own = sum(1 for r in sel if r["ledger"][k]["own"]["gain"][0] == 0)
        z_wild = sum(1 for r in sel if r["ledger"][k]["wild"]["gain"][0] == 0)
        heads_o = sum(r["ledger"][k]["own"]["n"] for r in sel)
        heads_w = sum(r["ledger"][k]["wild"]["n"] for r in sel)
        Pn(f"    这一窗 own 一格内置 AI 的地都没吃到的局 {z_own}/{len(sel)}，野人 {z_wild}/{len(sel)}；一格都没吃到的人头：own {sum(r['ledger'][k]['own']['zeroAi'] for r in sel)}/{heads_o}"
           f"（{pct(sum(r['ledger'][k]['own']['zeroAi'] for r in sel), heads_o)}），野人 {sum(r['ledger'][k]['wild']['zeroAi'] for r in sel)}/{heads_w}（{pct(sum(r['ledger'][k]['wild']['zeroAi'] for r in sel), heads_w)}）；"
           f"窗里挨着过内置 AI 的人头里一格都没吃到的：own {sum(r['ledger'][k]['own']['adjZero'] for r in sel)}/{sum(r['ledger'][k]['own']['adjAi'] for r in sel)}"
           f"（{pct(sum(r['ledger'][k]['own']['adjZero'] for r in sel), sum(r['ledger'][k]['own']['adjAi'] for r in sel))}），"
           f"野人 {sum(r['ledger'][k]['wild']['adjZero'] for r in sel)}/{sum(r['ledger'][k]['wild']['adjAi'] for r in sel)}"
           f"（{pct(sum(r['ledger'][k]['wild']['adjZero'] for r in sel), sum(r['ledger'][k]['wild']['adjAi'] for r in sel))}）")
        agg_c[nm].update(ownZeroMatches=z_own, wildZeroMatches=z_wild)

    # ---- [XP-D] ----
    Pn("")
    Pn("[XP-D] 接壤普查（真值；每 30 拍一个样本）：窗 | 组 | 局数 | 样本 | 挨着内置 AI | 挨着空壳 | 挨着无主地 | 挨着内置 AI 的样本里：挨着的 AI 地合计的均值 | 90 拍内出手（落在内置 AI 上） | 逐局 own ÷ 野人 的出手占比 中位")
    agg_d = {}
    for k, (nm, _a, _z) in enumerate(WINS):
        sel = [r for r in val if r["okWin"][k] and r["ledger"][k] and r["ledger"][k]["own"]["n"] >= 3 and r["ledger"][k]["wild"]["n"] >= 5]
        agg_d[nm] = {}
        pm = []
        for r in sel:
            o, w = r["ledger"][k]["own"]["reach"], r["ledger"][k]["wild"]["reach"]
            if o[6] >= 10 and w[6] >= 10 and w[5] > 0:
                pm.append((o[5] / o[6]) / (w[5] / w[6]))
        for g in GROUPS:
            rc = [sum(r["ledger"][k][g]["reach"][i] for r in sel) for i in range(7)]
            if not rc[0]:
                continue
            agg_d[nm][g] = rc
            Pn(f"  {nm} | {CN[g]} | {len(sel)} | {rc[0]} | {pct(rc[1], rc[0])} | {pct(rc[2], rc[0])} | {pct(rc[3], rc[0])} | {rc[4] / max(1, rc[1]):.0f} | {rc[5]}/{rc[6]}（{pct(rc[5], rc[6])}） | "
               + (f"{fmt(med(pm))}（{len(pm)} 局，<1 的 {sum(1 for x in pm if x < 1)}）" if g == "own" and pm else "—"))

    # ---- [XP-E] ----
    Pn("")
    Pn("[XP-E] 规则照抄（真值上的引擎状态；挨着内置 AI 的样本；只看内置 AI 的报价）")
    agg_e = {}

    def rule_table(tag, sel, groups=("own", "wild")):
        out = {}
        for k, (nm, _a, _z) in enumerate(WINS):
            ss = [r for r in sel if r["okWin"][k]]
            for g in groups:
                tot = {c: [sum(r["rule"][k][g]["cls"][c][i] for r in ss) for i in range(3)] for c in CLASSES}
                n = sum(v[0] for v in tot.values())
                if not n:
                    continue
                out[f"{nm}|{g}"] = dict(n=n, cls=tot)
                Pn(f"  {tag}{nm} | {CN[g]} | {len(ss)} 局 | 样本 {n} | "
                   + "；".join(f"{CLS_CN[c]} {pct(tot[c][0], n)}（出手 {pct(tot[c][2], tot[c][1])}）" for c in CLASSES if tot[c][0]))
        return out

    Pn("  读法：每一格 = 这一类占样本的比例（括号里 = 这一类样本里 90 拍内真有一条生效陆攻落在内置 AI 身上的占比）。")
    agg_e["all"] = rule_table("全部·", val)
    agg_e["squad20"] = rule_table("squad20（c110 的规则）·", [r for r in val if r["cohort"] == "squad20"])
    agg_e["squad10"] = rule_table("squad10（c116 的规则）·", [r for r in val if r["cohort"] == "squad10"])
    # 合并成三大类
    Pn("  合并成三类（own）：窗 | 档 | 样本 | 规则放行（ok）| 已经在打 / 兵已压够 | 被挡（其余各类合计）| 其中：safe（sb / dpKeep，含封顶）| keep | 报价 ≥ worth | minCmd | chunk | 槽满")
    agg_e["merged"] = {}
    for k, (nm, _a, _z) in enumerate(WINS):
        for coh in ("squad10", "squad20"):
            ss = [r for r in val if r["okWin"][k] and r["cohort"] == coh]
            tot = {c: sum(r["rule"][k]["own"]["cls"][c][0] for r in ss) for c in CLASSES}
            n = sum(tot.values())
            if not n:
                continue
            safe = tot["sb"] + tot["sb(cap)"] + tot["dp"] + tot["dp(cap)"]
            mc = tot["minCmd(want)"] + tot["minCmd(avail)"]
            busy = tot["attacking"] + tot["done"]
            blocked = n - tot["ok"] - busy
            agg_e["merged"][f"{nm}|{coh}"] = dict(n=n, ok=tot["ok"], busy=busy, blocked=blocked, safe=safe, keep=tot["keep"], price=tot["price"], minCmd=mc, chunk=tot["chunk"], slot=tot["slot"])
            Pn(f"    {nm} | {coh} | {n} | {pct(tot['ok'], n)} | {pct(busy, n)} | {pct(blocked, n)} | {pct(safe, n)} | {pct(tot['keep'], n)} | {pct(tot['price'], n)} | {pct(mc, n)} | {pct(tot['chunk'], n)} | {pct(tot['slot'], n)}")
    # safe 的来源
    Pn("  safe 起作用的那些样本（own），那个数是谁的兵：窗 | 档 | sb 类样本 → 来源 | dpKeep 类样本 → 来源")
    agg_e["src"] = {}
    for k, (nm, _a, _z) in enumerate(WINS):
        for coh in ("squad10", "squad20"):
            ss = [r for r in val if r["okWin"][k] and r["cohort"] == coh]
            sbs, dps = Counter(), Counter()
            for r in ss:
                sbs.update(r["rule"][k]["own"]["sbSrc"])
                dps.update(r["rule"][k]["own"]["dpSrc"])
            if not sbs and not dps:
                continue
            agg_e["src"][f"{nm}|{coh}"] = dict(sb=dict(sbs), dp=dict(dps))
            f1 = "、".join(f"{SRC_CN[s]} {pct(sbs[s], sum(sbs.values()))}" for s in SRC if sbs[s]) or "—"
            f2 = "、".join(f"{SRC_CN[s]} {pct(dps[s], sum(dps.values()))}" for s in SRC if dps[s]) or "—"
            Pn(f"    {nm} | {coh} | {sum(sbs.values())} → {f1} | {sum(dps.values())} → {f2}")
    # 各类样本的画像
    Pn("  各类样本的画像（own；中位）：窗 | 档 | 类 | 样本 | 本号兵密度 | 最便宜那个内置 AI 的地 | 吃光它要的 want ÷ 本号余额 | safe ÷ 本号余额")
    agg_e["profile"] = {}
    for k, (nm, _a, _z) in enumerate(WINS):
        for coh in ("squad10", "squad20"):
            ss = [r for r in val if r["okWin"][k] and r["cohort"] == coh]
            for c in CLASSES:
                dn = [x for r in ss for x in r["rule"][k]["own"]["det"].get("dens|" + c, [])]
                if len(dn) < 20:
                    continue
                tt = [x for r in ss for x in r["rule"][k]["own"]["det"].get("T|" + c, [])]
                ws = [x for r in ss for x in r["rule"][k]["own"]["det"].get("wantShare|" + c, [])]
                sf = [x for r in ss for x in r["rule"][k]["own"]["det"].get("safeShare|" + c, [])]
                agg_e["profile"][f"{nm}|{coh}|{c}"] = dict(n=len(dn), dens=med(dn), T=med(tt), wantShare=med(ws), safeShare=med(sf))
                Pn(f"    {nm} | {coh} | {CLS_CN[c]} | {len(dn)} | {fmt(med(dn), 1)} | {fmt(med(tt), 0)} | {('%.1f%%' % (100 * med(ws))) if ws else '—'} | {('%.2f' % med(sf)) if sf else '—'}")
    sm = {coh: [sum(r["rule"][k]["own"]["okSmall"] for r in val if r["okWin"][k] and r["cohort"] == coh) for k in range(len(WINS))] for coh in ("squad10", "squad20")}
    okn = {coh: [sum(r["rule"][k]["own"]["cls"]["ok"][0] for r in val if r["okWin"][k] and r["cohort"] == coh) for k in range(len(WINS))] for coh in ("squad10", "squad20")}
    Pn("  规则放行的样本里，放行的那一单不到 minCmd（4 倍手续费）的：" + "；".join(
        f"{coh} " + " / ".join(f"{sm[coh][k]}/{okn[coh][k]}（{pct(sm[coh][k], okn[coh][k])}）" for k in range(len(WINS))) for coh in ("squad10", "squad20")) + "（三个窗）")
    agg_e["okSmall"] = dict(small=sm, ok=okn)

    # ---- [XP-F] ----
    Pn("")
    Pn("[XP-F] 生效的陆攻按目标（真值）：窗 | 组 | 目标 | 条数 | 人均条数 | 一条派出的兵（均值） | 一条占发令前余额（均值） | 手续费合计 ÷ 派出的兵合计 | 派出的兵不到 4 倍手续费的条数")
    agg_f = {}
    TG = ("内置 AI", "空壳", "在线真人", "无主地")
    for k, (nm, _a, _z) in enumerate(WINS):
        sel = [r for r in val if r["okWin"][k] and r["ledger"][k] and r["ledger"][k]["own"]["n"] >= 3 and r["ledger"][k]["wild"]["n"] >= 5]
        for g in ("own", "wild"):
            n = sum(r["ledger"][k][g]["n"] for r in sel)
            sz = [sum(r["ledger"][k][g]["size"][i] for r in sel) for i in range(20)]
            cm = [sum(r["ledger"][k][g]["cmds"][i] for r in sel) for i in range(3)]
            agg_f[f"{nm}|{g}"] = dict(heads=n, size=sz, cmds=cm)
            for j, tg in enumerate(TG):
                o = 5 * j
                if not sz[o]:
                    continue
                Pn(f"  {nm} | {CN[g]} | {tg} | {sz[o]} | {sz[o] / max(1, n):.2f} | {sz[o + 1] / sz[o]:.0f} | {100 * sz[o + 2] / sz[o]:.1f}% | {pct(sz[o + 3], sz[o + 1], 1)} | {sz[o + 4]}（{pct(sz[o + 4], sz[o])}）")
            Pn(f"  {nm} | {CN[g]} | 落地的陆攻 {cm[0]}，生效 {cm[1]}，没生效 {pct(cm[0] - cm[1], cm[0])}，目标 512 占 {pct(cm[2], cm[0])}")
        for coh in ("squad10", "squad20"):
            ss = [r for r in sel if r["cohort"] == coh]
            n = sum(r["ledger"][k]["own"]["n"] for r in ss)
            sz = [sum(r["ledger"][k]["own"]["size"][i] for r in ss) for i in range(20)]
            if sz[0]:
                agg_f[f"{nm}|own|{coh}"] = dict(heads=n, size=sz)
                Pn(f"    {nm} | own·{coh} | 内置 AI | {sz[0]} | {sz[0] / max(1, n):.2f} | {sz[1] / sz[0]:.0f} | {100 * sz[2] / sz[0]:.1f}% | {pct(sz[3], sz[1], 1)} | {sz[4]}（{pct(sz[4], sz[0])}）")

    # ---- [XP-G] ----
    Pn("")
    Pn("[XP-G] 和影子普查逐点对照（shadow.mjs census2 在重演里跑真策略的 offers / safeAt；这里是照抄的规则。同一拍、同一个号，最便宜的内置 AI 报价卡在哪一关）")
    agg_g = []
    for r in val:
        sc = shadow_compare(r)
        if not sc or not (sc["same"] + sc["diff"]):
            continue
        agg_g.append(sc)
        Pn(f"  {sc['matchId']}（影子用的策略档 {sc['strategy']}" + (f"，录像取自 {sc['replayFrom']}" if sc.get("replayFrom") else "") + f"）：对上 {sc['same']}/{sc['same'] + sc['diff']}"
           + ("；对不上的（影子 → 照抄）：" + "、".join(f"{a} → {b} ×{n}" for a, b, n in sc["conf"]) if sc["diff"] else ""))
    if agg_g:
        s_, d_ = sum(x["same"] for x in agg_g), sum(x["diff"] for x in agg_g)
        Pn(f"  合计：对上 {s_}/{s_ + d_}（{pct(s_, s_ + d_)}）")
    else:
        Pn("  （没有可对照的点）")

    # ---- [XP-H] ----
    Pn("")
    Pn("[XP-H] 逐局：局 | 档 | 真人 | own/[APEX]/名字池/野人 | 重演到 | 核对 | 三个窗可用 | (1500,1800] own / 野人 人均吃内置 AI 的格 | (1800,2400] | (2400,3000] | 主队赢")
    for r in recs:
        cells = []
        for k in range(len(WINS)):
            c = r["ledger"][k] if r["valid"] else None
            if not c or not c["own"]["n"] or not c["wild"]["n"]:
                cells.append("—")
            else:
                cells.append(f"{c['own']['gain'][0] / c['own']['n']:.0f} / {c['wild']['gain'][0] / c['wild']['n']:.0f}")
        Pn(f"  {r['matchId']} | {r['cohort']} | {r['H']} | {r['size']['own']}/{r['size']['apex']}/{r['size']['pool']}/{r['size']['wild']} | {r['endTick']} | {r['exact']}/{r['rows']} | "
           + "".join("✓" if x else "✗" for x in r["okWin"]) + " | " + " | ".join(cells) + f" | {'是' if r['won'] else '否'}")
    Pn("  备注：A051 和 B033 是同一个房间的两份 bundle（各自的 own 不同，野人相同）；B033 自己的录像只到 1848 拍。")

    os.makedirs(os.path.join(OUT, "_cross"), exist_ok=True)
    with open(os.path.join(OUT, "_cross", "xpost.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    for r in recs:
        for k in list(r.keys()):
            if k.startswith("_"):
                del r[k]
        for k in range(len(WINS)):
            for g in GROUPS:
                r["rule"][k][g].pop("det", None)
    with open(os.path.join(OUT, "_cross", "xpost.json"), "w", encoding="utf-8") as f:
        json.dump(dict(replays=len(recs), valid=len(val), failed=failed, ai=agg_b, ledger=agg_c, reach=agg_d, rule=agg_e, attacks=agg_f, shadow=agg_g, matches=recs), f, ensure_ascii=False)
    if not quiet:
        print("\n".join(lines))
    else:
        print(f"xpost: {len(recs)} 局，own 对得上 {len(val)} 局 → out/_cross/xpost.txt")


if __name__ == "__main__":
    main()
