#!/usr/bin/env python3
"""donate_gate.py — 协防捐款（tryDonateToTeammate）的门槛在一局里各被踩到几次。
读 shadow.mjs --probe 打出的 shadow_probe_<tag>.txt（每个号一份，tag 由 --tags 给出，格式 号:tag），
逐决策拍取：余额/领土/密度、buyLand() 的返回值、tryDonateToTeammate() 有没有被调用和返回值；
再从 resim_squad.csv 取同一拍（向下取到 90 拍采样点）其他本队号里“正被人类进攻且还活着”的个数。
Va（v27-team-c116-va.js）里一个有敌邻的号要发 defense_dispatch，得同时满足：
  L4961 这一拍 buyLand 等前面的分支没有发令；L4328 t>=1500、领土>=1200、余额>=30000；L4330 轮到自己的时隙（(t/5|0)%5 == slot%5）；
  L4342 自己没被人类进攻、对人类的在途进攻 <= 8% 余额；L4464–4465 密度 >= 102、余额 > 1.12×max(88×领土, safeAt)、密度 >= 受赠者密度 + 16。
用法：python3 donate_gate.py <matchId> --tags zexos1:pz1,zero_7:pze,... [--t0 1500] [--t1 99999] [--dens 102]
输出：每个号一行——决策拍数；有队友正挨打的决策拍数；其中密度 >= 门槛的拍数；这些拍里 buyLand 已经发令的拍数、tryDonate 被调用的拍数、返回 true 的拍数；
      另列密度 >= 100 的决策拍数和其中 buyLand 发令的拍数（过 100 倍后 buyLand 的脉冲先于捐款）。
"""
import csv, os, re, sys
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
a = sys.argv[1:]
mid = a[0]
opt = lambda k, d=None: a[a.index('--' + k) + 1] if '--' + k in a else d
tags = dict(x.split(':') for x in opt('tags').split(','))
t0, t1, DENS = int(opt('t0', 1500)), int(opt('t1', 99999)), float(opt('dens', 102))
D = os.path.join(HERE, '..', 'out', mid)
sq = defaultdict(dict)
for r in csv.DictReader(open(os.path.join(D, 'resim_squad.csv'), encoding='utf8')):
    sq[int(r['t'])][r['bot']] = r
def under_fire(t, me):
    """采样点上其他本队号里：还活着、atkIn 里有人类席位来兵的个数。atkIn 形如 '席位:兵|席位:兵'。"""
    row = sq.get((t // 90) * 90, {})
    n = 0
    for b, r in row.items():
        if b == me or r['alive'] != '1' or int(r['terr']) < 150: continue
        inc = [x for x in (r.get('atkIn') or '').split('|') if x]
        if any(int(x.split(':')[0]) < HUM and int(x.split(':')[1]) > 0 for x in inc): n += 1
    return n
import json
HUM = json.load(open(os.path.join(D, 'resim_meta.json')))['humans']
print(f'== {mid} 协防捐款门槛（决策拍 {t0}–{t1}；密度门槛 {DENS:g}）')
print('   号 | 决策拍 | 有队友正被人类进攻 | 其中密度>=门槛 | 这些拍里 buyLand 已发令 / 调到 tryDonate / tryDonate 返回真 | 密度>=100 的决策拍 / 其中 buyLand 发令 | 密度最大值')
tot = [0] * 8
for bot, tag in tags.items():
    fn = os.path.join(D, f'shadow_probe_{tag}.txt')
    cur = {}
    for line in open(fn, encoding='utf8'):
        m = re.match(r't=(\d+) (.*)', line)
        if not m: continue
        t = int(m.group(1)); rest = m.group(2)
        if t < t0 or t > t1: continue
        d = cur.setdefault(t, {})
        if rest.startswith('状态'):
            mm = re.search(r'bal=(\d+) terr=(\d+)', rest)
            d['bal'], d['terr'] = int(mm.group(1)), int(mm.group(2))
        elif rest.startswith('buyLand() ->'):
            d['buy'] = rest.endswith('true')
        elif rest.startswith('tryDonateToTeammate('):
            d['don'] = rest.split('->')[1].strip()
    n = fire = hi = hbuy = hcall = htrue = o100 = o100buy = 0; dmax = 0
    for t, d in sorted(cur.items()):
        if 'bal' not in d or t % 5: continue   # 策略每 5 拍决策一次，探针的状态行每拍都有
        n += 1
        dens = d['bal'] / max(1, d['terr']); dmax = max(dmax, dens)
        if dens >= 100:
            o100 += 1; o100buy += 1 if d.get('buy') else 0
        if under_fire(t, bot) == 0: continue
        fire += 1
        if dens >= DENS:
            hi += 1; hbuy += 1 if d.get('buy') else 0
            hcall += 1 if 'don' in d else 0; htrue += 1 if d.get('don') == 'true' else 0
    print(f'   {bot:8s} | {n:5d} | {fire:5d} | {hi:4d} | {hbuy:3d} / {hcall:3d} / {htrue:3d} | {o100:4d} / {o100buy:3d} | {dmax:6.1f}')
    for i, v in enumerate([n, fire, hi, hbuy, hcall, htrue, o100, o100buy]): tot[i] += v
print(f'   合计     | {tot[0]:5d} | {tot[1]:5d} | {tot[2]:4d} | {tot[3]:3d} / {tot[4]:3d} / {tot[5]:3d} | {tot[6]:4d} / {tot[7]:3d} |')
