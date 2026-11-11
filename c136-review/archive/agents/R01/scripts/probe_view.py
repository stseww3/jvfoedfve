#!/usr/bin/env python3
"""probe_view.py — 把 shadow.mjs --probe 打出的 shadow_probe[_tag].txt 压成每个决策拍一行：
状态（余额/领土/密度）、offers() 里每个报价（目标、单价 c、要的兵 need、onMe、来袭兵 inAtk、nearCollapse/bleeding/crowdedHard），
以及 buyLand()/tryDonateToTeammate()/idleBoats() 的返回值。
用法：python3 probe_view.py <matchId> [--tag x] [--t0 a --t1 b] [--every 5] [--names]
      python3 probe_view.py <matchId> --tag x --pick [--t0 a --t1 b] [--every 50]
        --pick：1500 拍前（走 Style.pickTarget 的决策拍）逐邻居列 allow / 每格价 / floorFor / avail / minShare×余额，末尾按邻居汇总卡在哪一关。
      python3 probe_view.py <matchId> --tag x --gate <席位> [--t0 a --t1 b]
        --gate：只看对某个目标的报价，逐决策拍复算 buyLand 的几道闸门（v27-team-c116-vb.js L5350–5359、L5414–5447、L5594–5605）：
        worth = 0.5×winRatio×refDens（refDens：2500 拍起取 max(自己密度, 0.85×其他真人密度中位)）；
        预算 = max(0, (worthOwn×领土 − 手续费×m − c×领土)/(1+m))，m = 0.5×winRatio，worthOwn 在 4000 拍后（目标不是 nearCollapse 时）取 m×自己密度；
        价格 keep = max(c×领土/m（nearCollapse 的真人打 7 折）, 余额 − 手续费 − 预算)，c < cheap(=0.1/baseRate) 时为 0；c ≥ worth 时没有价格 keep（记 inf，除非 over）；
        over（余额 > 100×领土）时 keep 不超过 0.9×100×领土（密度 ≥122 时 0.82；isSoleHealthyBuffer 的 1.12 探针里看不到，没有算）；
        保底 = safeAt(目标)，非真人 / nearCollapse / bleeding / tD<0.45 的目标再封顶 88×领土；keep = max(价格 keep, 保底)；avail = 余额 − 手续费 − keep；
        Va（A003/A005/A009，v27-team-c116-va.js L5413–5425）与 Vb 的三处不同已按局号自动切换：封顶 78×领土（Vb 88）；
        封顶只对非真人 / nearCollapse 的目标生效（Vb 还包括 bleeding / tD<0.45）；价格 keep 的 7 折对 nearCollapse / bleeding / tD<0.48 的真人都生效（Vb 只对 nearCollapse）。
        末尾另打一行汇总：决策拍数、卡在价格线（c ≥ worth 且不 over）、过了价格线但 avail ≤ 0（其中 keep 取自 safeAt 的）、avail > 0 但没出手、出手。
        20% 线 = chunk(0.2)×余额：非真人分支和预算分支凑不够 want 且 x 低于它就不发；脉冲想出的兵 ≥ 1.2×need（不含 3×接壤格数）；最小出兵量 = max(4×手续费, 0.04×余额)。
"""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
a = sys.argv[1:]
mid = a[0]
opt = lambda k, d=None: a[a.index('--' + k) + 1] if '--' + k in a else d
tag = opt('tag', '')
t0, t1, every = int(opt('t0', 0)), int(opt('t1', 10**9)), int(opt('every', 5))
fn = os.path.join(HERE, '..', 'out', mid, 'shadow_probe' + ('_' + tag if tag else '') + '.txt')
meta = json.load(open(os.path.join(HERE, '..', 'out', mid, 'resim_meta.json')))
names = meta['names']
def nm(q):
    q = int(q)
    return (names[q].replace('[APEX] ', '')[:14] if q < len(names) else 'AI#%d' % q)
