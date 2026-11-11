#!/usr/bin/env python3
"""tick_attrib.py — 600–1500（或任意窗口）每个号每个决策拍的归因（广播 0007 第 3 条的三层归因）。全部机械计数。

输入：
  /tmp/c136-r05/work/<id>-shadow.json   由 node scripts/shadow.mjs <id> --quiet --tc 600:1500 --json … 生成（tc[] = 决策拍分类）
  /tmp/c136-r05/work/<id>-delay.json    由 python3 scripts/delay_account.py <id> --json … 生成（decisions[] = 每条影子决策的下场）
  /tmp/c136-r05/work/<id>-land.json     由 node scripts/land_account.mjs <id> --json … 生成（可选：出生份额）

每个 (号 × 决策拍) 只归一类（决策拍 = 策略每 5 拍真正走到出手判断的那一拍；客户端没跑到的拍不计）：
  发了指令（影子当拍发出陆攻/出船）→ 按这条指令的下场再分：
      有效 = 落地且照原目标打出；迟到·目标已死 = 落地时目标已死（被改写成中立或落空）；迟到·不接壤 = 目标还在但落空；没落地 = 始终没出现在录像里
  没发指令 →
      留底锁·无在途 = 贴着机器人、没有任何机器人目标过得了留底（可用兵 = 存兵 − floorFor(目标, floorAt(每格价)) 不够最小一条），且当拍自己没有任何进攻在途
      留底·有在途   = 同上，但当拍已有进攻在途（兵在外面，存兵本来就少；不算纯锁）
          两类里另数：safeFinite ≥ 一半存兵的有多少（留底由邻居兵力定：我方号 / 路人队友 / 敌方真人 / 机器人），其余是价格项/开局预留/最小指令等
      有目标没发 = 贴着机器人、至少一个目标过得了留底，但当拍没发（多数是已有进攻在途）
      只剩中立边 = 不贴机器人、还有中立边，没发
      只贴敌方真人 = 不贴机器人、没有中立边、贴着敌方真人（1500 拍前策略没有打真人的分支）
      围在里面 = 四周只有队友或水
三层合计：
  ① 结构（出生位置/被围）= 只贴敌方真人 + 围在里面        ② 策略留底 = 留底锁·无在途 + 留底·有在途（纯锁只算前者）
  ③ 执行（迟到/没到）= 迟到·目标已死 + 迟到·不接壤 + 没落地   有效 = 有效；其余 = 有目标没发 + 只剩中立边
  --exits：没发指令的各类决策拍，影子当拍走到哪个函数的哪一行返回（出口行前 6 个）。留底复刻是按 Vb 写的，
           别的版本（c110 / Va）「有目标没发」偏多时，用这一项看实际是哪道门没过。
用法：python3 scripts/tick_attrib.py <matchId> [--json FILE] [--by-bot] [--exits]
"""
import json
import os
import sys
from collections import Counter, defaultdict

a = sys.argv[1:]
mid = a[0]
W = '/tmp/c136-r05/work'
S = json.load(open(f'{W}/{mid}-shadow.json'))
Dl = json.load(open(f'{W}/{mid}-delay.json'))
tc = S.get('tc') or []
if not tc:
    print(f'{mid}: shadow JSON 里没有 tc[]（先跑 shadow.mjs --tc 600:1500 --json）')
    sys.exit(1)
