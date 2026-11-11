#!/usr/bin/env python3
"""54_spawn_seq.py — R07：日志里的出生指派，逐条对上录像里的出生指令，看哪几条指派没有进录像。

输入：
  bundles/<id>/in_game.log        [HL-SPAWN]（号自己先挑的点）/ [HL-SPAWN-BACKEND]（协调器指派）/ [BACKEND-SPAWN-COORD] Solved
  out/<id>/spawn_cmds.tsv         55_spawn_cmds.mjs：录像里全部出生指令（第几步、谁、指向哪）
做法：每个号的「指派序列」和「录像指令序列」按坐标做最长公共子序列对齐；对不上的指派 = 没进录像的指派。
      出生阶段只有 41 或 51 步；一步在开局以后等于一拍（56 毫秒），出生阶段里每一步有多长包里没有。

用法：python3 54_spawn_seq.py <matchId> [<matchId>...]
输出：out/<matchId>/spawn_seq.txt；多局时最后在 stdout 打一张汇总表
"""
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = "/agent/repos/c136-data"


def lcs_pairs(a, b):
    """a, b：坐标元组的序列。返回 [(i, j)]：a[i] 对上 b[j]。平手时让 b 尽量贴着靠后的 a（指令对上最近一次指派）。"""
    n, m = len(a), len(b)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            dp[i][j] = dp[i + 1][j + 1] + 1 if a[i] == b[j] else max(dp[i + 1][j], dp[i][j + 1])
    out = []
    i = j = 0
    while i < n and j < m:
        if a[i] == b[j] and dp[i][j] == dp[i + 1][j + 1] + 1:
            out.append((i, j))
            i += 1
            j += 1
        elif dp[i + 1][j] >= dp[i][j + 1]:
            i += 1
        else:
            j += 1
    return out