cur = {}
order = []
for line in open(fn, encoding='utf8'):
    m = re.match(r't=(\d+) (.*)', line.rstrip('\n'))
    if not m: continue
    t = int(m.group(1)); rest = m.group(2)
    if t < t0 or t > t1: continue
    d = cur.setdefault(t, {})
    if t not in order: order.append(t)
    if rest.startswith('offers() -> '):
        try: d['offers'] = json.loads(rest[len('offers() -> '):])
        except Exception: d['offers_raw'] = rest[:200]
    elif rest.startswith('buyLand() -> '): d['buy'] = rest[len('buyLand() -> '):]
    elif rest.startswith('tryDonateToTeammate() -> '): d['don'] = rest[len('tryDonateToTeammate() -> '):]
    elif rest.startswith('状态 '): d.setdefault('state', rest[3:])
    elif rest.startswith('safeAt('):
        d.setdefault('safe', []).append(rest)
    elif rest.startswith('send('):
        d.setdefault('send', []).append(rest[:120])
    elif rest.startswith('pickTarget('):
        mp = re.match(r'pickTarget\(fn,([\d.eE+-]+|Infinity)\) -> (.*)', rest)
        if mp: d['ptMax'] = float('inf') if mp.group(1) == 'Infinity' else float(mp.group(1)); d['pt'] = mp.group(2)
    elif re.match(r'(allow|price|motive|minShare)\((\d+)\) -> ', rest):
        mp = re.match(r'(allow|price|motive|minShare)\((\d+)\) -> (.*)', rest)
        d.setdefault('pick', {}).setdefault(int(mp.group(2)), {})[mp.group(1)] = mp.group(3)
    elif rest.startswith('floorFor('):
        mp = re.match(r'floorFor\((\d+),([\d.eE+-]+|Infinity)\) -> ([\d.eE+-]+|Infinity)', rest)
        if mp:
            e = d.setdefault('pick', {}).setdefault(int(mp.group(1)), {})
            e['f'] = float('inf') if mp.group(2) == 'Infinity' else float(mp.group(2))
            e['floor'] = float('inf') if mp.group(3) == 'Infinity' else float(mp.group(3))
    elif rest.startswith('winRatio() -> '): d.setdefault('wr', float(rest.split('-> ')[1]))
    elif rest.startswith('otherHumanMedDens() -> '): d.setdefault('med', float(rest.split('-> ')[1]))
    elif rest.startswith('baseRate() -> '): d.setdefault('br', float(rest.split('-> ')[1]))
