#!/usr/bin/env python3
"""spawn_geo.py — 出生点地形账：地图二进制 + 每个号的出生点。

出生点的来源（打印在表头）：
  · 有录像（哪怕只有选点阶段）：录像里每个号最后一条生效的选点指令 = 真正的出生点；
  · 没有录像：只能拿日志里每个号最后一条 HL-SPAWN。**这不可靠**：有录像的 5 局（B023/B039/B038/B010/B041，90 个号）里，
    日志最后一条就是真正出生点的只有 15 个号，倒数第二条 41 个，其余更靠前（digest.py <id> spawnlog 可重算）。
    所以没有录像的局，这张表只能当「候选之一」，不能用来下「谁和谁叠在一起」的结论。

用法：python3 spawn_geo.py <matchId> [json]
  · 地图：/agent/repos/c136-data/src/sim/maps/<mapId>_<seed>.bin.gz，没有就找 out/_maps/<mapId>_<seed>.bin.gz
    （随机地图：map_export.mjs 从真引擎导出），再没有就用 <mapId>_0.bin.gz（固定地图不随种子变）；
    陆地格数必须等于对局卡的 mapLand，否则报错退出（防止拿错地图）。
  · 每个号：出生点是否在陆地上、所在连通陆块（4 邻接）多大、到最近水格的直线距离。
  · 号与号：直线距离 < minSep(145) 的全部成对列出，附同队 / 异队。
  · 「陆上最近」：从 20 个出生点同时沿陆地（4 邻接）一圈一圈往外走，每格归最先走到的号（同步到的归编号小的）。
    这只是 20 个号彼此之间的分地（外人的出生点没有录像看不到），用来量「叠在一起的号彼此抢同一块地」。
  json：把结果写进 out/<id>/spawn_geo.json。
"""
import gzip
import json
import math
import os
import struct
import sys
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from r06lib import OUT, load_match  # noqa: E402

MAPS = '/agent/repos/c136-data/src/sim/maps'
T_LAND = 1
T_WATER = 2
MIN_SEP = 145


def load_map(map_id, seed):
    # 共享目录的 <mapId>_<seed> → 自己从真引擎导出的 out/_maps/<mapId>_<seed>（map_export.mjs）→ 固定地图 <mapId>_0
    for p in (os.path.join(MAPS, f"{map_id}_{seed}.bin.gz"), os.path.join(OUT, '_maps', f"{map_id}_{seed}.bin.gz"), os.path.join(MAPS, f"{map_id}_0.bin.gz")):
        name = os.path.basename(p)
        if os.path.exists(p):
            buf = gzip.open(p, 'rb').read()
            if buf[:4] != b'TMAP':
                raise SystemExit(f"地图文件头不对：{p}")
            w, h = struct.unpack_from('<HH', buf, 4)
            return name, w, h, buf[8:8 + w * h]
    raise SystemExit(f"找不到地图 {map_id}_{seed} / {map_id}_0")


