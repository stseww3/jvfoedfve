#!/usr/bin/env python3
"""team_assign.py — 按线上引擎的分队算法（live_game_js.js 里 bj.ee → aej / aKa / aek / ael / aem）
从录像头（每个真人的颜色 colorsData、名字里的战队标签、真人数、配置队数）重算每个玩家的队号。

用法：
    python3 team_assign.py <matchId> [--replay-of <otherMatchId>]   # 打印重算队号，并与 results.csv 的 teamMine 对照
    （先跑 replay_decode.mjs 生成 out/<matchId>/replay_decoded.json）

算法要点（逐行对照引擎原文，见 reviews 里的引用）：
  1. aej：每个真人按自己的颜色到 8 个队色（红绿蓝黄紫青白黑）的曼哈顿距离，得到第一志愿 a2F、第二志愿 a2G；
          第一志愿给该色 +4 票，第二志愿 +1 票。距离并列时按 (ft+玩家号)%8 的轮转顺序取先遇到的。
  2. aKa：8 个颜色按票数从高到低排成队序 lH[1..8]（并列取编号小的）。只有前 a0L 个颜色真正成队。
  3. aek：名字里带 [标签]（1~7 个字符）的算战队。最大战队人数 > floor(真人数/队数) 时队数减 1（直到 2）。
          战队从大到小整体放进「本战队票数最高且在场」的那个队，除非该队已经严格大于其它所有队。
  4. ael：每队上限 border = ceil(真人数/队数)。其余真人按玩家号顺序先进第一志愿队（没满），再试第二志愿，
          最后剩下的从队号大的队、玩家号大的人开始硬塞。
  5. aem：队数 < 8 时，内置 AI 不进任何队（队号 0，人人可打）；队数 = 8 时 AI 按 1 + 玩家号 % 8 分进 8 个队。
"""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'out')
DATA = '/agent/repos/c136-data/bundles'
TEAM_RGB = [[128, 128, 128], [255, 0, 0], [0, 255, 0], [0, 0, 255], [255, 255, 0],
            [255, 0, 255], [0, 255, 255], [255, 255, 255], [0, 0, 0]]
COLOR_NAME = ['灰', '红', '绿', '蓝', '黄', '紫', '青', '白', '黑']


def clan_tag(name):
    a = name.find('[')
    if a < 0:
        return None
    b = name.find(']')
    if 1 < b - a <= 8:
        return name[a + 1:b].upper().strip()
    return None


def assign_teams(names, colors, humans, n_teams, players=512):
    """返回 dict(team=[每个玩家的队号], lH=队序→颜色, teams=最终队数, first=[第一志愿色], second=[第二志愿色],
    clans={tag:[成员]}, border=每队上限, botsTeamed=bool)。"""
    H = humans
    a2F = [0] * H
    a2G = [0] * H
    votes = [0] * 8
    for p in range(H - 1, -1, -1):
        c = colors[p]
        r, g, b = 4 * (c >> 12), 4 * ((c >> 6) & 63), 4 * (c & 63)
        h = [abs(r - TEAM_RGB[k + 1][0]) + abs(g - TEAM_RGB[k + 1][1]) + abs(b - TEAM_RGB[k + 1][2]) for k in range(8)]
        best = 768
        for ft in range(7, -1, -1):
            e = (ft + p) % 8
            if h[e] < best:
                best = h[e]
                a2F[p] = e
        votes[a2F[p]] += 4
        best = 768
        for ft in range(7, -1, -1):
            e = (ft + p) % 8
            if h[e] < best and e != a2F[p]:
                best = h[e]
                a2G[p] = e
        votes[a2G[p]] += 1
    vote_snapshot = list(votes)
    # aKa
    lH = list(range(9))
    aeo = [v + 1 for v in votes]
    for k in range(1, 9):
        lr = 0
        for ft in range(1, 8):
            if aeo[ft] > aeo[lr]:
                lr = ft
        aeo[lr] = 0
        lH[k] = lr + 1
    # aek
    team = [0] * players
    size = [0] * 9
    tags, members = [], []
    biggest = 0
    for p in range(H):
        t = clan_tag(names[p])
        if t is None:
            continue
        for i in range(len(tags) - 1, -1, -1):
            if tags[i] == t:
                members[i].append(p)
                biggest = max(biggest, len(members[i]))
                break
        else:
            tags.append(t)
            members.append([p])
            biggest = max(biggest, 1)
    a0L = n_teams
    while a0L > 2 and biggest > H // a0L:
        a0L -= 1
    placed = [False] * len(tags)
    clan_team = {}
    for _ in range(len(tags)):
        fc = -1
        for ej in range(len(tags) - 1, -1, -1):
            if not placed[ej] and (fc == -1 or len(members[ej]) > len(members[fc])):
                fc = ej
        sp = [1] * 8
        for m in reversed(members[fc]):
            sp[a2F[m]] += 3
            sp[a2G[m]] += 1
        for _try in range(8):
            e = fc % 8
            for ej in range(7, -1, -1):
                if sp[ej] > sp[e]:
                    e = ej
            o7 = -1
            for ej in range(a0L, 0, -1):
                if lH[ej] == e + 1:
                    o7 = ej
                    break
            sp[e] = 0
            if o7 == -1:
                continue
            uv = 0
            for ej in range(a0L, 0, -1):
                if size[o7] > size[ej]:
                    uv += 1
            if uv == a0L - 1:
                continue
            for m in reversed(members[fc]):
                size[o7] += 1
                team[m] = o7
            clan_team[tags[fc]] = o7
            break
        placed[fc] = True
    # ael
    border = H // a0L + (1 if H % a0L > 0 else 0)
    aew = [0] * 9
    for ft in range(8, 0, -1):
        aew[lH[ft]] = ft
    how = [''] * H
    for p in range(H):
        if team[p]:
            how[p] = 'clan'
    for p in range(H):
        iv = aew[a2F[p] + 1]
        if team[p] == 0 and iv <= a0L and size[iv] < border:
            size[iv] += 1
            team[p] = iv
            how[p] = 'first'
    for p in range(H):
        iv = aew[a2G[p] + 1]
        if team[p] == 0 and iv <= a0L and size[iv] < border:
            size[iv] += 1
            team[p] = iv
            how[p] = 'second'
    for ft in range(a0L, 0, -1):
        for p in range(H - 1, -1, -1):
            if size[ft] >= border:
                break
            if team[p] == 0:
                size[ft] += 1
                team[p] = ft
                how[p] = 'fill'
    bots_teamed = a0L >= 8
    if bots_teamed:
        for p in range(H, players):
            team[p] = 1 + p % a0L
    return dict(team=team, lH=lH, teams=a0L, first=a2F, second=a2G, votes=vote_snapshot,
                clans={tags[i]: members[i] for i in range(len(tags))}, clanTeam=clan_team,
                border=border, botsTeamed=bots_teamed, how=how, size=size)