T0, T1 = S['tcWin']
last = Dl.get('lastLocalTick', {})
dec = {(d[0], d[1]): d for d in Dl['decisions']}
pc = lambda x, y: f'{100 * x / y:.1f}%' if y else '-'
k = lambda v: (f'{v / 1e6:.2f}M' if abs(v) >= 1e6 else f'{v / 1e3:.0f}k' if abs(v) >= 1e4 else f'{v:.0f}')
CATS = ['有效', '迟到·目标已死', '迟到·不接壤', '没落地', '留底锁·无在途', '留底·有在途', '有目标没发', '只剩中立边', '只贴敌方真人', '围在里面']
LAYER = {'有效': '有效', '迟到·目标已死': '③执行', '迟到·不接壤': '③执行', '没落地': '③执行', '留底锁·无在途': '②留底', '留底·有在途': '②留底', '有目标没发': '其余', '只剩中立边': '其余', '只贴敌方真人': '①结构', '围在里面': '①结构'}
half = Counter()
cnt = Counter()
by_bot = defaultdict(Counter)
setter = Counter()
busy = Counter()
issued_cls = defaultdict(Counter)
bank = defaultdict(list)
skipped = 0
rows = 0
exits = defaultdict(Counter)
gates = defaultdict(Counter)
gaex = defaultdict(Counter)
psx = defaultdict(Counter)      # 没发指令的拍里 Policy.send 被调用过：出口行（配额闸拒发等）
psbot = defaultdict(Counter)
nfs_rows = Counter()            # isNoFullSend=1 的决策拍数（全部决策拍 / 没发指令的）
for r in tc:
    b, t = r['bot'], r['t']
    if t > last.get(b, 10 ** 9):
        skipped += 1
        continue
    rows += 1
    cmds = [c for c in r['cmds'] if c[0] in ('attack', 'boat', 'boatTo')]
    if cmds:
        d = dec.get((b, t))
        st = d[4] if d else 'lost'
        cat = {'hit': '有效', 'dead': '迟到·目标已死', 'void': '迟到·不接壤', 'lost': '没落地'}[st]
        issued_cls[cat][d[3] if d else '?'] += 1
    elif r['nBot'] > 0:
        if r['canHit'] > 0:
            cat = '有目标没发'
        else:
            cat = '留底·有在途' if (r['busyBot'] or r['busyNeut']) else '留底锁·无在途'
            if r['sb'] is not None and r['sb'] >= 0.5 * r['B']:
                half[cat] += 1
                setter[r['setter'] or '(无)'] += 1
    elif r['neut'] > 0:
        cat = '只剩中立边'
    elif r['nEH'] > 0:
        cat = '只贴敌方真人'
    else:
        cat = '围在里面'
    if not cmds and (r['busyBot'] or r['busyNeut']):
        busy[cat] += 1
    cnt[cat] += 1
    if not cmds:
        exits[cat][r.get('exit') or '?'] += 1
        if r.get('pt') is not None or r.get('ga') is not None:
            pt = set(int(x) for x in (r.get('pt') or []))
            # pickTarget 循环里各道门（行号各版本相同的相对位置：c110 1192/1193/1195/1197/1199/1200/1202；Va/Vb 行号差几行，按出现的行号原样列）
            gates[cat][','.join(str(x) for x in sorted(pt)) or '(循环里没有 continue)'] += 1
            gaex[cat][str(r.get('ga'))] += 1
        if r.get('ps'):
            key = 'Policy.send ' + ','.join(str(x) for x in r['ps']) + (' → Strategy.send ' + ','.join(str(x) for x in r['ss']) if r.get('ss') else ' → 没到 Strategy.send') + ('｜isNoFullSend=1' if r.get('nfs') else '｜isNoFullSend=0')
            psx[cat][key] += 1
            psbot[b][key] += 1
    if r.get('nfs') is not None:
        nfs_rows['all'] += 1
        if r.get('nfs'): nfs_rows['nfs1'] += 1
        if not cmds and r.get('nfs'): nfs_rows['nfs1_nocmd'] += 1
    by_bot[b][cat] += 1
    bank[cat].append(r['B'])
print(f'===== {mid} 决策拍归因 t={T0}–{T1}：{rows} 个 (号×决策拍)（另有 {skipped} 个是客户端没跑到的拍，不计）=====')
CN = {'N': '中立', 'B': '机器人', 'H': '真人', 'S': '船', 'D': '捐', '?': '?'}
for c in CATS:
    n = cnt[c]
    ex = ''
    if c in issued_cls:
        ex = '｜目标：' + '、'.join(f'{CN[x]} {v}' for x, v in issued_cls[c].most_common())
    if c in ('留底锁·无在途', '留底·有在途'):
        ex = f'｜其中 safeFinite ≥ 一半存兵的 {half[c]}'
    elif busy[c]:
        ex += f'｜其中当拍已有进攻在途的 {busy[c]}'
    print(f'   {c}: {n}（{pc(n, rows)}）{ex}')
lay = Counter()
for c, n in cnt.items():
    lay[LAYER[c]] += n
if setter:
    print(f'   safeFinite ≥ 一半存兵的 {sum(half.values())} 个留底拍，留底由谁的兵力定：' + '、'.join(f'{x} {v}' for x, v in setter.most_common()))
print('   三层合计：' + '；'.join(f'{x} {lay[x]}（{pc(lay[x], rows)}）' for x in ('①结构', '②留底', '③执行', '有效', '其余')))
iss = sum(cnt[c] for c in ('有效', '迟到·目标已死', '迟到·不接壤', '没落地'))
print(f'   发了指令的 {iss} 个决策拍里：有效 {pc(cnt["有效"], iss)}、迟到·目标已死 {pc(cnt["迟到·目标已死"], iss)}、迟到·不接壤 {pc(cnt["迟到·不接壤"], iss)}、没落地 {pc(cnt["没落地"], iss)}')
OUT = {'matchId': mid, 'window': [T0, T1], 'rows': rows, 'skipped': skipped, 'cats': {c: cnt[c] for c in CATS}, 'layers': dict(lay), 'floorSetter': dict(setter), 'busy': dict(busy), 'safeFiniteHalf': dict(half),
       'issuedByClass': {c: dict(v) for c, v in issued_cls.items()}, 'byBot': {b: {c: v[c] for c in CATS} for b, v in by_bot.items()}}
