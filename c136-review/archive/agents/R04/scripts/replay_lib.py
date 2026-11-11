#!/usr/bin/env python3
"""replay_lib.py — 解码对局录像 replay.txt（游戏“分享录像”字符串），给出全场每一条被引擎接受的指令和它生效的拍号。

依据（本机 2.17.4 线上客户端）：
  * 记录器 aYp（bC.rg）：指令处理函数在全部校验通过之后才调用 bC.rg.rh(id, player, a, b) 记一笔；
    每拍结束 bC.ee() 记一个“拍”。所以录像里只有被接受的指令（陆攻 id=1 例外：记账在最后一步校验之前）。
  * 录像头与指令表的位布局与 /agent/repos/c136-data/src/sim/tools/c102-replay-lib.mjs 的 decodeReplay 相同（此处为 Python 重写）。
  * 选出生点阶段：每个服务器包记一步，共 a7a+1 步（真人 <=2 → 30，<=50 → 40，否则 50）；之后每拍一步，拍号从 0 起。
    一条指令的“拍号 t”表示它在第 t 拍的结算（n8）之前执行。

指令号：0 选出生点(a=格子下标)  1 陆攻(a=比例 0..1023, b=目标 512=无主地)  2 捐款(a=比例, b=收款人)
        3 发船(a=比例, b=水格*8+方向)  4 追船/召回(a=比例或 849=召回, b=船号)  5 撤回进攻(a=目标；513=发起和平投票)
        6 表情(a)  7 投票(a=1 赞成 0 反对)  8 认输/离开  9 掉线离场  10 越山进攻(a=比例*1024+目标, b=格子)

用法（库）：from replay_lib import load_replay
用法（命令行）：python3 replay_lib.py <replay.txt> 打印摘要
"""
import json
import sys

TEAM_COLOURS = [(128, 128, 128), (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255), (255, 255, 255), (0, 0, 0)]
TEAM_COLOUR_NAMES = ['灰(无队)', '红', '绿', '蓝', '黄', '品红', '青', '白', '黑']


