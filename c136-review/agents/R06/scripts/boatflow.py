#!/usr/bin/env python3
"""R06 船账（录像真值）：我方号发出的每条船，带多少兵、交多少手续费、最后靠在谁的岸上。

用法：python3 boatflow.py <matchId> [json]
  json  额外写 out/<id>/boatflow.json（crossmatch.py boats 读它）

口径
  船 = 录像里我方号生效的发船指令（simdigest.boat_rows，按引擎里的船编号配对靠岸 / 消失）。
  手续费 = 发船那一拍余额的 32/1024（3.125%），与船上带多少兵无关。
  小船 = 船上的兵不到发船时余额的 5%（手续费 ÷ 船上兵 > 0.6）；空船 = 千分比 0（引擎补到最少 60 兵）。
  靠岸类别：自己的岸（兵回家）；同队的岸（引擎当移交，兵归对方）；异队我方号的岸（引擎按进攻结算）；
            敌方真人 / 空壳 / 内置 AI / 无主地；无空槽白损（靠岸时没有空的进攻槽，兵直接没了）；
            沉没（海上被打光）；消失（主人阵亡等）；终局还在海上。
  被围 = 发船那一拍影子策略眼里 nb=0 且 neut=0（probe.json 的 tally；没有 tally 的拍记「未知」）。
"""
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import simdigest as SD  # noqa: E402
from r06lib import OUT  # noqa: E402

TB = [(0, 600, '<600'), (600, 1500, '600~1500'), (1500, 3000, '1500~3000'), (3000, 4284, '3000~4284'), (4284, 10 ** 9, '>=4284')]
SB = [(0, 0.05, '<5%'), (0.05, 0.2, '5~20%'), (0.2, 0.5, '20~50%'), (0.5, 9, '>=50%')]


def band(v, bands):
    for a, b, n in bands:
        if a <= v < b:
            return n
    return bands[-1][2]


def wan(n):
    n = float(n)
    if abs(n) >= 1e8:
        return f'{n / 1e8:.2f} 亿'
    if abs(n) >= 1e6:
        return f'{n / 1e4:,.0f} 万'
    if abs(n) >= 1e4:
        return f'{n / 1e4:.1f} 万'
    return f'{n:,.0f}'


def pc(a, b, d=1):
    return f'{100 * a / b:.{d}f}%' if b else '—'


