#!/usr/bin/env python3
"""recon_facts.py — 把复盘“兵力对账”一节反复要用的几组汇总数一次算出来（都只读 out/<mid>/ 下已有的表）。
用法: python3 recon_facts.py <matchId> [--section dispatch,siege,husk,slot,safe,ainb,doomed] [--siege bot:t0:t1[,bot:t0:t1..]]
  dispatch  日志调度 vs 录像：总数、落地、按配额时代、按捐出方、pct 分布、被拒单的 名义额/配额余量
  siege     某号在 [t0,t1] 里收到的调度：按捐出方的条数、落地、名义额、到账；配额台阶
  husk      离场壳：每个离场的人类席位离场时的领土/兵力，之后本队各号从它身上拿了多少格、花了多少兵，以及它的地最后归谁
  slot      1500 拍后 pct=47 的中立令条数；同拍第二条指令被拒（名额被占）的清单
  safe      保底线计数：1500 拍前后 bySafe / byKeep / byPx 的决策拍数
  ainb      1500 拍后身边有 AI/离场壳邻居的 100 拍窗口：决策拍、发令、过了价格线又被后面的闸门拦下的拍数
  doomed    本队各号挨打时 来兵/余额 的最大值，以及 isDoomedPocket 两个分支各自成立的采样点数（30 拍采样）
  peak      每个阵亡号死时的领土、余额，和按引擎规则（领土 ≤ 峰值/4 即清除）重算的峰值
"""
import csv, json, os, statistics, sys
from collections import defaultdict, Counter

HERE = os.path.dirname(os.path.abspath(__file__))


def load(mid, name):
    p = os.path.join(HERE, '..', 'out', mid, name)
    if not os.path.exists(p):
        return []
    with open(p, newline='', encoding='utf8') as f:
        return list(csv.DictReader(f))


def I(x):
    try:
        return int(float(x))
    except (ValueError, TypeError):
        return 0


def sec_dispatch(mid, meta):
    rows = load(mid, 'dispatch_audit.csv')
    if not rows:
        print('（没有 dispatch_audit.csv）'); return
    ex = [r for r in rows if r['executed'] == '1']
    print(f"== 调度对账：日志 {len(rows)} 条，录像落地 {len(ex)} 条，没落地 {len(rows) - len(ex)} 条")
    c = Counter((r['would'], r['executed']) for r in rows)
    for (w, e), n in sorted(c.items()):
        print(f"   按决策拍状态引擎会 {w:7s} 落地={e}: {n}")
    print('   按决策拍分段（条数/落地）：', end='')
    for lo, hi, name in ((0, 2141, '<2142'), (2142, 3212, '2142–3212'), (3213, 4283, '3213–4283'), (4284, 10 ** 9, '≥4284')):
        seg = [r for r in rows if lo <= I(r['t']) <= hi]
        print(f" {name} {len(seg)}/{sum(1 for r in seg if r['executed'] == '1')}", end='')
    print()
    rej = [r for r in rows if r['executed'] != '1']
    zero = [r for r in rej if I(r['maxByQuota']) <= 0 and r['would'] == 'quota']
    ratio = [I(r['nominal']) / I(r['maxByQuota']) for r in rej if r['would'] == 'quota' and I(r['maxByQuota']) > 0]
    print(f"   没落地的：配额余量为 0 的 {len(zero)} 条；余量 >0 的 {len(ratio)} 条里 名义额/余量 中位 {statistics.median(ratio):.2f}" if ratio else f"   没落地的：配额余量为 0 的 {len(zero)} 条")
    print(f"   名义额：没落地合计 {sum(I(r['nominal']) for r in rej)}，落地合计 {sum(I(r['nominal']) for r in ex)}；落地到账 {sum(I(r['received']) for r in ex)}，捐出方实付 {sum(I(r['paid']) for r in ex)}")
    lags = [I(r['lag']) for r in ex if r['lag'] != '']
    if lags:
        print(f"   落地的延迟：中位 {statistics.median(lags)}，最大 {max(lags)}")
    print('   按捐出方（条数/落地/落地到账）：' + '；'.join(f"{b} {len(v)}/{sum(1 for r in v if r['executed'] == '1')}/{sum(I(r['received']) for r in v)}" for b, v in sorted(group(rows, 'bot').items(), key=lambda kv: -len(kv[1]))))
    print('   按受赠方（条数/落地/落地到账）：' + '；'.join(f"{b.strip(chr(34))} {len(v)}/{sum(1 for r in v if r['executed'] == '1')}/{sum(I(r['received']) for r in v)}" for b, v in sorted(group(rows, 'toName').items(), key=lambda kv: -len(kv[1]))))
    print('   按类型（条数/落地/落地到账）：' + '；'.join(f"{b} {len(v)}/{sum(1 for r in v if r['executed'] == '1')}/{sum(I(r['received']) for r in v)}" for b, v in sorted(group(rows, 'kind').items(), key=lambda kv: -len(kv[1]))))
    print('   pct 分布：' + '；'.join(f"{k}×{n}" for k, n in Counter(r['pct'] for r in rows).most_common(8)))
    low = [r for r in ex if I(r['dMe']) < I(r['dAlly'])]
    print(f"   落地的里，决策拍捐出方密度 < 受赠方密度：{len(low)} 条（到账 {sum(I(r['received']) for r in low)}）")