def g0(a, b):
    """引擎的整数除法 c1.g0：floor((a+0.5)/b)。"""
    return int((a + 0.5) // b)


class Bits:
    def __init__(self, text):
        s = text.strip()
        eq = s.find('=')
        if eq >= 0:
            s = s[eq + 1:]
        vals = []
        for ch in s:
            c = ord(ch)
            if 48 <= c <= 57:
                v = c - 48 + 1
            elif 65 <= c <= 90:
                v = c - 65 + 11
            elif 97 <= c <= 122:
                v = c - 97 + 38
            elif c == 95:
                v = 37
            else:
                v = 0
            vals.append(v)
        self.n = 6 * len(vals)
        big = 0
        for v in vals:
            big = (big << 6) | v
        self.big = big
        self.pos = 0

    def take(self, size):
        if size == 0:
            return 0
        shift = self.n - self.pos - size
        self.pos += size
        if shift < 0:
            # 越界：按 0 补（与 JS 版读到数组外得到 0 一致）
            return (self.big << (-shift)) & ((1 << size) - 1)
        return (self.big >> shift) & ((1 << size) - 1)

    def string(self, lenbits):
        n = self.take(lenbits)
        units = [self.take(16) for _ in range(n)]
        # 名字按 UTF-16 码元存；成对的代理项合成一个字符，落单的代理项换成 U+FFFD
        return b''.join(u.to_bytes(2, 'little') for u in units).decode('utf-16-le', errors='replace')

    def array(self, lenbits, itembits, minlen):
        fe = self.take(lenbits)
        if not fe:
            return None
        out = [self.take(itembits) for _ in range(fe)]
        if len(out) < minlen and out[-1]:
            out += [out[-1]] * (minlen - len(out))
        elif len(out) < minlen:
            out += [0] * (minlen - len(out))
        return out

    def strings(self, lenbits, strlenbits, minlen):
        fe = self.take(lenbits)
        if not fe:
            return None
        out = [self.string(strlenbits) for _ in range(fe)]
        if len(out) < minlen:
            out += [out[-1]] * (minlen - len(out))
        return out


def decode(text):
    b = Bits(text)
    hdr = {'rVersion': b.take(12), 'checksum': b.take(12), 'statedSize': b.take(31)}
    vu = {}
    vu['mapType'] = b.take(2)
    vu['mapProceduralIndex'] = b.take(8)
    vu['mapRealisticIndex'] = b.take(8)
    vu['mapSeed'] = b.take(14)
    vu['mapName'] = b.string(5)
    if vu['mapType'] == 2:
        n = b.take(30)
        b.pos += 6 * n
    for k, n in [('passableWater', 1), ('passableMountains', 1), ('playerCount', 10), ('humanCount', 10), ('selectedPlayer', 9), ('gameMode', 1),
                 ('playerMode', 2), ('battleRoyaleMode', 2), ('numberTeams', 4), ('isZombieMode', 1), ('isContest', 1), ('isReplay', 1)]:
        vu[k] = b.take(n)
    vu['elo'] = b.array(2, 14, 2)
    vu['colorsType'] = b.take(1)
    vu['colorsPersonalized'] = b.take(1)
    vu['colorsData'] = b.array(10, 18, 512)
    vu['selectableColor'] = b.take(1)
    vu['teamPlayerCount'] = b.array(4, 10, 9)
    vu['neutralBots'] = b.take(1)
    vu['botDifficultyType'] = b.take(2)
    vu['botDifficultyValue'] = b.take(4)
    vu['botDifficultyTeam'] = b.array(4, 4, 9)
    vu['botDifficultyData'] = b.array(10, 4, 512)
    vu['spawningType'] = b.take(2)
    vu['spawningSeed'] = b.take(14)
    vu['spawningData'] = b.array(11, 12, 1024)
    vu['selectableSpawn'] = b.take(1)
    vu['playerNamesType'] = b.take(2)
    vu['playerNamesData'] = b.strings(10, 5, 512)
    vu['selectableName'] = b.take(1)
    for p in ('a', 't', 'i'):
        vu[p + 'IncomeType'] = b.take(2)
        vu[p + 'IncomeValue'] = b.take(8)
        vu[p + 'IncomeData'] = b.array(10, 8, 512)
    vu['sResourcesType'] = b.take(2)
    vu['sResourcesValue'] = b.take(11)
    vu['sResourcesData'] = b.array(10, 11, 512)
    vu['nA'] = b.array(10, 30, 0)
    ek = b.take(5)
    ncmd = b.take(30)
    nrun = b.take(30)
    cmds = []
    for _ in range(ncmd):
        cid = b.take(4)
        player = b.take(9)
        a = c = 0
        if cid == 0:
            a = b.take(22)
        elif cid == 1:
            a = b.take(10)
            c = b.take(10)
        elif cid == 2:
            a = b.take(10)
            c = b.take(9)
        elif cid == 3:
            a = b.take(10)
            c = b.take(27)
        elif cid == 4:
            a = b.take(10)
            c = b.take(16)
        elif cid in (5, 6):
            a = b.take(10)
        elif cid == 7:
            a = b.take(1)
        elif cid == 10:
            a = b.take(20)
            c = b.take(22)
        cmds.append((cid, player, a, c))
    runs = []
    for _ in range(nrun):
        flag = b.take(1)
        cnt = b.take(ek)
        runs.append((flag, cnt))
    return hdr, vu, cmds, runs, {'bitsUsed': b.pos, 'bitsTotal': b.n}


def timeline(vu, cmds, runs):
    """给每条指令配上步号和拍号。返回 (rows, total_steps, spawn_steps)。
    rows: (step, tick, id, player, a, b)；tick<0 表示选出生点阶段（-1 - 剩余步数 不重要，统一记 -1）。"""
    H = vu['humanCount']
    spawn_steps = 0
    if vu['selectableSpawn']:
        spawn_steps = (30 if H <= 2 else 40 if H <= 50 else 50) + 1
    rows = []
    step = 0
    ci = 0
    for flag, cnt in runs:
        if flag:
            tick = step - spawn_steps
            for k in range(cnt):
                cid, player, a, c = cmds[ci + k]
                rows.append((step, tick if tick >= 0 else -1, cid, player, a, c))
            ci += cnt
            step += 1
        else:
            step += cnt
    return rows, step, spawn_steps


def clan_tag(name):
    a = name.find('[')
    if a < 0:
        return None
    b = name.find(']')
    if 1 < b - a <= 8:
        return name[a + 1:b].upper().strip()
    return None


def assign_teams(ku, nominal, colors, names):
    """组队分配（引擎 dP.ee 的转述；与线上原文的一致性由 scripts/live-rules-check.cjs 的 T 组核对，3000 个随机大厅 0 不一致）。
    返回 dict：teams（参与分配的队数）、fX（每个真人的队号 1..teams）、rank（rank[队号] = 颜色号 1..8）、cap（每队人数上限）、clans。"""
    T = nominal
    first = [0] * ku
    second = [0] * ku
    votes = [0] * 8
    for p in range(ku - 1, -1, -1):
        c = colors[p]
        rgb = (4 * (c >> 12), 4 * ((c >> 6) & 63), 4 * (c & 63))
        d = [abs(rgb[0] - TEAM_COLOURS[k + 1][0]) + abs(rgb[1] - TEAM_COLOURS[k + 1][1]) + abs(rgb[2] - TEAM_COLOURS[k + 1][2]) for k in range(8)]
        best = 768
        for ft in range(7, -1, -1):
            e = (ft + p) % 8
            if d[e] < best:
                best = d[e]
                first[p] = e
        votes[first[p]] += 4
        best = 768
        for ft in range(7, -1, -1):
            e = (ft + p) % 8
            if d[e] < best and e != first[p]:
                best = d[e]
                second[p] = e
        votes[second[p]] += 1
    rank = [0] * 9
    v = [x + 1 for x in votes]
    for r in range(1, 9):
        lr = 0
        for ft in range(1, 8):
            if v[ft] > v[lr]:
                lr = ft
        v[lr] = 0
        rank[r] = lr + 1
    tags, members = [], []
    biggest = 0
    for p in range(ku):
        t = clan_tag(names[p])
        if t is None:
            continue
        k = -1
        for j in range(len(tags) - 1, -1, -1):
            if tags[j] == t:
                k = j
                break
        if k < 0:
            tags.append(t)
            members.append([p])
            biggest = max(biggest, 1)
        else:
            members[k].append(p)
            biggest = max(biggest, len(members[k]))
    while T > 2 and biggest > g0(ku, T):
        T -= 1
    fX = [0] * ku
    size = [0] * 9
    done = [False] * len(tags)
    for _ in range(len(tags)):
        fc = -1
        for j in range(len(tags) - 1, -1, -1):
            if not done[j] and (fc == -1 or len(members[j]) > len(members[fc])):
                fc = j
        sp = [1] * 8
        for p in members[fc]:
            sp[first[p]] += 3
            sp[second[p]] += 1
        for _attempt in range(8):
            e = fc % 8
            for j in range(7, -1, -1):
                if sp[j] > sp[e]:
                    e = j
            team = -1
            for j in range(T, 0, -1):
                if rank[j] == e + 1:
                    team = j
                    break
            sp[e] = 0
            if team == -1:
                continue
            bigger = sum(1 for j in range(T, 0, -1) if size[team] > size[j])
            if bigger == T - 1:
                continue
            for p in members[fc]:
                size[team] += 1
                fX[p] = team
            break
        done[fc] = True
    cap = g0(ku, T) + (1 if ku % T > 0 else 0)
    rank_of = [0] * 10
    for r in range(8, 0, -1):
        rank_of[rank[r]] = r
    for p in range(ku):
        tv = rank_of[first[p] + 1]
        if fX[p] == 0 and tv <= T and size[tv] < cap:
            size[tv] += 1
            fX[p] = tv
    for p in range(ku):
        tv = rank_of[second[p] + 1]
        if fX[p] == 0 and tv <= T and size[tv] < cap:
            size[tv] += 1
            fX[p] = tv
    for t in range(T, 0, -1):
        for p in range(ku - 1, -1, -1):
            if size[t] >= cap:
                break
            if fX[p] == 0:
                size[t] += 1
                fX[p] = t
    return {'teams': T, 'fX': fX, 'rank': rank, 'cap': cap, 'first': first, 'second': second,
            'clans': {tags[i]: members[i] for i in range(len(tags))}, 'size': size[:T + 1]}


def load_replay(path):
    text = open(path, encoding='utf8').read()
    hdr, vu, cmds, runs, bits = decode(text)
    rows, steps, spawn_steps = timeline(vu, cmds, runs)
    H = vu['humanCount']
    names = (vu['playerNamesData'] or [''] * 512)[:H]
    colors = (vu['colorsData'] or [0] * 512)[:H]
    game_mode = vu['gameMode']
    info = {'hdr': hdr, 'vu': vu, 'rows': rows, 'steps': steps, 'spawnSteps': spawn_steps, 'ticks': steps - spawn_steps,
            'H': H, 'P': vu['playerCount'], 'names': names, 'colors': colors, 'bits': bits}
    # 队伍：仅团队局（gameMode==1 且非僵尸）。lC = numberTeams-2 < 7。
    if game_mode == 1 and not vu['isZombieMode'] and vu['numberTeams'] >= 2:
        info['teams'] = assign_teams(H, vu['numberTeams'], colors, names)
    else:
        info['teams'] = None
    return info


if __name__ == '__main__':
    if sys.argv[1] == '--teams-json':
        # 给重放脚本用：真人队号、参与分配的队数、内置 AI 是否无队（队数 < 8 时内置 AI 都在 0 队）
        r = load_replay(sys.argv[2])
        t = r['teams']
        print(json.dumps({'H': r['H'], 'nominal': r['vu']['numberTeams'], 'teams': t['teams'] if t else 0, 'fX': t['fX'] if t else [],
                          'botsTeamless': bool(t and t['teams'] < 8), 'names': r['names']}, ensure_ascii=False))
        sys.exit(0)
    r = load_replay(sys.argv[1])
    vu = r['vu']
    print(json.dumps({k: vu[k] for k in ('mapType', 'mapProceduralIndex', 'mapRealisticIndex', 'mapSeed', 'mapName', 'passableWater', 'passableMountains', 'playerCount', 'humanCount',
                                         'selectedPlayer', 'gameMode', 'playerMode', 'battleRoyaleMode', 'numberTeams', 'isZombieMode', 'isContest', 'selectableSpawn',
                                         'botDifficultyType', 'botDifficultyValue', 'neutralBots', 'sResourcesType', 'aIncomeType', 'tIncomeType', 'iIncomeType')}, ensure_ascii=False))
    print('hdr', r['hdr'], 'bits', r['bits'], 'steps', r['steps'], 'spawnSteps', r['spawnSteps'], 'ticks', r['ticks'], 'cmds', len(r['rows']))
    from collections import Counter
    print('指令号计数', sorted(Counter(x[2] for x in r['rows']).items()))
    if r['teams']:
        t = r['teams']
        print('参与分配的队数', t['teams'], '每队上限', t['cap'], '各队人数', t['size'], '队号→颜色', [TEAM_COLOUR_NAMES[c] for c in t['rank'][:t['teams'] + 1]])
        print('战队', {k: len(v) for k, v in t['clans'].items()})
        for p in range(r['H']):
            print(p, t['fX'][p], repr(r['names'][p]))
