#!/usr/bin/env python3
"""roompairs.py — 同一个物理房间出了两份对局包时，整局重演该用哪一份包的录像。

两支编队进了同一个房间，两份对局包里各有一份录像；有的包自己的录像中途断了（B043 只到 819 拍、B038 只有出生期），
同房另一份包却录了全程。录像是同一场对局的同一条指令流，所以拿长的那份重演，本包的号按名字在名单里认。
只读 /agent/repos/c136-data 发现集（录像头由 replay_cmds.mjs 解到 out/_run/streams/）。

    python3 roompairs.py [--quiet]
    → out/_run/room_pairs.json   {局: 录像取自哪一局}（namepool.mjs / deathbank.mjs / fid_batch.sh 读）
    → out/_run/fid_extra.json    [[局, 真人数, 编队档, 录像取自哪一局], …]：靠这条规则才有对局段可重演的局（不在 fidabl_list.json 的局单里）
    → out/_cross/roompairs.txt

规则：
  · 同一个房间 = 录像头的真人数、地图号、地图种子、出生种子、整张名单全都相同。
  · 本包的号 = facts.py 席位表里的号；「认得出」= 名单里有名字以它的日志标签结尾的席位。
  · 同房另一份包的录像比自己的长 ≥300 拍（地的流水一个窗），并且本包的号在那份名单里认得出 ≥5 个 → 改用那一份。
    差不到 300 拍的（A010 和 B009 差 91 拍）不换：换了只多出不到一个窗，却要把已经对过引擎的那一份重演作废。
"""
import glob
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import facts  # noqa: E402
import xbatch as XB  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")
STREAMS = os.path.join(OUT, "_run", "streams")
MIN_GAIN = 300
MIN_SEATS = 5


def cut_of(rec):
    """这份录像上，模拟器的重演和真引擎第一次全场对不上的那一拍（engdiff.mjs 每 10 拍比 512 个玩家，fidmism.mjs 再逐拍定位）。
    返回 (拍, 有没有对过引擎)：一直对得上 → (None, True)；这份录像没跑过 engdiff → (None, False)。
    这一拍以后重演出来的东西不能当真相用——名字池账和出局账都只算到它之前。"""
    try:
        E = json.load(open(os.path.join(OUT, "_run", "engdiff", f"{rec}.json"), encoding="utf-8"))
    except Exception:
        return None, False
    if E.get("firstT") is None:
        return None, True
    return E.get("exactT", E["firstT"]), True


def found(mid, low_names):
    """本包的号里，名字在这张名单里认得出的个数 / 本包的号数。"""
    F = facts.build(mid)
    n = k = 0
    for _me, b in F["bots"].items():
        n += 1
        labs = [lab.lower() for lab in b["labels"]]
        if any(nm.endswith(lab) for nm in low_names for lab in labs):
            k += 1
    return k, n


def main():
    quiet = "--quiet" in sys.argv
    cohort = {mid: card.get("cohort") for mid, card in XB.discovery_ids()}
    try:
        XT = {m["matchId"]: m for m in json.load(open(os.path.join(OUT, "_cross", "xtruth.json"), encoding="utf-8"))["matches"]}
    except Exception:
        XT = {}
    try:
        base = {m for m, _h, _c in json.load(open(os.path.join(OUT, "_run", "fidabl_list.json"), encoding="utf-8"))}
    except Exception:
        base = set()
    rooms = defaultdict(list)
    n_rec = 0
    for fp in sorted(glob.glob(os.path.join(STREAMS, "*.json"))):
        m = json.load(open(fp, encoding="utf-8"))["meta"]
        if m["matchId"] not in cohort:
            continue
        n_rec += 1
        key = (m["humanCount"], m["mapType"], m["mapProceduralIndex"], m["mapRealisticIndex"], m["mapSeed"], m["spawningSeed"], tuple(str(x) for x in m["names"]))
        rooms[key].append((m["matchId"], m["lastTick"], [str(x).strip().lower() for x in m["names"]]))
    lines = []

    def P(s=""):
        lines.append(s)

    multi = [v for v in rooms.values() if len(v) > 1]
    P(f"roompairs.py — 发现集有录像的 {n_rec} 份对局包是 {len(rooms)} 个物理房间；同一个房间出了两份包的 {len(multi)} 个")
    P()
    P("[RP-A] 逐个房间：包（编队档）｜自己的录像到哪一拍｜本包的号在名单里认得出几个｜在不在 89 局的局单里（重演对得上、有对局段）")
    pairs = {}
    extra = []
    for v in sorted(multi, key=lambda v: v[0][0]):
        longest = max(t for _m, t, _n in v)
        P(f"  真人 {len(v[0][2])} 的房间：")
        for mid, last, low in v:
            k, n = found(mid, low)
            xt = XT.get(mid, {})
            note = "在局单里" if mid in base else ("不在：录像只有出生期" if xt.get("spawnOnly") else ("不在：重演和日志对不上" if xt and not xt.get("valid") else "不在"))
            others = [(m2, t2) for m2, t2, _n in v if m2 != mid and t2 - last >= MIN_GAIN]
            use = None
            if others and k >= MIN_SEATS:
                use = max(others, key=lambda r: r[1])[0]
                pairs[mid] = use
                if mid not in base:
                    extra.append([mid, len(low), cohort.get(mid), use])
            P(f"    {mid}（{cohort.get(mid)}）｜{last} 拍｜{k} / {n}｜{note}" + (f"｜→ 整局重演改用 {use} 的录像（{longest} 拍）" if use else ""))
    P()
    P(f"[RP-B] 结论：改用同房另一份录像的 {len(pairs)} 局：" + "；".join(f"{m} ← {s}" for m, s in sorted(pairs.items())))
    P(f"  其中本来不在 89 局局单里、这样才有对局段可重演的 {len(extra)} 局：" + (" ".join(r[0] for r in extra) or "无")
      + "（只进名字池账和出局账；重演和日志对不对得上，由那两本账各自打印的逐行核对把关）")
    os.makedirs(os.path.join(OUT, "_run"), exist_ok=True)
    json.dump(pairs, open(os.path.join(OUT, "_run", "room_pairs.json"), "w", encoding="utf-8"))
    json.dump(extra, open(os.path.join(OUT, "_run", "fid_extra.json"), "w", encoding="utf-8"))
    os.makedirs(os.path.join(OUT, "_cross"), exist_ok=True)
    open(os.path.join(OUT, "_cross", "roompairs.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    if not quiet:
        print("\n".join(lines))


if __name__ == "__main__":
    main()