if '--pick' in a:
    # 1500 拍（coreFrom）之前走 Style.pickTarget（Vb/Va L1144–1177）：逐个邻居 allow → price ≤ maxCost → avail = 余额 − floorFor(q, floorAt(price))
    # → avail ≤ minShare×余额 就跳过。这里把每个决策拍、每个被问到的邻居的这几项列出来，末尾按邻居汇总。
    print(f"== {mid} 探针[{tag}] pickTarget 复算（t < 1500 的决策拍；Style.pickTarget L1144–1177 → V13.floorFor0 L2233–2242）")
    print("      t     余额   领土  密度 | 目标              allow  每格价  maxCost  motive    floorAt(价)   floorFor    avail  minShare×余额 | 卡在 | pickTarget")
    agg = {}
    npick = nnull = 0
    for t in order:
        d = cur[t]
        if 'pt' not in d: continue
        ms = re.match(r'bal=(\d+) terr=(\d+) dens=([\d.]+)', d.get('state', ''))
        if not ms: continue
        B, L = int(ms.group(1)), max(1, int(ms.group(2)))
        npick += 1
        isnull = d['pt'].strip() == 'null'
        if isnull: nnull += 1
        mx = d.get('ptMax', float('inf'))
        for q, e in sorted(d.get('pick', {}).items()):
            if 'allow' not in e: continue
            al = e.get('allow') == 'true'
            price = float(e['price']) if 'price' in e else None
            fl = e.get('floor'); f = e.get('f')
            msh = float(e['minShare']) if 'minShare' in e else None
            avail = (B - fl) if fl is not None else None
            if not al: why = 'allow'
            elif price is not None and price > mx: why = 'maxCost'
            elif avail is not None and msh is not None and avail <= msh * B: why = '保底线'
            elif fl is None: why = '?'
            else: why = '-'
            g_ = agg.setdefault(q, {'n': 0, 'allow': 0, 'maxCost': 0, '保底线': 0, '-': 0, '?': 0, 'B': [], 'floor': [], 'price': [], 'nomotive': 0})
            g_['n'] += 1; g_[why] += 1
            if why == '保底线':
                g_['B'].append(B); g_['floor'].append(fl); g_['price'].append(price)
                if e.get('motive') == 'null': g_['nomotive'] += 1
            if t % every == 0:
                fv = lambda v, w: (f"{v:{w}.0f}" if v is not None and v != float('inf') else f"{'-':>{w}s}")
                print(f"  {t:5d} {B:8d} {L:6d} {B / L:5.1f} | {nm(q):16s} {str(al):5s} {price if price is not None else 0:7.1f} {mx:8.1f}  {str(e.get('motive'))[:8]:8s} {fv(f, 12)} {fv(fl, 10)} {fv(avail, 8)} {fv(msh * B if msh is not None else None, 12)} | {why:6s} | {d['pt'][:40]}")
    print(f"汇总 [{t0},{min(t1, 99999)}]：走到 pickTarget 的决策拍 {npick} 个，其中返回空的 {nnull} 个")
    for q, g_ in sorted(agg.items()):
        s = f"   对 {nm(q)}（席位 {q}）：被问到 {g_['n']} 拍；allow 不过 {g_['allow']}，每格价高于 maxCost {g_['maxCost']}，余额减保底线不到 minShare×余额 {g_['保底线']}（其中 motive 为空的 {g_['nomotive']}），过了这三关 {g_['-']}"
        if g_['B']:
            s += f"；卡在保底线的拍里 余额 {min(g_['B']):.0f}–{max(g_['B']):.0f}，floorFor {min(g_['floor']):.0f}–{max(g_['floor']):.0f}，每格价 {min(g_['price']):.1f}–{max(g_['price']):.1f}"
        print(s)
    sys.exit(0)