def group(rows, key):
    g = defaultdict(list)
    for r in rows:
        g[r[key]].append(r)
    return g


def sec_siege(mid, meta, spec):
    rows = load(mid, 'dispatch_audit.csv')
    for item in spec.split(','):
        bot, t0, t1 = item.split(':'); t0 = int(t0); t1 = int(t1)
        seat = str(meta['squad'][bot])
        seg = [r for r in rows if r['to'] == seat and t0 <= I(r['t']) <= t1]
        print(f"== {bot} 在 {t0}–{t1} 拍收到的调度：{len(seg)} 条，落地 {sum(1 for r in seg if r['executed'] == '1')} 条，到账 {sum(I(r['received']) for r in seg)}；没落地的名义额 {sum(I(r['nominal']) for r in seg if r['executed'] != '1')}")
        for b, v in sorted(group(seg, 'bot').items()):
            q = [I(r['maxByQuota']) for r in v]
            print(f"   {b:8s} 发 {len(v):3d} 落地 {sum(1 for r in v if r['executed'] == '1'):2d} 名义额 {sum(I(r['nominal']) for r in v):9d} 到账 {sum(I(r['received']) for r in v):8d} 决策拍密度 {min(I(r['dMe']) for r in v)}–{max(I(r['dMe']) for r in v)} 当拍配额还能放 {min(q)}–{max(q)}")
        seen = set()
        for r in seg:
            k = (r['cap'], r['used'])
            if k in seen:
                continue
            seen.add(k)
            print(f"   配额台阶 t={r['t']} cap={r['cap']} used={r['used']} 还能放 {r['maxByQuota']}（150 倍上限余量 {r['room']}）；这条 {r['bot']} 名义 {r['nominal']} → {r['would']}，落地={r['executed']}")


def sec_husk(mid, meta):
    ev = load(mid, 'resim_events.csv'); pairs = load(mid, 'resim_pairs.csv'); mt = load(mid, 'shadow_match.csv')
    names = meta['names']; seat = {v: k for k, v in meta['squad'].items()}
    left = [e for e in ev if e['ev'] == 'left' and I(e['p']) not in seat and I(e['terr']) >= 1000]
    print('== 离场壳（离场时 ≥1000 格的人类席位；“本队拿到”= 离场所在采样窗及之后 resim_pairs 里本队号从它身上拿的格数）')
    for e in left:
        q = I(e['p']); t = I(e['t'])
        got = defaultdict(int)
        for r in pairs:
            if I(r['victim']) == q and I(r['attacker']) in seat and I(r['t1']) > t:
                got[seat[I(r['attacker'])]] += I(r['px'])
        spend = defaultdict(lambda: [0, 0])
        for x in mt:
            if x['kind'] == 'attack' and x['applied'] == '1' and I(x['shTarget']) == q and I(x['tick']) >= t:
                spend[x['bot']][0] += 1; spend[x['bot']][1] += I(x['spent'])
        end = next((d for d in ev if I(d['p']) == q and d['ev'] == 'died' and I(d['t']) >= t), None)
        if not got and not spend and not any(str(q) + ':' in (r.get('huskNb') or '') for r in []):
            touching = False
        fate = ''
        if end:
            tl = [x for x in (end['detail'].split('tookLife=')[1] if 'tookLife=' in end['detail'] else '').split('|') if x]
            fate = f"；{end['t']} 拍被吃光，全程拿它地最多的：" + '、'.join(f"{names[I(x.split(':')[0])] if I(x.split(':')[0]) < len(names) else 'AI#' + x.split(':')[0]} {x.split(':')[1]}" for x in tl[:3])
        if got or spend:
            print(f"   {names[q]}（T{e['team']}）{t} 拍离场：{e['terr']} 格、{e['bal']} 兵（密度 {I(e['bal']) / max(1, I(e['terr'])):.1f}）；本队拿到 " + ('、'.join(f"{b} {n}" for b, n in got.items()) or '0') + '；离场后本队对它的进攻 ' + ('、'.join(f"{b} {n} 条实扣 {s}" for b, (n, s) in spend.items()) or '0 条') + fate)


