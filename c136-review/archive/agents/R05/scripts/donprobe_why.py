#!/usr/bin/env python3
"""donprobe_why.py — 汇总 shadow.mjs --don-probe 的输出：每个时间窗里，捐兵候选是在哪一行被拦下的。

口径：探针在每个采样拍、对每个在场的我方号（捐出方）复刻 tryDonateToTeammate 的候选循环（Vb L4413-4496），
每个候选队友一行，行尾是「在哪一行被跳过」或「★ 成为候选」。捐出方表头里若带「→ L4343 直接返回」，
说明捐出方自己正被真人打或自己在打真人（在外兵 > 8% 存兵），整个函数在候选循环之前就返回了。
注意：探针不看 L4329（t<1500、地<1200、兵<3 万、12 拍冷却）和 L4331（每 25 拍轮到一次）这两道前置门，
也不看最后的 L4506（比例 <180/1024 不发）；所以「★」只表示「候选循环里有人过关」，不等于会发。
本脚本另外按表头里的地/兵把 L4329 的两个硬门槛（地 <1200、兵 <30000）标出来。

用法：python3 scripts/donprobe_why.py probe.txt --win 1500,2175 --win 4285,4890 [--by-donor] [--by-cand]
"""
import re
import sys
from collections import Counter, defaultdict

args = sys.argv[1:]
f = args[0]
wins = []
i = 1
while i < len(args):
    if args[i] == '--win':
        a, b = args[i + 1].split(',')
        wins.append((int(a), int(b)))
        i += 2
    else:
        i += 1
by_donor = '--by-donor' in args
by_cand = '--by-cand' in args
if not wins:
    wins = [(0, 10 ** 9)]

rx_head = re.compile(r'^-- 调度候选 (\S+) t=(\d+) 地 (\d+) 兵 (\d+) 密度 (\S+)｜boxedIn=(\w+) 有海岸=(\w+)｜自己被真人打 (\d+) 自己在打真人 (\d+)(（→ L\d+ 直接返回）)?')
rx_cand = re.compile(r'^\s+→ (?:\[[^\]]*\] )?(.+?)#(\d+) 地 (\d+) 兵 (\d+) 密度 (\S+)｜被真人打 (\d+)（(\S+?)×兵）在打真人 (\d+)｜敌邻 (\d+)｜(.*)$')


def cat(why):
    if why.startswith('★ A'):
        return '★A 守方急援候选'
    if why.startswith('★ B'):
        return '★B ' + ('offense' if 'offense' in why else 'yield_opt') + ' 候选'
    m = re.match(r'L(\d+) (\S+)', why)
    if not m:
        return why[:20]
    return f'L{m.group(1)} {m.group(2)}'


heads = []  # (donor, t, L, B, boxed, selfRet, [cands])
cur = None
for line in open(f, encoding='utf-8', errors='replace'):
    m = rx_head.match(line)
    if m:
        cur = dict(donor=m.group(1), t=int(m.group(2)), L=int(m.group(3)), B=int(m.group(4)), boxed=m.group(6) == 'true',
                   myIn=int(m.group(8)), myOut=int(m.group(9)), selfRet=bool(m.group(10)), cands=[])
        heads.append(cur)
        continue
    m = rx_cand.match(line)
    if m and cur is not None:
        cur['cands'].append(dict(name=m.group(1).strip(), L=int(m.group(3)), B=int(m.group(4)), inH=int(m.group(6)), outH=int(m.group(8)), nb=int(m.group(9)), why=m.group(10), cat=cat(m.group(10))))

for a, b in wins:
    hs = [h for h in heads if a <= h['t'] <= b]
    ticks = sorted({h['t'] for h in hs})
    n = len(hs)
    gate = Counter()
    for h in hs:
        if h['L'] < 1200 or h['B'] < 30000:
            gate['L4329 捐出方 地<1200 或 兵<3万'] += 1
        elif h['selfRet']:
            gate['L4343 捐出方自己在交战'] += 1
        elif not h['cands']:
            gate['没有任何候选队友'] += 1
        elif any(c['cat'].startswith('★') for c in h['cands']):
            gate['候选循环里有人过关（★）'] += 1
        else:
            gate['候选全部被跳过 → L4498'] += 1
    print(f'== 窗口 {a}–{b}：采样拍 {len(ticks)} 个，（捐出方×拍）{n} 个 ==')
    print('  捐出方层面： ' + '；'.join(f'{k} {v}' for k, v in gate.most_common()))
    cc = Counter()
    under = Counter()
    for h in hs:
        if h['L'] < 1200 or h['B'] < 30000 or h['selfRet']:
            continue
        for c in h['cands']:
            cc[c['cat']] += 1
            if c['inH'] > 0:
                under[c['cat']] += 1
    tot = sum(cc.values())
    print(f'  候选层面（捐出方过了前两道门的 {tot} 个 捐出方×候选×拍）： ' + '；'.join(f'{k} {v}（其中候选正被真人打 {under[k]}）' for k, v in cc.most_common()))
    # 正被真人打的候选：有多少（候选×拍）没有任何一个捐出方把它列为 ★A
    need = defaultdict(lambda: dict(star=0, donors=0, why=Counter()))
    for h in hs:
        for c in h['cands']:
            if c['inH'] <= 0:
                continue
            k = (c['name'], h['t'])
            need[k]['donors'] += 1
            if h['L'] < 1200 or h['B'] < 30000:
                need[k]['why']['捐出方 地<1200 或 兵<3万'] += 1
            elif h['selfRet']:
                need[k]['why']['捐出方自己在交战(L4343)'] += 1
            elif c['cat'].startswith('★'):
                need[k]['star'] += 1
            else:
                need[k]['why'][c['cat']] += 1
    nn = len(need)
    no_star = [k for k, v in need.items() if v['star'] == 0]
    agg = Counter()
    for k in no_star:
        agg.update(need[k]['why'])
    print(f'  正被真人打的（候选×拍）{nn} 个：其中没有任何一个队友把它列为候选的 {len(no_star)} 个；这些里各捐出方的拦截原因合计： ' + '；'.join(f'{k} {v}' for k, v in agg.most_common()))
    if by_cand:
        per = defaultdict(lambda: dict(n=0, star=0, why=Counter()))
        for (name, t), v in need.items():
            per[name]['n'] += 1
            per[name]['star'] += 1 if v['star'] > 0 else 0
            per[name]['why'].update(v['why'])
        for name, v in sorted(per.items(), key=lambda kv: -kv[1]['n']):
            print(f'    候选 {name}: 被打的采样拍 {v["n"]}，其中至少一个队友列它为 ★ 的 {v["star"]}；拦截原因 ' + '；'.join(f'{k} {x}' for k, x in v['why'].most_common(5)))
    if by_donor:
        per = defaultdict(Counter)
        for h in hs:
            if h['L'] < 1200 or h['B'] < 30000:
                per[h['donor']]['L4329 地/兵不够'] += 1
            elif h['selfRet']:
                per[h['donor']]['L4343 自己在交战'] += 1
            elif any(c['cat'].startswith('★') for c in h['cands']):
                per[h['donor']]['有★候选'] += 1
            else:
                w = Counter(c['cat'] for c in h['cands'])
                per[h['donor']]['全跳过：' + (w.most_common(1)[0][0] if w else '无候选')] += 1
        for dn, v in sorted(per.items()):
            print(f'    捐出方 {dn}: ' + '；'.join(f'{k} {x}' for k, x in v.most_common()))
