#!/usr/bin/env python3
# match_digest.py — 把一局的“真相表”（engine_truth.cjs 用线上客户端重放得到）和我方日志合成一份复盘底稿。
#
# 用法：python3 scripts/match_digest.py <局号> [--ours p1,p2,…] > out/digest/<局号>.txt
#   先要有 tmp/truth/<局号>/（bash scripts/engine_truth_all.sh <局号>）
#   --ours 手工指定我方号的引擎编号（B 组日志名会轮换时用）
#
# 底稿里的每个数字都来自：引擎重放的状态数组 / 录像里被执行的指令 / 对局包里的日志表。
import csv, json, os, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = '/agent/repos/c136-data/bundles'
CHECK = [90, 270, 630, 1530, 3060, 4500, 6030, 7500]


def tsv(path):
    with open(path, encoding='utf8') as f:
        r = csv.reader(f, delimiter='\t', quoting=csv.QUOTE_NONE)
        head = next(r)
        return head, [row for row in r]


def bundle_csv(mid, name):
    p = os.path.join(DATA, mid, name)
    if not os.path.exists(p):
        return []
    with open(p, encoding='utf8') as f:
        return list(csv.DictReader(f))


def fmt(n):
    n = int(n)
    a = abs(n)
    if a >= 10000000:
        return f'{n/1e6:.1f}M'
    if a >= 100000:
        return f'{n/1e3:.0f}k'
    if a >= 10000:
        return f'{n/1e3:.1f}k'
    return str(n)


class Match:
    def __init__(self, mid, ours_override=None):
        self.mid = mid
        d = os.path.join(ROOT, 'tmp', 'truth', mid)
        self.meta = json.load(open(os.path.join(d, 'meta.json'), encoding='utf8'))
        self.ku = self.meta['info']['ku']
        self.ke = self.meta['info']['ke']
        self.last = self.meta['lastTick']
        self.step = self.meta['step']
        self.players = self.meta['players']
        self.team = {p['p']: p['team'] for p in self.players}
        self.name = {p['p']: p['name'] for p in self.players}
        self.ours = {int(k): v for k, v in self.meta['ours'].items()}
        if ours_override:
            self.ours = {p: self.name[p] for p in ours_override}
        self.our_ids = sorted(self.ours)
        tc = collections.Counter(self.team[p] for p in self.our_ids)
        self.our_team = tc.most_common(1)[0][0] if tc else 0
        self.teammates = [p for p in range(self.ku) if self.team[p] == self.our_team and self.our_team > 0]
        _, rows = tsv(os.path.join(d, 'state.tsv'))
        self.state = collections.defaultdict(dict)  # t -> p -> (terr, bal, atkOut, nOut, atkIn, nIn, boats, alive, st, debt)
        for r in rows:
            self.state[int(r[0])][int(r[1])] = tuple(int(float(x)) for x in r[2:])
        _, rows = tsv(os.path.join(d, 'team.tsv'))
        self.teamts = collections.defaultdict(dict)  # t -> team -> (terr, bal, alive, humansPlaying)
        for r in rows:
            self.teamts[int(r[0])][int(r[1])] = tuple(int(x) for x in r[2:])
        _, rows = tsv(os.path.join(d, 'our.tsv'))
        self.our = collections.defaultdict(dict)  # p -> t -> (terr, bal, atkOut, atkIn, nIn, boats)
        for r in rows:
            self.our[int(r[1])][int(r[0])] = tuple(int(float(x)) for x in r[2:])
        _, rows = tsv(os.path.join(d, 'flow.tsv'))
        self.flow = [(int(r[0]), int(r[1]), int(r[2]), int(r[3])) for r in rows]
        _, rows = tsv(os.path.join(d, 'cmd.tsv'))
        self.cmd = []
        for r in rows:
            c = dict(t=int(r[0]), sp=int(r[1]), id=int(r[2]), p=int(r[3]), a=int(r[4]), b=int(r[5]), bal0=int(r[6]), bal1=int(r[7]), terr0=int(r[8]))
            if r[9] != '':
                c.update(q=int(r[9]), balQ0=int(r[10]), balQ1=int(r[11]), terrQ=int(r[12]), used0=int(r[13]), used1=int(r[14]), cap=int(r[15]))
            c['sub'] = [s.split(':') for s in r[16].split(';')] if len(r) > 16 and r[16] else []
            self.cmd.append(c)
        _, rows = tsv(os.path.join(d, 'ev.tsv'))
        self.ev = [(int(r[0]), r[1], int(r[2]), r[3], r[4], r[5] if len(r) > 5 else '') for r in rows]
        _, rows = tsv(os.path.join(d, 'atk.tsv'))
        self.atk = [(int(r[0]), int(r[1]), int(r[2]), int(r[3])) for r in rows]
        self.results = bundle_csv(mid, 'results.csv')
        self.traj = bundle_csv(mid, 'traj.csv')
        self.events = bundle_csv(mid, 'events.csv')
        self.spawn = bundle_csv(mid, 'spawn.csv')
        self.opening = bundle_csv(mid, 'opening.csv')
        try:
            self.anom = json.load(open(os.path.join(DATA, mid, 'anomalies.json'), encoding='utf8'))
        except Exception:
            self.anom = {}
        try:
            self.card = json.load(open(os.path.join(DATA, mid, 'card.json'), encoding='utf8'))
        except Exception:
            self.card = {}
        self.samples = sorted(self.state)
        # 真人出局 / 清空 / 离场
        self.dead = {}   # p -> (t, terr, bal, detail)
        self.wiped = collections.defaultdict(list)
        self.left = {}
        for (t, kind, p, x, y, det) in self.ev:
            if kind == 'dead':
                self.dead[p] = (t, int(x), int(y), det)
            elif kind == 'wiped-keeps-boats':
                self.wiped[p].append((t, int(x), int(y), det))
            elif kind == 'state' and y == '2':
                self.left[p] = (t, det)
            elif kind == 'dead-other' and p not in self.dead:
                self.dead[p] = (t, int(x), int(y), det)

    def nm(self, p, short=True):
        if p == 512:
            return '无主地'
        if p >= self.ku:
            return f'AI#{p}'
        n = self.name[p]
        if p in self.ours:
            return n.replace('[APEX] ', '')
        n = n if len(n) <= 16 else n[:15] + '…'
        return f'{n}#{p}(队{self.team[p]})'

    def at(self, t):
        # 最近的采样拍（向下取）
        t = min(t, self.last)
        t = t - t % self.step
        while t not in self.state and t > 0:
            t -= self.step
        return t

    def flows(self, t0, t1):
        m = collections.Counter()
        for (t, a, b, px) in self.flow:
            if t0 < t <= t1:
                m[(a, b)] += px
        return m


