# A030_facts.py — A030 复盘里引用、而通用脚本（game_facts.py / match_facts.py / quota_room.py / shadow_gap.py …）不直接给的数字。
# 全部从 /tmp/c136-r05/truth/A030.json（match_truth.mjs 逐拍重放）、/tmp/c136-r05/work/A030-shadow.json（shadow.mjs --json）
# 和对局包 in_game.log 机械算出。
# 用法：python3 scripts/review_build/A030_facts.py [--sec A,B,…]
import json, bisect, re, sys, math, statistics
from collections import defaultdict, Counter

M = 'A030'
J = json.load(open(f'/tmp/c136-r05/truth/{M}.json'))
P = {p['id']: p for p in J['players']}
sq = {s['p']: s['bot'] for s in J['squad']}
pid = {b: p for p, b in sq.items()}
ev = J['events']
HS, T30, S10, C30 = J['HS'], J['T30'], J['S10'], J['C30']
LAND, H, OUR, END = J['map']['land'], J['humans'], J['ourTeam'], J['endTick']
a = sys.argv[1:]
SEC = set(a[a.index('--sec') + 1].split(',')) if '--sec' in a else None
on = lambda n: SEC is None or n in SEC
k = lambda x: f'{x/1e6:.2f}M' if abs(x) >= 1e6 else f'{x/1000:.0f}k' if abs(x) >= 1000 else str(int(x))


def nm(p):
    if p in sq:
        return sq[p]
    if p in P:
        return P[p]['name'][:16] + f"(#{p},T{P[p]['team']})"
    return '中立' if p == 512 else f'机器人#{p}'


def at(p, t):
    s = S10[str(p)]
    i = bisect.bisect_right(s['t'], t) - 1
    return (s['terr'][i], s['bal'][i]) if i >= 0 else (0, 0)


def hs(p, t):
    i = bisect.bisect_right(HS['t'], t) - 1
    return HS['terr'][i][p], HS['bal'][i][p]