def run(mid):
    out_dir = os.path.join(HERE, "..", "out", mid)
    tsv = os.path.join(out_dir, "spawn_cmds.tsv")
    if not os.path.exists(tsv):
        return None
    head = open(tsv, encoding="utf-8").readline()
    jj = int(re.search(r"第 0~(\d+) 步", head).group(1))
    cmds = defaultdict(list)   # bot -> [(step, x, y)]
    others = []                # steps of other humans' commands
    for ln in open(tsv, encoding="utf-8"):
        if ln.startswith("#") or ln.startswith("step"):
            continue
        c = ln.rstrip("\n").split("\t")
        if len(c) < 7:
            continue
        if c[4]:
            cmds[c[4]].append((int(c[0]), int(c[5]), int(c[6])))
        else:
            others.append(int(c[0]))

    check = {}                 # bot -> (tick, sent)：[OPENING-CHECK] 里宿主数的已发指令条数（含选点指令）
    opening = defaultdict(list)  # bot -> [t]：[HL-OPENING] 的开局指令
    asg = defaultdict(list)    # bot -> [(line, kind, x, y)]
    solves = []                # (line, text after the colon)
    first_open = None
    bots = []
    for i, ln in enumerate(open(os.path.join(DATA, "bundles", mid, "in_game.log"), encoding="utf-8", errors="replace"), 1):
        if "[BACKEND-SPAWN-COORD] Solved" in ln:
            solves.append((i, ln.split("):", 1)[-1].strip()))
            continue
        if "[OPENING-CHECK" in ln and not check:
            for mm in re.finditer(r"\] (\w+):tick=(\d+),terr=\d+,sent=(\d+)", ln):
                check[mm.group(1)] = (int(mm.group(2)), int(mm.group(3)))
            continue
        m = re.match(r"^\d+\t\[([A-Za-z0-9_]+)\] (.*)$", ln)
        if not m:
            continue
        mo = re.search(r"\[HL-OPENING\] t=(\d+) ", m.group(2))
        if mo:
            opening[m.group(1)].append(int(mo.group(1)))
        if m.group(1) not in bots:
            bots.append(m.group(1))
        s = re.search(r"\[HL-SPAWN(-BACKEND)?\] me=\d+ slot=\d+ .*?-> \((\d+),(\d+)\)", m.group(2))
        if s:
            asg[m.group(1)].append((i, "协调器" if s.group(1) else "自选", int(s.group(2)), int(s.group(3))))
        elif first_open is None and "[HL-OPENING]" in m.group(2):
            first_open = i

    L = []
    P = L.append
    P(f"# {mid} 出生指派 vs 录像里的出生指令（54_spawn_seq.py）")
    distinct = []
    for _, txt in solves:
        if not distinct or distinct[-1] != txt:
            distinct.append(txt)
    P(f"# 出生阶段 = 录像第 0~{jj} 步；协调器求解 {len(solves)} 次（相邻两次结果不同的 {max(0, len(distinct) - 1)} 次）；日志里第一条 [HL-OPENING] 在第 {first_open} 行")
    my_steps = sorted(s for b in cmds for s, _, _ in cmds[b])
    P(f"# 录像里的出生指令：我方 {len(my_steps)} 条" + (f"（第 {my_steps[0]}~{my_steps[-1]} 步）" if my_steps else "") + f"；其他真人 {len(others)} 条" + (f"（第 {min(others)}~{max(others)} 步）" if others else ""))
    P("")
    P("A. 各号：指派次数（自选 + 协调器）| 进了录像的指令 | 对上的 | 没进录像的指派（第几次，从 1 数；日志行）| 第一条 / 最后一条指令落在第几步")
    tot = dict(asg=0, cmd=0, match=0, first=0, last=0, mid=0, own=0, bots=0, firstStep=[], lastStep=[], multi=0, fwd=0, rev=0,
               grpRev=0, grpFwd=0, grpBoth=0, grpNone=0, fbBots=0, fbMiss=0, endLast=0, endOverwritten=0, endStale=0, endOther=0, endNone=0, overBots=[], staleBots=[])
    for b in bots:
        a = asg.get(b, [])
        c = cmds.get(b, [])
        # 同一步里同一个号有两条以上指令时，录像里的先后可能和发令先后相反：两种顺序都对一遍，取对得上更多的
        rev = []
        k = 0
        while k < len(c):
            e = k
            while e < len(c) and c[e][0] == c[k][0]:
                e += 1
            rev.extend(reversed(c[k:e]))
            if e - k >= 2 and len({(x, y) for _, x, y in c[k:e]}) >= 2:
                tot["multi"] += 1
            k = e
        pairs_fwd = lcs_pairs([(x, y) for _, _, x, y in a], [(x, y) for _, x, y in c])
        pairs_rev = lcs_pairs([(x, y) for _, _, x, y in a], [(x, y) for _, x, y in rev])
        tot["fwd"] += len(pairs_fwd)
        tot["rev"] += len(pairs_rev)
        # 逐组看：这一组的指令在「倒过来」的对齐里全部对上 = 录像里的先后正好和发令先后相反
        hit_fwd = {j for _, j in pairs_fwd}
        hit_rev = {j for _, j in pairs_rev}
        k = 0
        while k < len(c):
            e = k
            while e < len(c) and c[e][0] == c[k][0]:
                e += 1
            if e - k >= 2 and len({(x, y) for _, x, y in c[k:e]}) >= 2:
                f_ok = all(j in hit_fwd for j in range(k, e))
                r_ok = all(j in hit_rev for j in range(k, e))
                if r_ok and not f_ok:
                    tot["grpRev"] += 1
                elif f_ok and not r_ok:
                    tot["grpFwd"] += 1
                elif f_ok and r_ok:
                    tot["grpBoth"] += 1
                else:
                    tot["grpNone"] += 1
            k = e
        use_rev = len(pairs_rev) > len(pairs_fwd)
        pairs = pairs_rev if use_rev else pairs_fwd
        hit = {i for i, _ in pairs}
        # 协调器第一次给的点进录像了吗
        fb = next((i for i, x in enumerate(a) if x[1] == "协调器"), None)
        if fb is not None:
            tot["fbBots"] += 1
            if fb not in hit:
                tot["fbMiss"] += 1
        # 出生阶段结束时生效的是哪一次指派：录像里最后执行的那条指令对上的指派
        if c and a:
            seq = rev if use_rev else c            # 发令先后
            last_exec = c[-1]                      # 录像里最后执行的
            j_exec = len(seq) - 1 - [(x, y) for _, x, y in reversed(seq)].index((last_exec[1], last_exec[2]))
            i_exec = next((i for i, j in pairs if j == j_exec), None)
            if i_exec is None:
                tot["endOther"] += 1
            elif i_exec == len(a) - 1:
                tot["endLast"] += 1
            elif (len(a) - 1) in hit:
                tot["endOverwritten"] += 1         # 最后一次指派进了录像，但同一步里更早的那条排在它后面执行
                tot["overBots"].append(b)
            else:
                tot["endStale"] += 1               # 最后一次指派没进录像，停在更早的指派上
                tot["staleBots"].append(b)
        elif a:
            tot["endNone"] += 1
        miss = [i for i in range(len(a)) if i not in hit]
        desc = []
        for i in miss:
            where = "第一次" if i == 0 else ("最后一次" if i == len(a) - 1 else "中间")
            desc.append(f"#{i + 1}（{a[i][1]}，{where}，L{a[i][0]}）")
            if a[i][1] == "自选":
                tot["own"] += 1
            elif i == 0:
                tot["first"] += 1
            elif i == len(a) - 1:
                tot["last"] += 1
            else:
                tot["mid"] += 1
        n_own = sum(1 for x in a if x[1] == "自选")
        P(f"  {b:8s} {len(a)}（{n_own} + {len(a) - n_own}）| {len(c)} | {len(pairs)} | {'、'.join(desc) if desc else '无'} | {c[0][0] if c else '-'} / {c[-1][0] if c else '-'}")
        tot["asg"] += len(a)
        tot["cmd"] += len(c)
        tot["match"] += len(pairs)
        tot["bots"] += 1
        if c:
            tot["firstStep"].append(c[0][0])
            tot["lastStep"].append(c[-1][0])
    P("")
    P(f"  合计：指派 {tot['asg']}、进录像 {tot['cmd']}、对上 {tot['match']}；没进录像的指派 {tot['asg'] - tot['match']} = 自选 {tot['own']} + 协调器第一次 {tot['first']} + 协调器最后一次 {tot['last']} + 协调器中间 {tot['mid']}")
    P(f"  同一步里同一个号落了 ≥2 条（指向不同点）的组：{tot['multi']} 组；按录像里的先后对，对上 {tot['fwd']} 条；把这些组倒过来对，对上 {tot['rev']} 条（进录像 {tot['cmd']} 条）")

    P(f"  这 {tot['multi']} 组里：录像先后和发令先后正好相反 {tot['grpRev']} 组；相同 {tot['grpFwd']} 组；两种都说得通 {tot['grpBoth']} 组；都对不上 {tot['grpNone']} 组（日志只在指派挪动超过 4 像素时记一行，小挪动的指令在日志里没有对应行）")
    P(f"  协调器第一次给的点没进录像的号：{tot['fbMiss']} / {tot['fbBots']}")
    P(f"  出生阶段结束时各号停在哪一次指派上：最后一次 {tot['endLast']} 个号；最后一次进了录像但被同一步里更早的那条盖掉 {tot['endOverwritten']} 个"
      + (f"（{'、'.join(tot['overBots'])}）" if tot['overBots'] else "")
      + f"；最后一次没进录像、停在更早的指派上 {tot['endStale']} 个" + (f"（{'、'.join(tot['staleBots'])}）" if tot['staleBots'] else "")
      + f"；对不上 {tot['endOther']} 个；一条指令都没进录像 {tot['endNone']} 个")
    P("")
    P("B. 录像里每一步的出生指令条数：步 | 我方 | 其他真人")
    per = defaultdict(lambda: [0, 0])
    for s in my_steps:
        per[s][0] += 1
    for s in others:
        per[s][1] += 1
    for s in sorted(per):
        P(f"  {s}\t{per[s][0]}\t{per[s][1]}")

    P("")
    P("C. 协调器每次求解之后、下一次求解之前，日志里记了几条指派（[HL-SPAWN-BACKEND]）：求解所在行 | 指派条数 | 和上一次求解结果相同吗")
    lines = [ln for ln, _ in solves] + [10 ** 9]
    all_asg = sorted((ln, b) for b in asg for ln, kind, _, _ in asg[b] if kind == "协调器")
    prev = None
    for k, (ln, txt) in enumerate(solves):
        n = sum(1 for x, _ in all_asg if ln < x < lines[k + 1])
        P(f"  L{ln}\t{n}\t{'相同' if prev == txt else ('第一次' if prev is None else '不同')}")
        prev = txt

    P("")
    P("D. 选点指令发出去了吗：[OPENING-CHECK] 里宿主数的已发条数 sent（含选点指令）− 到那一拍为止的开局指令（[HL-OPENING]）= 宿主发出的选点指令")
    P("   号 | 核对拍 | sent | 开局指令 | 宿主发出的选点指令 | 日志里的指派次数 | 进了录像的选点指令 | 发了没进录像")
    tot["hostSpawn"] = 0
    tot["hostBots"] = 0
    for b in bots:
        if b not in check:
            continue
        tk, sent = check[b]
        n_open = sum(1 for t in opening.get(b, []) if t <= tk)
        host = sent - n_open
        tot["hostSpawn"] += host
        tot["hostBots"] += 1
        P(f"  {b:8s} {tk}\t{sent}\t{n_open}\t{host}\t{len(asg.get(b, []))}\t{len(cmds.get(b, []))}\t{host - len(cmds.get(b, []))}")
    if tot["hostBots"]:
        P(f"  合计（{tot['hostBots']} 个号）：宿主发出的选点指令 {tot['hostSpawn']}、日志里的指派 {tot['asg']}、进了录像 {tot['cmd']}、发了没进录像 {tot['hostSpawn'] - tot['cmd']}")

    with open(os.path.join(out_dir, "spawn_seq.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    tot["solves"] = len(solves)
    tot["changes"] = max(0, len(distinct) - 1)
    tot["jj"] = jj
    tot["myFirst"] = my_steps[0] if my_steps else None
    tot["myLast"] = my_steps[-1] if my_steps else None
    tot["othFirst"] = min(others) if others else None
    tot["othLast"] = max(others) if others else None
    return tot


def main():
    mids = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not mids:
        print(__doc__)
        sys.exit(2)
    print("局\t号\t求解（结果变了几次）\t指派\t进录像\t没进录像 = 自选 + 协调器第一次 + 最后一次 + 中间\t我方指令落在第几步\t其他真人落在第几步\t出生阶段步数\t同步多条的组：相反 / 相同 / 都说得通 / 都对不上\t按录像先后对上 / 倒过来对上\t协调器第一次给的点没进录像\t结束时停在：最后一次指派 / 被同步更早的盖掉 / 最后一次没进录像 / 对不上 / 一条都没进\t宿主发出的选点指令（OPENING-CHECK 的 sent − 开局指令）")
    for mid in mids:
        t = run(mid)
        if t is None:
            print(f"{mid}\t（没有 spawn_cmds.tsv）")
            continue
        print(f"{mid}\t{t['bots']}\t{t['solves']}（{t['changes']}）\t{t['asg']}\t{t['cmd']}\t{t['asg'] - t['match']} = {t['own']} + {t['first']} + {t['last']} + {t['mid']}\t"
              f"{t['myFirst']}~{t['myLast']}\t{t['othFirst']}~{t['othLast']}\t0~{t['jj']}\t{t['multi']}：{t['grpRev']} / {t['grpFwd']} / {t['grpBoth']} / {t['grpNone']}\t{t['fwd']} / {t['rev']}\t{t['fbMiss']} / {t['fbBots']}\t{t['endLast']} / {t['endOverwritten']} / {t['endStale']} / {t['endOther']} / {t['endNone']}\t{t.get('hostSpawn', '-')}")


if __name__ == "__main__":
    main()
