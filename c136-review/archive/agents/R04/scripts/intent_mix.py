#!/usr/bin/env python3
# intent_mix.py — 影子策略想发的陆攻按「目标类别 × 时段」分账，并和录像里真正落地的出兵对照。
# 用法：python3 scripts/intent_mix.py <局号> [<局号> …] [--win 630,1500,1850,2550,3060]
# 数据：tmp/shadow/<局号>/intents.tsv（shadow.mjs 的意图：t、号、kind、pct、target、troops）、
#       tmp/truth/<局号>/{cmd.tsv,meta.json}（真引擎重放里被执行的指令；sub = atk:<实际目标>:<实际出征的兵>）。
# 口径：
#   目标类别：无主地（编号 ≥ 512）/ 内置 AI（编号 ≥ 真人数 ku）/ 真人（编号 < ku）；捐款、发船另列。
#   「想出」= 影子在决策拍按当时余额算的出兵。每个决策拍都重新下单，所以同一笔会重复计：只用来比较「一条想出多少」，不能和真出的兵相加减。
#   「真出」= 录像里这个时段落地、且真的产生了进攻的陆攻（按落地拍分段、按落地时引擎规整后的实际目标分类）；
#            手续费 = 每条被执行的陆攻付的 余额×12/1024（bal0 − bal1 − 出征兵）；没产生进攻的不扣兵也不收费。
#   每条意图的比例（pct/1024）中位数：看策略一条指令想动用多少余额。
import sys, csv, json, os, statistics as st, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def f(n):
    return f'{n / 10000:.1f}万' if abs(n) >= 10000 else str(int(n))


def one(mid, win):
    tdir = os.path.join(ROOT, 'tmp', 'truth', mid)
    meta = json.load(open(os.path.join(tdir, 'meta.json'), encoding='utf8'))
    ku = meta['info']['ku']
    ours = {int(p) for p in meta['ours']}

    def cls(tgt):
        if tgt >= 512:
            return '无主地'
        return '真人' if tgt < ku else '内置AI'

    def wi(t):
        for k in range(len(win) - 1):
            if win[k] <= t < win[k + 1]:
                return k
        return len(win) - 2

    want = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0, []]))
    ipath = os.path.join(ROOT, 'tmp', 'shadow', mid, 'intents.tsv')
    if not os.path.exists(ipath):
        print(f'# {mid}：没有 tmp/shadow/{mid}/intents.tsv（先跑影子策略）')
        return
    for r in csv.DictReader(open(ipath, encoding='utf8'), delimiter='\t'):
        t = int(r['t'])
        k = wi(t)
        kind = r['kind']
        if kind == 'attack':
            c = cls(int(r['target']))
        elif kind == 'donate':
            c = '捐款'
        else:
            c = '发船'
        w = want[k][c]
        w[0] += 1
        w[1] += int(float(r['troops'] or 0))
        w[2].append(int(r['pct'] or 0))
    real = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0, 0, 0]))
    for r in csv.DictReader(open(os.path.join(tdir, 'cmd.tsv'), encoding='utf8'), delimiter='\t'):
        if int(r['spawnStep']) >= 0 or int(r['id']) != 1 or int(r['p']) not in ours:
            continue
        t = int(r['t'])
        k = wi(t)
        s = r['sub'] or ''
        if s.startswith('atk:'):
            _, tg, v = s.split(':')[:3]
            c = cls(int(tg))
            v = int(v)
            fee = int(r['bal0']) - int(r['bal1']) - v
            x = real[k][c]
            x[0] += 1
            x[1] += v
            x[2] += max(0, fee)
        else:
            real[k]['没产生进攻'][0] += 1
    print(f'# {mid} 影子想发的陆攻 vs 录像里落地的陆攻（按目标类别、按时段）')
    for k in range(len(win) - 1):
        lab = f'[{win[k]},{win[k + 1] if win[k + 1] < 99999 else "末"})'
        parts = []
        for c in ('无主地', '内置AI', '真人'):
            w = want[k].get(c, [0, 0, []])
            r = real[k].get(c, [0, 0, 0, 0])
            med = int(st.median(w[2])) if w[2] else 0
            parts.append(f'{c}：想发 {w[0]} 条（比例中位 {med}/1024，想出合计 {f(w[1])}）→ 落地并出兵 {r[0]} 条 真出 {f(r[1])} 手续费 {f(r[2])}')
        ex = [f'没产生进攻的落地指令 {real[k].get("没产生进攻", [0])[0]} 条']
        for c in ('捐款', '发船'):
            w = want[k].get(c)
            if w:
                ex.append(f'{c} 想发 {w[0]} 条 {f(w[1])}')
        print(f'  {lab} ' + '；'.join(parts) + '；' + '；'.join(ex))


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        sys.exit(1)
    win = [0, 630, 1500, 1850, 2550, 3060, 99999]
    mids = []
    i = 0
    while i < len(a):
        if a[i] == '--win':
            win = [0] + [int(x) for x in a[i + 1].split(',')] + [99999]
            i += 2
        else:
            mids.append(a[i])
            i += 1
    for mid in mids:
        one(mid, win)


main()