def dest(X, r):
    c, l = r['c'], r['land']
    p = c['p']
    if l is None:
        return {'sunk': '沉没', 'gone': '消失（主人阵亡等）', 'atsea': '终局还在海上'}[r['how']]
    if l['self']:
        return '自己的岸'
    if l['noSlot']:
        return '无空槽白损'
    k = X.cls(p, l['to'], l['t'])
    if k in ('我方号·同队', '队友', '同队AI', '我方号·同队(空壳)', '队友(空壳)'):
        return '同队的岸（移交）'
    if k.startswith('我方号·异队'):
        return '异队我方号的岸'
    if k.startswith('敌方真人'):
        return '敌方真人' + ('（空壳）' if '空壳' in k else '')
    return k


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    mid = sys.argv[1]
    X = SD.Sim(mid)
    rows = SD.boat_rows(X)
    doc = dict(matchId=mid, endT=X.endT, n=len(rows))
    if not rows:
        print(f'{mid}：我方没有发过船')
        if 'json' in sys.argv[2:]:
            json.dump(doc, open(os.path.join(OUT, mid, 'boatflow.json'), 'w'), ensure_ascii=False)
        return
    # 被围：影子 tally 里发船那一拍（就近的决策拍）nb=0 且 neut=0
    boxed = {}
    try:
        sh = SD.shadow_load(X)
        for row in (sh or {}).get('tally') or []:
            boxed[(row['p'], row['t'])] = (row.get('nb', 1) == 0 and row.get('neut', 1) == 0)
    except Exception:
        boxed = {}

    def is_boxed(p, t):
        for dt in range(0, 30, 1):
            k = (p, t - dt)
            if k in boxed:
                return boxed[k]
        return None

    tot = dict(n=0, sent=0, fee=0)
    by_dest = defaultdict(lambda: dict(n=0, sent=0, fee=0, landed=0))
    by_size = defaultdict(lambda: dict(n=0, sent=0, fee=0))
    by_t = defaultdict(lambda: dict(n=0, sent=0, fee=0))
    by_box = defaultdict(lambda: dict(n=0, sent=0, fee=0))
    zero = dict(n=0, sent=0, fee=0)
    big = dict(n=0, sent=0, fee=0, dest=defaultdict(lambda: dict(n=0, sent=0)))
    sea = dict(decay=0, hit=0)
    bots = defaultdict(lambda: dict(n=0, sent=0, fee=0))
    aim_hit = dict(aimHuman=0, aimHumanLandedOnIt=0)
    for r in rows:
        c = r['c']
        p = c['p']
        d = dest(X, r)
        landed = r['land']['troops'] if r['land'] else 0
        for o in (tot, by_dest[d], by_size[band(c['sent'] / max(1, c['B0']), SB)], by_t[band(c['t'], TB)], bots[p]):
            o['n'] += 1
            o['sent'] += c['sent']
            o['fee'] += c['fee']
        by_dest[d]['landed'] += landed
        bx = is_boxed(p, c['t'])
        o = by_box['未知' if bx is None else ('被围' if bx else '不被围')]
        o['n'] += 1
        o['sent'] += c['sent']
        o['fee'] += c['fee']
        if c['pct'] == 0:
            zero['n'] += 1
            zero['sent'] += c['sent']
            zero['fee'] += c['fee']
        if c['sent'] >= 100000:
            big['n'] += 1
            big['sent'] += c['sent']
            big['fee'] += c['fee']
            big['dest'][d]['n'] += 1
            big['dest'][d]['sent'] += c['sent']
        if r['left'] is not None:
            sea['decay'] += c['sent'] - r['decayOnly']
            sea['hit'] += r['hitLoss'] or 0
        tgt = c.get('tgt', -1)
        if 0 <= tgt < X.H and tgt not in X.squad and X.team[tgt] != X.team[p]:
            aim_hit['aimHuman'] += 1
            if r['land'] and not r['land']['self'] and r['land']['to'] == tgt:
                aim_hit['aimHumanLandedOnIt'] += 1
    inc = sum(X.led_sum(p, 'inc') for p in X.squad)
    doc.update(sent=tot['sent'], fee=tot['fee'], inc=inc, dest={k: v for k, v in by_dest.items()}, size={k: v for k, v in by_size.items()}, tband={k: v for k, v in by_t.items()},
               box={k: v for k, v in by_box.items()}, zero=zero, big=dict(n=big['n'], sent=big['sent'], fee=big['fee'], dest={k: v for k, v in big['dest'].items()}), sea=sea, aim=aim_hit,
               bots=len(bots), topBots=[dict(name=X.M.bots[p].name, **v) for p, v in sorted(bots.items(), key=lambda kv: -kv[1]['fee'])[:3]])

    print(f"{mid}：我方发船 {tot['n']} 条（{len(bots)} 个号），船上兵 {wan(tot['sent'])}，手续费 {wan(tot['fee'])}（手续费 ÷ 船上兵 {pc(tot['fee'], tot['sent'])}；÷ 实得利息 {pc(tot['fee'], inc)}）；录像到 t={X.endT}")
    print('  按靠岸：' + '；'.join(f"{k} {v['n']} 条 / 船上 {wan(v['sent'])} / 费 {wan(v['fee'])}" for k, v in sorted(by_dest.items(), key=lambda kv: -kv[1]['n'])))
    print('  按船上兵占余额：' + '；'.join(f"{n} {by_size[n]['n']} 条 / 船上 {wan(by_size[n]['sent'])} / 费 {wan(by_size[n]['fee'])}" for _, _, n in SB if n in by_size))
    print('  按拍：' + '；'.join(f"{n} {by_t[n]['n']} 条 / 船上 {wan(by_t[n]['sent'])} / 费 {wan(by_t[n]['fee'])}" for _, _, n in TB if n in by_t))
    print('  发船时是否被围（影子 nb=0 且 neut=0）：' + '；'.join(f"{k} {v['n']} 条 / 船上 {wan(v['sent'])} / 费 {wan(v['fee'])}" for k, v in by_box.items()))
    print(f"  空船（千分比 0）：{zero['n']} 条、船上 {wan(zero['sent'])}、手续费 {wan(zero['fee'])}；>=10 万兵的大船 {big['n']} 条、{wan(big['sent'])}："
          + '；'.join(f"{k} {v['n']} 条 / {wan(v['sent'])}" for k, v in sorted(big['dest'].items(), key=lambda kv: -kv[1]['sent'])))
    print(f"  海上：自然损耗 {wan(sea['decay'])}、被敌船打掉 {wan(sea['hit'])}；发船时瞄准敌方真人的 {aim_hit['aimHuman']} 条，其中靠上那个人的岸 {aim_hit['aimHumanLandedOnIt']} 条")
    print('  手续费最多的号：' + '；'.join(f"{b['name']} {b['n']} 条 / 船上 {wan(b['sent'])} / 费 {wan(b['fee'])}" for b in doc['topBots']))
    if 'json' in sys.argv[2:]:
        path = os.path.join(OUT, mid, 'boatflow.json')
        json.dump(doc, open(path, 'w'), ensure_ascii=False)
        print(f'写入 {path}')


if __name__ == '__main__':
    main()
