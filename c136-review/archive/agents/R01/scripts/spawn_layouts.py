#!/usr/bin/env python3
"""spawn_layouts.py — 协调器每一次求解的整份落点（日志 [BACKEND-SPAWN-COORD] 行）对上录像里落地的出生指令。

回答四件事：
  1. 协调器求解了几次、有几份不同的落点表（按第一次出现的顺序编号 v1、v2…），每份表相对上一份挪了几个号；
  2. 每个本队号在录像里落地的每一条出生指令（出生阶段第几步、坐标）属于哪一份表；
  3. 出生阶段结束时十个号站的是哪几份表拼起来的阵（各号最后一条落地指令的版本）、两两距离；
  4. 每个号最后落点离“当时已经落地的”非本队真人出生点有多近（对方在我这条指令落地之前最后一条出生指令的坐标），
     以及离对方最终出生点有多近。--near 像素以内的列出来。

输入：bundles/<log>/in_game.log、out/<mid>/replay_cmds.csv（replay_cmds.mjs 或 resim.mjs 写）、out/<mid>/resim_meta.json。
用法：python3 scripts/spawn_layouts.py <matchId> [--log id1,id2] [--near 40] [--brief]
"""
import argparse
import csv
import json
import os
import re
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
BUNDLES = '/agent/repos/c136-data/bundles'


