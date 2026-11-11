#!/usr/bin/env python3
# idle_scan.py — 用影子策略的逐行动拍记录（tmp/shadow/<局号>/rows.tsv）统计「该动没动」的时段。
# 用法：python3 scripts/idle_scan.py <局号>
# 每个号给出四类拍数（每 5 拍一个行动拍，所以 行动拍数×5 ≈ 持续拍数）：
#   A 贴着「兵比地少」的内置 AI 却没出手，且原因是底线高于余额（核心期前是 winFloor，核心期是 safeAt 封顶值）
#   B 封死（没有任何非队友邻居、没有无主地）
#   C 封死且一格海岸都没有（船也发不出去，只能靠捐款）
#   D 余额顶到 150×领土 的硬上限（利息归零）
# 另给：isNoFullSend 锁上的拍号（check.json）、开局到 630/1500 的领土。
import sys, os, csv, json, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


INT_COLS = ('t', 'terr', 'bal', 'nb', 'nAI', 'nAIweak', 'weakLand', 'nHum', 'neut', 'coast', 'intents', 'floorAI', 'nfs', 'atkOut')


def main():
    mid = sys.argv[1]
    sdir = os.path.join(ROOT, 'tmp', 'shadow', mid)
    rows = collections.defaultdict(list)
    with open(os.path.join(sdir, 'rows.tsv'), encoding='utf8') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            # 后加的几列（bind/sbRef/gate/gateAI…）是文字，只把整数列转成整数
            rows[r['bot']].append({k: (int(v) if k in INT_COLS else v) for k, v in r.items()})
    check = json.load(open(os.path.join(sdir, 'check.json')))
    lock = {b['bot']: b for b in check['bots']}
    print(f'# {mid} 该动没动的时段（影子策略 {check["ver"]} 的逐行动拍记录；持续拍数 = 行动拍数 × 5）')
    print('号        贴弱AI不出手(底线>余额)            封死          封死且无海岸     顶到硬上限      锁 isNoFullSend 的拍 / 之后被拦的出兵')
    tot = collections.Counter()
    for b, rs in rows.items():
        A = [r for r in rs if r['nAIweak'] > 0 and r['intents'] == 0 and r['floorAI'] >= 0 and r['floorAI'] > r['bal'] and r['t'] >= 300]
        Apre = [r for r in A if r['t'] < 1500]
        # 领土清零后（号还挂着船没出局）的行不算封死
        Bx = [r for r in rs if r['terr'] > 0 and r['nb'] == 0 and r['neut'] == 0 and r['t'] >= 300]
        Cx = [r for r in Bx if r['coast'] == 0]
        Dx = [r for r in rs if r['terr'] > 0 and r['bal'] >= 149.5 * r['terr']]
        land = max((r['weakLand'] for r in A), default=0)
        lk = lock.get(b, {})
        seg = lambda v: f'{5*len(v):5d} 拍' + (f'（{v[0]["t"]}~{v[-1]["t"]}）' if v else '')
        print(f'{b:8s} {seg(A):22s} 其中 t<1500 {5*len(Apre):4d} 拍，弱AI地最多 {land:5d}   {seg(Bx):20s} {seg(Cx):20s} {seg(Dx):20s} {lk.get("lockAt")} / {len(lk.get("blocked", []))} 次 {sum(x[2] for x in lk.get("blocked", []))} 兵')
        tot['A'] += 5 * len(A); tot['B'] += 5 * len(Bx); tot['C'] += 5 * len(Cx); tot['D'] += 5 * len(Dx)
    print(f'合计（号·拍）：贴弱AI不出手 {tot["A"]}；封死 {tot["B"]}；封死且无海岸 {tot["C"]}；顶到硬上限 {tot["D"]}')
    print('封死区间（连续 ≥50 拍的段）：')
    for b, rs in rows.items():
        iv = []
        cur = None
        for r in rs:
            bx = r['terr'] > 0 and r['nb'] == 0 and r['neut'] == 0 and r['t'] >= 300
            if bx and cur is None:
                cur = [r['t'], r['t']]
            elif bx:
                cur[1] = r['t']
            elif cur is not None:
                iv.append(cur); cur = None
        if cur:
            iv.append(cur)
        print(f'  {b:8s} ' + '，'.join(f'{x[0]}~{x[1]}' for x in iv if x[1] - x[0] >= 50))
    ticks = [630, 1080, 1530, 2070, 2520, 2700, 3060, 3600, 4140, 4500, 4860, 5220, 5760, 6030]
    print('各时刻的号数（有真人邻居 / 只有内置AI或无主地 / 封死 / 已无领土）：')
    for t in ticks:
        c = collections.Counter()
        for b, rs in rows.items():
            r = min(rs, key=lambda x: abs(x['t'] - t))
            if abs(r['t'] - t) > 10 or r['terr'] <= 0:
                c['dead'] += 1
            elif r['nHum'] > 0:
                c['hum'] += 1
            elif r['nb'] == 0 and r['neut'] == 0:
                c['boxed'] += 1
            else:
                c['ai'] += 1
        print(f'  拍 {t}: {c["hum"]} / {c["ai"]} / {c["boxed"]} / {c["dead"]}')


if __name__ == '__main__':
    main()