if on('A'):
    print('§A 非我方号的捐兵（allDon：[拍, 捐出方, 受赠方, 到账, 税]）：按队、按 600 拍、按「捐出方→受赠方」')
    D = [d for d in J['allDon'] if d[1] not in sq]
    byteam = Counter(P[d[1]]['team'] for d in D)
    print(f'   {len(D)} 笔 到账 {k(sum(d[3] for d in D))} 税 {k(sum(d[4] for d in D))}｜按捐出方的队：' + '、'.join(f'T{t} {n} 笔' for t, n in sorted(byteam.items()))
          + f'｜本队路人队友捐出 {sum(1 for d in D if P[d[1]]["team"] == OUR)} 笔')
    w = defaultdict(lambda: [0, 0, 0, 0])
    for t, p, q, got, fee in J['allDon']:
        i = 0 if p in sq else 2
        w[t // 600 * 600][i] += 1; w[t // 600 * 600][i + 1] += got
    print('   每 600 拍（编队 笔/到账 ｜ 敌队 笔/到账）：' + '；'.join(f'{t}: {v[0]}/{k(v[1])}｜{v[2]}/{k(v[3])}' for t, v in sorted(w.items())))
    rc = defaultdict(lambda: [0, 0, 99999])
    for t, p, q, got, fee in D:
        rc[q][0] += 1; rc[q][1] += got; rc[q][2] = min(rc[q][2], t)
    print('   敌队受赠方：' + '；'.join(f'{nm(q)} {v[0]} 笔 {k(v[1])}（首笔 t={v[2]}）' for q, v in sorted(rc.items(), key=lambda z: -z[1][1])[:6]))
    pr = defaultdict(lambda: [0, 0, 0, 99999, 0])
    for t, p, q, got, fee in D:
        v = pr[(p, q)]; v[0] += 1; v[1] += got; v[2] += fee; v[3] = min(v[3], t); v[4] = max(v[4], t)
    for (p, q), v in sorted(pr.items(), key=lambda z: -z[1][1])[:10]:
        print(f'     {nm(p)} → {nm(q)}: {v[0]} 笔 到账 {k(v[1])} 税 {k(v[2])}｜{v[3]}–{v[4]} 拍')
    kill = {35: '打 zero_7、ryan_m、noah88', 25: '打 riku_x、leo_tx、zexos1、noah88、sora_w', 36: '打 kaito9、talon5', 0: '打 sora_w', 22: '打 riku_x、sora_w'}
    for q, what in kill.items():
        pre = sum(d[3] for d in D if d[2] == q and d[0] < 4284)
        print(f'     {nm(q)}（{what}）：全程收到 {k(rc[q][1])}，其中 4284 拍前 {k(pre)}')

if on('B'):
    print('§B leo_tx 1500–1764 拍：影子逐决策拍想发的指令、录像里落地的指令、客户端自报的累计发令数；Nestle 的地归了谁')
    S = json.load(open(f'/tmp/c136-r05/work/{M}-shadow.json'))
    rows = [r for r in S['ticks'] if r['bot'] == 'leo_tx' and 1495 <= r['t'] <= 1800]
    tg = Counter((c['k'], nm(c['q']), c['pct']) for r in rows for c in r['cmds'])
    tr = [c.get('troops', 0) for r in rows for c in r['cmds']]
    exits = Counter([x for x in r['sig'].split(' > ') if x.startswith('buyLand:')][-1] for r in rows if r['cmds'])
    print(f'   影子：{len(rows)} 个决策拍（{rows[0]["t"]}–{rows[-1]["t"]}）各 1 条：' + '、'.join(f'{a_} → {b} pct {c}×{n}' for (a_, b, c), n in tg.items())
          + f'｜每条 {k(min(tr))}–{k(max(tr))}，合计 {k(sum(tr))}｜出口 ' + '、'.join(f'{x}×{n}' for x, n in exits.items()))
    p = pid['leo_tx']
    ex = [e for e in ev if e.get('p') == p and e['type'] in ('attack', 'boat') and 1100 <= e['t'] <= 1800]
    print('   录像：' + '；'.join(f't={e["t"]} {e["type"]} → {nm(e["q"])} pct {e["pct"]} {"落地 " + k(e.get("troops", 0)) if e["ok"] else "落空"}' for e in ex))
    cm = {}
    for ln in open(f'/agent/repos/c136-data/bundles/{M}/in_game.log', encoding='utf-8'):
        m = re.search(r'\[leo_tx\] \[HL-TICK\] t=(\d+) terr=(\d+).*? bal=(\d+).*? nb=(\d+) .*?cmds=(\d+)', ln)
        if m:
            cm[int(m.group(1))] = (int(m.group(5)), int(m.group(2)), int(m.group(3)), int(m.group(4)))
    print('   客户端自报（HL-TICK）：' + '；'.join(f't={t} cmds={cm[t][0]} 地 {cm[t][1]} 兵 {k(cm[t][2])} 邻居 {cm[t][3]}' for t in sorted(cm) if 1400 <= t <= 1900))
    L0, B0 = at(p, 1500)
    nL, nB = hs(17, 1500)
    print(f'   1500 拍：leo_tx {L0} 格/{k(B0)}（密 {B0/L0:.0f}）；Nestle {nL} 格/{k(nB)}（密 {nB/max(1,nL):.0f}）；leo_tx 的边界上 Nestle 占 {[c for c in [C30[str(p)]] ][0]["eh"][bisect.bisect_right(C30[str(p)]["t"], 1500) - 1]} 格（C30 eh）')
    tk = defaultdict(int)
    for w_, x, v, n in J['pairAll']:
        if v == 17:
            tk[x] += n
    print(f'   Nestle 阵亡 {P[17]["deathT"]}，被拿走 {sum(tk.values())} 格：' + '、'.join(f'{nm(x)} {n}' for x, n in sorted(tk.items(), key=lambda z: -z[1])))
    print('   其后 leo_tx：' + '；'.join(f't={t} {at(p, t)[0]} 格/{k(at(p, t)[1])}（密 {at(p, t)[1]/max(1, at(p, t)[0]):.0f}）' for t in (1800, 2100, 2400, 3000, 3200)))

if on('C'):
    print('§C 指令落地的拍号：录像里我方号的陆攻/出船/捐兵执行拍 mod 7；调度日志 → 落地的间隔')
    c = Counter(e['t'] % 7 for e in ev if e['type'] in ('attack', 'boat', 'donate') and e.get('p') in sq)
    print(f'   执行拍 mod 7：{dict(c)}（共 {sum(c.values())} 条）')
    lag = [d['exec']['t'] - d['t'] for d in J['dispatch'] if d.get('exec')]
    print(f'   已落地的 {len(lag)} 条调度：日志拍 → 落地拍 间隔 中位 {statistics.median(lag):.0f}、最大 {max(lag)}')
    late = [d for d in J['dispatch'] if d.get('exec') and d['t'] < 3213 <= d['exec']['t']]
    print(f'   日志拍 < 3213 ≤ 落地拍 的 {len(late)} 条：' + '；'.join(f'{d["bot"]} 日志 {d["t"]} → 落地 {d["exec"]["t"]}' for d in late))

if on('D'):
    print('§D 3213 拍换算之后的集中捐兵：每个捐出方 3213–3300 拍的笔数、捐前/捐后 地、兵、密度；其后第一条 ≥100k 的来袭（谁、多少、当时它的兵）；阵亡拍')
    for b in ('ryan_m', 'leo_tx', 'noah88', 'zexos1', 'talon5', 'zero_7'):
        p = pid[b]
        ds = [e for e in ev if e['type'] == 'donate' and e.get('ok') and e['p'] == p and 3213 <= e['t'] <= 3300]
        if not ds:
            print(f'   {b}: 3213–3300 拍没有捐兵'); continue
        L0, B0 = ds[0]['L0'], ds[0]['B0']
        L1, B1 = at(p, 3310)
        hit = next((e for e in ev if e['type'] == 'attack' and e.get('ok') and e.get('q') == p and e['p'] < H and e['p'] not in sq and e.get('troops', 0) >= 100000 and e['t'] > 3213), None)
        span = ds[-1]['t'] - ds[0]['t']
        print(f'   {b}: {len(ds)} 笔（{ds[0]["t"]}–{ds[-1]["t"]}，跨 {span} 拍）到账 {k(sum(e["got"] for e in ds))} 税 {k(sum(e["fee"] for e in ds))}｜捐前 {L0} 格/{k(B0)}（密 {B0/max(1,L0):.0f}）→ 3310 拍 {L1} 格/{k(B1)}（密 {B1/max(1,L1):.0f}，少了 {100*(B0-B1)/max(1,B0):.0f}%）'
              + (f'｜第一条 ≥100k 的来袭 t={hit["t"]} {nm(hit["p"])} {k(hit["troops"])}，当时它 {hit["tL"]} 格/{k(hit["tB"])}（密 {hit["tB"]/max(1,hit["tL"]):.0f}）' if hit else '｜没有 ≥100k 的来袭')
              + f'｜阵亡 {P[p]["deathT"]}')
    tot = [e for e in ev if e['type'] == 'donate' and e.get('ok') and e['p'] in sq and 3213 <= e['t'] <= 3283]
    print(f'   3213–3283 拍合计 {len(tot)} 笔 到账 {k(sum(e["got"] for e in tot))} 税 {k(sum(e["fee"] for e in tot))}；其中给 sora_w {sum(1 for e in tot if sq[e["q"]] == "sora_w")} 笔 {k(sum(e["got"] for e in tot if sq[e["q"]] == "sora_w"))}')
    dens = []
    for t in (3300, 3600, 3900):
        mine = [at(pid[b], t)[1] / max(1, at(pid[b], t)[0]) for b in ('ryan_m', 'leo_tx', 'noah88', 'zexos1', 'talon5')]
        en = sorted(hs(q, t)[1] / max(1, hs(q, t)[0]) for q in P if q < H and q not in sq and P[q]['team'] != OUR and hs(q, t)[0] >= 500)
        dens.append(f'{t}: 五个后排号密度 ' + '/'.join(f'{d:.0f}' for d in mine) + f'，敌方真人密度中位 {statistics.median(en):.0f}（{len(en)} 人）')
    print('   ' + '；'.join(dens))

if on('F'):
    print('§F 本队路人 Player 861、Tikiz 被吃的那两段：它们自己、吃它们的敌人、相邻我方号的 地/兵（HS 每 300 拍；S10）')
    for q, eaters, mates, ts in ((16, (25, 23, 22), ('riku_x', 'zero_7', 'ryan_m', 'leo_tx'), (2100, 2400, 2700, 3000, 3300)),
                                 (40, (22, 0, 30), ('sora_w', 'riku_x', 'leo_tx', 'zexos1'), (2400, 2700, 3000, 3300, 3600))):
        print(f'   {nm(q)} 峰值 {P[q]["peakTerr"]}@{P[q]["peakT"]} 阵亡 {P[q]["deathT"]} 离场 {P[q]["leftT"]}')
        for t in ts:
            print(f'      t={t}: 它 {hs(q, t)[0]}/{k(hs(q, t)[1])}｜' + '；'.join(f'{nm(x)} {hs(x, t)[0]}/{k(hs(x, t)[1])}（密 {hs(x, t)[1]/max(1, hs(x, t)[0]):.0f}）' for x in eaters)
                  + '｜' + '；'.join(f'{b} {at(pid[b], t)[0]}/{k(at(pid[b], t)[1])}' for b in mates))
        hit = [e for e in ev if False]
    print('   Troll(#25) 每 300 拍 地/兵/密度：' + '；'.join(f'{t}: {hs(25, t)[0]}/{k(hs(25, t)[1])}/{hs(25, t)[1]/max(1, hs(25, t)[0]):.0f}' for t in range(2100, 5401, 300)))
    tk = defaultdict(int)
    for w_, x, v, n in J['pairAll']:
        if x == 25:
            tk[v] += n
    print('   Troll 全程拿地：' + '、'.join(f'{nm(v)} {n}' for v, n in sorted(tk.items(), key=lambda z: -z[1])[:10]))

if on('G'):
    print('§G sora_w 打真人的每一轮（相邻两条 ≤21 拍归一轮）：出兵、对方当时的密度、自己的密度；按目标合计的每格花费（J.pairs）')
    atk = sorted([e for e in ev if e['type'] == 'attack' and e.get('ok') and e['p'] == pid['sora_w'] and e['q'] < H and e['q'] not in sq], key=lambda e: (e['q'], e['t']))
    vol = []
    for e in atk:
        if vol and vol[-1]['q'] == e['q'] and e['t'] - vol[-1]['t1'] <= 21:
            vol[-1]['t1'] = e['t']; vol[-1]['n'] += 1; vol[-1]['sent'] += e['troops']
        else:
            vol.append({'q': e['q'], 't0': e['t'], 't1': e['t'], 'n': 1, 'sent': e['troops'], 'B0': e['B0'], 'L0': e['L0'], 'tB': e['tB'], 'tL': e['tL']})
    for v in sorted(vol, key=lambda v: v['t0']):
        if v['sent'] < 150000:
            continue
        print(f'     {v["t0"]}–{v["t1"]} → {nm(v["q"])} {v["n"]} 条 {k(v["sent"])}｜我 {v["L0"]} 格/{k(v["B0"])}（密 {v["B0"]/max(1,v["L0"]):.0f}）对方 {v["tL"]} 格/{k(v["tB"])}（密 {v["tB"]/max(1,v["tL"]):.0f}）')
    for x in sorted([x for x in J['pairs'] if x['a'] == pid['sora_w'] and x['b'] < H and x['b'] not in sq], key=lambda x: -x['sent']):
        print(f'     对 {nm(x["b"])}：{x["n"]} 条 {k(x["sent"])} 拿 {x["tiles"]} 格 → 每格 {x["sent"]/max(1,x["tiles"]):.0f} 兵，打掉对方存兵 {k(x["balDmg"])}')
    print('   sora_w 每 300 拍 地/兵/密度：' + '；'.join(f'{t}: {at(pid["sora_w"], t)[0]}/{k(at(pid["sora_w"], t)[1])}/{at(pid["sora_w"], t)[1]/max(1, at(pid["sora_w"], t)[0]):.0f}' for t in range(3000, 5201, 300)))

if on('H'):
    print('§H 选点期：后端求解次数、每次求解十个点的质心、相邻两次质心的位移；全场出生指令里我方号占多少（A030-cmds.tsv）')
    sol = []
    for ln in open(f'/agent/repos/c136-data/bundles/{M}/in_game.log', encoding='utf-8'):
        if 'BACKEND-SPAWN-COORD' in ln and 'Solved' in ln:
            pts = [(int(x), int(y)) for x, y in re.findall(r'->\((\d+),(\d+)\)', ln)]
            ms = re.search(r'minSep=(\d+)px', ln)
            if pts:
                sol.append((sum(x for x, _ in pts) / len(pts), sum(y for _, y in pts) / len(pts), int(ms.group(1)) if ms else -1))
    mv = [math.hypot(sol[i][0] - sol[i - 1][0], sol[i][1] - sol[i - 1][1]) for i in range(1, len(sol))]
    print(f'   后端求解 {len(sol)} 次｜minSep {sol[0][2]}→{sol[-1][2]} px｜质心位移 ≥60 px 的 {sum(1 for d in mv if d >= 60)} 次、≥150 px 的 {sum(1 for d in mv if d >= 150)} 次、最大 {max(mv):.0f} px')
    print('   质心轨迹：' + ' → '.join(f'({x:.0f},{y:.0f})' for x, y, _ in sol[::4]) + f' → 终 ({sol[-1][0]:.0f},{sol[-1][1]:.0f})')
    ours = other = 0
    try:
        for ln in open(f'/tmp/c136-r05/work/{M}-cmds.tsv'):
            f = ln.rstrip('\n').split('\t')
            if f[0] == 'tick' or f[2] != 'spawn':
                continue
            if int(f[3]) in sq:
                ours += 1
            else:
                other += 1
        print(f'   出生指令：我方号 {ours} 条（每号 {ours/len(sq):.0f}），其他真人 {other} 条（{H - len(sq)} 人）')
    except FileNotFoundError:
        print('   （缺 A030-cmds.tsv：先跑 replay_cmds.mjs A030 --out /tmp/c136-r05/work/A030-cmds.tsv）')
    sp = {b: P[p]['spawn'] for p, b in sq.items()}
    cx = sum(v[0] for v in sp.values()) / len(sp); cy = sum(v[1] for v in sp.values()) / len(sp)
    print(f'   最终十个点质心 ({cx:.0f},{cy:.0f})，最远 {max(math.hypot(v[0]-cx, v[1]-cy) for v in sp.values()):.0f} px；地图 {J["map"]["W"] if "W" in J["map"] else "?"}×{J["map"].get("H", "?")}')
    inner = {b: min(math.hypot(P[q]['spawn'][0] - v[0], P[q]['spawn'][1] - v[1]) for q in P if q not in sq and q < H and P[q]['spawn'] and P[q]['spawn'][0] >= 0 and P[q]['team'] != OUR) for b, v in sp.items()}
    print('   各号到最近敌方真人出生点：' + '、'.join(f'{b} {d:.0f}' for b, d in sorted(inner.items(), key=lambda z: z[1])))

if on('I'):
    print('§I 被围的号：第一次被围的拍（C30：敌方真人/离场敌人/机器人/中立 邻格全为 0）、当时的地、其后 地 不变的拍数；1800–3200 拍每 200 拍的存兵与密度')
    for b in ('ryan_m', 'talon5', 'noah88', 'zexos1', 'leo_tx', 'alex_k'):
        p = pid[b]
        c = C30[str(p)]
        runs, cur = [], None
        for i, t in enumerate(c['t']):
            boxed = t >= 600 and c['eh'][i] == 0 and c['el'][i] == 0 and c['bot'][i] == 0 and c['neut'][i] == 0 and at(p, t)[0] > 0
            if boxed:
                cur = [t, t] if cur is None else [cur[0], t]
            elif cur is not None:
                runs.append(cur); cur = None
        if cur is not None:
            runs.append(cur)
        t0, t1 = max(runs, key=lambda r: r[1] - r[0]) if runs else (0, 0)
        L0 = at(p, t0)[0] if t0 else 0
        print(f'   {b}: 最长的一段被围 {t0}–{t1}（{t1 - t0} 拍）当时 {L0} 格｜' + '；'.join(f'{t}: {k(at(p, t)[1])}/密 {at(p, t)[1]/max(1, at(p, t)[0]):.0f}' for t in range(1800, 3201, 200)))
    tot = defaultdict(int)
    for t in range(1800, 3201, 200):
        tb = sum(at(pid[b], t)[1] for b in sq.values() if b != 'alex_k')
        bb = sum(at(pid[b], t)[1] for b in ('ryan_m', 'talon5', 'noah88', 'zexos1', 'leo_tx'))
        tot[t] = (bb, tb)
    print('   五个被围的号合计存兵 ÷ 编队：' + '；'.join(f'{t}: {k(v[0])}/{k(v[1])}＝{100*v[0]/max(1,v[1]):.0f}%' for t, v in tot.items()))
