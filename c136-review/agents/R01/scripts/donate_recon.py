#!/usr/bin/env python3
"""donate_recon.py — B 组（c110）日志里的 [HL-DONATE]/[HL-ASSIST] 行 对 录像里落地的捐兵/助攻令（逐条对账）。
c110 没有 HL-DISPATCH（调度器），捐兵只走 Policy.tryDonateToTeammate（squad rescue donate L4438 / surplus donate L4490 / 10% squad-rescue poke L4450）。
用法：python3 scripts/donate_recon.py <局号> [--win 800] [--doom 400]
对每条日志行（号、本地拍 t、对象席位、pct）在录像里找同号、同对象、同 pct、落地拍在 [t, t+win] 的指令（每条落地指令只配一次）。
输出：逐条（落地拍、延迟、实付、对象当时是不是离场壳/离场拍、对象之后哪一拍阵亡）+ 按号和按分支的小计 + 没落地的行。
依赖：out/<局号>/replay_cmds.csv、resim_transfers.csv、resim_events.csv、resim_meta.json。
"""
import csv, json, os, re, sys
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
a = sys.argv[1:]
mid = a[0]
win = int(a[a.index('--win') + 1]) if '--win' in a else 800
doom = int(a[a.index('--doom') + 1]) if '--doom' in a else 400
D = os.path.join(HERE, '..', 'out', mid)
rd = lambda f: list(csv.DictReader(open(os.path.join(D, f), encoding='utf8')))
meta = json.load(open(os.path.join(D, 'resim_meta.json')))
sq = {k: int(v) for k, v in meta['squad'].items()}
seat2 = {v: k for k, v in sq.items()}
names = meta['names']
ev = rd('resim_events.csv')
left = {int(r['p']): int(r['t']) for r in ev if r['ev'] == 'left'}
died = {int(r['p']): int(r['t']) for r in ev if r['ev'] != 'left'}
cmds = [r for r in rd('replay_cmds.csv') if r['kind'] in ('donate', 'attack')]
tr = rd('resim_transfers.csv')
paid = {}
for r in tr:
    if r['kind'] == 'cmd':
        paid[(int(r['t']), int(r['from']), int(r['to']))] = paid.get((int(r['t']), int(r['from']), int(r['to'])), [])
        paid[(int(r['t']), int(r['from']), int(r['to']))].append((int(float(r['paid'] or 0)), int(float(r['received'] or 0))))
B = '/agent/repos/c136-data/bundles'
alias = {k: int(v) for k, v in (meta.get('alias') or {}).items() if ':' not in k}
res = list(csv.DictReader(open(os.path.join(B, mid, 'results.csv'), encoding='utf8')))
for r in res:
    if r.get('meId') not in (None, ''):
        alias[r['bot']] = int(r['meId'])
pat = re.compile(r'^\d+\t\[([^\]]+)\] \[HL-(DONATE|ASSIST)\] t=(\d+) (.*)$')
lines = []
for ln in open(os.path.join(B, mid, 'in_game.log'), encoding='utf8', errors='replace'):
    m = pat.match(ln.rstrip('\n'))
    if not m:
        continue
    lb, kind, t, rest = m.group(1), m.group(2), int(m.group(3)), m.group(4)
    p = sq.get(lb, alias.get(lb))
    if kind == 'DONATE':
        mm = re.search(r'(squad rescue donate|surplus donate) pct=(\d+)/1024 -> ally=(\d+)', rest)
        if not mm:
            continue
        lines.append({'bot': lb, 'p': p, 't': t, 'branch': mm.group(1), 'pct': int(mm.group(2)), 'to': int(mm.group(3)), 'kind': 'donate'})
    else:
        mm = re.search(r'-> enemy=(\d+)\(.*?\) for ally=(\d+)', rest)
        if not mm:
            continue
        lines.append({'bot': lb, 'p': p, 't': t, 'branch': 'squad-rescue poke', 'pct': 102, 'to': int(mm.group(1)), 'ally': int(mm.group(2)), 'kind': 'attack'})
