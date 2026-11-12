#!/usr/bin/env python3
"""xchan2.py — 指令通道的两个补充事实（给「模拟器的通道模型怎么验收」用）：只数录像指令流，不做地图模拟。

和 xchan.py 用同一份解码（out/_run/streams/<局>.json，replay_cmds.mjs 产出）和同一套分组（own / [APEX] / 名字池 = 机器号；其余 = 野人）。
只读 /agent/repos/c136-data/bundles/（发现集）。

    python3 xchan2.py [--quiet]      → out/_cross/xchan2.txt、xchan2.json

节：
  [X2-A] 同一拍里不同席位的指令谁先执行：同一个服务器拍上有 ≥2 个席位落地时，执行顺序是不是按席位号排的；同一个席位的几条是不是挨在一起。
  [X2-B] 每个席位在连续 1 / 2 / 3 / 4 个回合（1 回合 = 7 拍）里最多落地几条（陆攻 + 捐款 + 发船）：用来检验「每回合 9 条」之外有没有跨回合的总量上限。
  [X2-C] 录像里出现过、重放器没有实现的指令号（6 表情、7 投票、10 指点进攻、5 带 513 = 发起投票）：各多少条、在哪些局。
"""
import json
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import xbatch as XB  # noqa: E402
import xchan as XC  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")
RUN = os.path.join(OUT, "_run", "streams")


