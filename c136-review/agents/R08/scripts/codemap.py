#!/usr/bin/env python3
"""codemap.py — 报告和假设卡里引用的策略函数，在各档策略文件里的定义行号（类名.函数名 → 起止行）。

    python3 codemap.py [--quiet]        → out/_cross/codemap.txt、codemap.json

只读 /agent/repos/c136-data/src/strategy/ 下的五个文件和 src/sim/sim/game.js。行号按「两格缩进的方法定义行」找，
方法结束行 = 下一个同级方法定义行之前的最后一个 `  }`。同名方法在继承链上出现几次就列几次（后面的类覆盖前面的）。
节：
  [CM-A] 策略文件：函数 | c110（squad20）| c116-vb（squad10 Vb）| c116（Vc）| c116-va（Va）| g09（squad8）
  [CM-B] 引擎 game.js 里引用到的方法
  [CM-C] 五个文件之间这些函数的正文是否逐字相同（去掉行首尾空白后比对）
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out", "_cross")
SRC = "/agent/repos/c136-data/src"
FILES = [("c110", "strategy/v27-team-c110.js"), ("c116-vb", "strategy/v27-team-c116-vb.js"), ("c116", "strategy/v27-team-c116.js"),
         ("c116-va", "strategy/v27-team-c116-va.js"), ("g09", "strategy/v27-team-g09.js")]
FUNCS = ["chooseSpawn", "analyze", "threatOf", "safeBalance", "elimCost", "minCmd", "send", "act", "floors", "pickTarget", "price", "allow", "minShare",
         "amount", "amount0", "expandNeutral", "food", "peopleFloor", "floorFor", "floorFor0", "dpKeep", "botOk", "botPx", "winWorth", "winFloor", "safeFinite",
         "waitDump", "reserve", "contested", "safeAt", "buyLand", "idleBoats", "idle", "isOurSquadBot", "hasWildOutsidersAlive", "isProtectedSquadMate",
         "tryEmergencyBossRescue", "tryDonateToTeammate", "updateShadowQuota", "hasBorderFood"]
GAME_FUNCS = ["isBot", "isEnemy", "isEnemyOf", "isTeammate", "leave", "runAsBot", "hasAttack", "hasFreeSlot", "attackTroopsOn", "aliveTick", "collapse",
              "victoryTick", "donate", "expandAttack"]


def scan(path):
    """返回 {函数名: [(类名, 起行, 止行, 正文)]}"""
    lines = open(path, encoding="utf-8").read().split("\n")
    cls = None
    defs = []
    for i, ln in enumerate(lines, 1):
        m = re.match(r"^(?:export\s+)?class\s+(\w+)", ln)
        if m:
            cls = m.group(1)
            continue
        m = re.match(r"^  (?:static\s+|async\s+)?(\w+)\s*\(.*\)\s*\{\s*(?://.*)?$", ln)
        if m and m.group(1) not in ("if", "for", "while", "switch", "catch", "constructor"):
            defs.append((m.group(1), cls, i))
    out = {}
    for name, c, start in defs:
        end = start
        for j in range(start, len(lines)):
            if lines[j] == "  }":
                end = j + 1
                break
        body = "\n".join(x.strip() for x in lines[start - 1:end])
        out.setdefault(name, []).append((c, start, end, body))
    return out


def main():
    quiet = "--quiet" in sys.argv
    out = []
    P = out.append
    maps = {k: scan(os.path.join(SRC, f)) for k, f in FILES}
    P("[CM-A] 策略文件里的定义行（类.函数 起~止）：函数 | " + " | ".join(k for k, _ in FILES))
    js = {}
    for fn in FUNCS:
        cells = []
        for k, _ in FILES:
            ds = maps[k].get(fn, [])
            cells.append("；".join(f"{c}.{fn} L{a}-{b}" for c, a, b, _ in ds) or "—")
            js.setdefault(fn, {})[k] = [dict(cls=c, start=a, end=b) for c, a, b, _ in ds]
        P(f"  {fn} | " + " | ".join(cells))
    P("")
    P("[CM-B] 引擎 src/sim/sim/game.js：方法 | 起~止")
    gm = scan(os.path.join(SRC, "sim/sim/game.js"))
    for fn in GAME_FUNCS:
        ds = gm.get(fn, [])
        P(f"  {fn} | " + ("；".join(f"L{a}-{b}" for _, a, b, _ in ds) or "—"))
        js.setdefault("game.js", {})[fn] = [dict(start=a, end=b) for _, a, b, _ in ds]
    P("")
    P("[CM-C] 正文逐字比对（去掉每行首尾空白；同名方法按出现顺序一一对；「同」= 和 c110 的正文完全一样）：函数 | " + " | ".join(k for k, _ in FILES[1:]))
    same = {}
    for fn in FUNCS:
        base = maps["c110"].get(fn, [])
        cells = []
        for k, _ in FILES[1:]:
            ds = maps[k].get(fn, [])
            if not base and not ds:
                cells.append("—")
                continue
            if len(ds) != len(base):
                cells.append(f"定义个数不同（{len(base)} / {len(ds)}）")
                same.setdefault(fn, {})[k] = False
                continue
            diff = [f"{c}" for (c, _, _, b1), (_, _, _, b0) in zip(ds, base) if b1 != b0]
            cells.append("同" if not diff else "不同：" + "、".join(diff))
            same.setdefault(fn, {})[k] = not diff
        P(f"  {fn} | " + " | ".join(cells))
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "codemap.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    with open(os.path.join(OUT, "codemap.json"), "w", encoding="utf-8") as f:
        json.dump(dict(defs=js, same=same), f, ensure_ascii=False, separators=(",", ":"))
    if not quiet:
        print("\n".join(out))


if __name__ == "__main__":
    main()