used = set()
nm = lambda p: seat2.get(p) or (f'{names[p]}#{p}' if p < len(names) else f'#{p}')
by_bot = defaultdict(lambda: [0, 0, 0, 0]); by_br = defaultdict(lambda: [0, 0, 0, 0, 0])
print(f'== {mid} [HL-DONATE]/[HL-ASSIST] 行 {len(lines)} 条 对 录像落地（同号、同对象、同 pct，落地拍在 [t, t+{win}]）')
miss = []
husk_pay = [0, 0, 0]; doom_pay = [0, 0, 0]; ret = []
landed = []
for L in lines:
    hit = None
    for i, c in enumerate(cmds):
        if i in used or c['kind'] != L['kind'] or int(c['player']) != L['p']:
            continue
        tgt = int(c['dX']) if c['dX'] not in ('', None) else -1
        # replay_cmds：donate 的对象和 pct 列名随类型不同，这里两种都试
        vals = {c.get('dX'), c.get('dZ')}
        tk = int(c['tick'])
        if not (L['t'] <= tk <= L['t'] + win):
            continue
        if str(L['to']) in vals and str(L['pct']) in vals:
            hit = (i, tk)
            break
    state = ''
    to = L['to']
    if to in left and left[to] <= L['t']:
        state = f'离场壳（{left[to]} 拍离场）'
    dd = f'，{died[to]} 拍阵亡' if to in died else ''
    br = by_br[L['branch']]; bb = by_bot[L['bot']]
    br[0] += 1; bb[0] += 1
    if state:
        br[4] += 1
    if hit:
        used.add(hit[0])
        pp = paid.get((hit[1], L['p'], to), [])
        pay = pp.pop(0) if pp else (0, 0)
        br[1] += 1; bb[1] += 1; br[2] += pay[0]; bb[2] += pay[0]; br[3] += pay[1]; bb[3] += pay[1]
        if L['kind'] == 'donate':
            landed.append((hit[1], L['p'], to, pay[0], pay[1]))
            if state:
                husk_pay[0] += 1; husk_pay[1] += pay[0]; husk_pay[2] += pay[1]
            elif to in died and died[to] - hit[1] <= doom:
                doom_pay[0] += 1; doom_pay[1] += pay[0]; doom_pay[2] += pay[1]
        print(f"   {L['bot']:14s} t={L['t']:5d} {L['branch']:20s} pct={L['pct']:3d} → {nm(to):16s} 落地 {hit[1]}（晚 {hit[1] - L['t']} 拍）" + (f" 实付 {pay[0]} 到账 {pay[1]}" if pay[0] else '') + f" {state}{dd}")
    else:
        miss.append(L)
        print(f"   {L['bot']:14s} t={L['t']:5d} {L['branch']:20s} pct={L['pct']:3d} → {nm(to):16s} 没落地 {state}{dd}")
print('-- 按分支：行数 / 落地 / 实付 / 到账 / 对象下令时已是离场壳的行数')
for k, v in by_br.items():
    print(f'   {k:20s} {v[0]:3d} / {v[1]:3d} / {v[2]} / {v[3]} / {v[4]}')
print('-- 按号：行数 / 落地 / 实付 / 到账')
for k, v in by_bot.items():
    print(f'   {k:14s} {v[0]:3d} / {v[1]:3d} / {v[2]} / {v[3]}')
print(f'-- 合计 {len(lines)} 行，落地 {len(lines) - len(miss)}，没落地 {len(miss)}')
dn = [x for x in landed]
print(f'-- 落地的捐兵 {len(dn)} 条：实付 {sum(x[3] for x in dn)}，到账 {sum(x[4] for x in dn)}，路上扣掉 {sum(x[3] - x[4] for x in dn)}（{100 * sum(x[3] - x[4] for x in dn) / max(1, sum(x[3] for x in dn)):.1f}%）')
print(f'   其中对象下令时已是离场壳：{husk_pay[0]} 条，实付 {husk_pay[1]}，到账 {husk_pay[2]}')
print(f'   其中对象（不是壳）在到账后 {doom} 拍内阵亡：{doom_pay[0]} 条，实付 {doom_pay[1]}，到账 {doom_pay[2]}')
back = 0; bp = 0
for (t, f, to, pd, rc) in dn:
    for (t2, f2, to2, pd2, rc2) in dn:
        if f2 == to and to2 == f and 0 < t2 - t <= 400:
            back += 1; bp += pd2
            print(f'   回捐：{nm(f)} → {nm(to)} {t} 拍实付 {pd}；{nm(f2)} → {nm(to2)} {t2} 拍实付 {pd2}（隔 {t2 - t} 拍）')
print(f'   400 拍内回捐 {back} 对，回捐实付合计 {bp}')
miss_k = defaultdict(int)
for L in miss:
    to = L['to']
    k = '离场壳' if (to in left and left[to] <= L['t']) else ('不在本队 20 个席位里的同名席位' if to not in seat2 else '在场的本队号')
    miss_k[k] += 1
print('-- 没落地的行按对象：' + '，'.join(f'{k} {v}' for k, v in miss_k.items()))
