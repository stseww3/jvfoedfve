#!/usr/bin/env python3
"""xbatch.py — 发现集全部录像的「指令流」机械计数：成批落地、连发串、出生期选点条数、离开指令。只解码录像，不做地图模拟。

先解码（重计算闸；107 份录像合计不到 1 秒）：
    bash c136-review/tools/run-heavy.sh node c136-review/agents/R08/scripts/replay_cmds.mjs \
         --out-dir c136-review/agents/R08/out/_run/streams <局> <局> …
再计数：
    python3 xbatch.py [--mine]        → out/_cross/xbatch.txt、xbatch.json

只读 /agent/repos/c136-data/bundles/（发现集）；验证集不碰。out/_run/ 不入库，随时可以按上面两步重建。

真人席位分四组（按录像头里的名字）：
  · 本编队 own：日志里这支编队的号（facts 的 me），且录像里这个席位的名字以它的某个日志标签结尾（对不上就不算——
    一个包里混了别的房间的录像时全部对不上，这一局记 ownMatched=0）；
  · [APEX]：名字带 [APEX] 标签、又不在 own 里的（同房的另一支 10 号编队）；
  · 名字池 pool：名字在 c110 的 SQUAD_POOL_SET 里（src/strategy/v27-team-c110.js 第 1 行）、又不在 own 里的
    （同房的另一支 20 号编队，或者名字撞进名字池的野人）；
  · 野人 wild：其余真人。
  「机器号」= own + [APEX] + pool。

口径：
  · 指令只数 陆攻(1) / 捐款(2) / 发船(3)，按录像里的执行拍分四段：0~600、600~1500、1500~3000、3000+。
  · 批 = 同一个席位在同一执行拍落地 ≥3 条；连发串 = 同席位、同类、同目标的指令，相邻两条执行拍相差 ≤14 拍（串里第 2 条起算「多出来的」）。
  · 目标 512 = 陆攻的目标在录像里记成无主地（本来就打无主地，或者目标已出局被引擎改写——单看指令流分不开，只作旁证）。
  · 成批波段 = 180 拍窗里机器号的指令 ≥10 条且其中 ≥30% 落在批里的窗；给出首末窗。
节：
  [XB-A] 逐局   [XB-B] 按编队档 × 时段的合计   [XB-C] 命中局数   [XB-D] 出生期选点条数   [XB-E] 成批波段的位置   [XB-F] 一拍最多几条
"""
import json
import os
import re
import statistics
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import facts  # noqa: E402
import r08lib as L  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")
RUN = os.path.join(OUT, "_run", "streams")
PERIODS = [("0~600", 0, 600), ("600~1500", 600, 1500), ("1500~3000", 1500, 3000), ("3000+", 3000, 10 ** 9)]
GROUPS = ("own", "apex", "pool", "wild")
GROUP_CN = dict(own="本编队", apex="[APEX]", pool="名字池", wild="野人", bot="机器号")
MINE = ["G02", "G05", "G08", "B043", "B033", "B034", "B031", "B049", "B006", "B030", "B019", "B009", "B015", "B029", "B035", "B027"]


def name_pool():
    src = os.path.join(L.DATA, "src", "strategy", "v27-team-c110.js")
    with open(src, encoding="utf-8") as f:
        line = f.readline()
    m = re.search(r"new Set\((\[.*?\])\)", line)
    return set(json.loads(m.group(1)))


def discovery_ids():
    with open(os.path.join(L.DATA, "manifest.jsonl"), encoding="utf-8") as f:
        rows = [json.loads(x) for x in f if x.strip()]
    return [(r["matchId"], r) for r in rows if r.get("split") == "discovery"]


def period_of(t):
    for i, (_, a, z) in enumerate(PERIODS):
        if a <= t < z:
            return i
    return len(PERIODS) - 1


