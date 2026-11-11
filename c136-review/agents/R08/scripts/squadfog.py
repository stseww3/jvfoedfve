#!/usr/bin/env python3
"""squadfog.py <matchId> [--room N] —— 停摆账号、捐给停摆账号的兵、「看不见的失地」、整队囤兵。只读日志（HL-TICK / HL-DONATE / RESULT）和 donfit.json。

用法：timeout 115 python3 squadfog.py B019
  [HA] 停摆账号：没有结果行、HL-TICK 在终局前 500 拍以上就断了的号；有录像时补上它在录像里最后一条指令的执行拍和录像末拍的地、兵。
  [HB] 捐款去向：donfit.json 里定案为成交的每一笔，按「收款方发令时是不是已经停摆」分两堆（停摆 = 收款方最后一条 HL-TICK 早于发令拍 180 拍以上）。
  [HC] 看不见的失地：一个快照窗两端都是 nb=0 且 neut=0（analyze 里没有任何敌邻、也没有中立地），领土却少了。
       c110 analyze L419-448 把 isProtectedSquadMate 为真的邻居从 nb 里剔掉，所以这种窗里吃地的一方不在 nb 里。
  [HD] 大幅失地窗（单窗丢 ≥8% 且 ≥300 格）逐条：两端 nb / neut / 密度、窗内新指令数、船数。
  [HE] 整队囤兵：每一队里还有快照的号，在同一拍的 地合计 / 兵合计 / 密度 / 被围（nb=0 且 neut=0）个数 / 超 100× 个数。
"""
import json
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import facts  # noqa: E402
import r08lib as L  # noqa: E402


