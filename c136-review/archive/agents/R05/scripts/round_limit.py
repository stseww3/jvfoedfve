#!/usr/bin/env python3
"""round_limit.py — 录像命令流里的「回合」与「每玩家执行条数上限」：全部录像、全部真人玩家机械计数。

要核对的四件事（都只读录像命令流，不跑引擎）：
  1) 指令只在 7 的倍数拍执行（服务器每 7 拍一个回合）：按 tick mod 7 数条数。
  2) 一个玩家一个回合最多执行几条：每（玩家, 回合）条数的分布与最大值。
  3) 任意连续 3 个回合（21 拍）同一个玩家执行的条数合计的最大值。
  4) 一个回合执行满 CAP 条之后的两个回合，这个玩家有没有再执行过指令（CAP = 第 2 项实测的最大值）。
另列：满回合里各指令种类的条数；满回合出现的拍段；满回合之后「下一条指令」隔了几个回合；
      三类玩家分开数：本编队的号 / 同房的另一支我方编队（card.json 的 sameMatchPeer）/ 其他真人。

口径：只数对局期（tick ≥ 0）、真人座位（座位号 < 真人数）的指令；出生（id 0）与离场（id 8/9）不计入条数。
      「回合」= 拍号 ÷ 7 的整数部分（第 1 项先核对所有指令都落在 7 的倍数拍）。
      号 ↔ 座位：in_game.log 的 [HL-GAME-INIT] me=、results.csv 的 meId；座位上的录像名去掉 [标签] 后 = 号名才算（同 pattern_scan.py）。
输入：/tmp/c136-r05/cmds/<局>.tsv、headers.json（replay_dump_all.mjs 的产物）
用法：python3 scripts/round_limit.py [局…] [--json FILE] [--per-match]
"""
import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict

a = sys.argv[1:]
jo = a[a.index('--json') + 1] if '--json' in a else None
per_match = '--per-match' in a
ids = [x for i, x in enumerate(a) if not x.startswith('--') and (i == 0 or a[i - 1] != '--json')]
CM = os.environ.get('C136_CMDS', '/tmp/c136-r05/cmds')
DATA = os.environ.get('C136_DATA', '/agent/repos/c136-data')
BUN = os.environ.get('C136_BUNDLES', 'bundles')   # 验证集：C136_BUNDLES=validation_bundles
H = json.load(open(f'{CM}/headers.json'))
if not ids:
    ids = sorted(m for m in H if 'error' not in H[m] and os.path.exists(f'{CM}/{m}.tsv'))
SKIP = {0, 8, 9}
GROUPS = (('squad', '本编队的号'), ('peer', '同房另一支我方编队'), ('other', '其他真人'))
IDMAP = defaultdict(list)
for r in csv.DictReader(open(f'{DATA}/src/tools/identity-map-discovery.csv', encoding='utf-8')):
    IDMAP[r['matchId']].append(r)
bare = lambda n: re.sub(r'\[[^\]]*\]', '', n or '').strip().lower()


def squad_seats(mid, names, humans):
    B = f'{DATA}/{BUN}/{mid}'
    if not mid or not os.path.exists(f'{B}/in_game.log'):
        return set()
    alias = {}
    for r in IDMAP.get(mid, []):
        ch = [x for x in (r.get('nameChain') or '').split('→') if x]
        for n in ch[1:]:
            alias[n] = ch[0]
    al = lambda n: alias.get(n, n)
    me = {}
    for ln in open(f'{B}/in_game.log', encoding='utf-8', errors='replace'):
        m = re.match(r'\d+\t\[([^\]]+)\] \[HL-GAME-INIT\].* me=(\d+)', ln)
        if m:
            me.setdefault(al(m.group(1)), int(m.group(2)))
    if os.path.exists(f'{B}/results.csv'):
        for r in csv.DictReader(open(f'{B}/results.csv', encoding='utf-8')):
            b = al(r['bot'])
            if b not in me and r.get('meId'):
                me[b] = int(r['meId'])
    return {p for b, p in me.items() if p < humans and p < len(names) and bare(names[p]) == b.lower()}


def peer_of(mid):
    p = f'{DATA}/{BUN}/{mid}/card.json'
    if not os.path.exists(p):
        return None
    return (json.load(open(p)).get('sameMatchPeer') or {}).get('peerMatchId')


