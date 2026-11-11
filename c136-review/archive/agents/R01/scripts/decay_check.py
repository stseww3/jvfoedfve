#!/usr/bin/env python3
"""decay_check.py — 挨打时“地和兵一起掉”的算式核对。
引擎 game.js expandAttack L958–1060 + damage L1062–1074：进攻方每吃一格付 2 + 2×def（def = 守方余额 / (1 + 10×守方领土/16) ≈ 1.6×守方密度），
同时守方余额被打掉 def（damage 里 dmg = (cost − base)/2）。于是守方挨打时 dB/dL = 1.6×B/L，即 B ∝ L^1.6：
  从 (L0,B0) 被吃到 L1 时，守方余额应剩 B0×(L1/L0)^1.6；进攻方总共要付 2×(L0−L1) + 2×B0×(1−(L1/L0)^1.6)。
本脚本对给定的 号:起拍:止拍 用 resim_squad.csv 的采样核对“预测余额 / 实际余额”，并列出窗口内该号自己落地的进攻实扣、捐出、收到，
以及按 30 拍采样看到的来兵合计（采样会漏掉两个采样点之间来了又走的兵，只作参考）。
用法：python3 decay_check.py <matchId> [--cases bot:t0:t1[,bot:t0:t1...]] [--kill 席位:拍[,席位:拍...]]
  --kill：按同一算式算“把这个席位从当拍的领土 L0 吃到阵亡线（峰值/4；峰值取它到当拍为止的最大领土，偏保守）要付多少兵”：
          2×(L0−峰值/4) + 2×B0×(1−(峰值/4/L0)^1.6)；用来和策略 buyLand 自己算的 need（probe_view.py --gate）对照。
依赖 out/<id>/resim_squad.csv、resim_players.csv、shadow_match.csv、resim_transfers.csv、resim_meta.json。
"""
import csv, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
a = sys.argv[1:]
mid = a[0]
cases = a[a.index('--cases') + 1].split(',') if '--cases' in a else []
kills = a[a.index('--kill') + 1].split(',') if '--kill' in a else []
OUT = os.path.join(HERE, '..', 'out', mid)
meta = json.load(open(os.path.join(OUT, 'resim_meta.json')))
seat = {b: int(p) for b, p in meta['squad'].items()}
sq = list(csv.DictReader(open(os.path.join(OUT, 'resim_squad.csv'))))
mt = list(csv.DictReader(open(os.path.join(OUT, 'shadow_match.csv'))))
tr = list(csv.DictReader(open(os.path.join(OUT, 'resim_transfers.csv'))))
print(f'== {mid} 挨打时余额随领土的衰减：预测 B1 = B0×(L1/L0)^1.6（game.js expandAttack + damage）')
print('   号 [t0,t1] 领土 L0→L1 | 余额 B0→B1 实际 | 预测 B1 | 实际/预测 | 窗口内自己进攻实扣 / 捐出 / 收到 | 进攻方按算式应付 2×ΔL+2×(B0−预测B1) | 采样到的来兵合计')
for c in cases:
    bot, t0, t1 = c.split(':'); t0 = int(t0); t1 = int(t1)
    rows = {int(r['t']): r for r in sq if r['bot'] == bot}
    if t0 not in rows or t1 not in rows:
        print(f'   {bot} [{t0},{t1}] 采样点不存在'); continue
    L0, B0 = int(rows[t0]['terr']), int(rows[t0]['bal'])
    L1, B1 = int(rows[t1]['terr']), int(rows[t1]['bal'])
    pred = B0 * (L1 / L0) ** 1.6 if L0 else 0
    spent = sum(int(float(r['spent'] or 0)) for r in mt if r['bot'] == bot and r['kind'] == 'attack' and t0 <= int(r['tick']) < t1)
    p = seat[bot]
    gave = sum(int(r['paid']) for r in tr if r['ok'] == '1' and int(r['from']) == p and t0 <= int(r['t']) < t1)
    got = sum(int(r['received']) for r in tr if r['ok'] == '1' and int(r['to']) == p and t0 <= int(r['t']) < t1)
    inc = 0
    for t, r in rows.items():
        if t0 <= t <= t1 and r['atkIn']:
            inc += sum(int(x.split(':')[1]) for x in r['atkIn'].split('|') if ':' in x)
    cost = 2 * (L0 - L1) + 2 * (B0 - pred)
    print(f'   {bot:8s} [{t0},{t1}] {L0}→{L1} | {B0}→{B1} | {pred:.0f} | {B1 / pred if pred else 0:.2f} | {spent} / {gave} / {got} | {cost:.0f} | {inc}')

if kills:
    pl = list(csv.DictReader(open(os.path.join(OUT, 'resim_players.csv'))))
    print(f'== {mid} 吃到阵亡线的算式价：2×(L0−峰值/4) + 2×B0×(1−(峰值/4/L0)^1.6)')
    for k in kills:
        p, t = (int(x) for x in k.split(':'))
        rows = sorted((int(r['t']), int(r['terr']), int(r['bal'])) for r in pl if int(r['p']) == p)
        cur = min(rows, key=lambda r: abs(r[0] - t))
        peak = max(r[1] for r in rows if r[0] <= cur[0])
        L0, B0 = cur[1], cur[2]; L1 = peak / 4
        cost = 2 * (L0 - L1) + 2 * B0 * (1 - (L1 / L0) ** 1.6) if L0 > L1 else 0
        print(f'   席位 {p} {meta["names"][p]} t={cur[0]}：领土 {L0} 余额 {B0} 峰值 {peak} → 阵亡线 {L1:.0f} 格；算式价 {cost:.0f}（余额的 {cost / B0 if B0 else 0:.2f} 倍），到线时还剩 {B0 * (L1 / L0) ** 1.6 if L0 else 0:.0f} 兵')
