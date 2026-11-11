#!/usr/bin/env python3
"""spawn_exec.py — 「出生点执行」机械检测（可对全部对局包跑）：协调器/策略给出的出生坐标，有没有变成录像里的出生指令。

输入（每局）：
  /agent/repos/c136-data/bundles/<id>/{in_game.log, spawn.csv, traj.csv, results.csv}
  /tmp/c136-r05/cmds/<id>.tsv   录像原始命令流（没有就先跑：node scripts/replay_cmds.mjs <id> --out /tmp/c136-r05/cmds/<id>.tsv；只解码，不重放）
口径：
  号 ↔ 录像玩家：录像玩家名去掉 [标签] 后与号名相同（大小写不敏感）；对不上的号 = 不在这一盘录像里（拆盘局的另一盘）。
  地图宽：日志 `[BACKEND-SPAWN-COORD] … (map=宽x高` 或 `[HL-SPAWN…] W=`；都没有时用「我方出生指令解出的坐标落在日志指派点集合里的条数最多」的宽度（枚举 400…4096）。
  求解轮数 = `[BACKEND-SPAWN-COORD] Solved` 的行数；不同的解 = 这些行里指派串去重后的个数。
  每个号的结论：
      最终坐标落地   录像里它最后一条出生指令 = 日志里它最后一次指派（±2 格）
      停在旧坐标     最后一条出生指令 = 日志里更早的某次指派
      日志外坐标     有出生指令，但不等于日志里任何一次指派
      0 条落地       录像里没有它的出生指令（选点期结束时由引擎随机落子）
  本地发送数（近似）= results.csv 的 accepted − 最后一条 [HL-TICK] 的 cmds（accepted 含出生发送；只有有结算行的号才有）。
输出：每局一行（TSV，可 --tsv），或带 --detail 逐号。
  --seq：把每个号在日志里的出生坐标序列（L = 策略兜底点 [HL-SPAWN]，B = 协调器点 [HL-SPAWN-BACKEND]；坐标每变一次一行）
      与录像里它的出生指令序列对齐：开头没落地的条数 = 录像第一条指令的坐标在日志序列里第一次出现的位置；
      结尾没落地的条数 = 录像最后一条指令的坐标在日志序列里最后一次出现之后还剩几行（选点期结束后才算出来的坐标）。
  --hops：选点期「跳点」与「叠号」账（每个号各算各的版本最需要看这一项）：
      每个号：槽位、日志里换了几次坐标（不同坐标几个）、相邻两次坐标相隔多远（中位 / 最大）、候选表长度出现过哪些值、
              录像里落地的出生指令条数与拍号范围、最终出生点 = 日志序列的倒数第几个；
      撞点：同一个坐标（±8 格）出现在 ≥2 个号的日志序列里；
      叠号：最终出生点两两距离 < minSep（日志行里的 minSep，没有就按 45）的号对，以及按这个距离连起来的堆。
用法：python3 scripts/spawn_exec.py <matchId> [...] [--detail] [--tsv] [--seq] [--hops]
"""
import csv
import math
import os
import re
import sys
from collections import Counter, defaultdict

a = sys.argv[1:]
ids = [x for x in a if not x.startswith('--')]
detail, tsv, seqmode, hopmode = '--detail' in a, '--tsv' in a, '--seq' in a, '--hops' in a
bare = lambda n: re.sub(r'\[[^\]]*\]', '', n or '').strip().lower()
COLS = ['matchId', 'logBots', 'inReplay', 'solveRounds', 'distinctSolutions', 'finalLanded', 'stuckOld', 'offLog', 'zeroLanded', 'spawnCmdTicks', 'phaseStart', 'othersWithSpawn', 'others', 'localSends(min-max)', 'sendsMinusLanded(min/med/max)', 'firstLandedTickMin', 'assignMinusLanded(med)']
if tsv:
    print('\t'.join(COLS))