G0 = lambda: {g: Counter() for g, _ in GROUPS}
mod7 = Counter()
per_round, win_hist, after_full, gap_after = G0(), G0(), G0(), G0()
kind_in_full, full_period = Counter(), Counter()
viol = []
OUT, KEEP = {}, {}
tot_cmds = 0
for mid in ids:
    hd = H[mid]
    sq = squad_seats(mid, hd['names'], hd['humans'])
    pm = peer_of(mid)
    peer = (squad_seats(pm, hd['names'], hd['humans']) - sq) if pm else set()
    occ = defaultdict(Counter)                     # 座位 → 回合 → 条数
    kinds = defaultdict(lambda: defaultdict(Counter))
    for r in csv.DictReader(open(f'{CM}/{mid}.tsv', encoding='utf-8'), delimiter='\t'):
        t, i, p = int(r['tick']), int(r['id']), int(r['player'])
        if t < 0 or i in SKIP or p >= hd['humans']:
            continue
        tot_cmds += 1
        mod7[t % 7] += 1
        occ[p][t // 7] += 1
        kinds[p][t // 7][r['kind']] += 1
    who = {p: ('squad' if p in sq else 'peer' if p in peer else 'other') for p in occ}
    m_round, m_win = Counter(), Counter()
    for p, rounds in occ.items():
        g = who[p]
        for rd, n in rounds.items():
            per_round[g][n] += 1
            m_round[g] = max(m_round[g], n)
            w = n + rounds.get(rd + 1, 0) + rounds.get(rd + 2, 0)
            win_hist[g][w] += 1
            m_win[g] = max(m_win[g], w)
    OUT[mid] = {'seats': {'squad': len(sq), 'peer': len(peer)}, 'maxPerRound': dict(m_round), 'maxPer3Rounds': dict(m_win)}
    KEEP[mid] = (occ, who, kinds)

CAP = max(max(c, default=0) for c in per_round.values())
for mid in ids:
    occ, who, kinds = KEEP[mid]
    nf = Counter()
    for p, rounds in occ.items():
        g = who[p]
        order = sorted(rounds)
        for j, rd in enumerate(order):
            if rounds[rd] < CAP:
                continue
            nf[g] += 1
            nxt = rounds.get(rd + 1, 0) + rounds.get(rd + 2, 0)
            after_full[g]['有指令' if nxt else '空'] += 1
            if nxt:
                viol.append((mid, p, rd * 7, nxt))
            if j + 1 < len(order):
                gap_after[g][min(order[j + 1] - rd, 10)] += 1
            for kk, c in kinds[p][rd].items():
                kind_in_full[kk] += c
            t = rd * 7
            full_period['0–600' if t < 600 else '600–1500' if t < 1500 else '1500–3000' if t < 3000 else '3000+'] += 1
    OUT[mid]['fullRounds'] = dict(nf)
    if per_match:
        mr, mw = OUT[mid]['maxPerRound'], OUT[mid]['maxPer3Rounds']
        print(f"{mid}: 座位 本编队 {OUT[mid]['seats']['squad']}、同房另一支 {OUT[mid]['seats']['peer']}｜每回合最大 " + ' / '.join(str(mr.get(g, 0)) for g, _ in GROUPS)
              + '｜3 回合窗口最大 ' + ' / '.join(str(mw.get(g, 0)) for g, _ in GROUPS) + f'｜满 {CAP} 条的回合 ' + ' / '.join(str(nf.get(g, 0)) for g, _ in GROUPS))

print(f"===== {len(ids)} 局录像，对局期真人指令 {tot_cmds:,} 条（出生、离场不计）=====")
print('1) 执行拍 mod 7：' + '、'.join(f'余 {k}: {v:,}' for k, v in sorted(mod7.items())))
for g, name in GROUPS:
    c = per_round[g]
    tot = sum(c.values())
    if tot:
        print(f"2) {name}：有指令的（玩家×回合）{tot:,} 个；每回合条数 → 个数：" + '、'.join(f'{k} 条 {c[k]:,}' for k in sorted(c))
              + f"；≥3 条的占 {100 * sum(v for k, v in c.items() if k >= 3) / tot:.2f}%；最大 {max(c)} 条")
print('3) 任意连续 3 个回合的合计：' + '；'.join(f"{name} 最大 {max(win_hist[g], default=0)}（合计 7 / 8 / 9 条的窗口 {win_hist[g][7]:,} / {win_hist[g][8]:,} / {win_hist[g][9]:,}，>9 的 {sum(v for k, v in win_hist[g].items() if k > 9)}）"
                                       for g, name in GROUPS if win_hist[g]))
print(f"4) 满 {CAP} 条的回合之后两个回合：" + '；'.join(f"{name} 空 {after_full[g]['空']:,}、有指令 {after_full[g]['有指令']:,}" for g, name in GROUPS if after_full[g]))
if viol:
    print('   反例（局/座位/满回合拍/其后两回合条数）：' + '、'.join(f'{m}/{p}/{t}/{n}' for m, p, t, n in viol[:20]))
print('   满回合之后下一条指令隔几个回合：' + '；'.join(f"{name} " + '、'.join(f"{'≥10' if k == 10 else k} 回合 {v:,}" for k, v in sorted(gap_after[g].items())) for g, name in GROUPS if gap_after[g]))
print('   满回合里的指令种类：' + '、'.join(f'{k} {v:,}' for k, v in kind_in_full.most_common()))
print('   满回合所在拍段：' + '、'.join(f'{k} 拍 {full_period[k]:,}' for k in ('0–600', '600–1500', '1500–3000', '3000+')))
print('   有满回合的局：' + '、'.join(f"{name} {sum(1 for m in ids if OUT[m]['fullRounds'].get(g))}/{len(ids)}" for g, name in GROUPS))
if jo:
    json.dump({'cap': CAP, 'mod7': dict(mod7), 'perRound': {g: dict(c) for g, c in per_round.items()}, 'win3': {g: dict(c) for g, c in win_hist.items()},
               'afterFull': {g: dict(c) for g, c in after_full.items()}, 'gapAfterFull': {g: dict(c) for g, c in gap_after.items()},
               'kindInFull': dict(kind_in_full), 'fullPeriod': dict(full_period), 'matches': OUT},
              open(jo, 'w', encoding='utf-8'), ensure_ascii=False)
    print('→', jo)
