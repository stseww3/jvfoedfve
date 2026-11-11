#!/usr/bin/env python3
"""team-count.py — 队伍数从哪来：用引擎规则预测，再和日志里的结算记录对照。

输入：已公布的小队实盘日志 /tmp/c136-r04/c116/data/G01-G09-squad.log（prep.sh 取回）。
  [HL-GAME-INIT] mode=<大厅对局类型 vz> map=.. mapSeed=.. players=<真人数 ku> me=<我的玩家号>
  [RESULT <bot>] result=.. event=.. place=.. peak=.. team={"mine":..,"best":..,"totals":{队号:领土合计}}
  （team 字段由注入页面的脚本算：mine = bj.fX[我]，totals 只统计当时领土>0 的玩家，键 "0" = 没有队伍的玩家）

引擎规则（live_game_js.js sha 2b5731c7，dP.ee → aek / ael / aem；c5.a7g；aFz.aH4）：
  配置队伍数 = vz + 2（vz < 7 时）
  同名战队标签的真人算一组；最大一组的人数 > floor((ku + 0.5) / 队伍数) 时，队伍数减 1，直到不超过或只剩 2 队
  真人队伍数 < 8 时内置 AI 不进任何队（队号 0）；= 8 时内置 AI 按 1 + 玩家号 % 8 分进各队
本脚本假设「最大一组」就是我方小队在场人数（看不到别的战队有多少人，别的战队更大时实际队伍数会更少）。

用法：timeout 120 python3 team-count.py > ../out/team-count.txt
"""
import json
import re
import sys
from collections import OrderedDict

LOG = sys.argv[1] if len(sys.argv) > 1 else '/tmp/c136-r04/c116/data/G01-G09-squad.log'


def g0(a, b):
    return int((a + 0.5) // b)


def predict_teams(vz, ku, biggest_clan):
    n = vz + 2
    steps = []
    while n > 2 and biggest_clan > g0(ku, n):
        steps.append('%d队时每队基准 %d 人 < 最大战队 %d 人 → 减为 %d 队' % (n, g0(ku, n), biggest_clan, n - 1))
        n -= 1
    return n, steps


init_re = re.compile(r'^\[(.+?)\] \[HL-GAME-INIT\] mode=(\d+) map=(\d+) mapSeed=(\d+) players=(\d+) me=(\d+)')
res_re = re.compile(r'^\[RESULT (.+?)\] result=(\w+) event=(\w+) place=(\S+) peak=(\S+) team=(.*)$')

games = OrderedDict()   # key -> dict
cur = {}                # bot -> game key
with open(LOG, encoding='utf-8', errors='replace') as f:
    for ln, line in enumerate(f, 1):
        m = init_re.match(line)
        if m:
            bot, vz, mp, seed, ku, me = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5)), int(m.group(6))
            key = (vz, mp, seed, ku)
            g = games.setdefault(key, {'vz': vz, 'map': mp, 'seed': seed, 'ku': ku, 'line': ln, 'bots': OrderedDict(), 'results': []})
            g['bots'][bot] = me
            cur[bot] = key
            continue
        m = res_re.match(line)
        if m:
            bot = m.group(1)
            try:
                team = json.loads(m.group(6))
            except Exception:
                team = None
            if bot in cur:
                games[cur[bot]]['results'].append({'bot': bot, 'result': m.group(2), 'event': m.group(3), 'team': team, 'line': ln})

print('# team-count：引擎规则预测的队伍数 vs 结算记录里出现过的队号')
print('# 输入 %s' % LOG)
print('局\t日志行\tmode(vz)\t真人数\t我方在场\t配置队数\t预测队数\t记录里的队号(非0)\t出现过队号0\t我方队号(mine)分布\t预测=观察')
ok = 0
n = 0
notes = []
for i, (key, g) in enumerate(games.items()):
    squad = len(g['bots'])
    pred, steps = predict_teams(g['vz'], g['ku'], squad)
    keys = set()
    mine = {}
    for r in g['results']:
        t = r['team']
        if not t:
            continue
        keys |= set(int(k) for k in (t.get('totals') or {}).keys())
        if t.get('mine') is not None:
            mine.setdefault(t['mine'], []).append(r['bot'].split('] ')[-1])
    nz = sorted(k for k in keys if k != 0)
    obs = max(nz) if nz else None
    match = (obs == pred and nz == list(range(1, pred + 1)))
    n += 1
    ok += 1 if match else 0
    print('G%02d\t%d\t%d\t%d\t%d\t%d\t%d\t%s\t%s\t%s\t%s' % (
        i, g['line'], g['vz'], g['ku'], squad, g['vz'] + 2, pred, ','.join(map(str, nz)) or '-', '是' if 0 in keys else '否',
        '; '.join('%s队:%s' % (k, '/'.join(v)) for k, v in sorted(mine.items())) or '-', '是' if match else '否'))
    for s in steps:
        notes.append('G%02d：%s' % (i, s))
    if len(mine) > 1:
        notes.append('G%02d：我方成员的 mine 不是同一个队号（%s）——这一局小队被分在了不同队伍' % (i, '; '.join('%s队 %d 人' % (k, len(v)) for k, v in sorted(mine.items()))))
    border = g0(g['ku'], pred) + (1 if g['ku'] % pred else 0)
    notes.append('G%02d：真人 %d / %d 队 → 每队人数上限 %d（ceil）' % (i, g['ku'], pred, border))
print('# 预测与观察一致：%d / %d 局' % (ok, n))
print('# 说明')
for s in notes:
    print('#  ' + s)
print('# 注：局号 G00 是日志里第一局（旧报告的 G01-G09 对应这里的 G01-G09，G00 是旧报告没编号的那一局）。')