def dist(a, b):
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def read_solves(logs):
    out = []
    for lid in logs:
        f = f'{BUNDLES}/{lid}/in_game.log'
        if not os.path.exists(f):
            continue
        for line in open(f, encoding='utf8'):
            m = re.search(r'^(\d+)\t.*\[BACKEND-SPAWN-COORD\] Solved (\d+) bots .*?minSep=(\d+)px.*?\): (.*)$', line)
            if not m:
                continue
            roster = {b: (int(x), int(y)) for b, x, y in re.findall(r'\[\w+\] (\w+)\(\w+\)->\((\d+),(\d+)\)', m.group(4))}
            out.append({'line': int(m.group(1)), 'n': int(m.group(2)), 'minSep': int(m.group(3)), 'pos': roster, 'log': lid})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mid')
    ap.add_argument('--log', default=None)
    ap.add_argument('--near', type=float, default=40)
    ap.add_argument('--brief', action='store_true')
    ap.add_argument('--json', action='store_true', help='把汇总数写到 out/<mid>/spawn_layouts.json（给 M6 跨局表用）')
    a = ap.parse_args()
    logs = (a.log or a.mid).split(',')
    od = os.path.join(HERE, '..', 'out', a.mid)
    meta = json.load(open(os.path.join(od, 'resim_meta.json')))
    W = meta['W']; H = meta['humans']
    squad = meta['squad']; seat2bot = {p: b for b, p in squad.items()}
    teams = {int(k): v for k, v in meta['teams'].items()}
    names = meta['names']
    my_team = teams[next(iter(squad.values()))]

    solves = read_solves(logs)
    # 同局还有另一支编队时（A057 的重演把 B038 的 20 个号也算进 squad），只留协调器名单里出现过的号
    roster = {b for sv in solves for b in sv['pos']}
    if roster:
        squad = {b: p for b, p in squad.items() if b in roster}
        seat2bot = {p: b for b, p in squad.items()}
    versions = []          # 不同的落点表
    for s in solves:
        key = tuple(sorted(s['pos'].items()))
        for i, v in enumerate(versions):
            if v['key'] == key:
                s['v'] = i + 1; v['count'] += 1
                break
        else:
            versions.append({'key': key, 'pos': s['pos'], 'minSep': s['minSep'], 'count': 1, 'line': s['line']})
            s['v'] = len(versions)

    cmds = defaultdict(list)   # seat -> [(step, x, y)]
    max_step = 0
    for r in csv.DictReader(open(os.path.join(od, 'replay_cmds.csv'), encoding='utf8')):
        if r['kind'] != 'spawn':
            continue
        px = int(r['dX']); st = int(r['step'])
        cmds[int(r['player'])].append((st, px % W, px // W))
        max_step = max(max_step, st)
    for v in cmds.values():
        v.sort(key=lambda c: c[0])   # 只按步排（稳定排序）：同一步里的多条出生指令保持录像里的先后，最后一条生效

    print(f'== {a.mid} 协调器求解 {len(solves)} 次，不同的落点表 {len(versions)} 份；录像里出生指令最晚在出生阶段第 {max_step} 步')
    prev = None
    for i, v in enumerate(versions, 1):
        moved = '' if prev is None else f"，相对上一份挪了 {sum(1 for b in v['pos'] if prev.get(b) != v['pos'][b])} 个号"
        ds = sorted(dist(p, q) for bi, p in enumerate(v['pos'].values()) for q in list(v['pos'].values())[bi + 1:])
        landed = sum(1 for b, p in v['pos'].items() if b in squad and any((x, y) == p for _, x, y in cmds.get(squad[b], [])))
        absent = [b for b in v['pos'] if b not in squad]
        print(f"  v{i}: 求解 {v['count']} 次（日志行 {v['line']} 起），minSep={v['minSep']}，表内两两最小距离 {ds[0]:.0f}{moved}；"
              f"这份表的落点在录像里落地 {landed}/{len(v['pos'])} 条" + (f"；名单里不在本局的号 {' '.join(absent)}" if absent else ''))
        prev = v['pos']

    def version_of(b, xy):
        return [i for i, v in enumerate(versions, 1) if v['pos'].get(b) == xy]

    print('== 每个号落地的出生指令（第几步 坐标 = 哪份表；? = 不在任何一份表里）')
    final = {}
    for b, p in sorted(squad.items(), key=lambda kv: kv[1]):
        cm = cmds.get(p, [])
        if not cm:
            print(f'  {b:<8} #{p} 没有出生指令'); continue
        parts = []
        for st, x, y in cm:
            vs = version_of(b, (x, y))
            parts.append(f"{st}:({x},{y})=" + ('/'.join(f'v{i}' for i in vs) if vs else '?'))
        st, x, y = cm[-1]
        vs = version_of(b, (x, y))
        final[b] = {'xy': (x, y), 'step': st, 'v': vs}
        lastv = versions[-1]['pos'].get(b) if versions else None
        note = ''
        if lastv and lastv != (x, y):
            note = f" | 最后一份表给的 ({lastv[0]},{lastv[1]}) 没落地，相距 {dist(lastv, (x, y)):.0f}"
        if not a.brief:
            print(f"  {b:<8} #{p:<3} " + '  '.join(parts) + note)
    by_v = defaultdict(list)
    for b, f in final.items():
        by_v['/'.join(f'v{i}' for i in f['v']) or '?'].append(b)
    print('== 出生阶段结束时的阵：' + '；'.join(f"{k}: {' '.join(v)}（落地在第 {min(final[b]['step'] for b in v)}–{max(final[b]['step'] for b in v)} 步）" for k, v in sorted(by_v.items())))
    bots = sorted(final)
    pd = sorted((dist(final[x]['xy'], final[y]['xy']), x, y) for i, x in enumerate(bots) for y in bots[i + 1:])
    if pd:
        print(f"   两两距离 最小/中位/最大 {pd[0][0]:.0f}/{pd[len(pd) // 2][0]:.0f}/{pd[-1][0]:.0f}；{a.near:.0f} 像素以内的对："
              + (' '.join(f'{x}-{y} {d:.0f}' for d, x, y in pd if d < a.near) or '无'))
        for d, x, y in pd:
            if d >= a.near:
                break
            vx, vy = final[x]['v'], final[y]['v']
            both = [i for i in vx if i in vy]
            print(f"   {x}-{y} {d:.0f} 像素：{x} 站 {'/'.join(f'v{i}' for i in vx) or '?'}，{y} 站 {'/'.join(f'v{i}' for i in vy) or '?'}"
                  + ('' if both else '（两个点不出自同一份表）'))

    print(f'== 落点离非本队真人的出生点（T{my_team} 以外；“当时”= 对方在我这条指令落地那一步之前最后一条出生指令）')
    flagged = 0
    for b in bots:
        f = final[b]
        best_then = None; best_final = None
        for q, cm in cmds.items():
            if q >= H or q in seat2bot or teams.get(q) == my_team:
                continue
            fin = cm[-1]
            d2 = dist(f['xy'], fin[1:])
            if best_final is None or d2 < best_final[0]:
                best_final = (d2, q, fin)
            before = [c for c in cm if c[0] < f['step']]
            if before:
                c = before[-1]
                d1 = dist(f['xy'], c[1:])
                if best_then is None or d1 < best_then[0]:
                    best_then = (d1, q, c)
        s = f"  {b:<8} ({f['xy'][0]},{f['xy'][1]}) 第 {f['step']} 步落地"
        if best_then:
            d1, q, c = best_then
            s += f" | 当时最近：{names[q]}/T{teams[q]} ({c[1]},{c[2]}) 第 {c[0]} 步已落地，{d1:.0f} 像素"
        if best_final:
            d2, q, c = best_final
            s += f" | 最终最近：{names[q]}/T{teams[q]} ({c[1]},{c[2]}) 第 {c[0]} 步，{d2:.0f} 像素"
        hit = best_then and best_then[0] < a.near
        if hit:
            flagged += 1
            s += '  <<< 落点选在已经落地的敌方真人旁边'
        print(s)
    print(f'   {a.near:.0f} 像素内有“当时已落地的敌方真人”的号：{flagged}/{len(bots)}')
    if a.json:
        v1 = versions[0]['pos'] if versions else {}
        vl = versions[-1]['pos'] if versions else {}
        landed_of = lambda pos: sum(1 for b, q in pos.items() if b in squad and any((x, y) == q for _, x, y in cmds.get(squad[b], [])))
        out = {
            'mid': a.mid, 'solves': len(solves), 'layouts': len(versions), 'lastSpawnStep': max_step,
            'v1Bots': sum(1 for b in v1 if b in squad), 'v1Landed': landed_of(v1),
            'squad': len(squad), 'noSpawnCmd': sum(1 for b, q in squad.items() if not cmds.get(q)),
            'spawnCmdsPerBot': sorted(len(cmds.get(q, [])) for q in squad.values()),
            # 收场时站在“最后一份表”给的点上的号数；站的点不在任何一份表里的号数；收场的阵由几种版本组合拼成
            'onLast': sum(1 for b, f in final.items() if vl.get(b) == f['xy']), 'offTable': sum(1 for f in final.values() if not f['v']),
            'finalGroups': len(by_v),
            'pairMin': round(pd[0][0]) if pd else None, 'pairMed': round(pd[len(pd) // 2][0]) if pd else None, 'pairMax': round(pd[-1][0]) if pd else None,
            'nearPairs': sum(1 for d, x, y in pd if d < a.near), 'nearEnemy': flagged, 'near': a.near,
            # 最后一条落地的出生指令是同一个像素的对；其中两个点不出自同一份表的对
            'samePixelPairs': sum(1 for d, x, y in pd if d == 0),
            'samePixelDiffVersion': sum(1 for d, x, y in pd if d == 0 and not [i for i in final[x]['v'] if i in final[y]['v']]),
        }
        json.dump(out, open(os.path.join(od, 'spawn_layouts.json'), 'w'), ensure_ascii=False)
        print(f'# 已写 out/{a.mid}/spawn_layouts.json')


if __name__ == '__main__':
    main()