def geo(mid):
    M = load_match(mid)
    import digest as D
    R = D.picks_rows(M)
    true_xy = {me: (v[-1][1], v[-1][2]) for me, v in R['per'].items() if v} if R else {}
    name, W, H, ty = load_map(M.card['mapId'], M.card['mapSeed'])
    land = sum(1 for v in ty if v == T_LAND)
    if land != M.card['mapLand']:
        raise SystemExit(f"地图 {name} 陆地 {land} 格，对局卡 mapLand={M.card['mapLand']}，对不上")
    N = W * H
    # 连通陆块
    comp = [-1] * N
    sizes = []
    for s in range(N):
        if ty[s] != T_LAND or comp[s] >= 0:
            continue
        cid = len(sizes)
        comp[s] = cid
        q = deque([s])
        n = 0
        while q:
            c = q.popleft()
            n += 1
            x = c % W
            for d in ((-1 if x > 0 else 0), (1 if x < W - 1 else 0), -W, W):
                if d == 0:
                    continue
                k = c + d
                if 0 <= k < N and ty[k] == T_LAND and comp[k] < 0:
                    comp[k] = cid
                    q.append(k)
        sizes.append(n)
    bots = []
    for me, b in sorted(M.bots.items()):
        if me in true_xy:
            x, y = true_xy[me]
            sp = dict(slot=(b.spawns[-1]['slot'] if b.spawns else None))
        elif b.spawns and not true_xy:
            sp = b.spawns[-1]
            x, y = sp['x'], sp['y']
        else:
            continue
        idx = y * W + x if 0 <= x < W and 0 <= y < H else None
        on = idx is not None and ty[idx] == T_LAND
        # 最近水格（直线，搜到半径 200 为止）
        wd = None
        if idx is not None:
            for r in range(1, 201):
                hit = False
                for dy in range(-r, r + 1):
                    yy = y + dy
                    if yy < 0 or yy >= H:
                        continue
                    span = int(math.isqrt(r * r - dy * dy))
                    for dx in (-span, span):
                        xx = x + dx
                        if 0 <= xx < W and ty[yy * W + xx] == T_WATER:
                            hit = True
                            break
                    if hit:
                        break
                if hit:
                    wd = r
                    break
        bots.append(dict(me=me, name=b.name, team=b.team, x=x, y=y, onLand=on, comp=(comp[idx] if on else None),
                         compSize=(sizes[comp[idx]] if on else None), waterDist=wd, picks=len(b.spawns), slot=sp['slot'],
                         fate=(b.result['event'] if b.result else None), fateTick=(b.result['tick'] if b.result else None)))
    # 陆上最近（多源 BFS）
    owner = [-1] * N
    dist = [0] * N
    q = deque()
    for i, bt in enumerate(bots):
        if bt['onLand']:
            k = bt['y'] * W + bt['x']
            if owner[k] < 0:
                owner[k] = i
                q.append(k)
    while q:
        c = q.popleft()
        x = c % W
        o = owner[c]
        for d in ((-1 if x > 0 else 0), (1 if x < W - 1 else 0), -W, W):
            if d == 0:
                continue
            k = c + d
            if 0 <= k < N and ty[k] == T_LAND and owner[k] < 0:
                owner[k] = o
                dist[k] = dist[c] + 1
                q.append(k)
    cnt = [0] * len(bots)
    near = [0] * len(bots)     # 其中陆上步数 <= 60 的格数（开局 600 拍内够得着的范围的粗略量级）
    for k in range(N):
        o = owner[k]
        if o >= 0:
            cnt[o] += 1
            if dist[k] <= 60:
                near[o] += 1
    for i, bt in enumerate(bots):
        bt['voronoi'] = cnt[i]
        bt['voronoi60'] = near[i]
    pairs = []
    for i in range(len(bots)):
        for j in range(i + 1, len(bots)):
            a, b = bots[i], bots[j]
            d = math.hypot(a['x'] - b['x'], a['y'] - b['y'])
            if d < MIN_SEP:
                pairs.append(dict(a=a['me'], b=b['me'], aName=a['name'], bName=b['name'], dist=round(d, 1), sameTeam=(a['team'] == b['team']), teams=[a['team'], b['team']],
                                  sameComp=(a['comp'] == b['comp'])))
    pairs.sort(key=lambda p: p['dist'])
    return dict(matchId=mid, map=name, W=W, H=H, land=land, components=sorted(sizes, reverse=True)[:8], bots=bots, pairs=pairs, minSep=MIN_SEP,
                source=('replay' if true_xy else 'log-last-unreliable'))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    mid = sys.argv[1]
    G = geo(mid)
    if len(sys.argv) > 2 and sys.argv[2] == 'json':
        os.makedirs(os.path.join(OUT, mid), exist_ok=True)
        p = os.path.join(OUT, mid, 'spawn_geo.json')
        json.dump(G, open(p, 'w'), ensure_ascii=False)
        print('写入', p)
        return 0
    print(f"== {mid} 出生点地形账：地图 {G['map']} {G['W']}x{G['H']}，陆地 {G['land']} 格（与对局卡一致）；最大的几块连通陆地：{G['components']}")
    print('   出生点来源：' + ('录像里最后一条生效的选点指令（真值）' if G['source'] == 'replay'
                            else '没有录像，用的是日志最后一条 HL-SPAWN——不可靠（校准局 90 个号里只有 15 个对），下表只能当候选，不能下结论'))
    print('   号 队 出生点 在陆地上? 所在陆块大小 离最近水格 ｜ 20 个号之间「陆上最近」分到的格数（其中 60 步以内）｜ 选点次数 ｜ 去向')
    tot = sum(b['voronoi'] for b in G['bots'])
    for b in sorted(G['bots'], key=lambda b: b['voronoi']):
        print(f"   {b['name']:14s} 队{b['team']} ({b['x']:4d},{b['y']:4d}) {'是' if b['onLand'] else '否'} {b['compSize'] or 0:7d} {b['waterDist'] if b['waterDist'] is not None else '>200':>4} ｜ {b['voronoi']:7d}（{100 * b['voronoi'] / max(1, tot):4.1f}%；60 步内 {b['voronoi60']:5d}）｜ {b['picks']:2d} ｜ {b['fate']}@{b['fateTick']}")
    print(f"   直线距离 < {G['minSep']} 的成对（共 {len(G['pairs'])} 对；同队 {sum(1 for p in G['pairs'] if p['sameTeam'])}、异队 {sum(1 for p in G['pairs'] if not p['sameTeam'])}）：")
    for p in G['pairs']:
        print(f"      {p['aName']}(队{p['teams'][0]}) — {p['bName']}(队{p['teams'][1]}) {p['dist']:6.1f} {'同队' if p['sameTeam'] else '异队'} {'同一陆块' if p['sameComp'] else '不同陆块'}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
