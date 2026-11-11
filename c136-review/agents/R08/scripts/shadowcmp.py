#!/usr/bin/env python3
"""shadowcmp.py — 把影子决策（shadow.json）和录像里真正执行的指令（resim.json 的 cmdLog）、真机日志（in_game.log）逐条对账。

    python3 shadowcmp.py <matchId> [--bot <名字>] [--quiet]
输出 out/<matchId>/shadowcmp.txt：
  [SA] 影子可信度：每个号「真机 HL-TICK 的 cmds 计数」对「影子 cmds 计数」、HL-OPENING 行逐条一致率；
  [SB] 指令时延：每条已执行指令配上「同类型、同 pct（目标一致优先）」的最早一条影子指令，执行拍 − 影子决策拍 = 时延；
       按时间段给中位/最大时延，列出同一服务器拍一次冲出多条的批次；
  [SC] 影子想发而录像里没有的（被丢/被本地拒/节流），与录像里有而影子没有的（局面滞后导致的不同决定）；
  [SD] isNoFullSend 置位拍。
匹配口径：陆攻按 (pct, 目标)；目标已死变空地的按 pct 单独配；船按 pct；捐款按 (pct, 收款人)。时延上限 600 拍。
"""
import json
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from truth import Truth, NEUTRAL  # noqa: E402
import r08lib as L  # noqa: E402

MAXLAG = 600


