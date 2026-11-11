#!/usr/bin/env python3
"""22_bot_story.py — 逐号轨迹：相邻两个 HL-TICK 快照之间的变化 + 夹在中间的事件。

用法：
  python3 22_bot_story.py <out_dir>           （读 traj.csv opening.csv events.csv results.csv ids.json）

输出 <out_dir>/story_<bot>.txt，每个快照一行：
  t  terr  dTerr  bal  dBal  dBal%  dens  nb  neut  dCmds  dBoats  | 本区间 (t_prev, t] 内的事件摘要
事件摘要：
  OPEN(t,spend)            本号的 HL-OPENING（中立扩张指令，spend=发出的兵）
  DON>id(t,pct,~amt)       本号捐出：amt≈pct/1024*myBal（日志里的 myBal 是捐之前的在家兵力）
  RCV<bot(t,~amt)          队友日志里显示捐给本号的：amt≈pct/1024*对方 myBal（到账前的毛额，税后到账多少归 R04）
  INT(t,pct,~amt,boat,owner,boatTroops)   本号拦截：amt≈pct/1024*bal（bal 用最近一个快照的值线性估，标 ~）
  AST(t,enemy,ally)        本号 10% 协防出兵（pct=102/1024）
  AST<bot(t,enemy)         队友为本号发的协防
另外标记：
  [DROP30]  本区间（90 拍）在家兵力下降 >=30%
  [GAP]     与上一快照间隔不是 90 拍
所有 ~ 开头的数是估算（见各项说明），其余是日志原值。
"""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from c136lib import BOTS  # noqa: E402

out = sys.argv[1]
traj = list(csv.DictReader(open(f"{out}/traj.csv", encoding="utf-8")))
opening = list(csv.DictReader(open(f"{out}/opening.csv", encoding="utf-8")))
events = list(csv.DictReader(open(f"{out}/events.csv", encoding="utf-8")))
results = {r["bot"]: r for r in csv.DictReader(open(f"{out}/results.csv", encoding="utf-8"))}
ids = json.load(open(f"{out}/ids.json", encoding="utf-8"))
id2bot = {v["me"]: b for b, v in ids.items()}

for bot in BOTS:
    rows = [r for r in traj if r["bot"] == bot]
    my_id = ids[bot]["me"]
    evs = []
    for r in opening:
        if r["bot"] == bot:
            evs.append((int(r["t"]), f"OPEN({r['t']},{r['spend']}/{r['bal']})"))
    for e in events:
        t = int(e["t"])
        if e["type"] == "DONATE":
            amt = round(int(e["pct"]) / 1024 * int(e["myBal"]))
            if e["bot"] == bot:
                to = id2bot.get(int(e["target"]), e["target"])
                evs.append((t, f"DON>{to}({t},{e['kind'][:6]},~{amt})"))
            if int(e["target"]) == my_id:
                evs.append((t, f"RCV<{e['bot']}({t},~{amt})"))
        elif e["type"] == "ASSIST":
            if e["bot"] == bot:
                ally = id2bot.get(int(e["ally"]), e["ally"]) if e["ally"] else "boss"
                evs.append((t, f"AST({t},e{e['target']},for {ally})"))
            if e["ally"] and int(e["ally"]) == my_id:
                evs.append((t, f"AST<{e['bot']}({t},e{e['target']})"))
        elif e["type"] == "INTERCEPT" and e["bot"] == bot:
            evs.append((t, ("INT", t, int(e["pct"]), e["boatId"], e["target"], e["boatTroops"])))
    evs.sort(key=lambda x: x[0])

    L = []
    r0 = results.get(bot)
    if r0:
        L.append(f"# {bot} id={my_id} result={r0['result']} event={r0['event']} tick={r0['tick']} place={r0['place']} peak={r0['peak']} "
                 f"lastTerritory={r0['lastTerritory']} balance={r0['balance']} sent={r0['sent']} accepted={r0['accepted']}")
    L.append("t\tterr\tdTerr\tbal\tdBal\tdBal%\tdens\tnb\tneut\tdCmds\tdBoats\tflags\t| events in (prev,t]")
    prev = None
    # 开局段：t<第一条快照
    first_t = int(rows[0]["t"]) if rows else 10 ** 9
    pre = [x[1] for x in evs if x[0] <= first_t and isinstance(x[1], str)]
    if pre:
        L.append("(pre)\t\t\t\t\t\t\t\t\t\t\t\t| " + " ".join(pre))
    for r in rows:
        t, terr, bal = int(r["t"]), int(r["terr"]), int(r["bal"])
        flags = []
        if prev is None:
            d = ["", "", "", "", ""]
            pt = first_t - 1 if True else 0
            lo = first_t
            seg = []
        else:
            pt, pterr, pbal = int(prev["t"]), int(prev["terr"]), int(prev["bal"])
            dbal = bal - pbal
            pctb = 100 * dbal / pbal if pbal > 0 else 0
            d = [terr - pterr, dbal, f"{pctb:+.0f}%", int(r["cmds"]) - int(prev["cmds"]), int(r["boats"]) - int(prev["boats"])]
            if t - pt != 90:
                flags.append("GAP")
            if pbal > 0 and dbal <= -0.30 * pbal:
                flags.append("DROP30")
            seg = []
            for et, x in evs:
                if pt < et <= t:
                    if isinstance(x, tuple):
                        # 拦截出兵估算：按区间首尾 bal 线性插值
                        frac = (et - pt) / max(1, t - pt)
                        est_bal = pbal + frac * (bal - pbal)
                        seg.append(f"INT({x[1]},{x[2]}/1024,~{round(x[2] / 1024 * est_bal)},boat{x[3]},owner{x[4]},tr{x[5]})")
                    else:
                        seg.append(x)
        if prev is None:
            L.append(f"{t}\t{terr}\t\t{bal}\t\t\t{r['dens']}\t{r['nb']}\t{r['neut']}\t\t\t\t| (first snapshot; cmds={r['cmds']} boats={r['boats']})")
        else:
            L.append(f"{t}\t{terr}\t{d[0]:+d}\t{bal}\t{d[1]:+d}\t{d[2]}\t{r['dens']}\t{r['nb']}\t{r['neut']}\t{d[3]}\t{d[4]}\t{','.join(flags)}\t| " + " ".join(seg))
        prev = r
    if prev is not None:
        tail = [x[1] if isinstance(x[1], str) else f"INT({x[1][1]},{x[1][2]}/1024,boat{x[1][3]},owner{x[1][4]},tr{x[1][5]})" for x in evs if x[0] > int(prev["t"])]
        if tail:
            L.append("(after last snapshot)\t\t\t\t\t\t\t\t\t\t\t\t| " + " ".join(tail))
    open(f"{out}/story_{bot}.txt", "w", encoding="utf-8").write("\n".join(L) + "\n")
print("ok")
