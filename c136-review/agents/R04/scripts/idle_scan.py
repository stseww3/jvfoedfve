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


def main():
    mid = sys.argv[1]
    sdir = os.path.join(ROOT, 'tmp', 'shadow', mid)
    rows = collections.defaultdict(list)
    with open(os.path.join(sdir, 'rows.tsv'), encoding='utf8') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            rows[r['bot']].append({k: (v if k == 'bot' else int(v)) for k, v in r.items()})
    check = json.load(open(os.path.join(sdir, 'check.json')))
    lock = {b['bot']: b for b in check['bots']}
    print(f'# {mid} 该动没动的时段（影子策略 {check["ver"]} 的逐行动拍记录；持续拍数 = 行动拍数 × 5）')
    print('号        贴弱AI不出手(底线>余额)            封死          封死且无海岸     顶到硬上限      锁 isNoFullSend 的拍 / 之后被拦的出兵')
    tot = collections.Counter()
    for b, rs in rows.items():
        A = [r for r in rs if r['nAIweak'] > 0 and r['intents'] == 0 and r['floorAI'] >= 0 and r['floorAI'] > r['bal'] and r['t'] >= 300]
        Apre = [r for r in A if r['t'] < 1500]
        Bx = [r for r in rs if r['nb'] == 0 and r['neut'] == 0 and r['t'] >= 300]
        Cx = [r for r in Bx if r['coast'] == 0]
        Dx = [r for r in rs if r['terr'] > 0 and r['bal'] >= 149.5 * r['terr']]
        land = max((r['weakLand'] for r in A), default=0)
        lk = lock.get(b, {})
        seg = lambda v: f'{5*len(v):5d} 拍' + (f'（{v[0]["t"]}~{v[-1]["t"]}）' if v else '')
        print(f'{b:8s} {seg(A):22s} 其中 t<1500 {5*len(Apre):4d} 拍，弱AI地最多 {land:5d}   {seg(Bx):20s} {seg(Cx):20s} {seg(Dx):20s} {lk.get("lockAt")} / {len(lk.get("blocked", []))} 次 {sum(x[2] for x in lk.get("blocked", []))} 兵')
        tot['A'] += 5 * len(A); tot['B'] += 5 * len(Bx); tot['C'] += 5 * len(Cx); tot['D'] += 5 * len(Dx)
    print(f'合计（号·拍）：贴弱AI不出手 {tot["A"]}；封死 {tot["B"]}；封死且无海岸 {tot["C"]}；顶到硬上限 {tot["D"]}')


if __name__ == '__main__':
    main()