def scan(mid, card, pool):
    p = os.path.join(RUN, f"{mid}.json")
    if not os.path.exists(p):
        return None
    S = json.load(open(p, encoding="utf-8"))
    meta, cmds = S["meta"], S["cmds"]
    H = meta["humanCount"]
    names = [str(x).strip() for x in (meta.get("names") or [""] * H)]
    low = [x.lower() for x in names]
    F = facts.build(mid)
    own = set()
    for me, b in F["bots"].items():
        mr = b.get("meReal") if b.get("meReal") is not None else me
        if mr is not None and 0 <= mr < H and any(low[mr].endswith(lab.lower()) for lab in b["labels"]):
            own.add(mr)
    grp = {}
    for q in range(H):
        if q in own:
            grp[q] = "own"
        elif "[apex]" in low[q]:
            grp[q] = "apex"
        elif low[q] in pool or re.sub(r"^\[[^\]]*\]\s*", "", low[q]) in pool:
            grp[q] = "pool"
        else:
            grp[q] = "wild"
    size = Counter(grp.values())
    # 出生期选点条数（t = -1 的 0 号指令）
    picks = Counter()
    for t, cid, pl, dx, dz in cmds:
        if cid == 0 and pl < H:
            picks[pl] += 1
    pick_med = {}
    for g in GROUPS:
        xs = [picks.get(q, 0) for q in range(H) if grp[q] == g and picks.get(q, 0) > 0]
        pick_med[g] = statistics.median(xs) if xs else None
    # 离开指令（8 / 9）
    leaves = defaultdict(list)
    for t, cid, pl, dx, dz in cmds:
        if cid in (8, 9) and pl < H:
            leaves[grp[pl]].append(t)
    # 批、连发串、目标 512
    per_tick = defaultdict(int)
    keep = defaultdict(lambda: 1.0)   # 这一拍几条指令按顺序各拿走余额的 pct/1024 之后还剩的比例（名义值）
    acts = []
    for t, cid, pl, dx, dz in cmds:
        if t < 0 or pl >= H or cid not in (1, 2, 3):
            continue
        per_tick[(pl, t)] += 1
        keep[(pl, t)] *= max(0.0, 1 - min(dx, 1024) / 1024)
        acts.append((pl, cid, dz, t, dx))
    stat = {g: [dict(cmds=0, batches=0, batchCmds=0, maxBatch=0, pairs=0, chains=0, chainExtra=0, atk=0, atk512=0, drain50=0, drain90=0, players=set())
                for _ in PERIODS] for g in GROUPS}
    for pl, cid, dz, t, dx in acts:
        s = stat[grp[pl]][period_of(t)]
        s["cmds"] += 1
        s["players"].add(pl)
        if cid == 1:
            s["atk"] += 1
            if dz == 512:
                s["atk512"] += 1
    for (pl, t), n in per_tick.items():
        s = stat[grp[pl]][period_of(t)]
        if n >= 3:
            s["batches"] += 1
            s["batchCmds"] += n
            s["maxBatch"] = max(s["maxBatch"], n)
            if keep[(pl, t)] <= 0.5:
                s["drain50"] += 1
            if keep[(pl, t)] <= 0.1:
                s["drain90"] += 1
        elif n == 2:
            s["pairs"] += 1
    last = {}
    run_len = {}
    for pl, cid, dz, t, dx in sorted(acts, key=lambda x: (x[0], x[1], x[2], x[3])):
        key = (pl, cid, dz)
        s = stat[grp[pl]][period_of(t)]
        if key in last and t - last[key] <= 14:
            run_len[key] += 1
            if run_len[key] == 2:
                s["chains"] += 1
            s["chainExtra"] += 1
        else:
            run_len[key] = 1
        last[key] = t
    for g in GROUPS:
        for s in stat[g]:
            s["players"] = len(s["players"])
    # 成批波段：180 拍窗，机器号
    win = defaultdict(lambda: [0, 0])
    for (pl, t), n in per_tick.items():
        if grp[pl] == "wild":
            continue
        w = t // 180 * 180
        win[w][0] += n
        if n >= 3:
            win[w][1] += n
    wave = sorted(w for w, (c, bc) in win.items() if c >= 10 and bc >= 0.3 * c)
    return dict(matchId=mid, cohort=card.get("cohort"), mode=card.get("mode"), H=H, numberTeams=meta.get("numberTeams"), gameMode=meta.get("gameMode"),
                lastTick=meta.get("lastTick"), squadBotsLog=len(F["bots"]), ownMatched=len(own), size={g: size.get(g, 0) for g in GROUPS},
                stat=stat, pickMedian=pick_med, leaves={g: sorted(v) for g, v in leaves.items()},
                waveWindows=wave, waveFirst=(wave[0] if wave else None), waveLast=(wave[-1] + 180 if wave else None),
                primaryTeamWon=(card.get("outcome") or {}).get("primaryTeamWon"))


def add(dst, src):
    for k in ("cmds", "batches", "batchCmds", "pairs", "chains", "chainExtra", "atk", "atk512", "drain50", "drain90", "players"):
        dst[k] = dst.get(k, 0) + src[k]
    dst["maxBatch"] = max(dst.get("maxBatch", 0), src["maxBatch"])
    dst["matches"] = dst.get("matches", 0) + (1 if src["cmds"] else 0)
    dst["matchesWithBatch"] = dst.get("matchesWithBatch", 0) + (1 if src["batches"] else 0)


