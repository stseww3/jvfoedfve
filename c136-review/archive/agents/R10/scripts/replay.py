#!/usr/bin/env python3
"""replay.py — 把对局包里的 replay.txt（实况分享串）解码成逐拍命令流。纯 Python，不依赖 node、不需要地图。

这是 R10 独立写的一份解码器，用来给「真实捐款账」做第二来源：
  - 字段顺序、位宽对照线上引擎 live_game_js.js 里录像读写的字段表（统筹工具 src/tools/replay_cmds.mjs
    和 src/sim/tools/c102-replay-lib.mjs 是同一张表）；
  - `selfcheck` 子命令把本解码器的结果和 node 版 replay_cmds.mjs --summary 的结果逐项比对
    （总拍数、各类命令条数、真人名单），不一致就报错。

命令记录点（线上引擎 `function qj()`，本文件不重复实现，只在这里记下核对过的原文位置）：
  id=1 陆攻 qj.i6：过了「对局进行中、玩家存活、目标不是自己、报价成立、目标是敌人、有接壤或已有同目标进攻」之后
        才 `bC.rg.rh(1,player,pct,target)`；
  id=2 捐款 qj.qv：过了「对局进行中、玩家存活、是组队局、对象不是自己、对象存活且是队友、到账量 ≥1
        （对方余额没顶到 150×领土）、配额 ao.ei 通过」之后才 `bC.rg.rh(2,player,pct,to)`，紧接着 af.qt 真正转账。
        所以录像里的每一条 id=2 都是一笔真实成交的捐款；被拒的捐款不会进录像。
  id=5 且参数 513：发起和平投票（qj.iK）；id=7：投票（qj.iN）；id=8/9：离开。

拍号口径：选点阶段占 jJ+1 步（真人数 ≤2:30，≤50:40，否则 50），之后每一步是一拍；
一个「命令块」占一步，一个「空跑块」占 ja 步；tick = 步号 − (jJ+1)。选点阶段的命令 tick 为负。

用法：
  python3 replay.py summary <matchId>          # 打印头信息与各类命令条数
  python3 replay.py selfcheck <matchId> [...]   # 和 node 版逐项比对（要套 run-heavy.sh）
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

DATA = os.environ.get("C136_DATA", "/agent/repos/c136-data")

KIND = {0: "spawn", 1: "attack", 2: "donate", 3: "boat", 4: "chase", 5: "retreat", 6: "c6", 7: "vote",
        8: "leave8", 9: "leave9", 10: "c10"}
NEUTRAL = 512
PEACE_CALL = 513


class _Bits:
    __slots__ = ("buf", "pos", "total")

    def __init__(self, text: str):
        ga = text.strip()
        eq = ga.find("=")
        if eq >= 0:
            ga = ga[eq + 1:]
        ga = re.sub(r"[^a-zA-Z0-9_\-]", "-", ga)
        abv = [0] * 78
        abv[50] = 37
        for i in range(10):
            abv[i + 3] = i + 1
        for i in range(26):
            abv[i + 20] = i + 11
            abv[i + 52] = i + 38
        # 每个字符 6 位，高位在前，拼成一个大整数再转字节
        acc = 0
        n = 0
        out = bytearray()
        for ch in ga:
            acc = (acc << 6) | abv[ord(ch) - 45]
            n += 6
            if n >= 8:
                n -= 8
                out.append((acc >> n) & 0xFF)
                acc &= (1 << n) - 1
        if n:
            out.append((acc << (8 - n)) & 0xFF)
        out.extend(b"\0" * 8)
        self.buf = bytes(out)
        self.pos = 0
        self.total = (6 * len(ga) + 7) // 8 * 8

    def read(self, size: int) -> int:
        if size == 0:
            return 0
        a = self.pos
        byte0 = a >> 3
        off = a & 7
        nbytes = (off + size + 7) >> 3
        v = int.from_bytes(self.buf[byte0:byte0 + nbytes], "big")
        v >>= (nbytes * 8 - off - size)
        self.pos = a + size
        return v & ((1 << size) - 1)

    def string(self, len_bits: int) -> str:
        n = self.read(len_bits)
        raw = b"".join(self.read(16).to_bytes(2, "big") for _ in range(n))
        return raw.decode("utf-16-be", errors="replace")   # 代理对合并成一个字符；被截断的半个代理对替换成 U+FFFD

    def array(self, len_bits: int, item_bits: int):
        n = self.read(len_bits)
        if not n:
            return None
        return [self.read(item_bits) for _ in range(n)]

    def strings(self, len_bits: int, item_len_bits: int):
        n = self.read(len_bits)
        if not n:
            return None
        return [self.string(item_len_bits) for _ in range(n)]


def decode(text: str) -> dict:
    b = _Bits(text)
    h = {}
    h["version"] = b.read(12)
    h["vs"] = b.read(12)
    h["statedSize"] = b.read(31)
    h["mapType"] = b.read(2)
    h["mapProceduralIndex"] = b.read(8)
    h["mapRealisticIndex"] = b.read(8)
    h["mapSeed"] = b.read(14)
    h["mapName"] = b.string(5)
    if h["mapType"] == 2:
        skip = b.read(30)
        b.pos += 6 * skip
    h["passableWater"] = b.read(1)
    h["passableMountains"] = b.read(1)
    h["playerCount"] = b.read(10)
    h["humanCount"] = b.read(10)
    h["selectedPlayer"] = b.read(9)
    h["gameMode"] = b.read(1)
    h["playerMode"] = b.read(2)
    h["battleRoyaleMode"] = b.read(2)
    h["numberTeams"] = b.read(4)
    h["isZombieMode"] = b.read(1)
    h["isContest"] = b.read(1)
    h["isReplay"] = b.read(1)
    h["elo"] = b.array(2, 14)
    h["colorsType"] = b.read(1)
    h["colorsPersonalized"] = b.read(1)
    h["colorsData"] = b.array(10, 18)
    h["selectableColor"] = b.read(1)
    h["teamPlayerCount"] = b.array(4, 10)
    h["neutralBots"] = b.read(1)
    h["botDifficultyType"] = b.read(2)
    h["botDifficultyValue"] = b.read(4)
    h["botDifficultyTeam"] = b.array(4, 4)
    h["botDifficultyData"] = b.array(10, 4)
    h["spawningType"] = b.read(2)
    h["spawningSeed"] = b.read(14)
    h["spawningData"] = b.array(11, 12)
    h["selectableSpawn"] = b.read(1)
    h["playerNamesType"] = b.read(2)
    h["playerNamesData"] = b.strings(10, 5)
    h["selectableName"] = b.read(1)
    for pre in ("aIncome", "tIncome", "iIncome"):
        h[pre + "Type"] = b.read(2)
        h[pre + "Value"] = b.read(8)
        h[pre + "Data"] = b.array(10, 8)
    h["sResourcesType"] = b.read(2)
    h["sResourcesValue"] = b.read(11)
    h["sResourcesData"] = b.array(10, 11)
    h["nA"] = b.array(10, 30)
    ek = b.read(5)
    n_cmds = b.read(30)
    n_blocks = b.read(30)
    cmds = []
    for _ in range(n_cmds):
        cid = b.read(4)
        player = b.read(9)
        a = c = 0
        if cid == 0:
            a = b.read(22)
        elif cid == 1:
            a = b.read(10)
            c = b.read(10)
        elif cid == 2:
            a = b.read(10)
            c = b.read(9)
        elif cid == 3:
            a = b.read(10)
            c = b.read(27)
        elif cid == 4:
            a = b.read(10)
            c = b.read(16)
        elif cid in (5, 6):
            a = b.read(10)
        elif cid == 7:
            a = b.read(1)
        elif cid == 10:
            a = b.read(20)
            c = b.read(22)
        cmds.append((cid, player, a, c))
    blocks = []
    for _ in range(n_blocks):
        is_cmd = b.read(1)
        cnt = b.read(ek)
        blocks.append((is_cmd, cnt))
    return {"header": h, "cmds": cmds, "blocks": blocks, "bitsUsed": b.pos, "totalBits": b.total}


def timeline(d: dict) -> dict:
    """逐拍展开。返回 {"cmds": [(tick, id, player, a, b)], "totalTicks", "spawnSteps", "usedCmds"}。"""
    H = d["header"]["humanCount"]
    jJ = 30 if H <= 2 else 40 if H <= 50 else 50
    spawn_steps = jJ + 1 if d["header"]["selectableSpawn"] else 0
    out = []
    step = 0
    iw = 0
    cmds = d["cmds"]
    for is_cmd, cnt in d["blocks"]:
        if is_cmd:
            for a in range(iw, iw + cnt):
                c = cmds[a]
                out.append((step - spawn_steps, c[0], c[1], c[2], c[3]))
            iw += cnt
            step += 1
        else:
            step += max(1, cnt)
    return {"cmds": out, "totalTicks": step - spawn_steps, "spawnSteps": spawn_steps, "usedCmds": iw}


def replay_path(match_id: str):
    for sub in ("bundles", "validation_bundles"):
        p = os.path.join(DATA, sub, match_id, "replay.txt")
        if os.path.exists(p):
            return p
    return None


_CACHE: dict = {}


def load(match_id: str):
    """返回 {"header", "names"(真人名单), "humans", "cmds"(逐拍), "totalTicks"}；没有录像返回 None。"""
    if match_id in _CACHE:
        return _CACHE[match_id]
    p = replay_path(match_id)
    if p is None:
        _CACHE[match_id] = None
        return None
    with open(p, encoding="utf-8", errors="replace") as f:
        d = decode(f.read())
    tl = timeline(d)
    h = d["header"]
    names = (h["playerNamesData"] or [])[: h["humanCount"]]
    r = {"header": h, "names": names, "humans": h["humanCount"], "cmds": tl["cmds"], "totalTicks": tl["totalTicks"],
         "spawnSteps": tl["spawnSteps"], "usedCmds": tl["usedCmds"], "nCmds": len(d["cmds"]),
         "bitsUsed": d["bitsUsed"], "totalBits": d["totalBits"]}
    _CACHE[match_id] = r
    return r


def summary(match_id: str) -> dict:
    r = load(match_id)
    if r is None:
        return {"match": match_id, "replay": False}
    cnt: dict = {}
    for _, cid, *_ in r["cmds"]:
        k = KIND.get(cid, str(cid))
        cnt[k] = cnt.get(k, 0) + 1
    h = r["header"]
    return {"match": match_id, "replay": True, "humans": r["humans"], "players": h["playerCount"],
            "numberTeams": h["numberTeams"], "gameMode": h["gameMode"], "playerMode": h["playerMode"],
            "teamPlayerCount": h["teamPlayerCount"], "mapSeed": h["mapSeed"], "totalTicks": r["totalTicks"],
            "spawnSteps": r["spawnSteps"], "cmdTotal": r["nCmds"], "usedCmds": r["usedCmds"],
            "bitsUsed": r["bitsUsed"], "totalBits": r["totalBits"], "counts": cnt, "names": r["names"]}


def selfcheck(ids: list[str]) -> int:
    """和 node 版 replay_cmds.mjs --summary 比对。"""
    tool = os.path.join(DATA, "src", "tools", "replay_cmds.mjs")
    bad = 0
    for mid in ids:
        mine = summary(mid)
        out = subprocess.run(["node", tool, mid, "--summary"], capture_output=True, text=True, timeout=100)
        if out.returncode != 0:
            print(f"{mid}: node 失败 {out.stderr[:200]}")
            bad += 1
            continue
        ref = json.loads(out.stdout)
        ref_counts = {("vote" if k == "c7" else k): v for k, v in ref["counts"].items()}   # node 版把 id=7 叫 c7
        ref_names = [re.sub(r"[\ud800-\udfff]", "\ufffd", x) for x in ref["names"]]
        ok = (mine["totalTicks"] == ref["totalTicks"] and mine["cmdTotal"] == ref["cmdTotal"]
              and mine["usedCmds"] == ref["usedCmds"] and mine["counts"] == ref_counts
              and mine["names"] == ref_names and mine["bitsUsed"] == ref["bitsUsed"])
        print(f"{mid}: {'一致' if ok else '不一致'} ticks={mine['totalTicks']}/{ref['totalTicks']} "
              f"cmds={mine['cmdTotal']}/{ref['cmdTotal']} bits={mine['bitsUsed']}/{ref['bitsUsed']} "
              f"counts={'=' if mine['counts'] == ref_counts else '≠'} names={'=' if mine['names'] == ref_names else '≠'}")
        bad += 0 if ok else 1
    return 1 if bad else 0


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "summary":
        print(json.dumps(summary(sys.argv[2]), ensure_ascii=False, indent=1))
    elif len(sys.argv) >= 3 and sys.argv[1] == "selfcheck":
        sys.exit(selfcheck(sys.argv[2:]))
    else:
        print(__doc__)
        sys.exit(2)
