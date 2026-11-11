#!/usr/bin/env python3
# B010_facts.py — B010 专用事实表（只读 /tmp/c136-r05/truth/B010.json、别名覆盖后的日志和命令流；全部机械计数）。
#   先跑：python3 scripts/alias_overlay.py B010；C136_DATA=/tmp/c136-r05/overlay node scripts/match_truth.mjs B010；
#         C136_DATA=/tmp/c136-r05/overlay node scripts/replay_cmds.mjs B010 --out /tmp/c136-r05/work/B010-cmds.tsv
#   A 段：[HL-ASSIST] 跨队救援戳——每条日志对上录像里的那条进攻；被戳的人当时多大、被救的号是不是已经离场的空壳；
#         其后 600 拍被戳的人回打戳人的号多少。
#   B 段：指定的几对之间逐条进攻（拍、兵、打之前双方的地/兵）。
#   C 段：六个掉线号——日志最后一拍、录像里最后一条自己的指令、离场拍、阵亡拍；离场时/阵亡前的地与兵；空壳期间打了谁、被谁吃。
#   D 段：开局上行卡住的号（AltF4、Chosokabe）——[HL-OPENING] 的决策拍 对 录像里的落地拍。
#   E 段：各号各时段在线状态下的地/兵/密度与名次（S10 / HS）。
# 用法：C136_DATA=/tmp/c136-r05/overlay python3 scripts/review_build/B010_facts.py [--sec A,B,C,D,E]
import json, os, re, sys, csv, collections
M = 'B010'
DATA = os.environ.get('C136_DATA', '/tmp/c136-r05/overlay')
T = json.load(open(f'/tmp/c136-r05/truth/{M}.json'))
sec = set((sys.argv[sys.argv.index('--sec') + 1] if '--sec' in sys.argv else 'A,B,C,D,E').split(','))
H = T['humans']
P = {p['id']: p for p in T['players']}
SQ = {s['p']: s for s in T['squad']}
name = lambda p: ('中立' if p >= 512 else f'机器人#{p}' if p >= H else f"{P[p]['name']}#{p}(T{P[p]['team']})")
k = lambda v: (f'{v / 1e6:.2f}M' if abs(v) >= 1e6 else f'{v / 1e3:.0f}k' if abs(v) >= 1e4 else f'{v:.0f}')
EV = T['events']
log = [ln.rstrip('\n') for ln in open(f'{DATA}/bundles/{M}/in_game.log', encoding='utf-8', errors='replace')]
lastLog = collections.defaultdict(lambda: -1)
for ln in log:
    m = re.search(r'\[([^\]]+)\] \[HL-TICK\] t=(\d+)', ln)
    if m: lastLog[m.group(1)] = max(lastLog[m.group(1)], int(m.group(2)))
# HS：每 300 拍每个真人的地/兵（[t, p, terr, bal] 或 dict）
HS = T.get('HS') or {}
def hs_at(p, t):
    """每 300 拍的真人快照：返回 (拍, 地, 兵)，取 ≤t 的最近一个。"""
    best = None
    for i, tt in enumerate(HS.get('t', [])):
        if tt <= t: best = (tt, HS['terr'][i][p], HS['bal'][i][p])
    return best
S10 = T.get('S10') or {}
def s10_at(p, t):
    """每 10 拍的我方号快照：返回 (拍, 地, 兵)，取 ≤t 的最近一个。"""
    s = S10.get(str(p))
    if not s: return None
    best = None
    for i, tt in enumerate(s['t']):
        if tt <= t: best = (tt, s['terr'][i], s['bal'][i])
        else: break
    return best

if 'A' in sec:
    print('== A 跨队救援戳（[HL-ASSIST] squad-rescue poke）==')
    for ln in log:
        m = re.search(r'\[([^\]]+)\] \[HL-ASSIST\] t=(\d+) (\d+)% squad-rescue poke -> enemy=(\d+)\((.*?)\) for ally=(\d+)\((.*?)\)', ln)
        if not m: continue
        bot, t, pc, en, enm, al, alm = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4)), m.group(5), int(m.group(6)), m.group(7)
        me = next(p for p, s in SQ.items() if s['bot'] == bot)
        hit = [e for e in EV if e['p'] == me and e.get('q') == en and e['type'] == 'attack' and t <= e['t'] <= t + 60]
        e = hit[0] if hit else None
        back = [x for x in EV if x['p'] == en and x.get('q') == me and x['type'] in ('attack', 'boat-land') and t <= x['t'] <= t + 600]
        prev = [x for x in EV if x['p'] == en and x.get('q') == me and x['type'] in ('attack', 'boat-land') and t - 1500 <= x['t'] < t]
        ally = P[al]
        st = '已离场的空壳' if ally['leftT'] >= 0 and ally['leftT'] <= t else '在线'
        ea = hs_at(en, t); aa = s10_at(al, t) or hs_at(al, t)
        print(f"   t={t} {bot}#{me}(T{SQ[me]['team']}) 戳 {name(en)}（当时约 {ea[1] if ea else '?'} 格/{k(ea[2]) if ea else '?'}@{ea[0] if ea else '?'}）救 {name(al)}（{st}，离场 {ally['leftT']}；当时 {aa[1] if aa else '?'} 格/{k(aa[2]) if aa else '?'}）"
              + (f"｜落地 t={e['t']} 打出 {k(e['troops'])}（戳前自己 {e['L0']} 格/{k(e['B0'])}；对方 {e['tL']} 格/{k(e['tB'])}）{'成' if e['ok'] else '落空'}" if e else '｜录像里 60 拍内没有对应进攻')
              + f"｜此前 1500 拍对方打过它 {len(prev)} 条 {k(sum(x.get('troops', 0) for x in prev))}；其后 600 拍对方打它 {len(back)} 条 {k(sum(x.get('troops', 0) for x in back))}" + ('（' + '、'.join(f"t={x['t']} {k(x.get('troops', 0))}" for x in back[:4]) + '）' if back else ''))

