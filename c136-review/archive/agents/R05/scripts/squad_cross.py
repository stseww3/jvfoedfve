#!/usr/bin/env python3
# squad_cross.py — 我方号打我方号的账（分队局 / 多队局里才会出现）。
#   数据：/tmp/c136-r05/truth/<局>.json 的 pairsW（引擎层每 100 拍的进攻账，含离场后由引擎代打的进攻）、
#         events（录像里真正执行的指令）、players（离场拍 leftT、阵亡拍 deathT）、tickLines（各号最后一条 [HL-TICK] 的拍）。
#   每一对 (进攻方 → 被打方) 输出：投兵、拿地、打掉的存兵、时段；并把进攻方当时的状态分成三段：
#       在线（日志还在走）｜日志已停未离场（最后一条 [HL-TICK] 之后、leave 之前）｜已离场（leave 之后，引擎按机器人规则代打）
#   同时列出这一对里由录像指令发起的进攻条数（录像指令 = 客户端自己发的；没有指令的 = 引擎代打）。
# 用法：python3 squad_cross.py <局> [--tsv]
import json, sys, collections
mid = sys.argv[1]
T = json.load(open(f'/tmp/c136-r05/truth/{mid}.json'))
sq = {s['p']: s for s in T['squad']}
P = {p['id']: p for p in T['players']}
lastLog = collections.defaultdict(lambda: -1)
tl = T.get('tickLines')
if isinstance(tl, dict):
    for bot, rows in tl.items():
        for r in rows:
            t = r['t'] if isinstance(r, dict) else r[0]
            lastLog[bot] = max(lastLog[bot], t)
elif isinstance(tl, list):
    for r in tl:
        if isinstance(r, dict): lastLog[r.get('bot')] = max(lastLog[r.get('bot')], r.get('t', -1))
if not lastLog:
    import os, re
    data = os.environ.get('C136_DATA', '/agent/repos/c136-data')
    for line in open(f'{data}/bundles/{mid}/in_game.log', encoding='utf-8', errors='replace'):
        m = re.search(r'\[([^\]]+)\] \[HL-TICK\] t=(\d+)', line)
        if m: lastLog[m.group(1)] = max(lastLog[m.group(1)], int(m.group(2)))
def state(p, w0):
    pl = P[p]; bot = sq[p]['bot']
    if pl['leftT'] >= 0 and w0 >= pl['leftT'] - 99: return '已离场' if w0 >= pl['leftT'] else '离场当窗'
    if lastLog[bot] >= 0 and w0 > lastLog[bot] + 90: return '日志已停'
    return '在线'
cmdN = collections.Counter(); cmdT = collections.defaultdict(list)
for e in T['events']:
    if e['type'] in ('attack', 'boat') and e['p'] in sq and e.get('q') in sq and e.get('ok'):
        cmdN[(e['p'], e['q'])] += 1; cmdT[(e['p'], e['q'])].append(e['t'])
landN = collections.Counter()
for e in T['events']:
    if e['type'] == 'boat-land' and e['p'] in sq and e.get('q') in sq: landN[(e['p'], e['q'])] += 1
rows = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0, 0, 10**9, -1]))
for r in T['pairsW']:
    a, b = r['a'], r['b']
    if a in sq and b in sq and (r['sent'] or r['tiles'] or r['balDmg']):
        w0 = r['w'] * 100 if r['w'] < 1000 else r['w']
        st = state(a, w0)
        x = rows[(a, b)][st]
        x[0] += r['sent']; x[1] += r['tiles']; x[2] += r['balDmg']; x[3] = min(x[3], w0); x[4] = max(x[4], w0 + 99)
tsv = '--tsv' in sys.argv
tot = collections.defaultdict(lambda: [0, 0, 0])
print(f'===== {mid} 我方号打我方号（{len(sq)} 个号；按进攻方当时的状态分段）=====')
for (a, b), by in sorted(rows.items(), key=lambda kv: -sum(v[1] for v in kv[1].values())):
    A, B = sq[a], sq[b]
    same = '同队' if A['team'] == B['team'] else '异队'
    head = f"{A['bot']}#{a}(T{A['team']}，离场 {P[a]['leftT'] if P[a]['leftT']>=0 else '-'}，日志到 {lastLog[A['bot']]}，阵亡 {P[a]['deathT'] if P[a]['deathT']>=0 else '-'}) → {B['bot']}#{b}(T{B['team']}，离场 {P[b]['leftT'] if P[b]['leftT']>=0 else '-'}，阵亡 {P[b]['deathT'] if P[b]['deathT']>=0 else '-'}) [{same}]"
    parts = []
    for st in ('在线', '日志已停', '离场当窗', '已离场'):
        if st in by:
            s, tl_, d, w0, w1 = by[st]
            parts.append(f'{st}：投兵 {s}、拿地 {tl_}、打掉存兵 {d}（{w0}–{w1}）')
            tot[st][0] += s; tot[st][1] += tl_; tot[st][2] += d
    ct = cmdT.get((a, b), [])
    print(f'   {head}\n      ' + '；'.join(parts) + f'｜录像指令发起 {cmdN[(a,b)]} 条' + (f'（拍 {min(ct)}–{max(ct)}）' if ct else '') + (f'、船登陆 {landN[(a,b)]} 次' if landN[(a,b)] else ''))
print('   合计：' + '；'.join(f'{st} 投兵 {v[0]}、拿地 {v[1]}、打掉存兵 {v[2]}' for st, v in tot.items()))