def main():
    quiet = "--quiet" in sys.argv
    pool = XB.name_pool()
    ids = XB.discovery_ids()
    lines = []
    J = {}

    def P(s=""):
        lines.append(s)

    n_match = 0
    # [X2-A]
    ticks_multi = 0            # 有 ≥2 个不同席位落地的服务器拍
    ticks_sorted = 0           # 其中席位号不降
    ticks_contig = 0           # 其中同一个席位的指令挨在一起
    ticks_multi_bot = 0        # 有 ≥2 个机器号席位落地的拍
    ticks_sorted_bot = 0
    inv_pairs = Counter()      # 相邻两条指令 席位号下降 的次数（按前一条的组→后一条的组）
    # [X2-B]
    win_max = {g: {k: Counter() for k in (1, 2, 3, 4)} for g in ("bot", "wild")}     # k 个回合窗里的最大条数 → 席位数
    over = {g: Counter() for g in ("bot", "wild")}
    glob_max = {g: {k: 0 for k in (1, 2, 3, 4)} for g in ("bot", "wild")}
    seats = {"bot": 0, "wild": 0}
    # [X2-C]
    odd = Counter()
    odd_matches = defaultdict(set)
    vote_matches = set()

    for mid, card in ids:
        p = os.path.join(RUN, f"{mid}.json")
        if not os.path.exists(p):
            continue
        S = json.load(open(p, encoding="utf-8"))
        meta, cmds = S["meta"], S["cmds"]
        H = meta["humanCount"]
        grp = XC.groups(mid, meta, pool)
        n_match += 1
        by_tick = defaultdict(list)
        per_seat_turn = defaultdict(Counter)
        for t, cid, pl, dx, dz in cmds:
            if cid == 6 or cid == 7 or cid == 10:
                odd[cid] += 1
                odd_matches[cid].add(mid)
            if cid == 5 and dx == 513:
                odd["5/513"] += 1
                odd_matches["5/513"].add(mid)
            if cid in (7,) or (cid == 5 and dx == 513):
                vote_matches.add(mid)
            if t < 0 or pl >= H or cid not in (1, 2, 3):
                continue
            by_tick[t].append(pl)
            per_seat_turn[pl][t // 7] += 1
        for t, seq in by_tick.items():
            ds = set(seq)
            if len(ds) < 2:
                continue
            ticks_multi += 1
            srt = all(seq[i] <= seq[i + 1] for i in range(len(seq) - 1))
            ticks_sorted += srt
            # 同一席位是否挨在一起
            seen, last, contig = set(), None, True
            for s in seq:
                if s != last:
                    if s in seen:
                        contig = False
                        break
                    seen.add(s)
                    last = s
            ticks_contig += contig
            bots = [s for s in seq if grp[s] != "wild"]
            if len(set(bots)) >= 2:
                ticks_multi_bot += 1
                ticks_sorted_bot += all(bots[i] <= bots[i + 1] for i in range(len(bots) - 1))
            if not srt:
                for i in range(len(seq) - 1):
                    if seq[i] > seq[i + 1]:
                        inv_pairs[("wild" if grp[seq[i]] == "wild" else "bot", "wild" if grp[seq[i + 1]] == "wild" else "bot")] += 1
        for s, turns in per_seat_turn.items():
            g = "wild" if grp[s] == "wild" else "bot"
            seats[g] += 1
            ks = sorted(turns)
            for k in (1, 2, 3, 4):
                best = 0
                for u in ks:
                    tot = sum(turns.get(u + j, 0) for j in range(k))
                    if tot > best:
                        best = tot
                win_max[g][k][best] += 1
                glob_max[g][k] = max(glob_max[g][k], best)
            for u in ks:
                two = turns[u] + turns.get(u + 1, 0)
                three = two + turns.get(u + 2, 0)
                if turns[u] > 9:
                    over[g]["1>9"] += 1
                if turns.get(u + 1, 0) and two > 9:
                    over[g]["2>9"] += 1
                if two >= 18:
                    over[g]["2>=18"] += 1
                if turns.get(u + 1, 0) and turns.get(u + 2, 0) and three > 9:
                    over[g]["3>9"] += 1
                if three >= 27:
                    over[g]["3>=27"] += 1

    P(f"[X2-A] 同一个服务器拍里不同席位的执行顺序（{n_match} 份录像；陆攻 / 捐款 / 发船，t ≥ 0）")
    P(f"  有 ≥2 个不同席位落地的拍 {ticks_multi} 个：执行顺序按席位号不降的 {ticks_sorted}（{XC.pct(ticks_sorted, ticks_multi, 1)}）；同一个席位的几条挨在一起的 {ticks_contig}（{XC.pct(ticks_contig, ticks_multi, 1)}）")
    P(f"  有 ≥2 个机器号席位落地的拍 {ticks_multi_bot} 个：机器号之间按席位号不降的 {ticks_sorted_bot}（{XC.pct(ticks_sorted_bot, ticks_multi_bot, 1)}）")
    P("  席位号下降的相邻指令对（前一条的组→后一条的组）：" + ("；".join(f"{a}→{b} {n}" for (a, b), n in inv_pairs.most_common()) or "无"))
    J["order"] = dict(ticks=ticks_multi, sorted=ticks_sorted, contig=ticks_contig, botTicks=ticks_multi_bot, botSorted=ticks_sorted_bot)
    P()
    P("[X2-B] 每个席位在连续 k 个回合（1 回合 = 7 拍）里最多落地几条")
    P("  组 | 席位 | k=1 的最大值分布（≤3 / 4~8 / 9 / >9）| k=2（≤9 / 10~17 / 18 / >18）| k=3（≤9 / 10~18 / 19~26 / 27 / >27）| 全体最大 k=1 / 2 / 3 / 4")
    J["windows"] = {}
    for g, cn in (("bot", "机器号"), ("wild", "野人")):
        n = seats[g]
        c1, c2, c3 = win_max[g][1], win_max[g][2], win_max[g][3]
        a = [sum(v for k, v in c1.items() if k <= 3), sum(v for k, v in c1.items() if 4 <= k <= 8), c1.get(9, 0), sum(v for k, v in c1.items() if k > 9)]
        b = [sum(v for k, v in c2.items() if k <= 9), sum(v for k, v in c2.items() if 10 <= k <= 17), c2.get(18, 0), sum(v for k, v in c2.items() if k > 18)]
        c = [sum(v for k, v in c3.items() if k <= 9), sum(v for k, v in c3.items() if 10 <= k <= 18), sum(v for k, v in c3.items() if 19 <= k <= 26), c3.get(27, 0), sum(v for k, v in c3.items() if k > 27)]
        P(f"  {cn} | {n} | {' / '.join(XC.pct(x, n) for x in a)} | {' / '.join(XC.pct(x, n) for x in b)} | {' / '.join(XC.pct(x, n) for x in c)} | {glob_max[g][1]} / {glob_max[g][2]} / {glob_max[g][3]} / {glob_max[g][4]}")
        J["windows"][g] = dict(seats=n, max=glob_max[g], k1=a, k2=b, k3=c, over=dict(over[g]))
    P(f"  机器号：一个回合 >9 条的（席位, 回合）{over['bot']['1>9']} 个；相邻两个回合都有落地且合计 >9 条的 {over['bot']['2>9']} 个，合计 ≥18 条的 {over['bot']['2>=18']} 个；"
      f"连续三个回合都有落地且合计 >9 条的 {over['bot']['3>9']} 个，合计 ≥27 条的 {over['bot']['3>=27']} 个")
    P(f"  野人：一个回合 >9 条的 {over['wild']['1>9']} 个；相邻两个回合合计 >9 条的 {over['wild']['2>9']} 个，≥18 条的 {over['wild']['2>=18']} 个；连续三个回合合计 >9 条的 {over['wild']['3>9']} 个")
    P()
    P("[X2-C] 录像里有、重放器没有实现的指令号")
    P(f"  6（表情，只改显示）{odd[6]} 条 / {len(odd_matches[6])} 局；7（给和平投票投票）{odd[7]} 条 / {len(odd_matches[7])} 局；5 带 513（发起和平投票）{odd['5/513']} 条 / {len(odd_matches['5/513'])} 局；"
      f"10（指定落点的陆攻）{odd[10]} 条 / {len(odd_matches[10])} 局（{' '.join(sorted(odd_matches[10])) or '无'}）")
    P(f"  有过和平投票（发起或投票）的局 {len(vote_matches)} 个")
    J["odd"] = {str(k): v for k, v in odd.items()}
    J["oddMatches"] = {str(k): sorted(v) for k, v in odd_matches.items()}

    os.makedirs(os.path.join(OUT, "_cross"), exist_ok=True)
    open(os.path.join(OUT, "_cross", "xchan2.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    json.dump(J, open(os.path.join(OUT, "_cross", "xchan2.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if not quiet:
        print("\n".join(lines))


if __name__ == "__main__":
    main()