for mid in ids:
    B = os.environ.get('C136_DATA', '/agent/repos/c136-data') + f"/{os.environ.get('C136_BUNDLES', 'bundles')}/{mid}"
    cp = os.environ.get('C136_CMDS', '/tmp/c136-r05/cmds') + f'/{mid}.tsv'
    if not os.path.exists(cp):
        alt = f'/tmp/c136-r05/work/{mid}-cmds.tsv'
        cp = alt if os.path.exists(alt) else cp
    if not os.path.exists(cp):
        print(f'{mid}\t缺命令流：node scripts/replay_cmds.mjs {mid} --out /tmp/c136-r05/cmds/{mid}.tsv')
        continue
    assign = defaultdict(list)
    if os.path.exists(f'{B}/spawn.csv'):
        for r in csv.DictReader(open(f'{B}/spawn.csv', encoding='utf-8')):
            assign[r['bot']].append((int(r['x']), int(r['y']), r['role']))
    solves, W = [], 0
    for ln in open(f'{B}/in_game.log', encoding='utf-8', errors='replace'):
        m = re.search(r'\[BACKEND-SPAWN-COORD\] Solved (\d+) bots in ([\d.]+)ms \(map=(\d+)x(\d+).*?\): (.*)', ln)
        if m:
            solves.append(m.group(5).strip())
            W = int(m.group(3))
    logseq = defaultdict(list)
    slotof, candn, minsep = {}, defaultdict(list), 0
    for ln in open(f'{B}/in_game.log', encoding='utf-8', errors='replace'):
        m = re.search(r'\[([^\]]+)\] \[(HL-SPAWN(?:-BACKEND)?)\].*?-> \((\d+),(\d+)\)', ln)
        if m:
            logseq[m.group(1)].append(('L' if m.group(2) == 'HL-SPAWN' else 'B', int(m.group(3)), int(m.group(4))))
            ms = re.search(r'slot=(\d+)', ln)
            if ms:
                slotof[m.group(1)] = int(ms.group(1))
            ms = re.search(r'chosenSlots=(\d+)/(\d+) minSep=(\d+)', ln)
            if ms:
                candn[m.group(1)].append(int(ms.group(2)))
                minsep = int(ms.group(3))
    bots = set(assign)
    lastcmds = {}
    if os.path.exists(f'{B}/traj.csv'):
        for r in csv.DictReader(open(f'{B}/traj.csv', encoding='utf-8')):
            bots.add(r['bot'])
            lastcmds[r['bot']] = int(r['cmds'])
    res = {}
    if os.path.exists(f'{B}/results.csv'):
        for r in csv.DictReader(open(f'{B}/results.csv', encoding='utf-8')):
            res[r['bot']] = r
            bots.add(r['bot'])
    names, sp, humans = {}, defaultdict(list), set()
    phase0 = 0
    for r in csv.DictReader(open(cp, encoding='utf-8'), delimiter='\t'):
        p = int(r['player'])
        if r['name']:
            names[p] = r['name']
        if r['kind'] == 'spawn':
            sp[p].append((int(r['tick']), int(r['a'])))
            phase0 = min(phase0, int(r['tick']))
    byname = defaultdict(list)
    for p, n in names.items():
        byname[bare(n)].append(p)
    pid = {b: byname[b.lower()][0] for b in bots if len(byname.get(b.lower(), [])) == 1}
    if not W:
        pts = {(x, y) for v in assign.values() for x, y, _ in v}
        best = (0, 0)
        for w in range(400, 4097):
            n = sum(1 for b, p in pid.items() for t, px in sp.get(p, []) if (px % w, px // w) in pts)
            if n > best[0]:
                best = (n, w)
        W = best[1]
    verd = Counter()
    rows = []
    ticks = []
    for b in sorted(bots):
        if b not in pid:
            rows.append((b, '不在这一盘录像里', None))
            continue
        R = [(t, px % W, px // W) for t, px in sp.get(pid[b], [])] if W else []
        A = assign.get(b, [])
        if not sp.get(pid[b]):
            v = '0 条落地'
        elif not W:
            v = '有出生指令（地图宽未知）'
        else:
            ex = R[-1][1:]
            if A and math.hypot(ex[0] - A[-1][0], ex[1] - A[-1][1]) <= 2:
                v = '最终坐标落地'
            elif any(math.hypot(ex[0] - x, ex[1] - y) <= 2 for x, y, _ in A[:-1]):
                v = '停在旧坐标'
            else:
                v = '日志外坐标'
        verd[v] += 1
        ticks += [t for t, _ in sp.get(pid[b], [])]
        sends = int(res[b]['accepted']) - lastcmds[b] if b in res and res[b].get('accepted') and b in lastcmds else None
        rows.append((b, v, {'assign': A, 'replay': R, 'sends': sends}))
    inrep = [r for r in rows if r[2] is not None]
    others = [p for p in names if p not in pid.values() and (sp.get(p) or True)]
    humans_with_names = [p for p in names if p not in set(pid.values())]
    oth_sp = sum(1 for p in sp if p not in set(pid.values()))
    sends = [r[2]['sends'] for r in inrep if r[2]['sends'] is not None]
    diff = sorted(r[2]['sends'] - len(r[2]['replay']) for r in inrep if r[2]['sends'] is not None)
    adiff = sorted(len(r[2]['assign']) - len(r[2]['replay']) for r in inrep)
    line = [mid, len(bots), len(inrep), len(solves), len(set(solves)), verd['最终坐标落地'], verd['停在旧坐标'], verd['日志外坐标'], verd['0 条落地'],
            f'{min(ticks)}..{max(ticks)}' if ticks else '-', phase0, oth_sp, len(humans_with_names), f'{min(sends)}-{max(sends)}' if sends else '-',
            f'{diff[0]}/{diff[len(diff) // 2]}/{diff[-1]}' if diff else '-', min(ticks) if ticks else '-', adiff[len(adiff) // 2] if adiff else '-']
    if tsv:
        print('\t'.join(str(x) for x in line))
    else:
        print(f'{mid}: 号 {len(bots)} 个（在这盘录像里 {len(inrep)}）｜求解 {len(solves)} 轮、不同的解 {len(set(solves))} 个｜最终坐标落地 {verd["最终坐标落地"]}、停在旧坐标 {verd["停在旧坐标"]}、日志外坐标 {verd["日志外坐标"]}、0 条落地 {verd["0 条落地"]}'
              f'｜我方出生指令落地拍 {line[9]}（选点期从 {phase0} 起）｜其他玩家有出生指令的 {oth_sp} 个｜本地发送数 {line[13]}｜每号 本地发送 − 录像落地（最小/中位/最大）{line[14]}｜每号 日志指派次数 − 录像落地 中位 {line[16]}')
    if seqmode and W:
        leads, trails, kinds, n0 = [], [], Counter(), 0
        for b, v, d in rows:
            if d is None:
                continue
            sq, R = logseq.get(b, []), d['replay']
            if not sq:
                continue
            if not R:
                n0 += 1
                leads.append(len(sq))
                trails.append(0)
                kinds.update(k for k, _, _ in sq)
                continue
            near = lambda e, r: abs(e[1] - r[1]) <= 2 and abs(e[2] - r[2]) <= 2
            first = next((i for i, e in enumerate(sq) if near(e, R[0])), None)
            last = next((i for i in range(len(sq) - 1, -1, -1) if near(sq[i], R[-1])), None)
            if first is None or last is None:
                continue
            leads.append(first)
            trails.append(len(sq) - 1 - last)
            kinds.update(k for k, _, _ in sq[:first])
        if leads:
            leads_s, trails_s = sorted(leads), sorted(trails)
            print(f'   [序列对齐] {mid}: 对得上的号 {len(leads)}｜开头没落地的条数 最小/中位/最大 {leads_s[0]}/{leads_s[len(leads_s) // 2]}/{leads_s[-1]}（≥1 条的号 {sum(1 for x in leads if x >= 1)}；其中 兜底点 L {kinds["L"]} 条、协调器点 B {kinds["B"]} 条）'
                  f'｜结尾没落地的条数 中位 {trails_s[len(trails_s) // 2]}、最大 {trails_s[-1]}（≥1 条的号 {sum(1 for x in trails if x >= 1)}）｜整条序列都没落地的号 {n0}')
    if detail:
        for b, v, d in rows:
            if d is None:
                print(f'   {b}: {v}')
                continue
            print(f'   {b}: {v}｜日志指派 {len(d["assign"])} 次' + (f'（最后 ({d["assign"][-1][0]},{d["assign"][-1][1]}) {d["assign"][-1][2]}）' if d['assign'] else '')
                  + f'｜录像出生指令 {len(d["replay"])} 条' + (('：' + '、'.join(f'拍 {t} ({x},{y})' for t, x, y in d['replay'][-3:])) if d['replay'] else '')
                  + (f'｜本地发送约 {d["sends"]} 条' if d['sends'] is not None else ''))
    if hopmode and W:
        med = lambda v: (sorted(v)[len(v) // 2] if v else 0)
        fin = {}
        print(f'   [跳点与叠号] {mid}（地图宽 {W}；minSep {minsep or 45}）')
        hopn, hopd = [], []
        for b, v, d in rows:
            if d is None:
                continue
            sq, R = logseq.get(b, []), d['replay']
            hops = [math.hypot(sq[i][1] - sq[i - 1][1], sq[i][2] - sq[i - 1][2]) for i in range(1, len(sq))]
            rh = [math.hypot(R[i][1] - R[i - 1][1], R[i][2] - R[i - 1][2]) for i in range(1, len(R))]
            if R:
                fin[b] = (R[-1][1], R[-1][2], R[-1][0])
            back = next((len(sq) - 1 - i for i in range(len(sq) - 1, -1, -1) if R and abs(sq[i][1] - R[-1][1]) <= 2 and abs(sq[i][2] - R[-1][2]) <= 2), None)
            hopn.append(len(sq)); hopd += hops
            print(f'      {b}: 槽位 {slotof.get(b, "-")}｜日志坐标 {len(sq)} 个（不同 {len(set((x, y) for _, x, y in sq))}）｜相邻两次相隔 中位 {med(hops):.0f} / 最大 {max(hops) if hops else 0:.0f} 格'
                  + (f'｜候选表长度 {dict(Counter(candn[b]))}' if candn.get(b) else '')
                  + f'｜录像落地 {len(R)} 条' + (f'（拍 {R[0][0]}…{R[-1][0]}；落地指令相邻相隔 中位 {med(rh):.0f} / 最大 {max(rh) if rh else 0:.0f}）' if R else '')
                  + (f'｜最终出生 ({R[-1][1]},{R[-1][2]}) = 日志序列倒数第 {back + 1} 个' if R and back is not None else ('｜最终出生点不在日志序列里' if R else '｜没有出生指令落地')))
        if hopn:
            print(f'      合计：每号日志坐标 中位 {med(hopn)} 个（最少 {min(hopn)}、最多 {max(hopn)}）；相邻两次相隔 中位 {med(hopd):.0f} 格、≥300 格的 {sum(1 for x in hopd if x >= 300)}/{len(hopd)} 次')
        shared = defaultdict(set)
        cells = defaultdict(set)
        for b, sq in logseq.items():
            for _, x, y in sq:
                cells[(x // 16, y // 16)].add((b, x, y))
        seen = set()
        for b, sq in logseq.items():
            for _, x, y in sq:
                who = set()
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        for (b2, x2, y2) in cells.get((x // 16 + dx, y // 16 + dy), ()):
                            if abs(x2 - x) <= 8 and abs(y2 - y) <= 8:
                                who.add(b2)
                if len(who) >= 2:
                    key = (round(x / 16), round(y / 16))
                    if key in seen:
                        continue
                    seen.add(key)
                    shared[(x, y)] = who
        if shared:
            top = sorted(shared.items(), key=lambda kv: -len(kv[1]))
            print(f'      撞点：{len(top)} 个坐标出现在 ≥2 个号的日志序列里（≥3 个号的 {sum(1 for _, w in top if len(w) >= 3)} 个）；前 8：'
                  + '；'.join(f'({x},{y}) {len(w)} 个号[' + '、'.join(f'{b}/{slotof.get(b, "-")}' for b in sorted(w)) + ']' for (x, y), w in top[:8]))
        sep = minsep or 45
        bl = sorted(fin)
        pairs = [(math.hypot(fin[x][0] - fin[y][0], fin[x][1] - fin[y][1]), x, y) for i, x in enumerate(bl) for y in bl[i + 1:]]
        close = sorted(p for p in pairs if p[0] < sep)
        par = {b: b for b in bl}
        def find(x):
            while par[x] != x:
                par[x] = par[par[x]]; x = par[x]
            return x
        for _, x, y in close:
            par[find(x)] = find(y)
        comp = defaultdict(list)
        for b in bl:
            comp[find(b)].append(b)
        heaps = [v for v in comp.values() if len(v) >= 2]
        nn = [min(p[0] for p in pairs if b in (p[1], p[2])) for b in bl] if len(bl) > 1 else []
        print(f'      叠号：最终出生点两两 < {sep} 格的号对 {len(close)} 对' + ('：' + '；'.join(f'{x}–{y} {d:.0f} 格（落地拍 {fin[x][2]} / {fin[y][2]}）' for d, x, y in close) if close else '')
              + f'｜堆 {len(heaps)} 个' + ('：' + '；'.join('＋'.join(h) for h in heaps) if heaps else '')
              + (f'｜每号到最近的我方号 中位 {med(nn):.0f} 格（最小 {min(nn):.0f}、最大 {max(nn):.0f}）' if nn else ''))
