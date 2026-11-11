#!/usr/bin/env python3
"""r07replay.py — 录像编码（replay.txt）的纯 Python 解码器（R07，v2.0）。

移植自 /agent/repos/c136-data/src/sim/tools/c102-replay-lib.mjs 的 decodeReplay()：
只解码「对局设置 + 全部指令 + 每拍指令数」，不重放地图（c136-data 里没有地图文件，无法整局重放）。

指令的执行拍号：
  录像尾部是一串 (jY, ja)：jY=1 表示「这一步执行 ja 条指令」，jY=0 表示「连续 ja 步没有指令」。
  每一步对应引擎的一拍（c102-replay-lib.mjs: makeStepper.step）。可选出生阶段先消耗 jJ+1 步
  （jJ = 人数<=2:30；<=50:40；否则 50；见 runSpawnPhase），其后第 k 步的指令在 g.t = k 时执行。

指令类型（id）：0 选点 | 1 陆攻(pct,target) | 2 捐款(pct,to) | 3 发船(pct, water*8+dir) | 4 追船/召回(pct,boatId；pct=849 是召回)
              | 5 撤回(target；513=无) | 6 ? | 7 和平投票(0/1) | 8/9 离开 | 10 翻山

用法：
  python3 r07replay.py <matchId>            # 打印设置摘要 + 指令类型计数
  作为库：from r07replay import load_replay
"""
import json
import os
import sys

DATA = "/agent/repos/c136-data"


class Bits:
    def __init__(self, raw):
        ga = raw.strip()
        eq = ga.find("=")
        if eq >= 0:
            ga = ga[eq + 1:]
        ga = "".join(ch if (ch.isalnum() or ch in "_-") else "-" for ch in ga)
        abv = [0] * 78
        abv[50] = 37
        for i in range(10):
            abv[i + 3] = i + 1
        for i in range(26):
            abv[i + 20] = i + 11
            abv[i + 52] = i + 38
        vals = [abv[ord(c) - 45] for c in ga]
        nbits = 6 * len(vals)
        big = 0
        for v in vals:
            big = (big << 6) | v
        self.big = big
        self.nbits = nbits
        self.pos = 0

    def take(self, size):
        if size == 0:
            return 0
        shift = self.nbits - self.pos - size
        self.pos += size
        if shift < 0:
            # 越界：与 JS 一致，越界位读作 0
            return (self.big << (-shift)) & ((1 << size) - 1)
        return (self.big >> shift) & ((1 << size) - 1)


