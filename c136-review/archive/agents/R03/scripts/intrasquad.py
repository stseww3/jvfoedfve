#!/usr/bin/env python3
"""intrasquad.py — 编队的号互相打了多少（自由混战局，或编队被拆到不同队的局）。

数据：out/cache/<mid>-resim.json（重放精确值）。
  pairLog 每行 [桶末拍, 攻方, 守方, 得地, 攻方烧兵, 守方掉余额, 守方掉反击槽, …]，30 拍一桶；cmdLog 的陆攻行见 cmdq.py。
分类按该行当拍的状态：
  「在控」= 本房间的编队号、还没离线；「编队空壳」= 编队号离线后由内置 AI 托管；「其他真人」= 不是编队号的真人（含他们离线后的空壳）；AI；无主地。
输出：
  [X1] 总账：在控的编队号打各类目标的 指令条数/送出/手续费（cmdLog）与 烧/得地/对方掉余额（pairLog）；各类攻方打在控编队号的 烧/得地/掉余额
  [X2] 分时间窗（--step，默认 300 拍）：编队打编队、编队打其他真人、其他真人打编队 的 烧/得地
  [X3] 每个号：吃编队友/吃其他真人 的 得地、烧；被编队友/被其他真人 吃掉的格、掉的余额；出局前 300 拍被谁吃掉多少格
  [X4] 编队内每一对（攻→守）：第一条落地的陆攻指令拍、条数、送出、手续费；烧、得地、对方掉余额
  [X5] DROP30 分类：出手打编队友 / 出手打其他真人 / 被编队友打 / 被其他真人打 / 开局打 AI、无主地（读 out/dossier/<mid>-facts.json 的 drops）
用法：python3 scripts/intrasquad.py <mid> [--step 300]
"""
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from dossier import Dossier, k, NEUTRAL  # noqa: E402


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        sys.exit(2)
    mid = args[0]
    step = int(sys.argv[sys.argv.index("--step") + 1]) if "--step" in sys.argv else 300
    D = Dossier(mid)
    R = D.R
    H = D.H
    sq = set(D.sqids)
    left = D.left

    def cls(q, t):
        if q >= NEUTRAL:
            return "无主地"
        if q >= H:
            return "AI"
        gone = 0 <= left[q] <= t
        if q in sq:
            return "编队空壳" if gone else "在控"
        return "其他真人"

    order = ["在控", "编队空壳", "其他真人", "AI", "无主地"]
    mode = "自由混战（无队伍）" if not D.team_game else f"{R['nTeams']} 队"
    print(f"# {mid} 编队内互打账（intrasquad.py；{mode}；本房间编队号 {len(sq)} 个；pairLog 30 拍一桶、按桶末拍记）")

    # ---- [X1] 总账 ----
    cmd = defaultdict(lambda: [0, 0, 0])  # 目标类 -> [条, 送出, 手续费]
    for c in R["cmdLog"]:
        if c[2] != 1 or not c[5] or c[1] not in sq:
            continue
        t = c[0]
        if cls(c[1], t) != "在控":
            continue
        x = cmd[cls(min(c[4], NEUTRAL), t)]
        x[0] += 1; x[1] += c[6]; x[2] += c[7]
    out = defaultdict(lambda: [0, 0, 0])  # 目标类 -> [烧, 得地, 对方掉余额]
    inc = defaultdict(lambda: [0, 0, 0])  # 攻方类 -> [烧, 得地, 我方掉余额]
    for t, att, de, tiles, burnt, dB, dS, n in R["pairLog"]:
        ca = cls(att, t) if att < NEUTRAL else "无主地"
        cd = cls(de, t)
        if ca == "在控":
            x = out[cd]
            x[0] += burnt; x[1] += tiles; x[2] += dB
        if cd == "在控":
            x = inc[ca]
            x[0] += burnt; x[1] += tiles; x[2] += dB
    print("[X1] 总账（只算编队号在控期间）")
    for cl in order:
        c = cmd.get(cl, [0, 0, 0])
        o = out.get(cl, [0, 0, 0])
        print(f"  在控的编队号 → {cl}：陆攻 {c[0]} 条 送出 {k(c[1])} 手续费 {k(c[2])} | 烧 {k(o[0])} 得地 {o[1]} 对方掉余额 {k(o[2])}")
    for cl in order:
        i = inc.get(cl)
        if i:
            print(f"  {cl} → 在控的编队号：对方烧 {k(i[0])} 我失地 {i[1]} 我掉余额 {k(i[2])}")

    # ---- [X2] 分窗 ----
    end = R["endTick"]
    print(f"[X2] 每 {step} 拍：编队打编队 | 编队打其他真人 | 其他真人打编队（烧 / 得地）；在控号数取窗口起点")
    wins = defaultdict(lambda: [[0, 0], [0, 0], [0, 0]])
    for t, att, de, tiles, burnt, dB, dS, n in R["pairLog"]:
        if att >= NEUTRAL:
            continue
        ca, cd = cls(att, t), cls(de, t)
        w = ((t - 1) // step) * step
        if ca == "在控" and cd == "在控":
            x = wins[w][0]
        elif ca == "在控" and cd == "其他真人":
            x = wins[w][1]
        elif ca == "其他真人" and cd == "在控":
            x = wins[w][2]
        else:
            continue
        x[0] += burnt; x[1] += tiles
    for w in sorted(wins):
        a, b, c = wins[w]
        if not (a[1] or b[1] or c[1] or a[0] or b[0] or c[0]):
            continue
        n_ctrl = sum(1 for p in sq if R["snapTerr"][D.ix(w)][p] > 0 and not (0 <= left[p] <= w))
        print(f"  {w:>5}~{min(w + step, end):<5} 在控 {n_ctrl:>2} 个 | 互打 烧 {k(a[0]):>6} 得地 {a[1]:>6} | 打其他真人 烧 {k(b[0]):>6} 得地 {b[1]:>6} | 被其他真人 烧 {k(c[0]):>6} 失地 {c[1]:>6}")

    # ---- [X3] 每个号 ----
    print("[X3] 每个号（在控期间）：吃编队友 得地/烧 | 吃其他真人 得地/烧 | 被编队友吃 失地/掉余额 | 被其他真人吃 失地/掉余额 | 出局前 300 拍失地：编队友 / 其他真人 / 编队空壳")
    for p in D.sqids:
        b = D.bot_of[p]
        eat = {"在控": [0, 0], "编队空壳": [0, 0], "其他真人": [0, 0]}
        for t, att, de, tiles, burnt, dB, dS, n in D.pair_att.get(p, ()):
            if cls(p, t) != "在控":
                continue
            cd = cls(de, t)
            if cd in eat:
                eat[cd][0] += tiles; eat[cd][1] += burnt
        lost = {"在控": [0, 0], "编队空壳": [0, 0], "其他真人": [0, 0]}
        dt = D.death[p]
        last = {"在控": 0, "编队空壳": 0, "其他真人": 0}
        for t, att, de, tiles, burnt, dB, dS, n in D.pair_def.get(p, ()):
            if att >= NEUTRAL or cls(p, t) != "在控":
                continue
            ca = cls(att, t)
            if ca in lost:
                lost[ca][0] += tiles; lost[ca][1] += dB
                if dt >= 0 and dt - 300 < t <= dt + 30:
                    last[ca] += tiles
        fate = f"出局 {dt}" if dt >= 0 else "没出局"
        if left[p] >= 0:
            fate = f"离线 {left[p]}（" + fate + "）"
        print(f"  {b:<7} {fate:<22} | 吃编队友 {eat['在控'][0] + eat['编队空壳'][0]:>6} 格/{k(eat['在控'][1] + eat['编队空壳'][1]):>6} | 吃其他真人 {eat['其他真人'][0]:>6} 格/{k(eat['其他真人'][1]):>6} "
              f"| 被编队友 {lost['在控'][0]:>6} 格/{k(lost['在控'][1]):>6} | 被其他真人 {lost['其他真人'][0]:>6} 格/{k(lost['其他真人'][1]):>6} "
              f"| 末 300 拍：{last['在控']} / {last['其他真人']} / {last['编队空壳']}")

    # ---- [X4] 每一对 ----
    print("[X4] 编队内每一对（攻方在控；守方在控或空壳）：首条落地拍、陆攻条数、送出、手续费 | 烧、得地、对方掉余额")
    pc = defaultdict(lambda: [None, 0, 0, 0])
    for c in R["cmdLog"]:
        if c[2] != 1 or not c[5] or c[1] not in sq:
            continue
        q = min(c[4], NEUTRAL)
        if q not in sq or cls(c[1], c[0]) != "在控":
            continue
        x = pc[(c[1], q)]
        if x[0] is None:
            x[0] = c[0]
        x[1] += 1; x[2] += c[6]; x[3] += c[7]
    pp = defaultdict(lambda: [0, 0, 0])
    for t, att, de, tiles, burnt, dB, dS, n in R["pairLog"]:
        if att in sq and de in sq and cls(att, t) == "在控":
            x = pp[(att, de)]
            x[0] += burnt; x[1] += tiles; x[2] += dB
    keys = sorted(set(pc) | set(pp), key=lambda kx: (pc[kx][0] if pc[kx][0] is not None else 10 ** 9, kx))
    for (a, d) in keys:
        c = pc[(a, d)]
        o = pp[(a, d)]
        gone = "（守方已是空壳）" if left[d] >= 0 and c[0] is not None and c[0] >= left[d] else ""
        first = c[0] if c[0] is not None else "—"
        print(f"  {D.bot_of[a]:<7} → {D.bot_of[d]:<7} 首条 {first:>5} 拍 {c[1]:>2} 条 送出 {k(c[2]):>6} 手续费 {k(c[3]):>6} | 烧 {k(o[0]):>6} 得地 {o[1]:>6} 对方掉余额 {k(o[2]):>6}{gone}")

    # ---- [X5] DROP30 分类 ----
    fp = os.path.join(os.path.dirname(HERE), "out", "dossier", f"{mid}-facts.json")
    if os.path.exists(fp):
        drops = json.load(open(fp)).get("drops") or []
        names = set(D.sq)
        cat = defaultdict(list)
        for d in drops:
            tg = d.get("target") or ""
            who = [x.strip() for x in tg.replace("对 ", "").replace("被 ", "").split(",") if x.strip()]
            mates = [x for x in who if x in names]
            if d["main"] == "攻真人":
                key = "出手打编队友" if mates and len(mates) == len(who) else ("出手打编队友和其他真人" if mates else "出手打其他真人")
            elif d["main"] == "挨打":
                key = "被编队友打" if mates and len(mates) == len(who) else ("被编队友和其他真人一起打" if mates else "被其他真人打")
            else:
                key = "开局" + d["main"] if d["t1"] <= 1500 else d["main"]
            cat[key].append(d)
        print(f"[X5] DROP30 分类（out/dossier/{mid}-facts.json 的 drops，共 {len(drops)} 个；按卷宗 [I] 的主因和对象分）")
        for key in sorted(cat, key=lambda x: -len(cat[x])):
            rows = cat[key]
            print(f"  {key}：{len(rows)} 个 — " + "；".join(f"{d['bot']} {d['t0']}-{d['t1']}（−{d['dropPct']:.0f}%" + (f"，{d['target']}" if d.get("target") else "") + "）" for d in rows))


if __name__ == "__main__":
    main()