def sec_slot(mid, meta):
    rows = load(mid, 'shadow_cmds.csv')
    n47 = [r for r in rows if r['kind'] == 'attack' and r['targetName'].strip('"') == 'NEUTRAL' and r['pct'] == '47' and I(r['t']) >= 1500]
    print(f"== pct=47 中立令（1500 拍后）：{len(n47)} 条，受理 {sum(1 for r in n47 if r['ok'] == '1')} 条")
    rej = [r for r in rows if r['ok'] == '0']
    print(f"   同拍第二条被拒的指令：{len(rej)} 条；其中 1500 拍后 {sum(1 for r in rej if I(r['t']) >= 1500)} 条")
    for r in rej:
        if I(r['t']) >= 1500:
            print(f"   t={r['t']} {r['bot']} {r['kind']} → {r['targetName']} 想出 {r['troops']}")


def sec_safe(mid, meta):
    rows = load(mid, 'shadow_idle.csv')
    for name, f in (('1500 拍前', lambda t: t < 1500), ('1500 拍及以后', lambda t: t >= 1500)):
        seg = [r for r in rows if f(I(r['t0']))]
        print(f"== {name}：决策拍 {sum(I(r['acts']) for r in seg)}，发令 {sum(I(r['cmd']) for r in seg)}，保底线取自 safeFinite {sum(I(r['bySafe']) for r in seg)}、取自 keep {sum(I(r['byKeep']) for r in seg)}、取自每格价 {sum(I(r['byPx']) for r in seg)}；价格线 {sum(I(r['oPrice']) for r in seg)}，过了价格线被后面的闸门拦下 {sum(I(r['oGate']) for r in seg)}，围死 {sum(I(r['boxed']) for r in seg)}")


def sec_ainb(mid, meta):
    rows = load(mid, 'shadow_idle.csv')
    print('== 1500 拍后身边有 AI/离场壳邻居的 100 拍窗口（aiNb = 窗口内平均邻居数，aiLand = 它们的领土，aiDens = 密度）')
    tot = [0, 0, 0]
    for r in rows:
        if I(r['t0']) >= 1500 and float(r['aiNb'] or 0) > 0:
            tot[0] += I(r['acts']); tot[1] += I(r['cmd']); tot[2] += I(r['oGate'])
            print(f"   {r['bot']:8s} {r['t0']:>5s} 决策拍 {r['acts']:>2s} 发令 {r['cmd']:>2s} 价格线 {r['oPrice']:>2s} 闸门 {r['oGate']:>2s} aiNb {r['aiNb']} aiLand {r['aiLand']} aiDens {r['aiDens']} 自己密度 {r['dens']}")
    print(f"   合计：决策拍 {tot[0]}，发令 {tot[1]}，闸门 {tot[2]}")


def parse_pairs(s):
    out = []
    for x in (s or '').split('|'):
        if ':' in x:
            a = x.split(':'); out.append([I(v) for v in a])
    return out


