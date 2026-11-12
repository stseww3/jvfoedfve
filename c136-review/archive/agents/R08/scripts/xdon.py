#!/usr/bin/env python3
"""xdon.py — 发现集全部录像里的「捐款指令」机械计数：谁在捐、什么时候捐、捐多大比例、是不是很多人喂一个号。只解码录像，不做地图模拟。

先解码（同 xbatch.py；107 份录像合计不到 1 秒）：
    bash c136-review/tools/run-heavy.sh node c136-review/agents/R08/scripts/replay_cmds.mjs \
         --out-dir c136-review/agents/R08/out/_run/streams <局> <局> …
再计数：
    python3 xdon.py [--quiet]        → out/_cross/xdon.txt、xdon.json

只读 /agent/repos/c136-data/bundles/（发现集）；验证集不碰。

口径：
  · 录像里的捐款指令（2 号指令：pct, 受捐席位）。录像只记「发到服务器的」；成没成交要模拟才知道，这里不判。
    本编队的号日志里写了、录像里没有的那些（被客户端 / 引擎的受捐额度挡回的）不在这里，见 xscan.py [XS-I]、xtruth.py [XT-F]。
  · 席位分四组（和 xbatch.py 一样）：own / [APEX] / 名字池 / 野人；「机器号」= 前三组。
  · 时段按引擎受捐额度的换档拍：0~2142、2142~3213、3213~4284、4284+（game.js donationCost L348-357、donationFree L360-362）。
  · 比例 pct：到账 = 余额 ×(pct+1)/1024；pct ≥ 900 记作「几乎全捐」（到账封顶在余额的 93.75%）。
  · 喂号窗：同一个受捐席位在 300 拍内收到 ≥3 个不同席位的捐款指令、合计 ≥5 条。按受捐方的组分。一个受捐席位的窗首尾相接的算一次。
节：
  [XO-A] 捐款指令按 组 × 时段   [XO-B] 比例分布   [XO-C] 集中度：一局里收得最多的那个席位   [XO-D] 喂号窗   [XO-F] 几乎全捐   [XO-E] R08 的 16 局逐局
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
import xbatch  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")
RUN = os.path.join(OUT, "_run", "streams")
BANDS = [("0~2142", 0, 2142), ("2142~3213", 2142, 3213), ("3213~4284", 3213, 4284), ("4284+", 4284, 10 ** 9)]
GROUPS = ("own", "apex", "pool", "wild")
CN = dict(own="本编队", apex="[APEX]", pool="名字池", wild="野人", bot="机器号")
MINE = xbatch.MINE
FEED_WIN, FEED_DONORS, FEED_CMDS = 300, 3, 5


def band_of(t):
    for i, (_, a, z) in enumerate(BANDS):
        if a <= t < z:
            return i
    return len(BANDS) - 1


def groups(mid, meta, pool):
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
    return grp, names


def feed_windows(rows):
    """rows：一个受捐席位收到的 [(t, 捐出席位, pct)]，按 t 排好。返回 [(t0, t1, 条数, 不同捐出席位数, pct≥900 的条数)]。"""
    out = []
    i, n = 0, len(rows)
    while i < n:
        j = i
        while j + 1 < n and rows[j + 1][0] - rows[i][0] <= FEED_WIN:
            j += 1
        seg = rows[i:j + 1]
        if len(seg) >= FEED_CMDS and len({x[1] for x in seg}) >= FEED_DONORS:
            # 往后接：只要下一条离这一段最后一条不超过 FEED_WIN 就并进来
            while j + 1 < n and rows[j + 1][0] - rows[j][0] <= FEED_WIN:
                j += 1
            seg = rows[i:j + 1]
            out.append((seg[0][0], seg[-1][0], len(seg), len({x[1] for x in seg}), sum(1 for x in seg if x[2] >= 900)))
            i = j + 1
        else:
            i += 1
    return out


def scan(mid, pool):
    p = os.path.join(RUN, f"{mid}.json")
    if not os.path.exists(p):
        return None
    S = json.load(open(p, encoding="utf-8"))
    meta, cmds = S["meta"], S["cmds"]
    H = meta["humanCount"]
    grp, names = groups(mid, meta, pool)
    dons = [(t, pl, dx, dz) for t, cid, pl, dx, dz in cmds if cid == 2 and t >= 0 and pl < H]
    stat = {g: [dict(cmds=0, donors=set(), recv=set(), pcts=[], toBot=0, toWild=0, toOther=0) for _ in BANDS] for g in GROUPS}
    recv_rows = defaultdict(list)
    for t, pl, pct, q in dons:
        s = stat[grp[pl]][band_of(t)]
        s["cmds"] += 1
        s["donors"].add(pl)
        s["recv"].add(q)
        s["pcts"].append(pct)
        if q < H:
            if grp[q] == "wild":
                s["toWild"] += 1
            else:
                s["toBot"] += 1
            recv_rows[q].append((t, pl, pct))
        else:
            s["toOther"] += 1
    # 集中度：野人发出的捐款指令里，收得最多的那个席位占多少；机器号同理
    conc = {}
    for side in ("wild", "bot"):
        sel = [(t, pl, pct, q) for t, pl, pct, q in dons if (grp[pl] == "wild") == (side == "wild") and q < H]
        if not sel:
            conc[side] = None
            continue
        c = Counter(q for _, _, _, q in sel)
        top, n = c.most_common(1)[0]
        conc[side] = dict(cmds=len(sel), receivers=len(c), top=names[top], topGroup=grp[top], topCmds=n, topDonors=len({pl for _, pl, _, q in sel if q == top}),
                          topFirst=min(t for t, _, _, q in sel if q == top), donors=len({pl for _, pl, _, _ in sel}))
    # 几乎全捐（pct ≥ 900）：[t, 组, 受捐方的组, 捐完之后 300 拍内这个席位有没有离开指令, 之后还有没有别的指令]
    leave_t = defaultdict(list)
    later = defaultdict(list)
    for t, cid, pl, dx, dz in cmds:
        if pl < H and t >= 0:
            if cid in (8, 9):
                leave_t[pl].append(t)
            elif cid in (1, 2, 3):
                later[pl].append(t)
    allin = []
    for t, pl, pct, q in dons:
        if pct >= 900:
            allin.append([t, grp[pl], grp[q] if q < H else "other", int(any(t <= x <= t + 300 for x in leave_t[pl])), int(any(x > t for x in later[pl]))])
    feeds = []
    for q, rows in recv_rows.items():
        rows.sort()
        for t0, t1, n, nd, nbig in feed_windows(rows):
            dg = Counter(grp[pl] for t, pl, _ in rows if t0 <= t <= t1)
            feeds.append(dict(recv=names[q], recvGroup=grp[q], t0=t0, t1=t1, cmds=n, donors=nd, big=nbig, donorGroups=dict(dg)))
    return dict(matchId=mid, H=H, lastTick=meta["lastTick"], sizes=dict(Counter(grp.values())), cmds=len(dons),
                stat={g: [dict(cmds=s["cmds"], donors=len(s["donors"]), recv=len(s["recv"]), pcts=s["pcts"], toBot=s["toBot"], toWild=s["toWild"], toOther=s["toOther"]) for s in stat[g]] for g in GROUPS},
                conc=conc, feeds=feeds, allin=allin)


def q3(xs):
    if not xs:
        return "–"
    if len(xs) < 4:
        return f"{statistics.median(xs):.0f}"
    q = statistics.quantiles(xs, n=4)
    return f"{q[0]:.0f} / {q[1]:.0f} / {q[2]:.0f}"


def pc(a, b):
    return "–" if not b else f"{100 * a / b:.0f}%"


def main():
    quiet = "--quiet" in sys.argv
    pool = xbatch.name_pool()
    ids = xbatch.discovery_ids()
    rows = []
    for mid, card in ids:
        r = scan(mid, pool)
        if r:
            r["cohort"] = card.get("cohort")
            rows.append(r)
    out = []
    out.append(f"[XO-A] 录像里的捐款指令（{len(rows)} 份录像；末拍 ≥3213 的 {sum(1 for r in rows if r['lastTick'] >= 3213)} 份、≥4284 的 {sum(1 for r in rows if r['lastTick'] >= 4284)} 份）。"
               "只数发到服务器的，成没成交不判。")
    out.append("  时段 | 组 | 有捐款指令的局 | 捐过的席位 | 指令 | 每个捐过的席位 | 受捐方是野人 / 机器号 | 比例 pct 的 25% / 50% / 75% 分位 | pct ≥ 512 的占比 | pct ≥ 900 的占比")
    A = {}
    for bi, (bn, _, _) in enumerate(BANDS):
        for g in list(GROUPS) + ["bot"]:
            gs = ("own", "apex", "pool") if g == "bot" else (g,)
            n = sum(r["stat"][x][bi]["cmds"] for r in rows for x in gs)
            if not n:
                continue
            pcts = [p for r in rows for x in gs for p in r["stat"][x][bi]["pcts"]]
            seats = sum(r["stat"][x][bi]["donors"] for r in rows for x in gs)
            out.append(f"  {bn} | {CN[g]} | {sum(1 for r in rows if any(r['stat'][x][bi]['cmds'] for x in gs))} | {seats} | {n} | {n / max(seats, 1):.1f} | "
                       f"{sum(r['stat'][x][bi]['toWild'] for r in rows for x in gs)} / {sum(r['stat'][x][bi]['toBot'] for r in rows for x in gs)} | {q3(pcts)} | "
                       f"{pc(sum(1 for p in pcts if p >= 512), n)} | {pc(sum(1 for p in pcts if p >= 900), n)}")
            A[f"{bn}|{g}"] = dict(cmds=n, seats=seats, big=sum(1 for p in pcts if p >= 900), half=sum(1 for p in pcts if p >= 512), median=statistics.median(pcts))
    out.append("")
    out.append("[XO-B] 野人的捐款比例分布（全程）：pct 区间 | 指令 | 占比")
    wp = [p for r in rows for bi in range(len(BANDS)) for p in r["stat"]["wild"][bi]["pcts"]]
    bp = [p for r in rows for bi in range(len(BANDS)) for g in ("own", "apex", "pool") for p in r["stat"][g][bi]["pcts"]]
    cuts = [(0, 63), (63, 128), (128, 256), (256, 512), (512, 900), (900, 1024)]
    B = {}
    for a, z in cuts:
        nw, nb = sum(1 for p in wp if a <= p < z), sum(1 for p in bp if a <= p < z)
        out.append(f"  {a}~{z - 1} | 野人 {nw}（{pc(nw, len(wp))}）| 机器号 {nb}（{pc(nb, len(bp))}）")
        B[f"{a}~{z - 1}"] = dict(wild=nw, bot=nb)
    out.append(f"  合计 | 野人 {len(wp)} | 机器号 {len(bp)}；pct < 63（到账比手续费少）：野人 {pc(sum(1 for p in wp if p < 63), len(wp))}、机器号 {pc(sum(1 for p in bp if p < 63), len(bp))}")
    out.append("")
    out.append("[XO-C] 集中度（一局里发给真人席位的捐款指令，收得最多的那个席位）：捐出方 | 有捐款的局 | 每局指令中位 | 每局受捐席位数中位 | 收得最多的席位占指令的比例：中位（四分位）| "
               "≥50% 的局 | 给它捐过的席位数中位 | 它第一次收到的拍：中位")
    C = {}
    for side in ("wild", "bot"):
        cs = [r["conc"][side] for r in rows if r["conc"].get(side)]
        if not cs:
            continue
        sh = [c["topCmds"] / c["cmds"] for c in cs]
        out.append(f"  {CN[side]} | {len(cs)} | {statistics.median(c['cmds'] for c in cs):.0f} | {statistics.median(c['receivers'] for c in cs):.0f} | "
                   f"{100 * statistics.median(sh):.0f}%（{' / '.join(f'{100 * x:.0f}%' for x in (statistics.quantiles(sh, n=4) if len(sh) >= 4 else sh))}）| "
                   f"{sum(1 for x in sh if x >= 0.5)} | {statistics.median(c['topDonors'] for c in cs):.0f} | {statistics.median(c['topFirst'] for c in cs):.0f}")
        C[side] = dict(matches=len(cs), topShareMedian=statistics.median(sh), half=sum(1 for x in sh if x >= 0.5))
    # 只看指令 ≥20 条的局
    for side in ("wild", "bot"):
        cs = [r["conc"][side] for r in rows if r["conc"].get(side) and r["conc"][side]["cmds"] >= 20]
        if cs:
            sh = [c["topCmds"] / c["cmds"] for c in cs]
            out.append(f"  {CN[side]}（只看指令 ≥20 条的 {len(cs)} 局）| 收得最多的席位占比中位 {100 * statistics.median(sh):.0f}% | ≥50% 的 {sum(1 for x in sh if x >= 0.5)} 局 | "
                       f"收得最多的那个是野人的 {sum(1 for c in cs if c['topGroup'] == 'wild')} 局、是机器号的 {sum(1 for c in cs if c['topGroup'] != 'wild')} 局")
    out.append("")
    out.append(f"[XO-D] 喂号窗（同一个受捐席位 {FEED_WIN} 拍内收到 ≥{FEED_DONORS} 个不同席位、合计 ≥{FEED_CMDS} 条捐款指令；首尾相接的并成一次）：")
    out.append("  受捐方 | 有喂号窗的局 | 窗数 | 起点拍的 10% / 25% / 50% / 75% / 90% 分位 | 起点 <3213 / 3213~4284 / ≥4284 | 一个窗的指令条数中位（最大）| 捐出席位数中位（最大）| 窗长中位 | 窗里 pct ≥ 900 的指令占比")
    D = {}
    for rg in ("wild", "bot"):
        fs = [(r["matchId"], f) for r in rows for f in r["feeds"] if (f["recvGroup"] == "wild") == (rg == "wild")]
        if not fs:
            continue
        t0s = sorted(f["t0"] for _, f in fs)
        q = statistics.quantiles(t0s, n=20) if len(t0s) >= 2 else [t0s[0]] * 19
        nc = [f["cmds"] for _, f in fs]
        nd = [f["donors"] for _, f in fs]
        out.append(f"  {CN[rg]} | {len({m for m, _ in fs})} | {len(fs)} | {q[1]:.0f} / {q[4]:.0f} / {q[9]:.0f} / {q[14]:.0f} / {q[17]:.0f} | "
                   f"{sum(1 for t in t0s if t < 3213)} / {sum(1 for t in t0s if 3213 <= t < 4284)} / {sum(1 for t in t0s if t >= 4284)} | "
                   f"{statistics.median(nc):.0f}（{max(nc)}）| {statistics.median(nd):.0f}（{max(nd)}）| {statistics.median(f['t1'] - f['t0'] for _, f in fs):.0f} | "
                   f"{pc(sum(f['big'] for _, f in fs), sum(nc))}")
        D[rg] = dict(matches=len({m for m, _ in fs}), windows=len(fs), t0Median=q[9], before3213=sum(1 for t in t0s if t < 3213), after4284=sum(1 for t in t0s if t >= 4284),
                     cmdsMedian=statistics.median(nc), donorsMedian=statistics.median(nd))
    late = [r for r in rows if r["lastTick"] >= 4284]
    out.append(f"  录像到 4284 拍以后的 {len(late)} 局里：野人受捐方有喂号窗的 {sum(1 for r in late if any(f['recvGroup'] == 'wild' for f in r['feeds']))} 局；"
               f"机器号受捐方有的 {sum(1 for r in late if any(f['recvGroup'] != 'wild' for f in r['feeds']))} 局；两边都没有的 {sum(1 for r in late if not r['feeds'])} 局")
    big = sorted(((f["cmds"], m, f) for r in rows for m, f in [(r["matchId"], x) for x in r["feeds"]] if f["recvGroup"] == "wild"), key=lambda x: -x[0])[:8]
    out.append("  野人受捐方最大的 8 个窗：" + "；".join(f"{m} {f['recv']} t={f['t0']}~{f['t1']} {f['cmds']} 条 / {f['donors']} 个席位（pct≥900 的 {f['big']} 条）" for _, m, f in big))
    out.append("")
    out.append("[XO-F] 几乎全捐（pct ≥ 900；到账封顶在余额的 93.75%）：捐出方 | 指令 | 有的局 | 每局中位（只看有的局）| 发令拍的 10% / 25% / 50% / 75% / 90% 分位 | "
               "捐完 300 拍内这个席位有『离开』指令的 | 捐完以后这个席位再没有任何进攻 / 捐款 / 船指令的")
    Fz = {}
    for side in ("wild", "bot"):
        al = [(r["matchId"], x) for r in rows for x in r["allin"] if (x[1] == "wild") == (side == "wild")]
        if not al:
            out.append(f"  {CN[side]} | 0")
            continue
        ts = sorted(x[0] for _, x in al)
        q = statistics.quantiles(ts, n=20) if len(ts) >= 2 else [ts[0]] * 19
        per = Counter(m for m, _ in al)
        qs = f"{q[1]:.0f} / {q[4]:.0f} / {q[9]:.0f} / {q[14]:.0f} / {q[17]:.0f}" if len(ts) >= 20 else "（太少，逐条：" + "、".join(str(t) for t in ts) + "）"
        out.append(f"  {CN[side]} | {len(al)} | {len(per)} | {statistics.median(per.values()):.0f} | {qs} | "
                   f"{sum(x[3] for _, x in al)}（{pc(sum(x[3] for _, x in al), len(al))}）| {sum(1 for _, x in al if not x[4])}（{pc(sum(1 for _, x in al if not x[4]), len(al))}）")
        Fz[side] = dict(cmds=len(al), matches=len(per), median=q[9], leaveSoon=sum(x[3] for _, x in al), silentAfter=sum(1 for _, x in al if not x[4]))
    out.append("")
    mine = [r for r in rows if r["matchId"] in MINE]
    mine.sort(key=lambda r: MINE.index(r["matchId"]))
    out.append("[XO-E] R08 的 16 局里有录像的：局 | 录像末拍 | 野人的捐款指令（<3213 / 3213~4284 / ≥4284）| 其中 pct ≥ 900 | 野人里收得最多的席位：指令 / 捐出席位 / 第一次拍 | "
               "本编队的捐款指令（同三段）| 喂号窗（受捐方、起点、条数 / 席位）")
    for r in mine:
        w = [r["stat"]["wild"][i] for i in range(len(BANDS))]
        o = [r["stat"]["own"][i] for i in range(len(BANDS))]
        cw = r["conc"].get("wild")
        fd = "；".join(f"{f['recv']}（{CN['wild'] if f['recvGroup'] == 'wild' else CN['bot']}）t={f['t0']} {f['cmds']}/{f['donors']}" for f in r["feeds"][:4]) or "–"
        out.append(f"  {r['matchId']} | {r['lastTick']} | {w[0]['cmds'] + w[1]['cmds']} / {w[2]['cmds']} / {w[3]['cmds']} | {sum(1 for x in w for p in x['pcts'] if p >= 900)} | "
                   f"{(str(cw['topCmds']) + ' / ' + str(cw['topDonors']) + ' / ' + str(cw['topFirst'])) if cw else '–'} | {o[0]['cmds'] + o[1]['cmds']} / {o[2]['cmds']} / {o[3]['cmds']} | {fd}")
    od = os.path.join(OUT, "_cross")
    os.makedirs(od, exist_ok=True)
    with open(os.path.join(od, "xdon.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    for r in rows:
        for g in GROUPS:
            for s in r["stat"][g]:
                s["pcts"] = len(s["pcts"])
    with open(os.path.join(od, "xdon.json"), "w", encoding="utf-8") as f:
        json.dump(dict(replays=len(rows), byBand=A, pctBins=B, concentration=C, feeds=D, allin=Fz, rows=rows), f, ensure_ascii=False)
    print("\n".join(out) if not quiet else f"xdon: {len(rows)} 份录像，{len(out)} 行")


if __name__ == "__main__":
    main()