def section(title):
    print()
    print('=' * 4 + ' ' + title + ' ' + '=' * 4)


def main():
    args = sys.argv[1:]
    mid = args[0]
    ours_override = None
    if '--ours' in args:
        ours_override = [int(x) for x in args[args.index('--ours') + 1].split(',')]
    M = Match(mid, ours_override)
    ku, ke = M.ku, M.ke
    info = M.meta['info']
    teams = sorted(set(M.team.values()))
    print(f'# {mid} 复盘底稿（真引擎重放 + 我方日志）')
    print(f'# 重算：bash scripts/engine_truth_all.sh {mid} && python3 scripts/match_digest.py {mid}')

    section('1 结构')
    tsz = collections.Counter(M.team.values())
    print(f'地图 {info["map"]}（{info["w"]}x{info["h"]}，陆地 {ke} 像素），真人 {ku}，全部玩家 {info["players"]}（其余是内置 AI），终局拍 {M.last}')
    print('各队真人数：' + '，'.join(f'队{t}={tsz[t]}' for t in teams) + f'；我方号 {len(M.our_ids)} 个，在队 {M.our_team}')
    other_tm = [p for p in M.teammates if p not in M.ours]
    print('同队的其他真人：' + ('，'.join(f'{M.name[p]}#{p}' for p in other_tm) if other_tm else '无'))
    card = M.card
    if card:
        o = card.get('outcome', {})
        print(f'对局卡：结果 {o.get("resultLabel")}，赢家队 {o.get("winnerTeam")}，对局卡终局拍 {o.get("endTick")}，我方号峰值占地 {o.get("peakSquadLandShare")}，主队最终占比 {o.get("ourFinalTeamShare")}')
    print('我方号（引擎编号 / 出生点 / 离最近队友、最近敌方真人的出生距离）：')
    sp = {p['p']: p['spawn'] for p in M.players}
    alive0 = [p for p in range(ku) if M.players[p]['box'][0] <= M.players[p]['box'][2]]
    for p in M.our_ids:
        x, y = sp[p]
        def dist(q):
            return ((sp[q][0] - x) ** 2 + (sp[q][1] - y) ** 2) ** 0.5
        allies = sorted((dist(q), q) for q in alive0 if q != p and M.team[q] == M.team[p] and M.team[p] > 0)
        foes = sorted((dist(q), q) for q in alive0 if q != p and (M.team[q] != M.team[p] or M.team[p] == 0))
        a = f'{allies[0][0]:.0f}（{M.nm(allies[0][1])}）' if allies else '-'
        f = f'{foes[0][0]:.0f}（{M.nm(foes[0][1])}）' if foes else '-'
        n60 = sum(1 for d, q in allies if d < 60)
        print(f'  {M.nm(p):8s} #{p:<3d} ({x},{y})  最近队友 {a}  60 像素内队友 {n60} 个  最近敌方真人 {f}')
    if M.results:
        print('results.csv：' + '；'.join(f'{r["bot"]} {r["event"]}/{r["result"]}@{r["tick"]} 名次{r["place"]} 领土{r["territory"]} 余额{r["balance"]}' for r in M.results))

    section('2 各队时间线（真引擎）')
    cps = [t for t in CHECK if t <= M.last] + [M.at(M.last)]
    print('占比 = 该队真人领土 / 全图陆地；余额单位 兵。AI 行是全部内置 AI 合计。')
    hdr = '拍      ' + ''.join(f'| 队{t} 占比 余额 在场 ' for t in teams if t > 0) + '| AI 占比 | 无主地占比'
    print(hdr)
    for t in cps:
        ts = M.teamts[M.at(t)]
        line = f'{t:<7d} '
        tot = 0
        for tm in teams:
            if tm == 0:
                continue
            v = ts.get(tm, (0, 0, 0, 0))
            tot += v[0]
            line += f'| {100*v[0]/ke:5.1f}% {fmt(v[1]):>6s} {v[3]:>2d}人 '
        ai = sum(v[0] for k, v in ts.items() if k >= 100)
        h0 = ts.get(0, (0, 0, 0, 0))[0]
        tot += ai + h0
        line += f'| {100*ai/ke:5.1f}% | {100*(ke-tot)/ke:5.1f}%'
        print(line)
    # 我方队占比峰值
    if M.our_team > 0:
        series = [(t, M.teamts[t].get(M.our_team, (0, 0, 0, 0))[0]) for t in M.samples]
        tp, vp = max(series, key=lambda x: x[1])
        print(f'我方队 {M.our_team} 占比峰值 {100*vp/ke:.1f}%（第 {tp} 拍）；终局 {100*series[-1][1]/ke:.1f}%')
        # 各队峰值
        for tm in teams:
            if tm in (0, M.our_team):
                continue
            s2 = [(t, M.teamts[t].get(tm, (0, 0, 0, 0))[0]) for t in M.samples]
            t2, v2 = max(s2, key=lambda x: x[1])
            print(f'  队 {tm} 占比峰值 {100*v2/ke:.1f}%（第 {t2} 拍），终局 {100*s2[-1][1]/ke:.1f}%')
    # 我方号合计
    print('我方号合计（只算我方号，不含同队其他真人）：')
    for t in cps:
        st = M.state[M.at(t)]
        terr = sum(st[p][0] for p in M.our_ids)
        bal = sum(st[p][1] for p in M.our_ids)
        alive = sum(1 for p in M.our_ids if st[p][7])
        tt = M.teamts[M.at(t)].get(M.our_team, (0, 0, 0, 0))
        print(f'  拍 {t:<5d} 在场 {alive:>2d} 领土 {terr:>7d}（全图 {100*terr/ke:4.1f}%，占本队 {100*terr/max(tt[0],1):3.0f}%） 余额 {fmt(bal):>7s}（占本队 {100*bal/max(tt[1],1):3.0f}%）')
    # 全场前 5
    for t in [x for x in (630, 1530, 3060, 4500, 6030) if x <= M.last] + [M.at(M.last)]:
        st = M.state[M.at(t)]
        top = sorted(range(ku), key=lambda p: -st[p][0])[:5]
        print(f'  拍 {t} 全场真人领土前五：' + '；'.join(f'{M.nm(p)} 领土{st[p][0]} 余额{fmt(st[p][1])}' for p in top))

    section('3 我方各号在检查拍的状态（领土/余额/密度，被攻兵=此刻别人压在它身上的在途进攻兵）')
    print('拍     ' + ''.join(f'| {M.nm(p):>20s} ' for p in M.our_ids))
    for t in cps:
        st = M.state[M.at(t)]
        line = f'{t:<6d} '
        for p in M.our_ids:
            v = st[p]
            if not v[7]:
                line += f'| {"-":>20s} '
            else:
                dens = v[1] / max(v[0], 1)
                extra = f' 被攻{fmt(v[4])}' if v[4] > 0 else ''
                line += f'| {v[0]:>6d}/{fmt(v[1]):>6s}/{dens:5.1f}{extra:<0s} '
        print(line)

    section('3b 出生指令、开局名次、内陆憋兵')
    # 出生：每个号在选点阶段被执行的出生指令条数、最后一条在第几步（共 spawnSteps 步）
    spn = collections.defaultdict(list)
    for c in M.cmd:
        if c['id'] == 0 and c['sp'] >= 0:
            spn[c['p']].append((c['sp'], c['a']))
    W = info['w']
    print(f'选点阶段共 {M.meta["spawnSteps"]} 步。我方号被执行的出生指令（条数 / 最后一条所在步 / 最后落点）：')
    cells = collections.Counter()
    for p in M.our_ids:
        v = spn.get(p, [])
        if v:
            px = v[-1][1]
            cells[px] += 1
            print(f'  {M.nm(p):8s} {len(v)} 条，最后在第 {v[-1][0]} 步，落点 ({px % W},{px // W})')
        else:
            print(f'  {M.nm(p):8s} 0 条（没有任何出生指令被执行，由引擎随机落点）')
    dup = [k for k, v in cells.items() if v > 1]
    if dup:
        print('  同一像素被多个我方号选中：' + '，'.join(f'({k % W},{k // W})×{cells[k]}' for k in dup))
    for t in (270, 630, 1080, 1530):
        if t > M.last:
            continue
        st = M.state[M.at(t)]
        alive = [p for p in range(ku) if st[p][7]]
        order = sorted(alive, key=lambda p: -st[p][0])
        rank = {p: i + 1 for i, p in enumerate(order)}
        terrs = sorted(st[p][0] for p in alive)
        med = terrs[len(terrs) // 2]
        foes = sorted(st[p][0] for p in alive if p not in M.ours)
        medf = foes[len(foes) // 2] if foes else 0
        bals = sorted(st[p][1] for p in alive if p not in M.ours)
        medb = bals[len(bals) // 2] if bals else 0
        ourt = sorted(st[p][0] for p in M.our_ids if st[p][7])
        ourb = sorted(st[p][1] for p in M.our_ids if st[p][7])
        print(f'拍 {t}：在场真人 {len(alive)}，其他真人领土中位 {medf} 余额中位 {fmt(medb)}；我方号领土中位 {ourt[len(ourt)//2] if ourt else 0} 余额中位 {fmt(ourb[len(ourb)//2]) if ourb else 0}；我方号名次 ' + ' '.join(f'{M.nm(p)}#{rank[p]}' for p in M.our_ids if p in rank))
    # 内陆憋兵：日志快照里 nb=0 且 neut=0 的拍数；其中密度≥95 的拍数
    print('内陆憋兵（日志每 90 拍一个快照；封死 = 没有任何非队友邻居也没有无主地）：')
    for p in M.our_ids:
        b = M.ours[p].replace('[APEX] ', '')
        rows = [r for r in M.traj if r['bot'] == b]
        boxed = [r for r in rows if r['nb'] == '0' and r['neut'] == '0' and int(r['t']) >= 630]
        hi = [r for r in boxed if float(r['dens']) >= 95]
        if not boxed:
            continue
        first = boxed[0]['t']; lastb = boxed[-1]['t']
        mx = max(boxed, key=lambda r: int(r['bal']))
        print(f'  {b:8s} 封死快照 {len(boxed)} 个（{first}~{lastb}），其中密度≥95 的 {len(hi)} 个；封死期间最高余额 {fmt(mx["bal"])}（拍 {mx["t"]}，领土 {mx["terr"]}）')

    section('4 我方队的大跌窗口（300 拍内队伍领土净跌最多的三段，互不重叠）')
    if M.our_team > 0:
        ser = {t: M.teamts[t].get(M.our_team, (0, 0, 0, 0))[0] for t in M.samples}
        cands = []
        for t in M.samples:
            if t - 300 in ser:
                cands.append((ser[t] - ser[t - 300], t - 300, t))
        cands.sort()
        chosen = []
        for d, a, b in cands:
            if d >= 0:
                break
            if all(b <= x or a >= y for _, x, y in chosen):
                chosen.append((d, a, b))
            if len(chosen) == 3:
                break
        for d, a, b in sorted(chosen, key=lambda x: x[1]):
            print(f'窗口 [{a}, {b}]：队伍领土 {ser[a]} → {ser[b]}（{d:+d}，全图占比 {100*ser[a]/ke:.1f}% → {100*ser[b]/ke:.1f}%）')
            fl = M.flows(a, b)
            tm = set(M.teammates)
            lost = collections.Counter()
            gained = collections.Counter()
            who = collections.Counter()
            for (x, y), px in fl.items():
                if x in tm and y not in tm:
                    lost[y] += px
                    who[x] += px
                if y in tm and x not in tm:
                    gained[x] += px
            print('  丢给：' + '；'.join(f'{M.nm(k)} {v}' for k, v in lost.most_common(6)))
            print('  丢地的是：' + '；'.join(f'{M.nm(k)} {v}' for k, v in who.most_common(6)))
            print('  同期拿到：' + '；'.join(f'从{M.nm(k)} {v}' for k, v in gained.most_common(5)))
            inc = collections.Counter()
            for c in M.cmd:
                if a < c['t'] <= b and c['id'] in (1,) and c['p'] not in tm:
                    for s in c['sub']:
                        if s[0] == 'atk' and int(s[1]) in tm:
                            inc[(c['p'], int(s[1]))] += int(s[2])
            print('  敌方真人对本队下的陆攻（进攻者→目标 兵）：' + '；'.join(f'{M.nm(k[0])}→{M.nm(k[1])} {fmt(v)}' for k, v in inc.most_common(8)))
            dd = [p for p in tm if p in M.dead and a < M.dead[p][0] <= b]
            if dd:
                print('  窗口内本队出局：' + '，'.join(f'{M.nm(p)}@{M.dead[p][0]}' for p in dd))

    section('5 我方号的出局链')
    for p in M.our_ids:
        evs = []
        if p in M.left:
            evs.append((M.left[p][0], '离场（变成不生息的 AI 号）', M.left[p][1]))
        for w in M.wiped[p]:
            evs.append((w[0], f'地和余额被清空但海上有船（领土 {w[1]} 余额 {w[2]}）', w[3]))
        if p in M.dead:
            evs.append((M.dead[p][0], f'出局（当时领土 {M.dead[p][1]} 余额 {M.dead[p][2]}）', M.dead[p][3]))
        if not evs:
            continue
        evs.sort()
        print(f'--- {M.nm(p)} #{p} ---')
        for t, what, det in evs:
            by = ''
            if 'by:' in det:
                parts = [x for x in det.split('by:')[1].split(',') if x]
                by = '；压在它身上的进攻者：' + '，'.join(f'{M.nm(int(a.split(":")[0]))} 剩余兵{fmt(a.split(":")[1])} 自身领土{a.split(":")[2]}' for a in parts) if parts else '；当时没有人在攻它'
            pk = det.split('peak:')[1].split(';')[0] if 'peak:' in det else '?'
            print(f'  第 {t} 拍 {what}，峰值线 {pk}{by}')
        tdead = evs[0][0] if evs[0][1].startswith('地和') or evs[0][1].startswith('出局') else (evs[1][0] if len(evs) > 1 else evs[0][0])
        tfirst = min(t for t, w, _ in evs if not w.startswith('离场')) if any(not w.startswith('离场') for _, w, _ in evs) else evs[0][0]
        o = M.our[p]
        print('  出局前轨迹（拍: 领土/余额/在外进攻兵/被攻兵）：' + '  '.join(f'{tfirst-k}: {o[tfirst-k][0]}/{fmt(o[tfirst-k][1])}/{fmt(o[tfirst-k][2])}/{fmt(o[tfirst-k][3])}' for k in (900, 600, 450, 300, 200, 100, 50, 20, 1) if tfirst - k in o))
        fl = M.flows(tfirst - 900, tfirst + M.step)
        took = collections.Counter()
        for (x, y), px in fl.items():
            if x == p:
                took[y] += px
        print('  最后 900 拍它的地被谁拿走：' + '；'.join(f'{M.nm(k)} {v}' for k, v in took.most_common(6)))
        inc = collections.defaultdict(lambda: [0, 0, 10**9, 0])
        for c in M.cmd:
            if tfirst - 900 < c['t'] <= tfirst and c['id'] == 1 and c['p'] != p:
                for s in c['sub']:
                    if s[0] == 'atk' and int(s[1]) == p:
                        v = inc[c['p']]
                        v[0] += 1; v[1] += int(s[2]); v[2] = min(v[2], c['t']); v[3] = max(v[3], c['t'])
        for (t, kind, pl, x, y, det) in M.ev:
            if tfirst - 900 < t <= tfirst and kind == 'land' and f'atk:{p}:' in det:
                v = inc[pl]
                v[0] += 1; v[1] += int(det.split(f'atk:{p}:')[1].split(';')[0]); v[2] = min(v[2], t); v[3] = max(v[3], t)
            if tfirst - 900 < t <= tfirst and kind == 'aiatk' and int(x) == p:
                v = inc[pl]
                v[0] += 1; v[1] += int(y); v[2] = min(v[2], t); v[3] = max(v[3], t)
        print('  最后 900 拍打它的出兵（含船登陆）：' + '；'.join(f'{M.nm(k)} {v[0]} 次共 {fmt(v[1])} 兵（{v[2]}~{v[3]}）' for k, v in sorted(inc.items(), key=lambda kv: -kv[1][1])[:6]))
        mine = collections.defaultdict(lambda: [0, 0])
        don = collections.defaultdict(lambda: [0, 0])
        boats = [0, 0]
        for c in M.cmd:
            if tfirst - 900 < c['t'] <= tfirst and c['p'] == p:
                if c['id'] == 1:
                    for s in c['sub']:
                        if s[0] == 'atk':
                            mine[int(s[1])][0] += 1; mine[int(s[1])][1] += int(s[2])
                elif c['id'] == 2 and 'q' in c:
                    don[c['q']][0] += 1; don[c['q']][1] += c['balQ1'] - c['balQ0']
                elif c['id'] in (3, 4):
                    for s in c['sub']:
                        if s[0] == 'boat':
                            boats[0] += 1; boats[1] += int(s[2])
        print('  最后 900 拍它自己的出兵：' + ('；'.join(f'打{M.nm(k)} {v[0]} 次 {fmt(v[1])} 兵' for k, v in sorted(mine.items(), key=lambda kv: -kv[1][1])[:6]) or '无')
              + '；捐出：' + ('；'.join(f'给{M.nm(k)} {v[0]} 笔到账 {fmt(v[1])}' for k, v in don.items()) or '无')
              + (f'；发船 {boats[0]} 条 {fmt(boats[1])} 兵' if boats[0] else ''))
        rec = collections.defaultdict(lambda: [0, 0])
        for c in M.cmd:
            if tfirst - 900 < c['t'] <= tfirst and c['id'] == 2 and c.get('q') == p:
                rec[c['p']][0] += 1; rec[c['p']][1] += c['balQ1'] - c['balQ0']
        print('  最后 900 拍它收到的捐款：' + ('；'.join(f'{M.nm(k)} {v[0]} 笔 {fmt(v[1])}' for k, v in rec.items()) or '无'))
        tr = [r for r in M.traj if r['bot'] == M.ours[p].replace('[APEX] ', '') and int(r['t']) <= tfirst][-4:]
        if tr:
            print('  日志最后几个快照（拍 领土 余额 密度 邻敌数 邻无主）：' + '  '.join(f'{r["t"]}:{r["terr"]}/{r["bal"]}/{r["dens"]}/nb{r["nb"]}/neut{r["neut"]}' for r in tr))

    section('6 余额骤降对账（对局包标的 DROP30：90 拍内余额跌 30% 以上）')
    drops = M.anom.get('drop30Events', []) if isinstance(M.anom, dict) else []
    idof = {v.replace('[APEX] ', ''): k for k, v in M.ours.items()}
    cls = collections.Counter()
    lines = []
    for dv in drops:
        b = dv['bot']
        if b not in idof:
            continue
        p = idof[b]
        t0, t1 = dv['t0'], dv['t1']
        atk = collections.Counter(); natk = 0
        don = collections.Counter(); ndon = 0; fee = 0; boat = 0; nboat = 0; refund = 0
        for c in M.cmd:
            if c['p'] != p or not (t0 <= c['t'] < t1):
                continue
            if c['id'] == 1:
                for s in c['sub']:
                    if s[0] == 'atk':
                        atk[int(s[1])] += int(s[2]); natk += 1
                        fee += c['bal0'] - c['bal1'] - int(s[2])
            elif c['id'] == 2 and 'q' in c:
                got = c['balQ1'] - c['balQ0']
                don[c['q']] += got; ndon += 1
                fee += c['bal0'] - c['bal1'] - got
            elif c['id'] in (3, 4):
                for s in c['sub']:
                    if s[0] == 'boat':
                        boat += int(s[2]); nboat += 1
                        fee += c['bal0'] - c['bal1'] - int(s[2])
            elif c['id'] == 5:
                refund += c['bal1'] - c['bal0']
        o = M.our[p]
        b0 = o[t0][1] if t0 in o else dv['bal0']
        b1 = o[t1][1] if t1 in o else dv['bal1']
        drop = b0 - b1
        sa, sd = sum(atk.values()), sum(don.values())
        parts = []
        if sa:
            parts.append('陆攻 ' + '，'.join(f'{M.nm(k)} {fmt(v)}' for k, v in atk.most_common(3)) + f'（{natk} 条）')
        if sd:
            parts.append('捐款到账 ' + '，'.join(f'{M.nm(k)} {fmt(v)}' for k, v in don.most_common(3)) + f'（{ndon} 笔）')
        if boat:
            parts.append(f'装船 {fmt(boat)}（{nboat} 条）')
        if fee:
            parts.append(f'手续费/税 {fmt(fee)}')
        if refund:
            parts.append(f'撤兵退回 {fmt(refund)}')
        main = max([('陆攻', sa), ('捐款', sd), ('装船', boat), ('挨打或其他', drop - sa - sd - boat - fee)], key=lambda x: x[1])[0]
        if sa:
            tgt = atk.most_common(1)[0][0]
            main = '陆攻-无主地' if tgt == 512 else ('陆攻-内置AI' if tgt >= ku else '陆攻-真人') if main == '陆攻' else main
        cls[main] += 1
        nb = max((c for c in [0]), default=0)
        lines.append(f'  {b:8s} [{t0},{t1}] 余额 {fmt(b0)}→{fmt(b1)}（-{100*drop/max(b0,1):.0f}%） 领土 {dv["terr0"]}→{dv["terr1"]}：' + '；'.join(parts) + f' ⇒ {main}')
    print(f'共 {len(lines)} 次；主因分类：' + '，'.join(f'{k} {v}' for k, v in cls.most_common()))
    lines.sort(key=lambda l: -float(l.split('（-')[1].split('%')[0]))
    for l in lines[:14]:
        print(l)
    if len(lines) > 14:
        print(f'  …其余 {len(lines)-14} 次略（按跌幅排序）')
    # 单批清仓：同一拍同一号 3 条以上出兵指令
    batches = collections.defaultdict(list)
    for c in M.cmd:
        if c['p'] in M.ours and c['id'] in (1, 2, 3) and c['sp'] < 0:
            batches[(c['t'], c['p'])].append(c)
    big = [(k, v) for k, v in batches.items() if len(v) >= 3]
    drained = [(k, v) for k, v in big if v[-1]['bal1'] < 0.4 * max(v[0]['bal0'], 1)]
    noop = sum(1 for c in M.cmd if c['p'] in M.ours and c['id'] == 1 and c['sp'] < 0 and not c['sub'])
    nall = sum(1 for c in M.cmd if c['p'] in M.ours and c['id'] == 1 and c['sp'] < 0)
    print(f'同一拍内同一号落地 3 条以上出兵/捐款指令的批次：{len(big)} 个，其中把余额打到四成以下的 {len(drained)} 个（下面列余额最大的 14 个）')
    print(f'我方陆攻指令 {nall} 条，其中 {noop} 条被录进录像但没有产生进攻（不扣兵）')
    for (t, p), v in sorted(drained, key=lambda kv: -kv[1][0]['bal0'])[:14]:
        b0 = v[0]['bal0']; b1 = v[-1]['bal1']
        kinds = collections.Counter({1: '陆攻', 2: '捐款', 3: '船'}[c['id']] for c in v)
        tg = collections.Counter()
        for c in v:
            for s in c['sub']:
                if s[0] == 'atk':
                    tg[M.nm(int(s[1]))] += int(s[2])
            if c['id'] == 2 and 'q' in c:
                tg['捐给' + M.nm(c['q'])] += c['balQ1'] - c['balQ0']
        print(f'  拍 {t} {M.nm(p)}：{len(v)} 条（' + '，'.join(f'{k}{n}' for k, n in kinds.items()) + f'），余额 {fmt(b0)}→{fmt(b1)}（剩 {100*b1/max(b0,1):.0f}%），去向 ' + '；'.join(f'{k} {fmt(n)}' for k, n in tg.most_common(4)))

    section('7 捐款真账（发出 = 日志里的调度；落地 = 录像里被执行的捐款指令；到账额来自引擎）')
    sent = collections.Counter(); sent_kind = collections.defaultdict(collections.Counter)
    for e in M.events:
        if e['type'] in ('DISPATCH', 'DONATE') and e['bot'] in idof:
            sent[idof[e['bot']]] += 1
            sent_kind[idof[e['bot']]][e['kind']] += 1
    done = collections.defaultdict(lambda: [0, 0, 0])
    recv = collections.defaultdict(lambda: [0, 0])
    pair = collections.defaultdict(lambda: [0, 0])
    for c in M.cmd:
        if c['id'] == 2 and 'q' in c and c['sp'] < 0:
            got = c['balQ1'] - c['balQ0']
            if c['p'] in M.ours:
                d = done[c['p']]; d[0] += 1; d[1] += got; d[2] += c['bal0'] - c['bal1'] - got
                pair[(c['p'], c['q'])][0] += 1; pair[(c['p'], c['q'])][1] += got
            if c['q'] in M.ours or c['p'] in M.ours:
                r = recv[c['q']]; r[0] += 1; r[1] += got
    print('号        发出  落地  到账合计   税合计   税/到账   种类')
    for p in M.our_ids:
        d = done[p]
        kinds = '，'.join(f'{k}{v}' for k, v in sent_kind[p].most_common(4))
        ratio = f'{100*d[2]/d[1]:.0f}%' if d[1] else '-'
        print(f'{M.nm(p):8s} {sent[p]:>5d} {d[0]:>5d} {fmt(d[1]):>9s} {fmt(d[2]):>8s} {ratio:>7s}   {kinds}')
    ts, td = sum(sent.values()), sum(d[0] for d in done.values())
    print(f'合计：发出 {ts}，落地 {td}（{100*td/max(ts,1):.0f}%），到账 {fmt(sum(d[1] for d in done.values()))}，税 {fmt(sum(d[2] for d in done.values()))}')
    print('收款方（我方号捐出的 + 我方号收到的）：' + '；'.join(f'{M.nm(k)} {v[0]} 笔 {fmt(v[1])}' for k, v in sorted(recv.items(), key=lambda kv: -kv[1][1])[:8]))
    # 捐款落地按时段
    seg = collections.Counter(); segamt = collections.Counter()
    for c in M.cmd:
        if c['id'] == 2 and 'q' in c and c['p'] in M.ours and c['sp'] < 0:
            k = '<1071' if c['t'] < 1071 else '<2142' if c['t'] < 2142 else '<3213' if c['t'] < 3213 else '<4284' if c['t'] < 4284 else '≥4284'
            seg[k] += 1; segamt[k] += c['balQ1'] - c['balQ0']
    segs = collections.Counter()
    for e in M.events:
        if e['type'] in ('DISPATCH', 'DONATE') and e['bot'] in idof:
            t = int(e['t'])
            k = '<1071' if t < 1071 else '<2142' if t < 2142 else '<3213' if t < 3213 else '<4284' if t < 4284 else '≥4284'
            segs[k] += 1
    print('按时段（发出/落地/到账）：' + '；'.join(f'{k} {segs[k]}/{seg[k]}/{fmt(segamt[k])}' for k in ('<1071', '<2142', '<3213', '<4284', '≥4284')))
    # 船移交
    ho = collections.defaultdict(lambda: [0, 0, 0])
    for (t, kind, pl, x, y, det) in M.ev:
        if kind == 'land' and 'give:' in det:
            for s in det.split('|')[1].split(';'):
                f = s.split(':')
                if f[0] == 'give':
                    k = (pl, int(f[1]))
                    ho[k][0] += 1; ho[k][1] += int(f[2]); ho[k][2] += int(f[3])
    mine_ho = {k: v for k, v in ho.items() if k[0] in M.ours or k[1] in M.ours}
    if mine_ho:
        print('船靠在队友地上移交（涉及我方号）：' + '；'.join(f'{M.nm(k[0])}→{M.nm(k[1])} {v[0]} 条 送 {fmt(v[1])} 到账 {fmt(v[2])}（蒸发 {fmt(v[1]-v[2])}）' for k, v in sorted(mine_ho.items(), key=lambda kv: -kv[1][1])))
    else:
        print('船靠在队友地上移交（涉及我方号）：无')
    # 全场捐款使用：按队
    byteam = collections.defaultdict(lambda: [0, 0])
    for c in M.cmd:
        if c['id'] == 2 and 'q' in c and c['sp'] < 0 and c['p'] < ku:
            byteam[M.team[c['p']]][0] += 1; byteam[M.team[c['p']]][1] += c['balQ1'] - c['balQ0']
    print('全场各队落地的捐款：' + '；'.join(f'队{k} {v[0]} 笔 {fmt(v[1])}' for k, v in sorted(byteam.items())))
    ai = collections.defaultdict(lambda: [0, 0])
    for (t, kind, pl, x, y, det) in M.ev:
        if kind == 'aigift' and int(x) < ku and M.team[int(x)] == M.our_team:
            ai[(pl, int(x))][0] += 1; ai[(pl, int(x))][1] += int(y)
    if ai:
        print('离场号/AI 赠送给本队：' + '；'.join(f'{M.nm(k[0])}→{M.nm(k[1])} {v[0]} 次 {fmt(v[1])}' for k, v in sorted(ai.items(), key=lambda kv: -kv[1][1])[:8]))

    section('8 我方各号全局出兵去向（陆攻兵力按目标类别；括号内是同期从该类目标净拿到的地）')
    allfl = M.flows(-1, M.last + 1)
    print('号        无主地            内置AI            敌方真人          撤兵退回   发船(条/兵)   船结果')
    for p in M.our_ids:
        cat = collections.Counter(); catn = collections.Counter(); refund = 0; nb = 0; bt = 0
        for c in M.cmd:
            if c['p'] != p or c['sp'] >= 0:
                continue
            if c['id'] == 1:
                for s in c['sub']:
                    if s[0] == 'atk':
                        k = 'N' if int(s[1]) == 512 else 'A' if int(s[1]) >= ku else 'H'
                        cat[k] += int(s[2]); catn[k] += 1
            elif c['id'] == 5 and c['a'] <= 512:
                refund += c['bal1'] - c['bal0']
            elif c['id'] in (3, 4):
                for s in c['sub']:
                    if s[0] == 'boat':
                        nb += 1; bt += int(s[2])
        g = collections.Counter()
        for (x, y), px in allfl.items():
            if y == p:
                g['N' if x == 512 else 'A' if x >= ku else 'H'] += px
            if x == p:
                g['-N' if y == 512 else '-A' if y >= ku else '-H'] += px
        res = collections.Counter()
        for (t, kind, pl, x, y, det) in M.ev:
            if pl == p and kind in ('land', 'sunk', 'boatend'):
                if kind == 'land':
                    s = det.split('|')[1]
                    res['登陆陆攻' if s.startswith('atk') else '移交队友' if s.startswith('give') else '回自己地/作废'] += 1
                else:
                    res['沉没' if kind == 'sunk' else '其他'] += 1
        print(f'{M.nm(p):8s} {fmt(cat["N"]):>7s}({g["N"]:>6d}) {fmt(cat["A"]):>7s}({g["A"]:>6d}) {fmt(cat["H"]):>7s}({g["H"]:>6d}，被拿走{g["-H"]+g["-A"]:>6d}) {fmt(refund):>8s}   {nb}/{fmt(bt)}   ' + '，'.join(f'{k}{v}' for k, v in res.items()))

    section('9 对手与赢家')
    endt = M.at(M.last)
    ts = M.teamts[endt]
    rank = sorted(((v[0], k) for k, v in ts.items() if 0 < k < 100), reverse=True)
    print('终局各队领土：' + '；'.join(f'队{k} {v}（{100*v/ke:.1f}%）' for v, k in rank))
    if rank:
        win = rank[0][1]
        st = M.state[endt]
        top = sorted((p for p in range(ku) if M.team[p] == win), key=lambda p: -st[p][0])[:6]
        print(f'领土最多的队 {win} 的前六名：' + '；'.join(f'{M.nm(p)} 领土{st[p][0]} 余额{fmt(st[p][1])}' for p in top))
    # 真人出局表
    print('真人出局顺序（拍 号 队 当时领土/余额 主要进攻者）：')
    for p, (t, terr, bal, det) in sorted(M.dead.items(), key=lambda kv: kv[1][0]):
        if p >= ku or t == 0:
            continue
        by = ''
        if 'by:' in det:
            parts = [x for x in det.split('by:')[1].split(',') if x]
            if parts:
                best = max(parts, key=lambda a: int(a.split(':')[1]))
                by = f'{M.nm(int(best.split(":")[0]))} 压兵{fmt(best.split(":")[1])}'
        mark = ' ←我方' if p in M.ours else ''
        print(f'  {t:>5d} {M.nm(p)} {terr}/{fmt(bal)} {by}{mark}')
    # 各队出兵结构
    print('各队真人全局指令结构（陆攻兵力：无主地/内置AI/敌方真人；船；捐款）：')
    for tm in teams:
        if tm == 0 and not any(M.team[p] == 0 for p in range(ku)):
            continue
        cat = collections.Counter(); nb = 0; bt = 0; nd = 0; da = 0
        for c in M.cmd:
            if c['p'] >= ku or M.team[c['p']] != tm or c['sp'] >= 0:
                continue
            if c['id'] == 1:
                for s in c['sub']:
                    if s[0] == 'atk':
                        cat['N' if int(s[1]) == 512 else 'A' if int(s[1]) >= ku else 'H'] += int(s[2])
            elif c['id'] in (3, 4):
                for s in c['sub']:
                    if s[0] == 'boat':
                        nb += 1; bt += int(s[2])
            elif c['id'] == 2 and 'q' in c:
                nd += 1; da += c['balQ1'] - c['balQ0']
        print(f'  队{tm}：陆攻 {fmt(cat["N"])}/{fmt(cat["A"])}/{fmt(cat["H"])}；船 {nb} 条 {fmt(bt)}；捐款 {nd} 笔 {fmt(da)}')

    section('10 投票与离场')
    votes = [c for c in M.cmd if (c['id'] == 5 and c['a'] == 513) or c['id'] == 7]
    for c in votes[:40]:
        print(f'  拍 {c["t"]} {M.nm(c["p"])} ' + ('发起投票' if c['id'] == 5 else f'投票 {c["a"]}'))
    if not votes:
        print('  无投票')
    lv = [(t, p, det) for p, (t, det) in M.left.items()]
    print('离场（真人变成不生息的 AI 号）：' + ('；'.join(f'{M.nm(p)}@{t}（{det}）' for t, p, det in sorted(lv)[:30]) or '无'))


if __name__ == '__main__':
    main()