def pct(a, b):
    return "–" if not b else f"{100 * a / b:.1f}%"


def main():
    mine_only = "--mine" in sys.argv
    pool = name_pool()
    rows = []
    for mid, card in discovery_ids():
        if mine_only and mid not in MINE:
            continue
        try:
            r = scan(mid, card, pool)
        except Exception as e:  # noqa: BLE001
            print(f"{mid}: 失败 {e!r}", file=sys.stderr)
            continue
        if r:
            rows.append(r)
    out = [f"[XB-A] 发现集录像指令流（{len(rows)} 份录像；名字池 {len(pool)} 个名字）。逐局：局 | 编队档 | 真人席位 | 录像末拍 | 席位数 本编队(日志里的号数) / [APEX] / 名字池 / 野人 | "
           "600~1500：机器号 指令 / 批 / 批里的指令 / 一拍最多 | 野人 指令 / 批 | 1500~3000：机器号 指令 / 批 / 批里的指令 | 野人 指令 / 批 | 成批波段 首窗~末窗"]

    def bot_sum(r, i):
        d = {}
        for g in ("own", "apex", "pool"):
            add(d, r["stat"][g][i])
        return d
    for r in rows:
        b1, b2 = bot_sum(r, 1), bot_sum(r, 2)
        w1, w2 = r["stat"]["wild"][1], r["stat"]["wild"][2]
        wave = "–" if r["waveFirst"] is None else f"{r['waveFirst']}~{r['waveLast']}（{len(r['waveWindows'])} 窗）"
        out.append(f"    {r['matchId']} | {r['cohort']} | {r['H']} | {r['lastTick']} | {r['size']['own']}({r['squadBotsLog']}) / {r['size']['apex']} / {r['size']['pool']} / {r['size']['wild']} | "
                   f"{b1['cmds']} / {b1['batches']} / {b1['batchCmds']} / {b1['maxBatch']} | {w1['cmds']} / {w1['batches']} | "
                   f"{b2['cmds']} / {b2['batches']} / {b2['batchCmds']} | {w2['cmds']} / {w2['batches']} | {wave}")
    # [XB-B] 合计
    out.append("[XB-B] 合计（全部录像）：时段 | 组 | 有指令的局数 | 席位·局 | 指令 | 批（≥3 条同拍）| 批里的指令（占指令 %）| 有批的局数 | 一拍最多 | 同拍 2 条的次数 | "
               "连发串 / 串里多出来的指令（占指令 %）| 陆攻 / 其中目标 512（%）| 名义上一拍拿走 ≥50% / ≥90% 余额的批")
    agg = {}
    for i, (pn, _, _) in enumerate(PERIODS):
        for g in GROUPS + ("bot",):
            d = {}
            for r in rows:
                if g == "bot":
                    for gg in ("own", "apex", "pool"):
                        add(d, r["stat"][gg][i])
                    # 一局里三组合并只算一局
                else:
                    add(d, r["stat"][g][i])
            if g == "bot":
                d["matches"] = sum(1 for r in rows if any(r["stat"][gg][i]["cmds"] for gg in ("own", "apex", "pool")))
                d["matchesWithBatch"] = sum(1 for r in rows if any(r["stat"][gg][i]["batches"] for gg in ("own", "apex", "pool")))
            agg[(pn, g)] = d
            out.append(f"    {pn} | {GROUP_CN[g]} | {d.get('matches', 0)} | {d.get('players', 0)} | {d.get('cmds', 0)} | {d.get('batches', 0)} | "
                       f"{d.get('batchCmds', 0)}（{pct(d.get('batchCmds', 0), d.get('cmds', 0))}）| {d.get('matchesWithBatch', 0)} | {d.get('maxBatch', 0)} | {d.get('pairs', 0)} | "
                       f"{d.get('chains', 0)} / {d.get('chainExtra', 0)}（{pct(d.get('chainExtra', 0), d.get('cmds', 0))}）| {d.get('atk', 0)} / {d.get('atk512', 0)}（{pct(d.get('atk512', 0), d.get('atk', 0))}）| "
                       f"{d.get('drain50', 0)} / {d.get('drain90', 0)}")
    # [XB-B2] 按编队档
    out.append("[XB-B2] 按编队档（600~1500 和 1500~3000 两段）：编队档 | 时段 | 录像数 | 机器号 指令 / 批 / 批里的指令（%）/ 有批的局数 | 野人 指令 / 批 / 批里的指令（%）/ 有批的局数")
    cohorts = sorted({r["cohort"] for r in rows})
    by_cohort = {}
    for c in cohorts:
        for i in (1, 2):
            rs = [r for r in rows if r["cohort"] == c]
            b, w = {}, {}
            for r in rs:
                for gg in ("own", "apex", "pool"):
                    add(b, r["stat"][gg][i])
                add(w, r["stat"]["wild"][i])
            nb = sum(1 for r in rs if any(r["stat"][gg][i]["batches"] for gg in ("own", "apex", "pool")))
            by_cohort[(c, PERIODS[i][0])] = dict(replays=len(rs), bot=b, wild=w, botMatchesWithBatch=nb)
            out.append(f"    {c} | {PERIODS[i][0]} | {len(rs)} | {b.get('cmds', 0)} / {b.get('batches', 0)} / {b.get('batchCmds', 0)}（{pct(b.get('batchCmds', 0), b.get('cmds', 0))}）/ {nb} | "
                       f"{w.get('cmds', 0)} / {w.get('batches', 0)} / {w.get('batchCmds', 0)}（{pct(w.get('batchCmds', 0), w.get('cmds', 0))}）/ {w.get('matchesWithBatch', 0)}")
    # [XB-C] 命中局数
    long_ = [r for r in rows if (r["lastTick"] or 0) >= 1500]
    c1 = [r for r in long_ if any(r["stat"][g][1]["batches"] for g in ("own", "apex", "pool"))]
    c2 = [r for r in c1 if r["stat"]["wild"][1]["batches"] == 0]
    c3 = [r for r in long_ if r["stat"]["wild"][1]["batches"] > 0]
    out.append(f"[XB-C] 录像到 1500 拍以后的 {len(long_)} 局里：600~1500 机器号有批的 {len(c1)} 局；其中野人一批都没有的 {len(c2)} 局；野人有批的 {len(c3)} 局"
               f"（{'、'.join(r['matchId'] + ':' + str(r['stat']['wild'][1]['batches']) for r in c3) or '无'}）")
    heavy = sorted(long_, key=lambda r: -sum(r["stat"][g][1]["batchCmds"] for g in ("own", "apex", "pool")))[:12]
    out.append("    600~1500 机器号批里指令最多的 12 局：" + "、".join(
        f"{r['matchId']} {sum(r['stat'][g][1]['batchCmds'] for g in ('own', 'apex', 'pool'))}/{sum(r['stat'][g][1]['cmds'] for g in ('own', 'apex', 'pool'))}" for r in heavy))
    none = [r["matchId"] for r in long_ if not any(r["stat"][g][i]["batches"] for g in ("own", "apex", "pool") for i in (1, 2))]
    out.append(f"    600~3000 机器号一批都没有的 {len(none)} 局：" + ("、".join(none) or "无"))
    # 胜负对照（主队胜 / 负）
    for lab, pred in (("主队胜", lambda r: r["primaryTeamWon"]), ("主队负", lambda r: not r["primaryTeamWon"])):
        rs = [r for r in long_ if pred(r)]
        xs = []
        for r in rs:
            c = sum(r["stat"][g][1]["cmds"] for g in ("own", "apex", "pool"))
            bc = sum(r["stat"][g][1]["batchCmds"] for g in ("own", "apex", "pool"))
            if c:
                xs.append(bc / c)
        out.append(f"    {lab} {len(rs)} 局：600~1500 机器号『批里的指令 ÷ 指令』的中位 {('%.1f%%' % (100 * statistics.median(xs))) if xs else '–'}，"
                   f"≥30% 的 {sum(1 for x in xs if x >= 0.3)} 局，= 0 的 {sum(1 for x in xs if x == 0)} 局")
    # [XB-D] 出生期选点
    out.append("[XB-D] 出生期每个席位落地的选点指令条数（只数落地 ≥1 条的席位，取每局中位，再看各局）：组 | 局数 | 各局中位的中位 | 四分位 | 最大")
    pick_summary = {}
    for g in GROUPS:
        xs = sorted(r["pickMedian"][g] for r in rows if r["pickMedian"].get(g) is not None)
        if xs:
            q = statistics.quantiles(xs, n=4) if len(xs) >= 4 else [xs[0], statistics.median(xs), xs[-1]]
            pick_summary[g] = dict(n=len(xs), median=statistics.median(xs), q1=q[0], q3=q[2], max=xs[-1])
            out.append(f"    {GROUP_CN[g]} | {len(xs)} | {statistics.median(xs)} | {q[0]}~{q[2]} | {xs[-1]}")
    # [XB-E] 成批波段
    wv = [r for r in long_ if r["waveFirst"] is not None]
    out.append(f"[XB-E] 成批波段（180 拍窗里机器号指令 ≥10 条且 ≥30% 落在批里）：录像到 1500 拍以后的 {len(long_)} 局里 {len(wv)} 局有；"
               f"首窗起点的中位 {statistics.median([r['waveFirst'] for r in wv]) if wv else '–'}，末窗终点的中位 {statistics.median([r['waveLast'] for r in wv]) if wv else '–'}")
    hist = Counter()
    for r in wv:
        for w in r["waveWindows"]:
            hist[w] += 1
    out.append("    各 180 拍窗命中的局数：" + "、".join(f"{w}:{n}" for w, n in sorted(hist.items()) if w < 5400))
    first_hist = Counter((r["waveFirst"] // 180 * 180) for r in wv)
    out.append("    首窗起点的分布：" + "、".join(f"{w}:{n}" for w, n in sorted(first_hist.items())))
    # [XB-F] 一拍最多几条
    mb = Counter()
    for r in rows:
        m = max(r["stat"][g][i]["maxBatch"] for g in ("own", "apex", "pool") for i in range(4))
        mb[m] += 1
    out.append("[XB-F] 机器号一个席位一拍最多落地几条（每局取最大）：" + "、".join(f"{k} 条:{n} 局" for k, n in sorted(mb.items())))
    mw = Counter()
    for r in rows:
        mw[max(r["stat"]["wild"][i]["maxBatch"] for i in range(4))] += 1
    out.append("    野人（每局取最大；0 = 没有 ≥3 条的拍）：" + "、".join(f"{k} 条:{n} 局" for k, n in sorted(mw.items())))
    # [XB-H] 房间大小
    out.append("[XB-H] 房间大小（真人席位数）和 600~1500 的批（只看录像到 1500 拍以后的局）：席位数 | 局数 | 机器号 指令 / 批里的指令（%）| 各局占比的中位 | 一批都没有的局 | 野人 批里的指令占比")
    by_size = {}
    for lab, lo, hi in (("≤30", 0, 30), ("31~60", 31, 60), ("61~90", 61, 90), ("≥91", 91, 10 ** 6)):
        rs = [r for r in long_ if lo <= r["H"] <= hi]
        c = sum(r["stat"][g][1]["cmds"] for r in rs for g in ("own", "apex", "pool"))
        bc = sum(r["stat"][g][1]["batchCmds"] for r in rs for g in ("own", "apex", "pool"))
        xs = [sum(r["stat"][g][1]["batchCmds"] for g in ("own", "apex", "pool")) / max(1, sum(r["stat"][g][1]["cmds"] for g in ("own", "apex", "pool"))) for r in rs
              if sum(r["stat"][g][1]["cmds"] for g in ("own", "apex", "pool"))]
        wc = sum(r["stat"]["wild"][1]["cmds"] for r in rs)
        wb = sum(r["stat"]["wild"][1]["batchCmds"] for r in rs)
        by_size[lab] = dict(replays=len(rs), cmds=c, batchCmds=bc, median=(statistics.median(xs) if xs else None), zero=sum(1 for x in xs if x == 0))
        out.append(f"    {lab} | {len(rs)} | {c} / {bc}（{pct(bc, c)}）| {('%.1f%%' % (100 * statistics.median(xs))) if xs else '–'} | {sum(1 for x in xs if x == 0)} | {pct(wb, wc)}")
    lv = [(r["matchId"], len(r["leaves"].get("own", [])), r["size"]["own"]) for r in rows if r["leaves"].get("own")]
    out.append(f"[XB-G] 本编队的号在录像里有『离开』指令的 {len(lv)} 局：" + "、".join(f"{m} {n}/{k}" for m, n, k in lv))
    od = os.path.join(OUT, "_cross")
    os.makedirs(od, exist_ok=True)
    name = "xbatch_mine" if mine_only else "xbatch"
    open(os.path.join(od, f"{name}.txt"), "w", encoding="utf-8").write("\n".join(out) + "\n")
    json.dump(dict(replays=len(rows), periods=[p[0] for p in PERIODS], rows=rows,
                   agg={f"{k[0]}|{k[1]}": v for k, v in agg.items()}, byCohort={f"{k[0]}|{k[1]}": v for k, v in by_cohort.items()},
                   pickSummary=pick_summary, waveMatches=len(wv), longReplays=len(long_), bySize=by_size,
                   waveFirstMedian=(statistics.median([r["waveFirst"] for r in wv]) if wv else None),
                   waveLastMedian=(statistics.median([r["waveLast"] for r in wv]) if wv else None)),
              open(os.path.join(od, f"{name}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n".join(out[len(rows) + 1:]))
    print(f"（逐局 {len(rows)} 行见 out/_cross/{name}.txt）")


if __name__ == "__main__":
    main()