if 'B' in sec:
    print('\n== B 指定的几对之间逐条进攻 ==')
    pairs = [(40, 77), (77, 40), (74, 77), (77, 74), (74, 62), (62, 74), (49, 62), (62, 49), (62, 40), (55, 65), (65, 55), (48, 65), (65, 48), (15, 59), (15, 65), (65, 15), (36, 61), (20, 64), (45, 64), (38, 64), (57, 63), (8, 63), (18, 63), (63, 18), (72, 63)]
    for a, b in pairs:
        rows = [e for e in EV if e['p'] == a and e.get('q') == b and e['type'] in ('attack', 'boat-land')]
        if not rows: continue
        print(f'   {name(a)} → {name(b)}: {len(rows)} 条，合计 {k(sum(e.get("troops", 0) for e in rows))}')
        for e in rows[:14]:
            print(f"      t={e['t']} {e['type']} 打出 {k(e.get('troops', 0))}" + (f"（打之前进攻方 {e['L0']} 格/{k(e['B0'])}；对方 {e['tL']} 格/{k(e['tB'])}）{'' if e.get('ok', True) else ' 落空'}" if e['type'] == 'attack' else ''))

if 'C' in sec:
    print('\n== C 掉线号（日志停 → leave → 阵亡）==')
    cmds = collections.defaultdict(list)
    for r in csv.DictReader(open(f'/tmp/c136-r05/work/{M}-cmds.tsv', encoding='utf-8'), delimiter='\t'):
        cmds[int(r['player'])].append((int(r['tick']), r['kind']))
    for p, s in SQ.items():
        pl = P[p]
        own = [t for t, kd in cmds[p] if kd in ('attack', 'boat', 'donate') ]
        lv = [t for t, kd in cmds[p] if kd.startswith('leave')]
        a = s10_at(p, pl['leftT']) if pl['leftT'] >= 0 else None
        d = s10_at(p, pl['deathT'] - 11) if pl['deathT'] >= 0 else None
        pk = (pl['peakTerr'], pl['peakT'])
        print(f"   {s['bot']}#{p}(T{s['team']}): 日志最后一条 [HL-TICK] t={lastLog[s['bot']]}｜录像里最后一条自己的进攻/出船 t={max(own) if own else '-'}（共 {len(own)} 条）｜leave 指令 {lv or '-'}｜离场 {pl['leftT']}"
              + (f"（当时 {a[1]} 格/{k(a[2])}）" if a else '') + f"｜峰值 {pk[0]}@{pk[1]}｜阵亡 {pl['deathT']}" + (f"（前 10 拍 {d[1]} 格/{k(d[2])}）" if d else ''))
    print('   掉线号空壳期（leave 之后）的地：')
    for p, s in SQ.items():
        pl = P[p]
        if pl['leftT'] < 0: continue
        pts = [s10_at(p, t) for t in range(pl['leftT'], pl['deathT'] + 1, 300)]
        print(f"      {s['bot']}: " + '；'.join(f't={x[0]} {x[1]} 格/{k(x[2])}' for x in pts if x))

if 'D' in sec:
    print('\n== D 开局上行：[HL-OPENING] 决策拍 对 录像落地拍 ==')
    cm = collections.defaultdict(list)
    for r in csv.DictReader(open(f'/tmp/c136-r05/work/{M}-cmds.tsv', encoding='utf-8'), delimiter='\t'):
        if r['kind'] == 'attack' and 0 <= int(r['tick']) < 700: cm[r['name']].append((int(r['tick']), int(r['a'])))
    for p, s in SQ.items():
        bot = s['bot']
        op = [(int(m.group(1)), int(m.group(2)), int(m.group(3))) for ln in log for m in [re.search(r'\[' + re.escape(bot) + r'\] \[HL-OPENING\] t=(\d+) cyc=(\d+) .*?terr=(\d+)', ln)] if m and int(m.group(1)) < 650]
        land = cm.get(bot, [])
        first = land[0][0] if land else None
        print(f"   {bot}: 开局决策拍 {[t for t, _, _ in op][:8]}（决策时的地 {[x for _, _, x in op][:8]}）｜录像落地拍 {[t for t, _ in land][:10]}｜第一条落地 − 第一条决策 = {first - op[0][0] if first is not None and op else '-'} 拍")

if 'E' in sec:
    print('\n== E 各号 地/兵/密度（S10）==')
    for p, s in SQ.items():
        row = []
        for t in (600, 900, 1200, 1500, 1800, 2100, 2400, 3000, 3600, 4200, 4800, 5400, 6000):
            x = s10_at(p, t)
            if x and x[0] >= t - 10 and x[1] > 0: row.append(f't={t} {x[1]}/{k(x[2])}/{x[2] / max(1, x[1]):.0f}')
        print(f"   {s['bot']}(T{s['team']}): " + '；'.join(row))