# 兵的口径：窗口内落地的「目标已死」指令打出多少、退回多少（delay JSON 的 lateVoid）
lv = [x for x in Dl.get('lateVoid', []) if x['period'] == '600–1500']
if lv and T0 == 600 and T1 == 1500:
    x = lv[0]
    for c, nm in (('B', '机器人'), ('H', '真人')):
        if c in x:
            y = x[c]
            print(f'   兵的口径（按落地拍 600–1500，决策目标={nm}）：照打 {y["hit"]} 条打出 {k(y["hitOut"])}、退回 {k(y["hitRet"])}（{pc(y["hitRet"], y["hitOut"])}）'
                  f'｜目标已死 {y["rewrittenOk"] + y["rewrittenVoid"]} 条：打到中立 {k(y["rewrittenOut"])}＋手续费 {k(y["rewrittenFee"])}、退回 {k(y["rewrittenRet"])}（{pc(y["rewrittenRet"], y["rewrittenOut"])}），落空 {y["rewrittenVoid"]} 条；目标在但不接壤落空 {y["void"]} 条')
    OUT['troops600_1500'] = x
lp = f'{W}/{mid}-land.json'
if os.path.exists(lp):
    L = json.load(open(lp))
    v = L['voronoi']
    print(f'   结构旁证（出生份额）：我方号名下 {v["squadCells"]} 格 = 全图 {100 * v["landShare"]:.1f}%，人数占 {100 * v["headShare"]:.1f}% → 份额÷人数 {v["ratio"]:.2f}；每号中位 {v["squadMedian"]:.0f} 对其他真人 {v["othersMedian"]:.0f}')
    OUT['voronoiRatio'] = v['ratio']
if '--exits' in a:
    print('   -- 没发指令的决策拍，影子当拍的出口（函数:行；前 6 个）')
    for c in CATS:
        if exits.get(c):
            print(f'      {c}（{sum(exits[c].values())}）: ' + '；'.join(f'{x} ×{v}' for x, v in exits[c].most_common(6)))
    OUT['exits'] = {c: dict(v.most_common(12)) for c, v in exits.items()}
    if gates:
        print('   -- 没发指令的决策拍：General.act 的出口行｜pickTarget 循环里命中过的 continue 行组合（前 6 个）')
        for c in CATS:
            if gates.get(c):
                print(f'      {c}（{sum(gates[c].values())}）: 出口 ' + '、'.join(f'L{x} ×{v}' for x, v in gaex[c].most_common(4)) + '｜continue 行 ' + '；'.join(f'[{x}] ×{v}' for x, v in gates[c].most_common(6)))
        OUT['ptGates'] = {c: dict(v.most_common(12)) for c, v in gates.items()}
        OUT['gaExit'] = {c: dict(v) for c, v in gaex.items()}
    if psx:
        tot = sum(sum(v.values()) for v in psx.values())
        print(f'   -- 没发指令、但当拍调用过 Policy.send 的决策拍 {tot} 个（{100 * tot / max(1, rows):.1f}%；send 返回 false）：Policy.send 出口行 → 最底层 Strategy.send 出口行｜当拍 isNoFullSend')
        for c in CATS:
            if psx.get(c):
                print(f'      {c}（{sum(psx[c].values())}）: ' + '；'.join(f'[{x}] ×{v}' for x, v in psx[c].most_common(6)))
        print('      逐号：' + '；'.join(f'{b} {sum(v.values())}' for b, v in sorted(psbot.items(), key=lambda kv: -sum(kv[1].values()))))
        OUT['sendRefused'] = {'rows': tot, 'share': tot / max(1, rows), 'byCat': {c: dict(v) for c, v in psx.items()}, 'byBot': {b: sum(v.values()) for b, v in psbot.items()}}
    if nfs_rows['all']:
        print(f"   -- isNoFullSend=1 的决策拍 {nfs_rows['nfs1']}/{nfs_rows['all']}（{100 * nfs_rows['nfs1'] / nfs_rows['all']:.1f}%）；其中没发指令的 {nfs_rows['nfs1_nocmd']}")
        OUT['noFullSendRows'] = dict(nfs_rows)
if '--by-bot' in a:
    print('   -- 逐号（决策拍数：' + ' / '.join(CATS) + '）')
    for b, v in by_bot.items():
        n = sum(v.values())
        print(f'      {b}（{n}）: ' + ' / '.join(str(v[c]) for c in CATS) + '｜' + '、'.join(f'{x} {pc(sum(v[c] for c in CATS if LAYER[c] == x), n)}' for x in ('①结构', '②留底', '③执行', '有效')))
if '--json' in a:
    json.dump(OUT, open(a[a.index('--json') + 1], 'w'), ensure_ascii=False)