def load_decoded(mid):
    p = os.path.join(OUT, mid, 'replay_decoded.json')
    return json.load(open(p)) if os.path.exists(p) else None


def teams_for_match(mid, replay_of=None):
    d = load_decoded(replay_of or mid)
    if d is None or not d.get('colors'):
        return None, None
    s = d['settings']
    res = assign_teams(d['names'], d['colors'], s['humanCount'], s['numberTeams'], s['playerCount'])
    return d, res


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    mid = sys.argv[1]
    replay_of = sys.argv[sys.argv.index('--replay-of') + 1] if '--replay-of' in sys.argv else None
    d, res = teams_for_match(mid, replay_of)
    if d is None:
        print(f'{mid}: 没有录像头，无法重算队号')
        return 0
    names = d['names']
    H = d['settings']['humanCount']
    obs = {}
    with open(os.path.join(DATA, mid, 'results.csv')) as f:
        for r in csv.DictReader(f):
            if r['meId'] and r['teamMine']:
                obs[int(r['meId'])] = int(r['teamMine'])
    ok = sum(1 for p, t in obs.items() if res['team'][p] == t)
    print(f"{mid}: 真人 {H}，配置队数 {d['settings']['numberTeams']} → 实际队数 {res['teams']}，每队上限 {res['border']}，"
          f"队色序 {[COLOR_NAME[c] for c in res['lH'][1:res['teams'] + 1]]}，各色票数(红绿蓝黄紫青白黑) {res['votes']}，"
          f"AI 入队={res['botsTeamed']}，各队真人数 {res['size'][1:res['teams'] + 1]}")
    print(f"  战队：{ {k: (len(v), res['clanTeam'].get(k)) for k, v in res['clans'].items() if len(v) >= 2} }")
    print(f"  与 results.csv 的 teamMine 对照：{ok}/{len(obs)} 一致")
    for p, t in sorted(obs.items()):
        flag = 'OK ' if res['team'][p] == t else 'BAD'
        c = d['colors'][p]
        print(f"   {flag} id={p} {names[p]!r} 观察队={t} 重算队={res['team'][p]} 入队方式={res['how'][p]} "
              f"颜色=({4 * (c >> 12)},{4 * ((c >> 6) & 63)},{4 * (c & 63)}) 志愿={COLOR_NAME[res['first'][p] + 1]}/{COLOR_NAME[res['second'][p] + 1]}")
    if '--all' in sys.argv:
        for p in range(H):
            c = d['colors'][p]
            print(f"   id={p} {names[p]!r} 队={res['team'][p]} 方式={res['how'][p]} 颜色=({4 * (c >> 12)},{4 * ((c >> 6) & 63)},{4 * (c & 63)}) "
                  f"志愿={COLOR_NAME[res['first'][p] + 1]}/{COLOR_NAME[res['second'][p] + 1]}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
