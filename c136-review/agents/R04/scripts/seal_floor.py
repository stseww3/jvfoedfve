#!/usr/bin/env python3
# seal_floor.py — 被封住的号（陆上邻居 0、无主地 0）能不能发船：按「发船保底线」把号·行动拍分档。
# 背景（Vb：Policy.idleBoats L5022~5043 → General.boatOut L999~1015；Va / Vc / c110 的同名函数行号不同，公式一样时才可比）：
#   被封住的号走 idleBoats 的「封死」分支，搜水范围 2500；保底线 keepFloor = 68×领土（没有「接敌兄弟」时）或 92×领土（有，且本号密度要 ≥115）；
#   boatOut：可装 = boatFrac×(余额 − 保底线)，目标是内置 AI 或真人时最小船量 = feeK×船手续费 = 4×(32/1024)×余额 = 余额/8。
#   boatFrac 取 max(原值, 0.24)，实测原值 0.5 → 0.5×(余额 − 68×地) ≥ 余额/8  ⇔  密度 ≥ 90.7（没有接敌兄弟）；
#   有接敌兄弟时 0.5×(余额 − 92×地) ≥ 余额/8 ⇔ 密度 ≥ 122.7。目标是无主地且有船费时最小船量只有 60，余额 > 保底线就能发。
# 本脚本只按密度分档，不重放 searchWater（有没有落点、落点是谁看 shadow.mjs --at 的 [idleBoats] 段）。
# 用法：python3 scripts/seal_floor.py <局号> [<局号> …] [--from t0] [--to t1] [--list]
# 数据：tmp/shadow/<局号>/rows.tsv（shadow_all.sh 或 shadow_chunk.sh + shadow_merge.py 产出；要 28 列的新版）、
#       tmp/truth/<局号>/{cmd.tsv,meta.json}（我方号的发船指令）
# 输出（每局）：封住的号·行动拍总数；没有海岸的；有海岸的按密度 <68 / 68~90.7 / ≥90.7 分档；全队同时封住的行动拍数；
#       封住期间我方发的船（条 / 载兵）；--list 再按号列出封住的拍段和各档拍数。
import sys, os, csv, json, collections
sys.dont_write_bytecode = True
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
K_FLOOR = 68.0
K_SHIP = 68.0 / (1 - 0.25)      # 0.5×(B − 68L) ≥ B/8


def w(n):
    return f'{n / 1e4:.1f}万'