def sec_doomed(mid, meta):
    rows = load(mid, 'resim_squad.csv')
    humans = meta['humans']
    by_t = defaultdict(list)
    for r in rows:
        if r['alive'] == '1' and r['state'] != '2':
            by_t[I(r['t'])].append(r)
    res = defaultdict(lambda: [0, 0, 0.0, 0])
    for t, rs in by_t.items():
        mx = max(I(r['terr']) for r in rs)
        for r in rs:
            inatk = sum(v[1] for v in parse_pairs(r['atkIn']) if v[0] < humans)
            bal = max(1, I(r['bal']))
            if inatk <= 0:
                continue
            a = res[r['bot']]
            ratio = inatk / bal
            if ratio > a[2]:
                a[2] = ratio; a[3] = t
            if inatk > 1.65 * bal:
                a[0] += 1
            elif t >= 4500 and I(r['terr']) < 0.22 * mx and inatk > 0.45 * bal:
                a[1] += 1
    print('== isDoomedPocket 条件（按采样点；来兵只算人类席位）：第一分支 来兵 > 1.65×余额；第二分支 t≥4500 且 领土 < 0.22×本队最大号 且 来兵 > 0.45×余额')
    for b, a in sorted(res.items()):
        print(f"   {b:8s} 第一分支 {a[0]:3d} 个采样点，只满足第二分支 {a[1]:3d} 个；来兵/余额 最大 {a[2]:.2f}（t={a[3]}）")


def sec_peak(mid, meta):
    """引擎的阵亡判定（game.js aliveTick L1298–1312）：领土 <= 峰值/4 → collapse；峰值在领土低于它时每拍回落 max(1, (峰值-领土)//1000)。
    这里用 resim_squad.csv 的采样（两个采样点之间领土按前一个采样点算）近似重算峰值，核对每个阵亡号死时的 领土/峰值。"""
    rows = load(mid, 'resim_squad.csv'); ev = load(mid, 'resim_events.csv')
    seat = {v: k for k, v in meta['squad'].items()}
    by = defaultdict(list)
    for r in rows:
        if r['alive'] == '1':
            by[r['bot']].append((I(r['t']), I(r['terr'])))
    print('== 阵亡时的领土与峰值（引擎：领土 ≤ 峰值/4 即整号清除，余下的地和兵一起清零）')
    tot_t = tot_b = 0
    for e in ev:
        if e['ev'] != 'died' or I(e['p']) not in seat:
            continue
        bot = seat[I(e['p'])]; td = I(e['t']); pts = [x for x in by[bot] if x[0] <= td]
        mx = max(pts, key=lambda x: x[1])
        peak = 0
        for (t0, v0), (t1, _) in zip(pts, pts[1:] + [(td, 0)]):
            for _i in range(max(0, t1 - t0)):
                if v0 >= peak:
                    peak = v0
                else:
                    peak -= max(1, (peak - v0) // 1000)
        tot_t += I(e['terr']); tot_b += I(e['bal'])
        print(f"   {bot:8s} 阵亡 t={td} 剩 {e['terr']:>6s} 格 {e['bal']:>8s} 兵；最大领土 {mx[1]}（t={mx[0]}），按采样重算的峰值约 {peak} → 峰值/4 ≈ {peak // 4}；死时领土/最大领土 = {I(e['terr']) / max(1, mx[1]):.2f}")
    print(f"   合计：阵亡时还剩 {tot_t} 格、{tot_b} 兵")


def main():
    a = sys.argv[1:]
    mid = a[0]
    opt = lambda k, d=None: a[a.index('--' + k) + 1] if '--' + k in a else d
    meta = json.load(open(os.path.join(HERE, '..', 'out', mid, 'resim_meta.json')))
    secs = (opt('section') or 'dispatch,husk,slot,safe,ainb,doomed').split(',')
    if opt('siege') and 'siege' not in secs:
        secs.append('siege')
    for s in secs:
        if s == 'dispatch': sec_dispatch(mid, meta)
        elif s == 'siege': sec_siege(mid, meta, opt('siege') or '')
        elif s == 'husk': sec_husk(mid, meta)
        elif s == 'slot': sec_slot(mid, meta)
        elif s == 'safe': sec_safe(mid, meta)
        elif s == 'ainb': sec_ainb(mid, meta)
        elif s == 'doomed': sec_doomed(mid, meta)
        elif s == 'peak': sec_peak(mid, meta)
        print()


if __name__ == '__main__':
    main()
