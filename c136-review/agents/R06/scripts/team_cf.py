#!/usr/bin/env python3
"""team_cf.py — 分队反事实（纯离线，不重放）：用线上引擎的分队算法（team_assign.assign_teams，逐行移植自 bj.ee → aej/aKa/aek/ael/aem）
在同一份录像头（全体真人的名字、颜色、真人数、配置队数）上，只改我方号「进房间时的名字标签 / 颜色」，看 20 个号会被分到哪。

用法：python3 team_cf.py [<matchId> ...]        不带局号 = 有录像头的 12 局

每局四行：
  实际       ：按真实名字和颜色重算（先与真引擎重放的队伍表核对，全部一致才往下算）。
  同一个标签 ：我方号的名字前都加同一个战队标签（其余不变）。引擎规则：最大战队人数 > floor(真人数 / 队数) 时队数减 1（直到 2），
               战队整体放进一个队。
  同一个颜色 ：我方号不加标签，颜色都改成同一个队色（取实际分队里我方人数最多的那个队的队色）。引擎规则：每队上限 ceil(真人数 / 队数)，
               按玩家号顺序先进第一志愿队，满了进第二志愿，再满硬塞。
  两个颜色   ：我方号按玩家号前后各一半，分别用实际里我方人数最多、第二多的两个队色。
输出：我方号在各队的人数、最大一队占我方在场席位的比例、队数。
局限：只改我方号自己的标签 / 颜色；别的真人的选择不变。队色的票数会因我方号改色而变（脚本照引擎规则重算）。
      这是「服务器会怎么分」的答案，不是「分到一起以后能不能赢」的答案。
"""
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import simdigest as SD  # noqa: E402
import team_assign as TA  # noqa: E402

DEFAULT = ['B010', 'B014', 'B017', 'B018', 'B021', 'B022', 'B023', 'B025', 'B038', 'B039', 'B041', 'B045']
REPLAY_OF = {'B038': 'A057', 'B039': 'A058'}
# 引擎的 8 个队色（红绿蓝黄紫青白黑）对应的 18 位颜色值（每通道 6 位，×4 还原）
PURE = [(63, 0, 0), (0, 63, 0), (0, 0, 63), (63, 63, 0), (63, 0, 63), (0, 63, 63), (63, 63, 63), (0, 0, 0)]


def col(k):
    r, g, b = PURE[k]
    return (r << 12) | (g << 6) | b


def split(res, squad):
    c = Counter(res['team'][p] for p in squad)
    return sorted(c.values(), reverse=True), c


def fmt(res, squad):
    sizes, c = split(res, squad)
    return f"{'/'.join(map(str, sizes))}（最大一队 {100 * sizes[0] / len(squad):.0f}%；全场 {res['teams']} 队，各队真人 {'/'.join(str(x) for x in res['size'][1:res['teams'] + 1])}）"


def one(mid):
    d = TA.load_decoded(mid)
    if d is None or not d.get('colors'):
        return None
    X = SD.Sim(mid)
    s = d['settings']
    H, n, P = s['humanCount'], s['numberTeams'], s['playerCount']
    names, colors = list(d['names']), list(d['colors'])
    squad = sorted(p for p in X.squad if p < H)
    base = TA.assign_teams(names, colors, H, n, P)
    ok = sum(1 for p in squad if base['team'][p] == X.team[p])
    out = dict(id=mid, H=H, n=n, squad=len(squad), ok=ok)
    out['real'] = fmt(base, squad)
    out['realMax'] = split(base, squad)[0][0]
    # 同一个标签
    nm = list(names)
    for p in squad:
        nm[p] = '[SQ] ' + nm[p]
    r1 = TA.assign_teams(nm, colors, H, n, P)
    out['tag'] = fmt(r1, squad)
    out['tagMax'] = split(r1, squad)[0][0]
    out['tagTeams'] = r1['teams']
    # 同一个颜色：实际里我方人数最多的队的队色
    _, c = split(base, squad)
    order = [t for t, _ in c.most_common()]
    k1 = base['lH'][order[0]] - 1
    k2 = base['lH'][order[1]] - 1 if len(order) > 1 else k1
    cl = list(colors)
    for p in squad:
        cl[p] = col(k1)
    r2 = TA.assign_teams(names, cl, H, n, P)
    out['color'] = fmt(r2, squad)
    out['colorMax'] = split(r2, squad)[0][0]
    cl = list(colors)
    half = len(squad) // 2
    for i, p in enumerate(squad):
        cl[p] = col(k1 if i < half else k2)
    r3 = TA.assign_teams(names, cl, H, n, P)
    out['color2'] = fmt(r3, squad)
    out['border'] = base['border']
    return out


def main():
    ids = [a for a in sys.argv[1:] if not a.startswith('-')] or DEFAULT
    rows = [o for o in (one(m) for m in ids) if o]
    print('| 局 | 真人 / 配置队数 / 每队上限 | 我方号 | 与真引擎队伍表核对 | 实际 | 同一个标签 | 同一个颜色 | 两个颜色各一半 |')
    print('|---|---|---|---|---|---|---|---|')
    for o in rows:
        print(f"| {o['id']} | {o['H']} / {o['n']} / {o['border']} | {o['squad']} | {o['ok']}/{o['squad']} | {o['real']} | {o['tag']} | {o['color']} | {o['color2']} |")
    n = len(rows)
    print(f"合计 {n} 局：实际最大一队占我方席位的中位 {sorted(100 * o['realMax'] / o['squad'] for o in rows)[n // 2]:.0f}%；"
          f"同一个标签：全部进同一个队的 {sum(1 for o in rows if o['tagMax'] == o['squad'])} 局，全场变成 2 队的 {sum(1 for o in rows if o['tagTeams'] == 2)} 局；"
          f"同一个颜色：全部进同一个队的 {sum(1 for o in rows if o['colorMax'] == o['squad'])} 局，最大一队占比中位 {sorted(100 * o['colorMax'] / o['squad'] for o in rows)[n // 2]:.0f}%")


if __name__ == '__main__':
    main()