def decode(raw):
    b = Bits(raw)
    i2 = b.take

    def a_str(n):
        ln = i2(n)
        return "".join(chr(i2(16)) for _ in range(ln))

    def a_arr(aEd, aY3, aZd):
        fe = i2(aEd)
        if not fe:
            return None
        ln = max(fe, aZd)
        dC = [0] * ln
        for i in range(fe):
            dC[i] = i2(aY3)
        if dC[fe - 1]:
            for i in range(fe, ln):
                dC[i] = dC[fe - 1]
        return dC

    def a_strs(aEd, aY6, aZd):
        fe = i2(aEd)
        if not fe:
            return None
        ln = max(fe, aZd)
        dC = [None] * ln
        for i in range(fe):
            dC[i] = a_str(aY6)
        for i in range(fe, ln):
            dC[i] = dC[fe - 1]
        return dC

    vu = {}
    vu["rVersion"] = i2(12)
    vu["vs"] = i2(12)
    vu["statedSize"] = i2(31)
    vu["mapType"] = i2(2)
    vu["mapProceduralIndex"] = i2(8)
    vu["mapRealisticIndex"] = i2(8)
    vu["mapSeed"] = i2(14)
    vu["mapName"] = a_str(5)
    if vu["mapType"] == 2:
        aDc = i2(30)
        b.pos += 6 * aDc
    vu["passableWater"] = i2(1)
    vu["passableMountains"] = i2(1)
    vu["playerCount"] = i2(10)
    vu["humanCount"] = i2(10)
    vu["selectedPlayer"] = i2(9)
    vu["gameMode"] = i2(1)
    vu["playerMode"] = i2(2)
    vu["battleRoyaleMode"] = i2(2)
    vu["numberTeams"] = i2(4)
    vu["isZombieMode"] = i2(1)
    vu["isContest"] = i2(1)
    vu["isReplay"] = i2(1)
    vu["elo"] = a_arr(2, 14, 2)
    vu["colorsType"] = i2(1)
    vu["colorsPersonalized"] = i2(1)
    vu["colorsData"] = a_arr(10, 18, 512)
    vu["selectableColor"] = i2(1)
    vu["teamPlayerCount"] = a_arr(4, 10, 9)
    vu["neutralBots"] = i2(1)
    vu["botDifficultyType"] = i2(2)
    vu["botDifficultyValue"] = i2(4)
    vu["botDifficultyTeam"] = a_arr(4, 4, 9)
    vu["botDifficultyData"] = a_arr(10, 4, 512)
    vu["spawningType"] = i2(2)
    vu["spawningSeed"] = i2(14)
    vu["spawningData"] = a_arr(11, 12, 1024)
    vu["selectableSpawn"] = i2(1)
    vu["playerNamesType"] = i2(2)
    vu["playerNamesData"] = a_strs(10, 5, 512)
    vu["selectableName"] = i2(1)
    for k in ("a", "t", "i"):
        vu[k + "IncomeType"] = i2(2)
        vu[k + "IncomeValue"] = i2(8)
        vu[k + "IncomeData"] = a_arr(10, 8, 512)
    vu["sResourcesType"] = i2(2)
    vu["sResourcesValue"] = i2(11)
    vu["sResourcesData"] = a_arr(10, 11, 512)
    vu["nA"] = a_arr(10, 30, 0)
    ek = i2(5)
    aHp = i2(30)
    aHq = i2(30)
    cmds = []
    for _ in range(aHp):
        cid = i2(4)
        player = i2(9)
        dX = dZ = 0
        if cid == 0:
            dX = i2(22)
        elif cid == 1:
            dX = i2(10)
            dZ = i2(10)
        elif cid == 2:
            dX = i2(10)
            dZ = i2(9)
        elif cid == 3:
            dX = i2(10)
            dZ = i2(27)
        elif cid == 4:
            dX = i2(10)
            dZ = i2(16)
        elif cid in (5, 6):
            dX = i2(10)
        elif cid == 7:
            dX = i2(1)
        elif cid == 10:
            dX = i2(20)
            dZ = i2(22)
        cmds.append([cid, player, dX, dZ])
    jY = []
    ja = []
    for _ in range(aHq):
        jY.append(i2(1))
        ja.append(i2(ek))
    return vu, cmds, jY, ja, b


def timed_commands(vu, cmds, jY, ja):
    """给每条指令标上执行拍号（出生阶段的指令 t=-1，并附 step 序号）。"""
    H = vu["humanCount"]
    jJ = 30 if H <= 2 else 40 if H <= 50 else 50
    spawn_steps = (jJ + 1) if vu["selectableSpawn"] else 0
    out = []
    step = 0
    iw = 0
    for flag, n in zip(jY, ja):
        if flag:
            t = step - spawn_steps
            for k in range(iw, iw + n):
                cid, player, dX, dZ = cmds[k]
                out.append({"t": t if t >= 0 else -1, "step": step, "id": cid, "player": player, "dX": dX, "dZ": dZ})
            iw += n
            step += 1
        else:
            step += n
    total_ticks = step - spawn_steps
    return out, total_ticks, spawn_steps


def load_replay(match_id):
    path = os.path.join(DATA, "bundles", match_id, "replay.txt")
    if not os.path.exists(path):
        return None
    raw = open(path, encoding="utf-8").read()
    vu, cmds, jY, ja, bits = decode(raw)
    tc, total_ticks, spawn_steps = timed_commands(vu, cmds, jY, ja)
    return {"vu": vu, "cmds": tc, "totalTicks": total_ticks, "spawnSteps": spawn_steps,
            "nRawCmds": len(cmds), "bitsUsed": bits.pos, "bitsTotal": bits.nbits}


def main():
    mid = sys.argv[1]
    r = load_replay(mid)
    if not r:
        print("no replay for", mid)
        return
    vu = r["vu"]
    brief = {k: v for k, v in vu.items() if not isinstance(v, list)}
    print(json.dumps(brief, ensure_ascii=False))
    print("teamPlayerCount", vu["teamPlayerCount"])
    print("names(humans):", [(i, n) for i, n in enumerate((vu["playerNamesData"] or [])[: vu["humanCount"]])])
    print("totalTicks", r["totalTicks"], "spawnSteps", r["spawnSteps"], "cmds", r["nRawCmds"], "bits", r["bitsUsed"], "/", r["bitsTotal"])
    cnt = {}
    for c in r["cmds"]:
        cnt[c["id"]] = cnt.get(c["id"], 0) + 1
    print("cmd counts by id:", dict(sorted(cnt.items())))


if __name__ == "__main__":
    main()