def main():
    a = sys.argv[1:]
    lst = '--list' in a
    t0 = int(a[a.index('--from') + 1]) if '--from' in a else 0
    t1 = int(a[a.index('--to') + 1]) if '--to' in a else 10 ** 9
    skip = set()
    for k in ('--from', '--to'):
        if k in a:
            skip.add(a.index(k)); skip.add(a.index(k) + 1)
    mids = [x for i, x in enumerate(a) if i not in skip and not x.startswith('--')]
    tot = collections.Counter()
    for mid in mids:
        rp = os.path.join(ROOT, 'tmp', 'shadow', mid, 'rows.tsv')
        if not os.path.exists(rp):
            print(f'{mid}：没有 tmp/shadow/{mid}/rows.tsv（先跑影子策略）')
            continue
        meta = json.load(open(os.path.join(ROOT, 'tmp', 'truth', mid, 'meta.json')))
        nm2p = {v.replace('[APEX] ', ''): int(k) for k, v in meta['ours'].items()}
        per = collections.defaultdict(collections.Counter)
        span = {}
        sealed_at = collections.defaultdict(set)      # 拍 -> 封住的号
        alive_at = collections.Counter()
        dens_at = {}
        with open(rp, encoding='utf8') as f:
            rd = csv.DictReader(f, delimiter='\t')
            if 'coast' not in rd.fieldnames:
                print(f'{mid}：rows.tsv 是旧版（没有 coast 列），要重跑影子策略')
                continue
            for r in rd:
                t = int(r['t'])
                if not (t0 <= t <= t1):
                    continue
                terr, bal = int(r['terr']), int(r['bal'])
                if terr <= 0:
                    continue
                b = r['bot']
                alive_at[t] += 1
                if int(r['nb']) != 0 or int(r['neut']) != 0:
                    continue
                sealed_at[t].add(b)
                d = bal / terr
                dens_at[(t, b)] = d
                c = per[b]
                c['sealed'] += 1
                if b not in span:
                    span[b] = [t, t]
                span[b][1] = t
                if int(r['coast']) <= 0:
                    c['nocoast'] += 1
                    if d >= 100:
                        c['nocoast100'] += 1
                elif d < K_FLOOR:
                    c['lt68'] += 1
                elif d < K_SHIP:
                    c['mid'] += 1
                else:
                    c['ok'] += 1
        S = collections.Counter()
        for c in per.values():
            S.update(c)
        all_sealed = sum(1 for t, s in sealed_at.items() if len(s) == alive_at[t] and alive_at[t] >= 2)
        # 封住期间发的船
        boats = []
        with open(os.path.join(ROOT, 'tmp', 'truth', mid, 'cmd.tsv'), encoding='utf8') as f:
            for r in csv.DictReader(f, delimiter='\t'):
                if not r['sub'] or not r['sub'].startswith('boat:'):
                    continue
                p = int(r['p'])
                nm = [n for n, q in nm2p.items() if q == p]
                if not nm:
                    continue
                t = int(r['t'])
                tt = t - t % 5
                near = [x for x in (tt, tt - 5, tt - 10, tt - 15, tt - 20) if nm[0] in sealed_at.get(x, ())]
                if near and t0 <= t <= t1:
                    boats.append((t, nm[0], int(r['sub'].split(':')[2])))
        n = S['sealed']
        if n == 0:
            print(f'{mid}：没有被封住的号·行动拍')
            continue
        coast = S['lt68'] + S['mid'] + S['ok']
        print(f'{mid}：被封住（陆上邻居 0、无主地 0）的号·行动拍 {n}（{len(per)} 个号）；没有海岸的 {S["nocoast"]}（{S["nocoast"] / n:.0%}，其中密度 ≥100 的 {S["nocoast100"]}）；'
              f'有海岸的 {coast}：密度 <68（低于保底线，发不了船）{S["lt68"]}（{S["lt68"] / max(1, coast):.0%}），68~90.7（过了保底线但不够打 AI/真人的最小船量）{S["mid"]}（{S["mid"] / max(1, coast):.0%}），'
              f'≥90.7 {S["ok"]}（{S["ok"] / max(1, coast):.0%}）；全队活着的号同时被封住的行动拍 {all_sealed}；封住期间发的船 {len(boats)} 条 {w(sum(b[2] for b in boats))} 兵')
        if lst:
            for b in sorted(per, key=lambda x: span[x][0]):
                c = per[b]
                print(f'    {b:8s} 封住 {c["sealed"]} 拍（{span[b][0]}~{span[b][1]}）：没有海岸 {c["nocoast"]}，密度 <68 {c["lt68"]}，68~90.7 {c["mid"]}，≥90.7 {c["ok"]}')
            for t, b, v in boats:
                print(f'    船：拍 {t} {b} 载 {w(v)}')
        for k in ('sealed', 'nocoast', 'lt68', 'mid', 'ok'):
            tot[k] += S[k]
        tot['boats'] += len(boats); tot['games'] += 1; tot['all'] += all_sealed
    if tot['games'] > 1:
        coast = tot['lt68'] + tot['mid'] + tot['ok']
        print(f'合计 {tot["games"]} 局：封住 {tot["sealed"]} 个号·行动拍；没有海岸 {tot["nocoast"]}；有海岸 {coast}（密度 <68 {tot["lt68"]}，68~90.7 {tot["mid"]}，≥90.7 {tot["ok"]}）；全队同时封住 {tot["all"]} 拍；封住期间发船 {tot["boats"]} 条')


if __name__ == '__main__':
    main()