def stalled_ids(F):
    end = F["endTick"]
    out = {}
    for me, b in F["bots"].items():
        if not b["ticks"]:
            continue
        last = b["ticks"][-1]["t"]
        if b.get("event") in (None, "") and last < end - 500:
            out[me] = last
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    mid = args[0]
    room = int(sys.argv[sys.argv.index("--room") + 1]) if "--room" in sys.argv else None
    F = facts.full(mid, room=room)
    bots = F["bots"]
    end = F["endTick"]
    name = lambda me: "%s(%d) T%s" % (bots[me]["labels"][0], me, bots[me].get("team"))
    st = stalled_ids(F)

    resim = None
    rp = os.path.join(L.OUT, mid, "resim.json")
    if os.path.exists(rp):
        resim = json.load(open(rp))

    # 全局行序：每一行日志落在「当时跑得最前的号」的哪一拍（所有号的 HL-TICK 按行号排，取到这一行为止出现过的最大拍）
    lead = []  # (line, 到这一行为止的最大 HL-TICK 拍)
    mx = 0
    last_line = {}
    for r in L.parse_log(mid):
        if r.get("tag") == "HL-TICK" and r.get("tick"):
            mx = max(mx, r["tick"]["t"])
        lead.append((r["line"], mx))
        if r.get("label"):
            last_line[r["label"]] = r["line"]

    def lead_at(line):
        best = 0
        for ln, t in lead:
            if ln > line:
                break
            best = t
        return best

    print("[HA] %s 停摆账号 %d 个（没有结果行，HL-TICK 在终局 %d 拍前 500 拍以上就断了）：号 队 | 最后一条 HL-TICK 拍、地、兵、敌邻 | 录像里最后一条已执行指令的拍 | 录像末拍（t=%s）地 / 兵 | 最后一行日志的行号 → 那时领跑号已经记到的 HL-TICK 拍" % (
        mid, len(st), end, resim["endTick"] if resim else "-"))
    for me in sorted(st, key=lambda m: (st[m], m)):
        b = bots[me]
        s = b["ticks"][-1]
        extra = "-"
        tail = "-"
        if resim:
            last_cmd = max([c[0] for c in resim["cmdLog"] if c[1] == me] or [-1])
            extra = str(last_cmd)
            i = len(resim["snapT"]) - 1
            tail = "%d / %d" % (resim["snapTerr"][i][me], resim["snapBal"][i][me])
        ll = max([last_line.get(lb, 0) for lb in b["labels"]] or [0])
        print("     %s | %d、%d、%d、nb=%d | %s | %s | L%d → %d" % (name(me), s["t"], s["terr"], s["bal"], s["nb"], extra, tail, ll, lead_at(ll)))
    for me, b in sorted(bots.items()):
        if b.get("event") == "left":
            print("     另：%s 有结果行 left（本地拍 %s，L%s）→ 那时领跑号已经记到 HL-TICK 拍 %d" % (name(me), b.get("deathTick"), b.get("resLine"), lead_at(b.get("resLine") or 0)))
    alive_logged = [me for me in bots if me not in st]
    print("     其余 %d 个号有结果行或一直记到终局：%s" % (len(alive_logged), "、".join(bots[m]["labels"][0] for m in sorted(alive_logged))))

    dp = os.path.join(L.OUT, mid, "donfit.json")
    if os.path.exists(dp):
        D = json.load(open(dp))["rows"]
        agg = defaultdict(lambda: [0, 0, 0, 0, 0])
        per = defaultdict(lambda: [0, 0, 0, 0, 0, None, None])
        for r in D:
            ally = r["ally"]
            last = bots[ally]["ticks"][-1]["t"] if ally in bots and bots[ally]["ticks"] else None
            cls = "不在编队" if ally not in bots else ("停摆" if last is not None and last < r["t"] - 180 else "在跑")
            a = agg[cls]
            p = per[(cls, ally)]
            a[0] += 1; p[0] += 1
            if r["status"] == "EXEC":
                a[1] += 1; a[2] += r["amt"] or 0; a[3] += r["fee"] or 0
                p[1] += 1; p[2] += r["amt"] or 0; p[3] += r["fee"] or 0
                p[5] = r["t"] if p[5] is None else min(p[5], r["t"])
                p[6] = r["t"] if p[6] is None else max(p[6], r["t"])
            elif r["status"] == "NOEXEC":
                a[4] += 1; p[4] += 1
        tot_amt = sum(a[2] for a in agg.values()) or 1
        print("[HB] 捐款去向（donfit 定案）：收款方状态 | 日志笔数 | 成交笔数 | 到账合计（占全部到账 %）| 捐出方付的税 | 没成交笔数")
        for cls in ("停摆", "在跑", "不在编队"):
            if cls in agg:
                a = agg[cls]
                print("     %s | %d | %d | %d（%.0f%%）| %d | %d" % (cls, a[0], a[1], a[2], 100 * a[2] / tot_amt, a[3], a[4]))
        print("     逐个收款方：状态 号 队 | 日志笔数 / 成交 / 没成交 | 到账 | 税 | 成交首末拍 | 收款方最后一条 HL-TICK")
        for (cls, ally), p in sorted(per.items(), key=lambda kv: (-kv[1][2], kv[0][1])):
            last = bots[ally]["ticks"][-1]["t"] if ally in bots and bots[ally]["ticks"] else "-"
            nm = name(ally) if ally in bots else str(ally)
            print("     %s %s | %d / %d / %d | %d | %d | %s~%s | %s" % (cls, nm, p[0], p[1], p[4], p[2], p[3], p[5], p[6], last))
        # 谁捐给停摆账号
        by_donor = defaultdict(lambda: [0, 0, 0, 0])
        for r in D:
            ally = r["ally"]
            if ally not in bots or r["status"] != "EXEC":
                continue
            last = bots[ally]["ticks"][-1]["t"]
            d = by_donor[r["donor"]]
            if last < r["t"] - 180:
                d[0] += 1; d[1] += (r["amt"] or 0) + (r["fee"] or 0)
            else:
                d[2] += 1; d[3] += (r["amt"] or 0) + (r["fee"] or 0)
        print("     按捐出方（成交的）：号 | 给停摆账号 笔数 / 付出（到账+税）| 给在跑的号 笔数 / 付出")
        for me, d in sorted(by_donor.items(), key=lambda kv: -kv[1][1]):
            print("     %s | %d / %d | %d / %d" % (name(me), d[0], d[1], d[2], d[3]))
    else:
        print("[HB] 没有 donfit.json，先跑 donfit.py")

    print("[HC] 看不见的失地（窗两端都是 nb=0 且 neut=0，领土却少了）：号 队 | 这种窗数 / 两端都被围的窗总数 | 丢的格数合计 | 首末拍 | 单窗最大丢失（拍，格）| 这些窗里的新指令 / 船 | 两端被围而地变多的窗：窗数、涨的格数、其中有船的窗数")
    tot_w = tot_c = 0
    blind_rows = []
    for me in sorted(bots):
        tk = bots[me]["ticks"]
        n_box = n_loss = cells = cmds = boats = 0
        first = last = None
        worst = (0, None)
        n_gain = g_cells = g_boat = 0
        for i in range(1, len(tk)):
            a, c = tk[i - 1], tk[i]
            if c["t"] - a["t"] > 270:
                continue
            if a["nb"] == 0 and a["neut"] == 0 and c["nb"] == 0 and c["neut"] == 0:
                n_box += 1
                d = c["terr"] - a["terr"]
                if d < 0:
                    n_loss += 1; cells += -d
                    cmds += c["cmds"] - a["cmds"]; boats += c["boats"] - a["boats"]
                    first = a["t"] if first is None else first
                    last = c["t"]
                    if -d > worst[0]:
                        worst = (-d, "%d~%d" % (a["t"], c["t"]))
                    blind_rows.append((me, a, c))
                elif d > 0:
                    n_gain += 1; g_cells += d
                    if c["boats"] > a["boats"]:
                        g_boat += 1
        if n_loss:
            tot_w += n_loss; tot_c += cells
            print("     %s | %d / %d | %d | %s~%s | %s，%d | %d / %d | %d、%d、%d" % (
                name(me), n_loss, n_box, cells, first, last, worst[1], worst[0], cmds, boats, n_gain, g_cells, g_boat))
    print("     合计：%d 个窗，丢 %d 格" % (tot_w, tot_c))

    # [HF] 看不见的失地 和 同期捐给异队停摆账号的兵（只有异队的编队名字既能打过来、又不进 nb）
    victims = defaultdict(list)
    for me, a, c in blind_rows:
        victims[me].append((a, c))
    if os.path.exists(dp):
        D = json.load(open(dp))["rows"]
        for me, rows in victims.items():
            if len(rows) < 5:
                continue
            vteam = bots[me].get("team")
            print("[HF] %s 看不见的失地 对照 同期成交的、收款方是异队停摆账号的捐款：桶（450 拍）| 这个号在被围窗里丢的格数 | 余额 桶首→桶末 | 各异队停摆账号到账（笔数）" % name(me))
            t0 = (rows[0][0]["t"] // 450) * 450
            t1 = rows[-1][1]["t"]
            t = t0
            while t < t1:
                lost = sum(a["terr"] - c["terr"] for a, c in rows if t <= a["t"] < t + 450)
                tk = [s for s in bots[me]["ticks"] if t <= s["t"] <= t + 450]
                recv = defaultdict(lambda: [0, 0])
                for r in D:
                    ally = r["ally"]
                    if r["status"] != "EXEC" or ally not in bots or not (t <= r["t"] < t + 450):
                        continue
                    if bots[ally].get("team") == vteam or bots[ally]["ticks"][-1]["t"] >= r["t"] - 180:
                        continue
                    recv[ally][0] += r["amt"] or 0
                    recv[ally][1] += 1
                rs = "、".join("%s %d（%d 笔）" % (bots[a]["labels"][0], v[0], v[1]) for a, v in sorted(recv.items(), key=lambda kv: -kv[1][0])) or "-"
                print("     %5d~%5d | %d | %s | %s" % (t, t + 450, lost, ("%d→%d" % (tk[0]["bal"], tk[-1]["bal"])) if tk else "-", rs))
                t += 450

    # [HH] 捐款的几个计数：按种类、小比例、同拍多号捐同一人、分时段、在跑的号之间
    if os.path.exists(dp):
        D = json.load(open(dp))["rows"]
        ex = [r for r in D if r["status"] == "EXEC"]

        def line(rows, title):
            e = [r for r in rows if r["status"] == "EXEC"]
            cl = [r for r in e if r["clip"]]
            return "     %s | %d | %d / %d / %d | %d | %d | %d 笔、到账 %d、税 %d | %d" % (
                title, len(rows), len(e), sum(1 for r in rows if r["status"] == "NOEXEC"), sum(1 for r in rows if r["status"] == "AMB"),
                sum(r["amt"] or 0 for r in e), sum(r["fee"] or 0 for r in e), len(cl), sum(r["amt"] or 0 for r in cl), sum(r["fee"] or 0 for r in cl),
                sum(1 for r in e if (r["fee"] or 0) >= (r["amt"] or 0)))

        print("[HH] 捐款计数（donfit 定案）：口径 | 日志笔数 | 成交 / 没成交 / 定不了 | 到账 | 税 | 其中到账被收款方 150 倍上限夹小的 | 税 ≥ 到账的成交笔数")
        print(line(D, "全部"))
        print(line([r for r in D if r["kind"].startswith("squad")], "救援（squad rescue donate）"))
        print(line([r for r in D if r["kind"].startswith("surplus")], "盈余（surplus donate）"))
        print(line([r for r in D if r["pct"] <= 70], "pct ≤ 70/1024"))
        by = defaultdict(list)
        for r in D:
            by[(r["t"], r["ally"])].append(r)
        multi = [x for v in by.values() if len({y["donor"] for y in v}) >= 2 for x in v]
        print(line(multi, "同一拍 ≥2 个号捐同一人（%d 组）" % sum(1 for v in by.values() if len({y["donor"] for y in v}) >= 2)))
        live = {me for me in bots if me not in st and bots[me].get("event") != "left"}
        print(line([r for r in D if r["donor"] in live and r["ally"] in live], "收款方也是一直在跑的号"))
        last_t = max(r["t"] for r in D)
        edges = [0, 2300, 4284, 6300, 9400, 10000, 11200, last_t + 1]
        for a, b in zip(edges, edges[1:]):
            print(line([r for r in D if a <= r["t"] < b], "发令拍 %d~%d" % (a, b)))
        print("     成交的 %d 笔：捐出方一共付出 到账 + 税 = %d" % (len(ex), sum((r["amt"] or 0) + (r["fee"] or 0) for r in ex)))
        early = [r for r in D if r["t"] < 2300]
        print("     发令拍 <2300 的 %d 笔：捐出方 %s；收款方 %s；其中收款方是停摆账号的 %d 笔" % (
            len(early), "、".join("%s×%d" % kv for kv in Counter(r["donorName"] for r in early).most_common()),
            "、".join("%s×%d" % kv for kv in Counter(r["allyName"] for r in early).most_common()), sum(1 for r in early if r["ally"] not in live)))
        print(line([r for r in D if r["t"] >= 9400 and r["donor"] in live and r["ally"] in live], "发令拍 ≥9400 且收款方也是一直在跑的号"))
        print(line([r for r in D if r["t"] >= 9400 and r["ally"] not in live], "发令拍 ≥9400 且收款方是停摆账号"))

        # [HJ] 每个收款方的成交捐款按时间聚成段（相邻两笔发令拍间隔 > 600 就断开）
        print("[HJ] 每个收款方的捐款段（相邻两笔日志的发令拍间隔 > 600 拍就断开）：收款方 队（停摆/在跑）| 段 首末拍 | 日志笔数 / 成交 / 没成交 / 定不了 | 到账 | 税 | 夹小笔数、到账、税 | 捐出方（成交笔数）")
        byr = defaultdict(list)
        for r in D:
            byr[r["ally"]].append(r)
        for ally, rows in sorted(byr.items(), key=lambda kv: -sum((x["amt"] or 0) for x in kv[1] if x["status"] == "EXEC")):
            rows.sort(key=lambda r: r["t"])
            segs = [[rows[0]]]
            for r in rows[1:]:
                if r["t"] - segs[-1][-1]["t"] > 600:
                    segs.append([])
                segs[-1].append(r)
            b = bots.get(ally) or bots.get(str(ally))
            tag = "T%s %s" % (b.get("team") if b else "?", "停摆" if ally not in live else "在跑")
            for sg in segs:
                e = [r for r in sg if r["status"] == "EXEC"]
                cl = [r for r in e if r["clip"]]
                dn = Counter(r["donorName"] for r in e)
                da = defaultdict(lambda: [0, 0])
                for r in e:
                    da[r["donorName"]][0] += r["amt"] or 0
                    da[r["donorName"]][1] += r["fee"] or 0
                print("     %s %s | %d~%d | %d / %d / %d / %d | %d | %d | %d、%d、%d | %s" % (
                    rows[0]["allyName"], tag, sg[0]["t"], sg[-1]["t"], len(sg), len(e), sum(1 for r in sg if r["status"] == "NOEXEC"), sum(1 for r in sg if r["status"] == "AMB"),
                    sum(r["amt"] or 0 for r in e), sum(r["fee"] or 0 for r in e), len(cl), sum(r["amt"] or 0 for r in cl), sum(r["fee"] or 0 for r in cl),
                    "、".join("%s×%d（到账 %d、税 %d）" % (k, n, da[k][0], da[k][1]) for k, n in dn.most_common())))

    # [HL] 救援捐款日志里记下的收款方密度 dAlly（停摆账号没有 HL-TICK，这是它们在 t>录像末拍 之后唯一的读数）
    import re
    lp = os.path.join(L.bundle_dir(mid), "in_game.log")
    rx = re.compile(r"t=(\d+) squad rescue donate .*ally=(\d+)\(([^)]*)\).*dMe=(\d+) dAlly=(\d+)")
    seen_d = defaultdict(list)
    for ln in open(lp, encoding="utf-8", errors="replace"):
        m = rx.search(ln)
        if m:
            seen_d[(int(m.group(2)), m.group(3))].append((int(m.group(1)), int(m.group(5))))
    if seen_d:
        print("[HL] 救援捐款日志里的收款方密度 dAlly（发令拍:密度）：收款方（停摆/在跑）| 条数 | 最小~最大 | 序列（按发令拍）")
        for (ally, nm), v in sorted(seen_d.items(), key=lambda kv: (kv[0][0] in st or (bots.get(kv[0][0]) or {}).get("event") == "left", kv[1][0][0])):
            v.sort()
            stalled = ally in st or (bots.get(ally) or {}).get("event") == "left"
            print("     %s（%s）| %d | %d~%d | %s" % (nm, "停摆" if stalled else "在跑", len(v), min(x[1] for x in v), max(x[1] for x in v), " ".join("%d:%d" % x for x in v)))
        sv = [x[1] for (ally, nm), v in seen_d.items() if (ally in st or (bots.get(ally) or {}).get("event") == "left") for x in v]
        if sv:
            sv.sort()
            print("     停摆账号合计 %d 条读数：密度 最小 %d / 中位 %d / 最大 %d" % (len(sv), sv[0], sv[len(sv) // 2], sv[-1]))
        # 对照：一直在跑的号同一时段的密度（HL-TICK）
        ref = []
        for me, b in bots.items():
            if me in st or b.get("event") == "left":
                continue
            for x in b["ticks"]:
                if x["t"] >= 1800 and x["terr"] > 0:
                    ref.append(x["bal"] / x["terr"])
        if ref:
            ref.sort()
            print("     对照：一直在跑的号 t≥1800 的 %d 条 HL-TICK：密度 P10 %.0f / 中位 %.0f / P90 %.0f" % (len(ref), ref[len(ref) // 10], ref[len(ref) // 2], ref[len(ref) * 9 // 10]))

    # [HM] 策略自身的耗时（HL-TICK 的 avgMs / maxMs，HL-SLOW-TICK 行）：区分『策略算得慢』和『客户端 / 主机慢』
    segs_ms = [(0, 540), (540, 900), (900, 1260), (1260, 2300), (2300, 10 ** 9)]
    agg = {s: [0, 0.0, 0.0] for s in segs_ms}  # 条数、avgMs 最大、maxMs 最大
    slow = defaultdict(list)
    rs = re.compile(r"\[HL-SLOW-TICK\].*?t=(\d+).*?(?:ms=|took=|dt=)?([\d.]+)\s*ms")
    for r in L.parse_log(mid):
        tk = r.get("tick")
        if r.get("tag") == "HL-TICK" and tk and tk.get("avgMs") is not None:
            for s in segs_ms:
                if s[0] <= tk["t"] < s[1]:
                    a = agg[s]
                    a[0] += 1; a[1] = max(a[1], tk["avgMs"]); a[2] = max(a[2], tk["maxMs"] or 0)
        elif r.get("tag") == "HL-SLOW-TICK":
            m = re.search(r"t=(\d+)", r.get("body") or "")
            ms = re.findall(r"([\d.]+)\s*ms", r.get("body") or "")
            slow[r.get("label")].append((int(m.group(1)) if m else -1, max((float(x) for x in ms), default=0.0)))
    print("[HM] 策略自身的耗时：本地拍段 | HL-TICK 条数 | avgMs 最大 | maxMs 最大")
    for s in segs_ms:
        a = agg[s]
        print("     %d~%s | %d | %.2f | %.1f" % (s[0], ("末" if s[1] > 10 ** 8 else s[1]), a[0], a[1], a[2]))
    n_slow = sum(len(v) for v in slow.values())
    if n_slow:
        early = [x for v in slow.values() for x in v if 0 <= x[0] < 2300]
        print("     HL-SLOW-TICK %d 行：%s；t<2300 的 %d 行（最长 %.1f ms）；全局最长 %.1f ms" % (
            n_slow, "、".join("%s×%d" % (k, len(v)) for k, v in sorted(slow.items(), key=lambda kv: -len(kv[1]))[:6]),
            len(early), max((x[1] for x in early), default=0.0), max(x[1] for v in slow.values() for x in v)))

    # [HN] 规则啃地：只有 1 个敌邻、没有中立地的连续快照窗里，每窗掉一小口（<2% 领土）；内置 AI 的出手周期是 100 拍，第一圈必赢
    print("[HN] 规则啃地（连续 ≥8 个窗 两端 nb=1、neut=0，每窗领土变化在 −2%~0 之间）：号 队 | 首末拍 | 窗数 / 掉地的窗数 | 每窗掉的格数序列 | 合计 | 密度 最小~最大 | 这段的陆攻+船指令数（指令增量 − 捐款日志条数）")
    don_t = defaultdict(list)
    if os.path.exists(dp):
        for r in json.load(open(dp))["rows"]:
            don_t[r["donor"]].append(r["t"])
    for me, b in bots.items():
        tk = b["ticks"]
        run = []
        runs = []
        for p, s in zip(tk, tk[1:]):
            ok = (p["nb"] == 1 and s["nb"] == 1 and p["neut"] == 0 and s["neut"] == 0 and s["t"] - p["t"] == 90
                  and 0 <= p["terr"] - s["terr"] <= 0.02 * p["terr"])
            if ok:
                run.append((p, s))
            else:
                if len(run) >= 8:
                    runs.append(run)
                run = []
        if len(run) >= 8:
            runs.append(run)
        for run in runs:
            drops = [p["terr"] - s["terr"] for p, s in run]
            if sum(1 for d in drops if d > 0) < 5:
                continue
            t0, t1 = run[0][0]["t"], run[-1][1]["t"]
            dens = [p["bal"] / max(1, p["terr"]) for p, s in run]
            ncmd = run[-1][1]["cmds"] - run[0][0]["cmds"]
            ndon = sum(1 for t in don_t.get(me, []) if t0 <= t < t1)
            print("     %s | %d~%d | %d / %d | %s | %d | %.0f~%.0f | %d" % (name(me), t0, t1, len(run), sum(1 for d in drops if d > 0), " ".join(str(d) for d in drops), sum(drops), min(dens), max(dens), ncmd - ndon))

    # [HK] 结果行：出局时的领土对历史峰值、带走的余额
    import csv
    rp = os.path.join(L.bundle_dir(mid), "results.csv")
    if os.path.exists(rp):
        print("[HK] 结果行（results.csv）：号 | 事件 拍 | 名次 | 历史峰值 | 出局前最后一次领土（÷峰值）| 出局时余额")
        gone = 0
        for r in csv.DictReader(open(rp, encoding="utf-8")):
            pk = int(r["peak"] or 0); lt = int(r["lastTerritory"] or 0); bal = int(r["balance"] or 0)
            print("     %s | %s %s | %s | %d | %d（%.3f）| %d" % (r["bot"], r["event"], r["tick"], r["place"], pk, lt, (lt / pk if pk else 0), bal))
            if r["event"] == "died":
                gone += bal
        print("     阵亡的号出局时余额合计 %d（引擎 aliveTick：领土 ≤ 峰值的 1/4 就出局，余额一并清零）" % gone)

    # [HG] 清仓拟合：余额在 ≤180 拍里掉到 ≤10% 的窗，之前 700 拍里 donfit 没判成交的捐款如果一笔笔按当时余额成交，要几笔才对得上
    if os.path.exists(dp):
        D = json.load(open(dp))["rows"]
        print("[HG] 清仓拟合（余额 ≤180 拍掉到 ≤10%；只是算术：每笔捐款按当时余额扣 (pct+1+64)/1024，利息不计）：号 队 | 窗 | 余额 前→后（比值）| 领土 前→后 | 之前 700 拍里没判成交的捐款笔数 | 从最后一笔往前连乘到最接近观测比值：笔数、连乘比值、这些笔的到账合计、税合计")
        for me in sorted(bots):
            tk = bots[me]["ticks"]
            i = 1
            while i < len(tk):
                # 找到一个起点 a 和终点 c（≤180 拍），余额掉到 ≤10%
                hit = None
                for j in (i, i + 1):
                    if j < len(tk) and tk[j]["t"] - tk[i - 1]["t"] <= 180 and tk[i - 1]["bal"] > 20000 and tk[j]["bal"] <= 0.10 * tk[i - 1]["bal"]:
                        hit = j
                        break
                if hit is None:
                    i += 1
                    continue
                a, c = tk[i - 1], tk[hit]
                pend = [r for r in D if r["donor"] == me and a["t"] - 700 <= r["t"] <= c["t"] and r["status"] != "EXEC"]
                ratio = c["bal"] / a["bal"]
                best = None
                prod, bal, amt_sum, fee_sum = 1.0, float(a["bal"]), 0.0, 0.0
                for k, r in enumerate(reversed(pend), 1):
                    f = (r["pct"] + 1 + 64) / 1024.0
                    amt_sum += bal * (r["pct"] + 1) / 1024.0
                    fee_sum += bal * 64 / 1024.0
                    bal *= (1 - f)
                    prod *= (1 - f)
                    if best is None or abs(prod - ratio) < abs(best[1] - ratio):
                        best = (k, prod, amt_sum, fee_sum)
                bs = "%d 笔、%.4f、%d、%d" % (best[0], best[1], best[2], best[3]) if best else "-"
                print("     %s | %d~%d | %d→%d（%.4f）| %d→%d | %d | %s" % (
                    name(me), a["t"], c["t"], a["bal"], c["bal"], ratio, a["terr"], c["terr"], len(pend), bs))
                i = hit + 1

    print("[HD] 大幅失地窗（单窗丢 ≥8% 且 ≥300 格）：号 队 | 窗 | 地 前→后 | 兵 前→后（密度 前→后）| nb 前/后 | neut 前/后 | 新指令 / 船")
    for me in sorted(bots):
        tk = bots[me]["ticks"]
        for i in range(1, len(tk)):
            a, c = tk[i - 1], tk[i]
            if c["t"] - a["t"] > 270:
                continue
            d = a["terr"] - c["terr"]
            if d >= 300 and d >= 0.08 * a["terr"]:
                print("     %s | %d~%d | %d→%d | %d→%d（%.1f→%.1f）| %d/%d | %d/%d | %d / %d" % (
                    name(me), a["t"], c["t"], a["terr"], c["terr"], a["bal"], c["bal"], a["dens"], c["dens"],
                    a["nb"], c["nb"], a["neut"], c["neut"], c["cmds"] - a["cmds"], c["boats"] - a["boats"]))

    # [HI] 结果行里的全队领土 对照 这一队里还有日志的编队号（取结果拍之前 ≤180 拍的最近一条快照）
    print("[HI] 结果拍的全队领土 对照 队里还在记日志的编队号：拍（哪个号的结果行）| 各队：全队格数（占陆地 %）← 其中在记日志的编队号 个数 / 格数（占全队 %）/ 兵")
    land = F["land"]
    seen = set()
    for me, b in sorted(bots.items(), key=lambda kv: (kv[1].get("deathTick") or 10 ** 9)):
        tot = b.get("teamTotals")
        dt = b.get("deathTick")
        if not tot or dt is None or dt in seen:
            continue
        seen.add(dt)
        cells = []
        for k, v in sorted(tot.items(), key=lambda kv: int(kv[0])):
            tm = int(k)
            if tm == 0:
                continue
            n = terr = bal = 0
            for me2, b2 in bots.items():
                if b2.get("team") != tm:
                    continue
                s = None
                for x in b2["ticks"]:
                    if x["t"] <= dt:
                        s = x
                if s is None or dt - s["t"] > 180 or (b2.get("deathTick") is not None and b2["deathTick"] <= dt and b2.get("event") == "died"):
                    continue
                n += 1; terr += s["terr"]; bal += s["bal"]
            cells.append("T%d %d（%.1f%%）← %d / %d（%.1f%%）/ %d" % (tm, v, 100 * v / land, n, terr, (100 * terr / v if v else 0), bal))
        print("     %5d（%s）| %s" % (dt, b["labels"][0], " | ".join(cells)))

    print("[HE] 整队囤兵（每 900 拍一行；只算这一拍有快照的号）：拍 | 各队：号数 / 地合计 / 兵合计 / 密度 / 被围个数 / 超 100× 个数")
    teams = sorted({b.get("team") for b in bots.values() if b.get("team") is not None})
    all_t = sorted({s["t"] for b in bots.values() for s in b["ticks"]})
    for t in all_t:
        if t % 900 != 0 or t < 1800:
            continue
        cells = []
        for tm in teams:
            n = terr = bal = box = over = 0
            for me, b in bots.items():
                if b.get("team") != tm:
                    continue
                s = next((x for x in b["ticks"] if x["t"] == t), None)
                if s is None:
                    continue
                n += 1; terr += s["terr"]; bal += s["bal"]
                box += 1 if (s["nb"] == 0 and s["neut"] == 0) else 0
                over += 1 if s["bal"] > 100 * s["terr"] else 0
            cells.append("T%s %d / %d / %d / %.1f / %d / %d" % (tm, n, terr, bal, (bal / terr if terr else 0), box, over))
        print("     %5d | %s" % (t, " | ".join(cells)))


if __name__ == "__main__":
    main()