if '--safe' in a:
    # 1500 拍前对 AI 地的保底线 winFloor = max(每格价项, dpKeep, safeFinite)（Va/Vb V13.winFloor L2489–2496）。
    # safeFinite（L2500–2510）= 对每个有空槽、没在打我的机器人邻居 q，取 threatOf(q).minOther（L417–445：q 的其他邻居里
    # “余额 + 打在 q 身上的在途兵”最小的一个，q 正在打的那个不算）减去我打在 q 身上的在途兵，再取各 q 的最大值。
    # 探针的“机器人邻居 … 的其他邻居按余额从小到大”行给了每个 q 的前三个其他邻居；这里据此复算出“是谁的余额定了保底线”，
    # 并和探针记下的 winFloor 实际值对一遍（对得上 = 相差 ≤1；对不上的拍多半是 q 贴着无主地被 threatOf 判成 neutral，或我有在途兵）。
    lines = {}
    wf = {}
    for line in open(fn, encoding='utf8'):
        m = re.match(r't=(\d+) (.*)', line.rstrip('\n'))
        if not m: continue
        t = int(m.group(1)); rest = m.group(2)
        if t < t0 or t > t1: continue
        mq = re.match(r'\s*机器人邻居 (.+?)（地(\d+) 兵(\d+) 空槽(\d) 正打我(\d)）的其他邻居按余额从小到大：(.*)$', rest)
        if mq:
            others = []
            for part in mq.group(6).split(' , '):
                mo = re.match(r'(.+)\[T(\S+?)( 壳)?( 正被它打)?\]=(-?\d+)$', part.strip())
                if mo: others.append({'name': mo.group(1), 'team': mo.group(2), 'husk': bool(mo.group(3)), 'hit': bool(mo.group(4)), 'v': int(mo.group(5))})
            lines.setdefault(t, []).append({'q': mq.group(1), 'terr': int(mq.group(2)), 'bal': int(mq.group(3)), 'slot': mq.group(4) == '1', 'onMe': mq.group(5) == '1', 'others': others})
        mw = re.match(r'winFloor\((\d+)\) -> ([\d.eE+-]+)', rest)
        if mw: wf.setdefault(t, []).append(float(mw.group(2)))
        mk = re.match(r'dpKeep\(\) -> ([\d.eE+-]+)', rest)
        if mk: cur.setdefault(t, {})['dpKeep'] = float(mk.group(1))
    my_team = str(meta['teams'][str(next(iter(meta['squad'].values())))])
    print(f"== {mid} 探针[{tag}] 1500 拍前对 AI 地的保底线出自谁（winFloor = max(每格价项, dpKeep, safeFinite)；只列走到 winFloor 的决策拍）")
    print("      t     余额   领土 | winFloor    dpKeep | safeFinite 复算：哪块 AI 地 → 它的其他邻居里余额最小的（不算它正在打的） | 对得上 | 保底线 ≥ 余额")
    cnt = {'n': 0, 'ge': 0, 'match': 0, 'mate': 0, 'foe': 0, 'ai': 0, 'keep': 0, 'px': 0, 'nomatch': 0}
    run = best_run = 0; who = {}
    for t in sorted(wf):
        d = cur.get(t, {}); st = d.get('state', '')
        mB = re.search(r'bal=(\d+) terr=(\d+)', st)
        if not mB: continue
        B, L = int(mB.group(1)), int(mB.group(2))
        floor = max(wf[t]); keep = d.get('dpKeep', 0.0)
        best = None
        for e in lines.get(t, []):
            if not e['slot'] or e['onMe']: continue
            cand = next((o for o in e['others'] if not o['hit']), None)
            if cand and (best is None or cand['v'] > best[1]['v']): best = (e, cand)
        cnt['n'] += 1
        ge = floor >= B
        src = '-'; ok = ''
        if best and abs(best[1]['v'] - floor) <= 1:
            o = best[1]
            kind = 'ai' if o['team'] == '0' else ('mate' if o['team'] == my_team else 'foe')
            src = f"{best[0]['q']}（地{best[0]['terr']} 兵{best[0]['bal']}）→ {o['name']}[T{o['team']}{' 壳' if o['husk'] else ''}]={o['v']}"
            ok = '是'; cnt['match'] += 1
            if ge:
                cnt[kind] += 1; who[o['name']] = who.get(o['name'], 0) + 1
        elif abs(keep - floor) <= 1:
            src = 'dpKeep'; ok = '是'
            if ge: cnt['keep'] += 1
        elif min(wf[t]) != max(wf[t]):
            src = '每格价项（各目标不同）'; ok = '是'
            if ge: cnt['px'] += 1
        else:
            src = (f"复算得 {best[1]['name']}={best[1]['v']}" if best else '没有可算的机器人邻居'); ok = '否'
            if ge: cnt['nomatch'] += 1
        if ge:
            cnt['ge'] += 1; run += 1; best_run = max(best_run, run)
        else:
            run = 0
        if t % every == 0:
            print(f"  {t:5d} {B:8d} {L:6d} | {floor:8.0f} {keep:9.0f} | {src} | {ok} | {'是' if ge else ''}")
    print(f"汇总 [{t0},{min(t1, 99999)}]：走到 winFloor 的决策拍 {cnt['n']} 个，保底线 ≥ 余额的 {cnt['ge']} 个（最长连续 {best_run} 个）；"
          f"其中保底线出自 safeFinite 且复算对得上的：队友的余额 {cnt['mate']}、敌方真人的余额 {cnt['foe']}、别的 AI {cnt['ai']}；出自 dpKeep {cnt['keep']}；出自每格价项 {cnt['px']}；对不上 {cnt['nomatch']}")
    if who:
        print('   定下保底线的席位（保底线 ≥ 余额的拍数）：' + '，'.join(f'{k} {v}' for k, v in sorted(who.items(), key=lambda kv: -kv[1])))
    sys.exit(0)