def median(v):
    v = sorted(v)
    return v[len(v) // 2] if v else None


def match_bot(T, name, sb):
    p = sb["id"]
    real = [c for c in T.R["cmdLog"] if c[1] == p and c[2] in (1, 2, 3)]
    sh = [c for c in sb["cmds"] if c[1] in (1, 2, 3)]
    used = [False] * len(sh)
    pairs = []          # (real, shadow index or None, lag)
    for c in real:
        te, kind, pct = c[0], c[2], c[3]
        tgt = min(c[4], NEUTRAL) if kind in (1, 2) else None
        best = None
        # 先在近窗（≤40 拍）里找，再放宽到 MAXLAG；每一档里目标一致优先、先发先配
        for lo in (40, MAXLAG):
            for strict in (True, False):
                for i, s in enumerate(sh):
                    if used[i] or s[1] != kind or s[2] != pct:
                        continue
                    if not (te - lo <= s[0] < te):
                        continue
                    if kind in (1, 2) and strict and s[3] != tgt:
                        continue
                    if kind == 2 and s[3] != tgt:
                        continue
                    best = i
                    break
                if best is not None:
                    break
            if best is not None:
                break
        if best is not None:
            used[best] = True
            pairs.append((c, best, te - sh[best][0]))
        else:
            pairs.append((c, None, None))
    return real, sh, used, pairs


def sec_SH(S, T, w):
    """[SH] 口粮门槛普查：影子在真值上每隔几拍把「接壤的内置 AI」按 pickTarget 的顺序过一遍门槛（不落后的客户端此刻的代码口径）。
    重点数：没有任何 AI 过得了门槛、且最便宜那个被防人机留底 sb（safeFinite）挡住的号·点；sb 由谁的余额定出；两个号互相定对方 sb 的互锁。"""
    WIN = [(300, 630), (630, 900), (900, 1260), (1260, 1500), (1500, 1800)]
    rows = {}
    for name, sb in S["bots"].items():
        for c in sb.get("census", []):
            if len(c) < 14:
                return
            rows[(sb["id"], c[0])] = (name, c)
    if not rows:
        return
    every = sorted({t for (_, t) in rows})
    step = every[1] - every[0] if len(every) > 1 else 0
    w("")
    w(f"[SH] 口粮门槛普查（影子按真值每 {step} 拍一次；t<1500 打内置 AI 的可用兵 = 余额 − max(winFloor 价位底, dpKeep, sb)，c110 L2270-2276 / L4542-4550 / L2532-2541）")
    w("  窗口 | 号·点 | 接壤 AI 的 | 其中至少一个 AI 过门槛 | 全被挡 | 最便宜那个被挡的原因分布")
    tot_lock = defaultdict(int)
    for a, b in WIN:
        n = nai = ok = 0
        why = defaultdict(int)
        for (p, t), (name, c) in rows.items():
            if not (a <= t < b):
                continue
            n += 1
            if c[10] == "noAI":
                continue
            nai += 1
            if c[13] > 0:
                ok += 1
                continue
            why[c[10]] += 1
        ws = " ".join(f"{k}:{v}" for k, v in sorted(why.items(), key=lambda kv: -kv[1]))
        w(f"  {a}~{b} | {n} | {nai} | {ok} | {nai - ok} | {ws}")
    w("  sb 挡住（全被挡且最便宜那个的原因含 floor:sb）时，sb 由谁的余额定出：窗口 | 号·点 | 本编队同队 / 本编队异队 / 另一支受控编队 / 同队真人 / 敌队真人 / 内置 AI | 其中互锁（对方同一点也被我定的 sb 挡住）| 被挡 AI 的兵为 0 的 | 吃光它所需 ≤ 自己余额 10% 的")
    for a, b in WIN:
        n = 0
        cat = defaultdict(int)
        mutual = zero = cheap = 0
        for (p, t), (name, c) in rows.items():
            if not (a <= t < b) or c[10] == "noAI" or c[13] > 0 or "floor:sb" not in c[10] or not c[11]:
                continue
            n += 1
            src = c[11]
            cat[src[2]] += 1
            o = rows.get((src[1], t))
            if o and o[1][10] != "noAI" and o[1][13] == 0 and "floor:sb" in o[1][10] and o[1][11] and o[1][11][1] == p:
                mutual += 1
            if c[7] == 0:
                zero += 1
            if c[8] <= 0.10 * c[1]:
                cheap += 1
        if n:
            tot_lock[(a, b)] = n
        w(f"  {a}~{b} | {n} | {cat['squadSameTeam']} / {cat['squadOtherTeam']} / {cat['peerSameTeam'] + cat['peerOtherTeam']} / {cat['teammate']} / {cat['enemy']} / {cat['ai']} | {mutual} | {zero} | {cheap}")
    w("  逐号（t<1500 全被 sb 挡住的点数 ≥10 的）：号 | 点数 | 首末拍 | 定 sb 的邻居（次数）| 中位：自己余额 / sb / 被挡 AI 的格数·兵·吃光所需")
    per = defaultdict(list)
    for (p, t), (name, c) in rows.items():
        if t < 1500 and c[10] != "noAI" and c[13] == 0 and "floor:sb" in c[10] and c[11]:
            per[name].append(c)
    for name, cs in sorted(per.items(), key=lambda kv: -len(kv[1])):
        if len(cs) < 10:
            continue
        who = defaultdict(int)
        for c in cs:
            o = c[11][1]
            who[f"{T.nm(o)}[{c[11][2]}]"] += 1
        med = lambda xs: sorted(xs)[len(xs) // 2]
        ws = " ".join(f"{k}×{v}" for k, v in sorted(who.items(), key=lambda kv: -kv[1])[:4])
        w(f"  {name:12s} | {len(cs)} | {min(c[0] for c in cs)}~{max(c[0] for c in cs)} | {ws} | {med([c[1] for c in cs])} / {med([c[11][5] for c in cs])} / {med([c[6] for c in cs])}·{med([c[7] for c in cs])}·{med([c[8] for c in cs])}")


def sec_SI(S, T, w, allpairs):
    """[SI] 同一次 act 里发出多条指令时，第 1 条与第 2 条及以后各有多少进了录像（验证「适配层每次 act 只受理 1 条」）。"""
    KN = {1: "攻", 2: "捐", 3: "船"}
    stat = defaultdict(lambda: [0, 0])
    ex = []
    for name, (real, sh, used, pairs) in allpairs.items():
        by = defaultdict(list)
        for i, c in enumerate(sh):
            by[c[0]].append(i)
        for t, idx in sorted(by.items()):
            if len(idx) < 2:
                stat["single"][0] += 1
                stat["single"][1] += 1 if used[idx[0]] else 0
                continue
            for k, i in enumerate(idx):
                key = "first" if k == 0 else "later"
                stat[key][0] += 1
                stat[key][1] += 1 if used[i] else 0
            ex.append((t, name, [(KN[sh[i][1]], sh[i][2], (T.nm(sh[i][3]) if sh[i][1] != 3 and sh[i][3] < NEUTRAL else "空地" if sh[i][1] != 3 else "-"),
                                  round(sh[i][6] * (sh[i][2] + 1) / 1024) if len(sh[i]) > 6 else None, used[i]) for i in idx]))
    if not stat["first"][0]:
        return
    pc = lambda v: f"{v[1]}/{v[0]}（{round(100 * v[1] / max(1, v[0]))}%）"
    w("")
    w("[SI] 同一次 act 里的多条指令：影子一次 act 只发 1 条的 / 发多条时的第 1 条 / 第 2 条及以后，各有多少在录像里配上了")
    w(f"  单条 {pc(stat['single'])} | 多条的第 1 条 {pc(stat['first'])} | 多条的第 2 条及以后 {pc(stat['later'])}")
    w("  逐次（决策拍 | 号 | 各条：类型 pct 目标 本意兵力 录像里有没有）；按第 2 条及以后的本意兵力排序前 25 次")
    ex.sort(key=lambda e: -max((x[3] or 0) for x in e[2][1:]))
    for t, name, lst in ex[:25]:
        w(f"  {t} | {name} | " + " ; ".join(f"{k} {pct} →{tg} {tr} {'有' if u else '无'}" for (k, pct, tg, tr, u) in lst))


def main():
    args = sys.argv[1:]
    mid = args[0]
    quiet = "--quiet" in args
    only = args[args.index("--bot") + 1] if "--bot" in args else None
    T = Truth(mid)
    peer = "--side" in args and args[args.index("--side") + 1] == "peer"
    S = json.load(open(os.path.join(L.OUT, mid, "shadow_peer.json" if peer else "shadow.json"), encoding="utf-8"))
    out = []
    w = out.append
    tn = lambda q, t=0: "空地" if q >= NEUTRAL else (f"AI{q}" if q >= T.H else T.nm(q, t))  # noqa: E731

    # 真机日志
    logp = os.path.join(L.DATA, "bundles", T.R.get("peer") if peer else mid, "in_game.log")
    real_tick = defaultdict(dict)     # label -> t -> cmds
    real_open = defaultdict(set)
    if os.path.exists(logp):
        for line in open(logp, encoding="utf-8", errors="replace"):
            m = re.search(r"\[([^\]]+)\] \[HL-TICK\] t=(\d+) .*?cmds=(\d+) boats=(\d+)", line)
            if m:
                real_tick[m.group(1)][int(m.group(2))] = (int(m.group(3)), int(m.group(4)))
                continue
            m = re.search(r"\[([^\]]+)\] (\[HL-OPENING\] t=\d+ .*)$", line)
            if m:
                real_open[m.group(1)].add(m.group(2).strip())

    w(f"[SA] 影子可信度（{mid}，策略 {S['strategy']}，录像取自 {S['replayFrom']}，到 t={S['endTick']}）")
    w("  号 | 真机 HL-TICK 条数（按日志标签=号名的部分）| cmds 计数：一致 / 差 1 / 差更多 | 末条 真机 vs 影子 | HL-OPENING 真机条数 / 影子逐字相同条数 | 影子报错")
    for name, sb in sorted(S["bots"].items(), key=lambda kv: kv[1]["id"]):
        sh_tick = {}
        sh_open = set()
        for t, l in sb["logs"]:
            m = re.search(r"\[HL-TICK\] t=(\d+) .*?cmds=(\d+) boats=(\d+)", l)
            if m:
                sh_tick[int(m.group(1))] = (int(m.group(2)), int(m.group(3)))
            elif l.startswith("[HL-OPENING]"):
                sh_open.add(l.strip())
        label = name.split(":", 1)[1] if ":" in name else name
        rt = real_tick.get(label, {})
        eq = d1 = dm = 0
        last = ""
        for t in sorted(rt):
            if t not in sh_tick:
                continue
            d = sh_tick[t][0] - rt[t][0]
            if d == 0:
                eq += 1
            elif abs(d) == 1:
                d1 += 1
            else:
                dm += 1
            last = f"t={t} {rt[t][0]} vs {sh_tick[t][0]}"
        ro = real_open.get(label, set())
        w(f"  {name:12s} | {len(rt):3d} | {eq}/{d1}/{dm} | {last} | {len(ro)}/{len(ro & sh_open)} | {len(sb['errors'])}")

    w("")
    w("[SB] 指令时延（执行拍 − 影子决策拍）")
    w("  号 | 已执行指令数 | 配上影子的 | 各时段中位时延（<630 / 630~1260 / 1260~1800 / 1800~3500 / >3500）| 最大时延@执行拍 | 时延≥35 拍的条数 | ≥90 拍的条数")
    allpairs = {}
    for name, sb in sorted(S["bots"].items(), key=lambda kv: kv[1]["id"]):
        if only and name != only:
            continue
        real, sh, used, pairs = match_bot(T, name, sb)
        allpairs[name] = (real, sh, used, pairs)
        seg = defaultdict(list)
        mx = (0, 0)
        ge35 = ge90 = 0
        for c, i, lag in pairs:
            if lag is None:
                continue
            t = c[0]
            k = 0 if t < 630 else 1 if t < 1260 else 2 if t < 1800 else 3 if t < 3500 else 4
            seg[k].append(lag)
            if lag > mx[0]:
                mx = (lag, t)
            ge35 += lag >= 35
            ge90 += lag >= 90
        nm = sum(1 for _, i, _ in pairs if i is not None)
        w(f"  {name:12s} | {len(real):3d} | {nm:3d} | " + " / ".join(str(median(seg[k])) if seg[k] else "-" for k in range(5)) + f" | {mx[0]}@{mx[1]} | {ge35} | {ge90}")

    w("")
    w("[SB2] 同一服务器拍冲出 ≥3 条的批次（影子决策拍跨度 = 这些指令本来分布在多少拍里）")
    for name, (real, sh, used, pairs) in allpairs.items():
        by = defaultdict(list)
        for c, i, lag in pairs:
            by[c[0]].append((c, i, lag))
        for te in sorted(by):
            g = by[te]
            if len(g) < 3:
                continue
            ds = [sh[i][0] for _, i, _ in g if i is not None]
            span = f"影子决策拍 {min(ds)}~{max(ds)}" if ds else "影子无对应"
            w(f"  {name} 执行拍 {te} 一次 {len(g)} 条：" + " ".join(
                f"{'攻' if c[2] == 1 else '捐' if c[2] == 2 else '船'}{c[3]}{'✓' if c[5] else '✗'}" for c, _, _ in g) + f" | {span}")

    w("")
    w("[SC] 没配上的：影子想发而录像里没有 / 录像里有而影子没有")
    w("  号 | 影子指令数 | 影子多出（陆攻/捐/船）| 录像多出（陆攻/捐/船）")
    for name, (real, sh, used, pairs) in allpairs.items():
        ex_s = defaultdict(int)
        for i, s in enumerate(sh):
            if not used[i]:
                ex_s[s[1]] += 1
        ex_r = defaultdict(int)
        for c, i, lag in pairs:
            if i is None:
                ex_r[c[2]] += 1
        w(f"  {name:12s} | {len(sh):3d} | {ex_s[1]}/{ex_s[2]}/{ex_s[3]} | {ex_r[1]}/{ex_r[2]}/{ex_r[3]}")

    w("")
    w("[SD] isNoFullSend（影子内部状态；置位后不会复位）")
    w("  号 | 置位拍 | 那一手想发 want | 7 拍窗口里看到的余额降幅 actualSent | 窗口内真正执行的本号指令（拍:类型:实发）| 当时身上的进攻兵")
    for name, sb in sorted(S["bots"].items(), key=lambda kv: kv[1]["id"]):
        locks = sb.get("locks", [])
        if not locks:
            w(f"  {name:12s} | 从未置位")
            continue
        for lk in locks:
            pc = lk.get("pc") or {}
            p = sb["id"]
            t0 = (pc.get("t", lk["t"]) - 1)
            ex = [c for c in T.R["cmdLog"] if c[1] == p and c[2] in (1, 2, 3) and t0 <= c[0] <= lk["t"]]
            exs = " ".join(f"{c[0]}:{'攻' if c[2] == 1 else '捐' if c[2] == 2 else '船'}:{c[6]}" for c in ex) or "无"
            w(f"  {name:12s} | {lk['t']} | {round(pc.get('want', 0))} | {lk.get('actualSent')} | {exs} | {lk.get('incoming')}")

    # 口粮门槛普查
    sec_SH(S, T, w)
    sec_SI(S, T, w, allpairs)

    # 全队时延曲线
    w("")
    w("[SF] 全队时延曲线：按执行拍每 180 拍一窗，配上影子的已执行指令的时延 中位 / P90 / 最大，及其中落地时已无效（生效=0）的陆攻占比")
    byw = defaultdict(list)
    inval = defaultdict(lambda: [0, 0])
    for name, (real, sh, used, pairs) in allpairs.items():
        for c, i, lag in pairs:
            k = c[0] // 180
            if lag is not None:
                byw[k].append(lag)
            if c[2] == 1:
                inval[k][0] += 1
                inval[k][1] += 0 if c[5] else 1
    for k in sorted(set(byw) | set(inval)):
        v = sorted(byw[k])
        if not v and not inval[k][0]:
            continue
        med = v[len(v) // 2] if v else "-"
        p90 = v[min(len(v) - 1, int(0.9 * len(v)))] if v else "-"
        mx = v[-1] if v else "-"
        a, b = inval[k]
        w(f"  {k * 180:5d}~{k * 180 + 179:5d} | 指令 {len(v):3d} | 时延 中位 {med} / P90 {p90} / 最大 {mx} | 陆攻 {a} 条，其中无效 {b}（{100 * b / max(a, 1):.0f}%）")

    # 过期放大：指令带的是「执行时余额的千分比」，滞后期间余额涨了，同一条指令实发兵跟着放大
    w("")
    w("[SG] 过期放大（时延≥35 拍、已生效的陆攻/船）：决策拍 余额→本意兵力 | 执行拍 余额→实发兵力 | 放大倍数；按多发出去的兵排序前 20 条")
    rows = []
    tot_int = tot_act = 0
    for name, (real, sh, used, pairs) in allpairs.items():
        for c, i, lag in pairs:
            if i is None or lag < 35 or c[2] not in (1, 3) or not c[5]:
                continue
            sbal = sh[i][6]
            intended = (c[3] + 1) * sbal // 1024
            actual = c[6]
            tot_int += intended
            tot_act += actual
            tgt = tn(min(c[4], NEUTRAL), c[0]) if c[2] == 1 else (tn(c[10], c[0]) if c[10] >= 0 else "?")
            rows.append((actual - intended, name, sh[i][0], sbal, intended, c[0], c[8], actual, "攻" if c[2] == 1 else "船", c[3], tgt, lag))
    rows.sort(reverse=True)
    w(f"  合计 {len(rows)} 条：本意 {tot_int}，实发 {tot_act}（{tot_act / max(tot_int, 1):.2f} 倍）")
    for ex, name, ts, sbal, intended, te, bal, actual, kind, pct, tgt, lag in rows[:20]:
        w(f"  {name:12s} {kind}{pct} →{tgt} | 决策 {ts} 余额 {sbal} 本意 {intended} | 执行 {te} 余额 {bal} 实发 {actual} | {actual / max(intended, 1):.1f} 倍（晚 {lag} 拍）")

    if only:
        real, sh, used, pairs = allpairs[only]
        w("")
        w(f"[SE] {only} 逐条：执行拍 | 类型 pct 目标 | 生效 | 影子决策拍 | 时延")
        for c, i, lag in pairs:
            kind = "陆攻" if c[2] == 1 else "捐款" if c[2] == 2 else "发船"
            tgt = tn(min(c[4], NEUTRAL), c[0]) if c[2] != 3 else (tn(c[10], c[0]) if c[10] >= 0 else "?")
            w(f"  {c[0]:5d} | {kind} {c[3]} →{tgt} | {c[5]} | {sh[i][0] if i is not None else '-'} | {lag if lag is not None else '-'}")
        w(f"  影子多出：")
        for i, s in enumerate(sh):
            if not used[i]:
                kind = "陆攻" if s[1] == 1 else "捐款" if s[1] == 2 else "发船"
                tgt = tn(s[3], s[0]) if s[1] != 3 else (tn(s[5], s[0]) if s[5] >= 0 else "?")
                w(f"    {s[0]:5d} | {kind} {s[2]} →{tgt} | 本地校验 {s[4]} | 当时余额 {s[6]} 地 {s[7]}")

    text = "\n".join(out)
    if not only:
        open(os.path.join(L.OUT, mid, "shadowcmp_peer.txt" if peer else "shadowcmp.txt"), "w", encoding="utf-8").write(text + "\n")
    if not quiet:
        print(text)


if __name__ == "__main__":
    main()