gate = opt('gate')
if gate is not None:
    gq = int(gate)
    INF = float('inf')
    VA = mid in ('A003', 'A005', 'A009')
    CAP = 78 if VA else 88
    cnt = {'n': 0, 'price': 0, 'noavail': 0, 'bysafe': 0, 'held': 0, 'sent': 0, 'canKill': 0, 'canKillBlocked': 0}
    cs, ws, rs, bs, ss = [], [], [], [], []
    print(f"== {mid} 探针[{tag}] 对 {nm(gq)}（席位 {gq}）的闸门复算")
    print("      t     余额   领土  密度 |  单价c  worth |    need | safeAt(封顶后)    预算  价格keep |    avail    20%线  最小出兵量 | 标记 | buyLand")
    for t in order:
        d = cur[t]
        if 'offers' not in d: continue
        o = [x for x in d['offers'] if int(x['q']) == gq]
        ms = re.match(r'bal=(\d+) terr=(\d+) dens=([\d.]+)', d.get('state', ''))
        if not o or not ms: continue
        o = o[0]
        B, L = int(ms.group(1)), max(1, int(ms.group(2)))
        dMe = B / L
        fee = 12 * B // 1024
        m = 0.5 * d.get('wr', 0)
        ref = max(dMe, 0.85 * d.get('med', 0)) if t >= 2500 else dMe
        worth = m * ref
        over = B > 100 * L
        cheap = 0.1 / d['br'] if d.get('br') else 0
        c, person, nc = o['c'], o.get('person', True), o.get('nearCollapse')
        sv = None
        for s in d.get('safe', []):
            m2 = re.match(r'safeAt\((\d+)\) -> ([\d.eE+-]+)', s)
            if m2 and int(m2.group(1)) == gq: sv = float(m2.group(2)); break
        safe = sv
        if safe is not None and (not person or nc or (not VA and (o.get('bleeding') or o.get('tD', 9) < 0.45))):
            safe = min(safe, CAP * L)
        keep = INF; budget = None
        if c < cheap: keep = 0
        if c < worth and m > 0:
            worth_own = m * dMe if (t >= 4000 and not nc) else worth
            budget = max(0, (worth_own * L - fee * m - c * L) / (1 + m))
            soft = nc or (VA and (o.get('bleeding') or o.get('tD', 9) < 0.48))
            min_keep = (0.7 if (person and soft) else 1.0) * c * L / m
            keep = min(keep, max(min_keep, B - fee - budget))
        if over:
            keep = min(keep, (0.82 if dMe >= 122 else 0.9) * 100 * L)
        pk = keep
        if safe is not None: keep = max(keep, safe)
        avail = (B - fee - keep) if keep != INF else None
        fl = ''.join(k for k, f in (('M', o.get('onMe')), ('N', nc), ('B', o.get('bleeding')), ('H', o.get('isCrowdedHard')), ('O', over), ('A', not person), ('P', o.get('pulseMode'))) if f)
        f0 = lambda v, w: (f"{v:{w}.0f}" if v is not None and v != INF else f"{'-':>{w}s}")
        sent = str(d.get('buy')) == 'true'
        cnt['n'] += 1
        cs.append(c); ws.append(worth); rs.append(c / worth if worth else 0); bs.append(B)
        if safe is not None: ss.append(safe)
        if o['need'] < B: cnt['canKill'] += 1
        n_person = len([x for x in d['offers'] if x.get('person', True)])
        plain = person and not o.get('isDoorSea') and not nc and not o.get('bleeding') and not o.get('onMe')
        if over:
            cnt['over'] = cnt.get('over', 0) + 1
            if sent: cnt['overSent'] = cnt.get('overSent', 0) + 1
            elif plain and o.get('newNbs', 0) > 0 and n_person == 1 and c >= worth and c >= cheap and B < 1.28 * 100 * L:
                cnt['sole'] = cnt.get('sole', 0) + 1
            elif person and not o.get('isDoorSea') and o.get('isCrowdedHard') and c >= worth and c >= cheap and B < 1.26 * 100 * L:
                cnt['hard'] = cnt.get('hard', 0) + 1
        if sent: cnt['sent'] += 1
        elif c >= worth and c >= cheap and not over: cnt['price'] += 1
        elif avail is not None and avail <= 0:
            cnt['noavail'] += 1
            if safe is not None and safe >= pk: cnt['bysafe'] += 1
            if o['need'] < B: cnt['canKillBlocked'] += 1
        else: cnt['held'] += 1
        print(f"  {t:5d} {B:8d} {L:6d} {dMe:5.1f} | {c:6.1f} {worth:6.1f} | {o['need']:7.0f} | {f0(safe, 14)} {f0(budget, 7)} {f0(pk, 9)} | {f0(avail, 8)} {0.2 * B:8.0f} {max(4 * fee, 0.04 * B):9.0f} | {fl:4s} | {d.get('buy')}")
    print('（标记：M=对方正在打我 N=nearCollapse B=bleeding H=isCrowdedHard O=余额过 100 倍领土 A=非真人（离场壳或 AI） P=pulseMode（真人目标走脉冲分支 Vb L5595–5607 / Va L5594–5606，否则走预算分支）；c ≥ worth 且不 over 时 buyLand 在价格线（Vb L5359 / Va L5358）直接退出）')
    print(f"汇总 [{t0},{min(t1, 99999)}] 对 {nm(gq)}：有报价的决策拍 {cnt['n']}；这一拍 buyLand 出手 {cnt['sent']}（不一定是打它）；没出手的：卡在价格线 {cnt['price']}，"
          f"过了价格线但 avail ≤ 0 的 {cnt['noavail']}（其中 keep 取自 safeAt 的 {cnt['bysafe']}），avail > 0 但没出手 {cnt['held']}")
    if cs:
        import statistics as _st
        print(f"   单价 c {min(cs):.1f}–{max(cs):.1f}（中位 {_st.median(cs):.1f}），worth {min(ws):.1f}–{max(ws):.1f}（中位 {_st.median(ws):.1f}），c/worth {min(rs):.2f}–{max(rs):.2f}（中位 {_st.median(rs):.2f}）；"
              f"余额 {min(bs):.0f}–{max(bs):.0f}" + (f"；过了价格线的拍里 safeAt(封顶后) {min(ss):.0f}–{max(ss):.0f}" if ss else ''))
        print(f"   need（策略自己算的、把对方打到阵亡线要的兵）低于本号余额的决策拍 {cnt['canKill']} 个，其中过了价格线却因 avail ≤ 0 没出手的 {cnt['canKillBlocked']} 个")
        print(f"   余额过 100 倍领土的决策拍 {cnt.get('over', 0)} 个：这一拍 buyLand 出手 {cnt.get('overSent', 0)}；没出手的里，按“唯一健康真人邻居”跳过（buyLand L5361–5365：只有它一个真人邻居、它没在掉地也没打我、c ≥ worth、余额 < 128 倍领土）{cnt.get('sole', 0)}，"
              f"按 isCrowdedHard 跳过（L5371–5374，余额 < 126 倍领土）{cnt.get('hard', 0)}")
    sys.exit(0)
for t in order:
    d = cur[t]
    if 'offers' not in d and 'buy' not in d: continue
    if t % every: continue
    st = d.get('state', '')
    ms = re.match(r'bal=(\d+) terr=(\d+) dens=([\d.]+)', st)
    head = f"t={t} " + (f"余额 {ms.group(1)} 领土 {ms.group(2)} 密度 {ms.group(3)}" if ms else st[:60])
    offs = []
    for o in d.get('offers', []):
        fl = ''.join(k for k, f in (('M', o.get('onMe')), ('N', o.get('nearCollapse')), ('B', o.get('bleeding')), ('H', o.get('isCrowdedHard')), ('S', o.get('isDoorSea'))) if f)
        offs.append(f"{nm(o['q'])}:c={o['c']:.0f},need={o['need']:.0f},in={o.get('inAtk', 0):.0f}{',' + fl if fl else ''}")
    print(head + ' | buy=' + str(d.get('buy')) + ' don=' + str(d.get('don')) + ' | ' + ' ; '.join(offs) + (' | ' + ' '.join(d['send']) if d.get('send') else ''))
print('（报价标记：M=对方正在打我 N=nearCollapse B=bleeding H=isCrowdedHard S=隔海门）')
